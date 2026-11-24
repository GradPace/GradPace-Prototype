import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import SettingsTab from './SettingsTab'
import { getSettings, updateSettings, type SiteSettings } from '../../lib/api/admin'
import { ApiError } from '../../lib/api/api'

vi.mock('../../lib/api/admin', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/api/admin')>()),
  getSettings: vi.fn(),
  updateSettings: vi.fn(),
}))

// As a fresh database returns them: the row exists, nobody has changed it.
const DEFAULTS: SiteSettings = {
  require_email_verification: true,
  updated_at: '2026-11-20T10:00:00Z',
  updated_by: null,
}
const TURNED_OFF: SiteSettings = {
  require_email_verification: false,
  updated_at: '2026-11-24T15:30:00Z',
  updated_by: 'admin@example.com',
}

function toggle() {
  return screen.getByRole('switch', { name: 'Require email verification' })
}

async function renderTab(settings: SiteSettings = DEFAULTS) {
  vi.mocked(getSettings).mockResolvedValue(settings)
  render(<SettingsTab />)
  await screen.findByRole('switch')
}

describe('SettingsTab', () => {
  afterEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('shows the current setting and what it does', async () => {
    await renderTab()

    expect(toggle()).toHaveAttribute('aria-checked', 'true')
    expect(screen.getByText(/confirm their email before reaching their profile/i)).toBeInTheDocument()
    expect(screen.getByText(/doesn't change anyone's verified status/i)).toBeInTheDocument()
  })

  it('hides "last changed" until someone has changed it', async () => {
    await renderTab()

    expect(screen.queryByText(/last changed/i)).not.toBeInTheDocument()
  })

  it('asks before turning verification off, and cancelling sends nothing', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const user = userEvent.setup()
    await renderTab()

    await user.click(toggle())

    expect(confirm).toHaveBeenCalled()
    expect(updateSettings).not.toHaveBeenCalled()
    expect(toggle()).toHaveAttribute('aria-checked', 'true')
  })

  it('saves when confirmed and shows who changed it', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(updateSettings).mockResolvedValue(TURNED_OFF)
    const user = userEvent.setup()
    await renderTab()

    await user.click(toggle())

    expect(updateSettings).toHaveBeenCalledWith({ require_email_verification: false })
    expect(
      await screen.findByText(
        `Last changed by admin@example.com on ${new Date(TURNED_OFF.updated_at).toLocaleString()}`,
      ),
    ).toBeInTheDocument()
    expect(toggle()).toHaveAttribute('aria-checked', 'false')
  })

  it('turns verification back on without asking', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    vi.mocked(updateSettings).mockResolvedValue({ ...TURNED_OFF, require_email_verification: true })
    const user = userEvent.setup()
    await renderTab(TURNED_OFF)

    await user.click(toggle())

    expect(confirm).not.toHaveBeenCalled()
    expect(updateSettings).toHaveBeenCalledWith({ require_email_verification: true })
  })

  it("shows the backend's message when saving fails, and keeps the setting", async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(updateSettings).mockRejectedValue(
      new ApiError(403, {}, 'You do not have permission to perform this action.'),
    )
    const user = userEvent.setup()
    await renderTab()

    await user.click(toggle())

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You do not have permission to perform this action.',
    )
    expect(toggle()).toHaveAttribute('aria-checked', 'true')
    expect(toggle()).toBeEnabled()
  })

  it("shows the backend's message when loading fails", async () => {
    vi.mocked(getSettings).mockRejectedValue(new ApiError(500, {}, 'Server error.'))

    render(<SettingsTab />)

    expect(await screen.findByRole('alert')).toHaveTextContent('Server error.')
  })
})
