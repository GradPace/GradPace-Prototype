import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RequireVerifiedEmail from './RequireVerifiedEmail'

function me(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) }
}

function renderGuarded() {
  render(
    <MemoryRouter initialEntries={['/private']}>
      <Routes>
        <Route
          path="/private"
          element={
            <RequireVerifiedEmail>
              <p>secret page</p>
            </RequireVerifiedEmail>
          }
        />
        <Route path="/verify-your-email" element={<p>verify your email page</p>} />
        <Route path="/login" element={<p>login page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireVerifiedEmail', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the page to a user whose email is verified', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me({ email_verified: true })))

    renderGuarded()

    expect(await screen.findByText('secret page')).toBeInTheDocument()
  })

  it('sends a user whose email is not verified to the verify your email page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me({ email_verified: false })))

    renderGuarded()

    expect(await screen.findByText('verify your email page')).toBeInTheDocument()
    expect(screen.queryByText('secret page')).not.toBeInTheDocument()
  })

  it('sends someone who is not logged in to the login page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me({ detail: 'no' }, 401)))

    renderGuarded()

    expect(await screen.findByText('login page')).toBeInTheDocument()
  })

  it('does not lock anyone out when the account cannot be checked', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('Failed to fetch')))

    renderGuarded()

    expect(await screen.findByText('secret page')).toBeInTheDocument()
  })

  it('shows nothing from the page while it checks', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))

    renderGuarded()

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(screen.queryByText('secret page')).not.toBeInTheDocument()
  })
})
