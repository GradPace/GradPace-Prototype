import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import VerifyEmailPage from './VerifyEmailPage'

function openLink(path = '/verify-email?token=signed-token') {
  render(
    <MemoryRouter initialEntries={[path]}>
      <VerifyEmailPage />
    </MemoryRouter>,
  )
}

function reply(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(JSON.stringify(body)),
  }
}

describe('VerifyEmailPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('sends the token from the link and says the email is verified', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(200, { verified: true, already_verified: false })),
    )

    openLink()

    expect(await screen.findByRole('heading', { name: /your email is verified/i })).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/api/auth/verify-email/')
    expect(JSON.parse(options?.body as string)).toEqual({ token: 'signed-token' })
  })

  it('says so when the email was already verified', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(200, { verified: true, already_verified: true })),
    )

    openLink()

    expect(await screen.findByRole('heading', { name: /already verified/i })).toBeInTheDocument()
  })

  it('explains an invalid or expired link', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(400, { detail: 'This verification link is invalid or has expired.' })),
    )

    openLink()

    expect(await screen.findByRole('heading', { name: /this link doesn.t work/i })).toBeInTheDocument()
    expect(screen.getByText(/invalid or has expired/i)).toBeInTheDocument()
  })

  it('does not call the server when the link has no token', () => {
    vi.stubGlobal('fetch', vi.fn())

    openLink('/verify-email')

    expect(screen.getByRole('heading', { name: /this link doesn.t work/i })).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('offers to try again later when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('Failed to fetch')))

    openLink()

    expect(await screen.findByRole('heading', { name: /something went wrong/i })).toBeInTheDocument()
  })

  it('links a logged-out visitor to the login page', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(200, { verified: true, already_verified: false })),
    )

    openLink()

    const link = await screen.findByRole('link', { name: /^log in$/i })
    expect(link).toHaveAttribute('href', '/login')
  })

  it('links a logged-in visitor to their profile', async () => {
    localStorage.setItem('access', 'a')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(reply(200, { verified: true, already_verified: false })),
    )

    openLink()

    const link = await screen.findByRole('link', { name: /go to your profile/i })
    expect(link).toHaveAttribute('href', '/profile')
  })
})
