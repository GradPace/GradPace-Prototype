import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import AdminDashboardPage from './AdminDashboardPage'
import { listUsers, setUserActive, type AdminUser } from '../../lib/api/admin'
import { ApiError } from '../../lib/api/api'
import { rememberMe } from '../../lib/api/me'

vi.mock('../../lib/api/admin', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/api/admin')>()),
  listUsers: vi.fn(),
  setUserActive: vi.fn(),
  // The Data quality tab has its own tests - here it only needs to open.
  getDataHealth: vi.fn(() => new Promise(() => {})),
  getSettings: vi.fn(() => new Promise(() => {})),
}))

const ME = { email: 'admin@example.com', email_verified: true, role: 'admin', email_verification_required: true }

function user(overrides: Partial<AdminUser>): AdminUser {
  return {
    id: 'id-ada',
    first_name: 'Ada',
    last_name: 'Lovelace',
    email: 'ada@example.com',
    role: 'student',
    date_joined: '2026-11-01T12:00:00Z',
    is_active: true,
    ...overrides,
  }
}

const ADA = user({})
const ADMIN = user({
  id: 'id-admin',
  first_name: 'Grace',
  last_name: 'Hopper',
  email: 'admin@example.com',
  role: 'admin',
})
const NAMELESS = user({
  id: 'id-blank',
  first_name: '',
  last_name: '',
  email: 'blank@example.com',
  role: null,
})

function page(results: AdminUser[], count = results.length) {
  return { count, next: null, previous: null, results }
}

function renderPage() {
  render(
    <MemoryRouter>
      <AdminDashboardPage />
    </MemoryRouter>,
  )
}

function rowFor(email: string) {
  return screen.getByText(email).closest('tr') as HTMLElement
}

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    rememberMe(ME)
    vi.mocked(listUsers).mockResolvedValue(page([ADA, ADMIN, NAMELESS]))
  })

  afterEach(() => {
    vi.clearAllMocks()
    vi.restoreAllMocks()
  })

  it('lists users with their name, role, joined date and status', async () => {
    renderPage()

    await screen.findByText('ada@example.com')
    const row = within(rowFor('ada@example.com'))
    expect(row.getByText('Ada Lovelace')).toBeInTheDocument()
    expect(row.getByText('Student')).toBeInTheDocument()
    expect(row.getByText('Active')).toBeInTheDocument()
    expect(row.getByText(new Date(ADA.date_joined).toLocaleDateString())).toBeInTheDocument()
    expect(listUsers).toHaveBeenCalledWith('', 0)
  })

  it('shows fallbacks for a missing role and an empty name', async () => {
    renderPage()

    await screen.findByText('blank@example.com')
    const row = within(rowFor('blank@example.com'))
    expect(row.getByText('No role')).toBeInTheDocument()
    expect(row.getByText('(no name)')).toBeInTheDocument()
  })

  it('searches by email once typing pauses', async () => {
    const typist = userEvent.setup()
    renderPage()
    await screen.findByText('ada@example.com')

    await typist.type(screen.getByRole('searchbox', { name: /search users/i }), 'ada')

    await waitFor(() => expect(listUsers).toHaveBeenLastCalledWith('ada', 0))
    // Debounced: not one request per letter.
    expect(listUsers).not.toHaveBeenCalledWith('a', 0)
  })

  it('shows an empty state when nothing matches', async () => {
    vi.mocked(listUsers).mockResolvedValue(page([]))

    renderPage()

    expect(await screen.findByText('No users yet.')).toBeInTheDocument()
  })

  it('asks before deactivating, then updates the row', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(setUserActive).mockResolvedValue({ ...ADA, is_active: false })
    const clicker = userEvent.setup()
    renderPage()
    await screen.findByText('ada@example.com')

    await clicker.click(screen.getByRole('button', { name: 'Deactivate ada@example.com' }))

    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('ada@example.com'))
    expect(setUserActive).toHaveBeenCalledWith('id-ada', false)
    const row = within(rowFor('ada@example.com'))
    expect(await row.findByText('Inactive')).toBeInTheDocument()
    expect(row.getByRole('button', { name: 'Reactivate ada@example.com' })).toBeEnabled()
  })

  it('does nothing when the confirmation is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const clicker = userEvent.setup()
    renderPage()
    await screen.findByText('ada@example.com')

    await clicker.click(screen.getByRole('button', { name: 'Deactivate ada@example.com' }))

    expect(setUserActive).not.toHaveBeenCalled()
  })

  it('reactivates without asking', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    vi.mocked(listUsers).mockResolvedValue(page([{ ...ADA, is_active: false }]))
    vi.mocked(setUserActive).mockResolvedValue(ADA)
    const clicker = userEvent.setup()
    renderPage()

    await clicker.click(
      await screen.findByRole('button', { name: 'Reactivate ada@example.com' }),
    )

    expect(confirm).not.toHaveBeenCalled()
    expect(setUserActive).toHaveBeenCalledWith('id-ada', true)
  })

  it("disables the button on the admin's own row", async () => {
    renderPage()

    expect(
      await screen.findByRole('button', { name: 'Deactivate admin@example.com' }),
    ).toBeDisabled()
  })

  it("shows the backend's message when an update fails", async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(setUserActive).mockRejectedValue(
      new ApiError(400, {}, "You can't deactivate your own account."),
    )
    const clicker = userEvent.setup()
    renderPage()
    await screen.findByText('ada@example.com')

    await clicker.click(screen.getByRole('button', { name: 'Deactivate ada@example.com' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      "You can't deactivate your own account.",
    )
  })

  it("shows the backend's message when the list fails", async () => {
    vi.mocked(listUsers).mockRejectedValue(
      new ApiError(403, {}, 'You do not have permission to perform this action.'),
    )

    renderPage()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'You do not have permission to perform this action.',
    )
  })

  it('pages through the users', async () => {
    vi.mocked(listUsers).mockResolvedValue(page([ADA], 120))
    const clicker = userEvent.setup()
    renderPage()
    await screen.findByText('ada@example.com')

    expect(screen.getByRole('button', { name: 'Prev' })).toBeDisabled()
    await clicker.click(screen.getByRole('button', { name: 'Next' }))

    expect(listUsers).toHaveBeenLastCalledWith('', 50)
    expect(await screen.findByRole('button', { name: 'Prev' })).toBeEnabled()
  })

  it('switches between tabs', async () => {
    const clicker = userEvent.setup()
    renderPage()
    await screen.findByText('ada@example.com')

    await clicker.click(screen.getByRole('tab', { name: 'Data quality' }))

    expect(screen.getByRole('tab', { name: 'Data quality' })).toHaveAttribute(
      'aria-selected',
      'true',
    )
    expect(screen.getByText('Loading data quality...')).toBeInTheDocument()
    expect(screen.queryByText('ada@example.com')).not.toBeInTheDocument()

    await clicker.click(screen.getByRole('tab', { name: 'Users' }))

    expect(await screen.findByText('ada@example.com')).toBeInTheDocument()

    await clicker.click(screen.getByRole('tab', { name: 'Settings' }))

    expect(screen.getByRole('tab', { name: 'Settings' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('Loading settings...')).toBeInTheDocument()
  })
})
