import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import CheckEmailPage from './CheckEmailPage'

function getReply(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) }
}

function postReply(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(JSON.stringify(body)),
  }
}

const unverified = { email: 'john@example.com', email_verified: false }

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/verify-your-email']}>
      <Routes>
        <Route path="/verify-your-email" element={<CheckEmailPage />} />
        <Route path="/profile" element={<p>profile page</p>} />
        <Route path="/login" element={<p>login page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CheckEmailPage', () => {
  beforeEach(() => {
    localStorage.setItem('access', 'a')
  })

  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
  })

  it('says which address the link was sent to', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(getReply(unverified)))

    renderPage()

    expect(await screen.findByRole('heading', { name: /verify your email/i })).toBeInTheDocument()
    expect(await screen.findByText('john@example.com')).toBeInTheDocument()
  })

  it('sends a logged-out visitor to the login page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(getReply({ detail: 'no' }, 401)))

    renderPage()

    expect(await screen.findByText('login page')).toBeInTheDocument()
  })

  it('asks for the email to be sent again and confirms it', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(getReply(unverified))
        .mockResolvedValueOnce(postReply({ sent: true, already_verified: false })),
    )
    renderPage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /resend the email/i }))

    expect(await screen.findByText(/sent a new link to john@example.com/i)).toBeInTheDocument()
    const [url, options] = vi.mocked(fetch).mock.calls[1]
    expect(String(url)).toContain('/api/auth/verify-email/resend/')
    expect(options?.headers).toMatchObject({ Authorization: 'Bearer a' })
  })

  it('shows the server message when resending is limited', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(getReply(unverified))
        .mockResolvedValueOnce(
          postReply({ detail: 'Request was throttled. Expected available in 600 seconds.' }, 429),
        ),
    )
    renderPage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /resend the email/i }))

    expect(await screen.findByText(/request was throttled/i)).toBeInTheDocument()
  })

  it('moves on to the profile once the email has been verified', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(getReply(unverified))
        .mockResolvedValueOnce(getReply({ ...unverified, email_verified: true })),
    )
    renderPage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /i.ve verified my email/i }))

    expect(await screen.findByText('profile page')).toBeInTheDocument()
  })

  it('says so, and stays, when the email is still not verified', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(getReply(unverified)).mockResolvedValueOnce(getReply(unverified)),
    )
    renderPage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /i.ve verified my email/i }))

    expect(await screen.findByText(/not verified yet/i)).toBeInTheDocument()
    expect(screen.queryByText('profile page')).not.toBeInTheDocument()
  })

  it('sends the user on straight away when verification has been turned off', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(getReply({ ...unverified, email_verification_required: false })),
    )

    renderPage()

    expect(await screen.findByText('profile page')).toBeInTheDocument()
  })

  it('sends the user on when verification is turned off while they wait', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(getReply({ ...unverified, email_verification_required: true }))
        .mockResolvedValueOnce(getReply({ ...unverified, email_verification_required: false })),
    )
    renderPage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /i.ve verified my email/i }))

    expect(await screen.findByText('profile page')).toBeInTheDocument()
  })

  it('sends the user on if the account turns out to be verified already', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce(getReply(unverified))
        .mockResolvedValueOnce(postReply({ sent: false, already_verified: true })),
    )
    renderPage()
    const user = userEvent.setup()

    await user.click(await screen.findByRole('button', { name: /resend the email/i }))

    expect(await screen.findByText('profile page')).toBeInTheDocument()
  })
})
