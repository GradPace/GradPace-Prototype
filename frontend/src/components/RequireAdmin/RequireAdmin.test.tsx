import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RequireAdmin from './RequireAdmin'
import { rememberMe } from '../../lib/api/me'

const ADMIN = { email: 'a@b.com', email_verified: true, role: 'admin', email_verification_required: true }
const STUDENT = { email: 'a@b.com', email_verified: true, role: 'student', email_verification_required: true }

function me(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) }
}

function renderGuarded() {
  render(
    <MemoryRouter initialEntries={['/admin-dashboard']}>
      <Routes>
        <Route
          path="/admin-dashboard"
          element={
            <RequireAdmin>
              <p>admin page</p>
            </RequireAdmin>
          }
        />
        <Route path="/profile" element={<p>profile page</p>} />
        <Route path="/login" element={<p>login page</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RequireAdmin', () => {
  beforeEach(() => {
    rememberMe(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the page to an admin', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me(ADMIN)))

    renderGuarded()

    expect(await screen.findByText('admin page')).toBeInTheDocument()
  })

  it('sends a student to their profile', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me(STUDENT)))

    renderGuarded()

    expect(await screen.findByText('profile page')).toBeInTheDocument()
    expect(screen.queryByText('admin page')).not.toBeInTheDocument()
  })

  it('sends someone who is not logged in to the login page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me({ detail: 'no' }, 401)))

    renderGuarded()

    expect(await screen.findByText('login page')).toBeInTheDocument()
    expect(screen.queryByText('admin page')).not.toBeInTheDocument()
  })

  it('uses the account the outer guard already fetched', () => {
    vi.stubGlobal('fetch', vi.fn())
    rememberMe(ADMIN)

    renderGuarded()

    expect(screen.getByText('admin page')).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('shows nothing from the page while it checks', () => {
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => {})))

    renderGuarded()

    expect(screen.getByText(/loading/i)).toBeInTheDocument()
    expect(screen.queryByText('admin page')).not.toBeInTheDocument()
  })
})
