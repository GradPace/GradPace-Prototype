import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from './LoginPage'

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
})
