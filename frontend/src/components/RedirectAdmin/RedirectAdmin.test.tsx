import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RedirectAdmin from './RedirectAdmin'
import { rememberMe } from '../../lib/api/me'

const ADMIN = { email: 'a@b.com', email_verified: true, role: 'admin', email_verification_required: true }
const STUDENT = { email: 'a@b.com', email_verified: true, role: 'student', email_verification_required: true }

function me(body: unknown, status = 200) {
  return { ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) }
}

function renderGuarded(path: '/profile' | '/profileSetup') {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/profile"
          element={
            <RedirectAdmin>
              <p>profile page</p>
            </RedirectAdmin>
          }
        />
        <Route
          path="/profileSetup"
          element={
            <RedirectAdmin>
              <p>profile setup page</p>
            </RedirectAdmin>
          }
        />
        <Route path="/admin-dashboard" element={<p>admin dashboard</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RedirectAdmin', () => {
  beforeEach(() => {
    rememberMe(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it.each(['/profile', '/profileSetup'] as const)(
    'sends an admin who opens %s to the admin dashboard',
    async (path) => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me(ADMIN)))

      renderGuarded(path)

      expect(await screen.findByText('admin dashboard')).toBeInTheDocument()
      expect(screen.queryByText(/profile/)).not.toBeInTheDocument()
    },
  )

  it('sends a cached admin on without asking the server', () => {
    vi.stubGlobal('fetch', vi.fn())
    rememberMe(ADMIN)

    renderGuarded('/profileSetup')

    expect(screen.getByText('admin dashboard')).toBeInTheDocument()
    expect(fetch).not.toHaveBeenCalled()
  })

  it.each([
    ['/profile', 'profile page'],
    ['/profileSetup', 'profile setup page'],
  ] as const)('shows %s to a student', async (path, page) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me(STUDENT)))

    renderGuarded(path)

    expect(await screen.findByText(page)).toBeInTheDocument()
  })

  it('leaves someone not logged in to the page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(me({ detail: 'no' }, 401)))

    renderGuarded('/profile')

    expect(await screen.findByText('profile page')).toBeInTheDocument()
  })
})
