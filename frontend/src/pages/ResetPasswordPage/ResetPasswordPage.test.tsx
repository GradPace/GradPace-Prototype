import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ResetPasswordPage from './ResetPasswordPage'

function reply(status: number, body: unknown = null) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(body === null ? '' : JSON.stringify(body)),
  }
}

function openLink(path = '/reset-password?uid=abc&token=xyz-123') {
  render(
    <MemoryRouter initialEntries={[path]}>
      <ResetPasswordPage />
    </MemoryRouter>,
  )
}

async function changePassword(password = 'Wolf!42gt', confirm = password) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('New password'), password)
  await user.type(screen.getByLabelText('Confirm new password'), confirm)
  await user.click(screen.getByRole('button', { name: /change password/i }))
}

describe('ResetPasswordPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the link values and the new password, then says it worked', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(200)))
    openLink()

    await changePassword('Wolf!42gt')

    expect(await screen.findByRole('heading', { name: /password has been changed/i })).toBeInTheDocument()
    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/api/auth/password/reset/confirm/')
    expect(JSON.parse(options?.body as string)).toEqual({
      uid: 'abc',
      token: 'xyz-123',
      new_password: 'Wolf!42gt',
      new_password_confirm: 'Wolf!42gt',
    })
    // The navbar has a Log in link too, so look inside the page body.
    expect(within(screen.getByRole('main')).getByRole('link', { name: /^log in$/i })).toHaveAttribute('href', '/login')
  })

  it('drops any login left in the browser, since the backend signs every session out', async () => {
    localStorage.setItem('access', 'a')
    localStorage.setItem('refresh', 'r')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(200)))
    openLink()

    await changePassword()

    await screen.findByRole('heading', { name: /password has been changed/i })
    expect(localStorage.getItem('access')).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })

  it('shows why a password was rejected and keeps the form', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(400, { new_password: ['This password is too common.'] })),
    )
    openLink()

    await changePassword('Password1!')

    expect(await screen.findByText(/this password is too common/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument()
  })

  it('shows an expired or invalid link error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(400, { token: ['Invalid or expired reset link.'] })),
    )
    openLink()

    await changePassword()

    expect(await screen.findByText(/invalid or expired reset link/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /get a new one/i })).toHaveAttribute('href', '/forgot-password')
  })

  it('shows the password rules when the password box is selected', async () => {
    openLink()
    const user = userEvent.setup()

    expect(screen.queryByText(/at least 8 characters/i)).not.toBeInTheDocument()
    await user.click(screen.getByLabelText('New password'))

    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()
  })

  it('does not show a form when the link is missing its values', () => {
    vi.stubGlobal('fetch', vi.fn())
    openLink('/reset-password')

    expect(screen.getByRole('heading', { name: /this link doesn.t work/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /change password/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /get a new link/i })).toHaveAttribute('href', '/forgot-password')
  })
})
