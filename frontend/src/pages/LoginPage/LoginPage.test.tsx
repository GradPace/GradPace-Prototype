import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import LoginPage from './LoginPage'
import { knownMe, rememberMe } from '../../lib/api/me'

const STUDENT = { email: 'a@b.com', email_verified: true, role: 'student' }
const ADMIN = { email: 'a@b.com', email_verified: true, role: 'admin' }

const navigateMock = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

// The real widget loads Cloudflare's script, which jsdom can't run - pass
// the challenge straight away instead.
vi.mock('../../components/Turnstile/Turnstile', async () => {
  const { useEffect } = await import('react')
  function FakeTurnstile({ onToken }: { onToken: (token: string) => void }) {
    useEffect(() => onToken('turnstile-token'), [onToken])
    return null
  }
  return { default: FakeTurnstile }
})

async function fillAndSubmit(email = 'a@b.com', password = 'pw') {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/email/i), email)
  await user.type(screen.getByLabelText(/password/i), password)
  await user.click(screen.getByRole('button', { name: /log in/i }))
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
    navigateMock.mockClear()
    rememberMe(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('logs in, stores tokens, and navigates to /profile when a profile exists', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        // POST /api/auth/login/
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          text: () =>
            Promise.resolve(JSON.stringify({ access: 'a', refresh: 'r' })),
        })
        // GET /api/auth/me/
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve(STUDENT),
        })
        // GET /api/auth/profile/
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ first_name: 'Ada' }),
        }),
    )

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )
    await fillAndSubmit()

    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse(options?.body as string)).toMatchObject({
      cf_turnstile_response: 'turnstile-token',
    })
    expect(localStorage.getItem('access')).toBe('a')
    expect(localStorage.getItem('refresh')).toBe('r')
    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
  })

  it('navigates to /profileSetup when the account has no profile yet', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          text: () =>
            Promise.resolve(JSON.stringify({ access: 'a', refresh: 'r' })),
        })
        // GET /api/auth/me/
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve(STUDENT),
        })
        .mockResolvedValueOnce({
          ok: false,
          status: 404,
          json: () => Promise.resolve(null),
        }),
    )

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )
    await fillAndSubmit()

    expect(navigateMock).toHaveBeenCalledWith('/profileSetup', {
      replace: true,
    })
  })

  it('sends an admin to /admin-dashboard without checking for a student profile', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        // POST /api/auth/login/
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          text: () =>
            Promise.resolve(JSON.stringify({ access: 'a', refresh: 'r' })),
        })
        // GET /api/auth/me/
        .mockResolvedValueOnce({
          ok: true,
          status: 200,
          json: () => Promise.resolve(ADMIN),
        }),
    )

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )
    await fillAndSubmit()

    expect(navigateMock).toHaveBeenCalledWith('/admin-dashboard', {
      replace: true,
    })
    expect(navigateMock).toHaveBeenCalledTimes(1)
    expect(fetch).toHaveBeenCalledTimes(2)
    expect(knownMe()).toEqual(ADMIN)
  })

  it('sends an already logged-in admin to /admin-dashboard', () => {
    localStorage.setItem('access', 'a')
    rememberMe(ADMIN)

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin-dashboard" element={<p>admin dashboard</p>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('admin dashboard')).toBeInTheDocument()
  })

  it('shows an error and does not navigate on invalid credentials', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        text: () =>
          Promise.resolve(
            JSON.stringify({ detail: 'No active account found.' }),
          ),
      }),
    )

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )
    await fillAndSubmit()

    expect(
      await screen.findByText('No active account found.'),
    ).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
    expect(localStorage.getItem('access')).toBeNull()
  })

  it('links to the forgot password page', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /forgot password/i })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
  })
})
