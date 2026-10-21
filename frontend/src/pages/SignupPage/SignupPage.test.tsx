import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import SignupPage from './SignupPage'

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

async function fillAndSubmit() {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText(/first name/i), 'Ada')
  await user.type(screen.getByLabelText(/last name/i), 'Lovelace')
  await user.type(screen.getByLabelText(/^email$/i), 'ada@example.com')
  await user.type(screen.getByLabelText(/^password$/i), 'Str0ng!Pass')
  await user.type(screen.getByLabelText(/confirm password/i), 'Str0ng!Pass')
  await user.click(screen.getByRole('button', { name: /sign up/i }))
}

describe('SignupPage', () => {
  beforeEach(() => {
    localStorage.clear()
    navigateMock.mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('registers, stores tokens, and navigates to /profileSetup on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        text: () =>
          Promise.resolve(JSON.stringify({ access: 'a', refresh: 'r' })),
      }),
    )

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )
    await fillAndSubmit()

    expect(localStorage.getItem('access')).toBe('a')
    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect(JSON.parse(options?.body as string)).toMatchObject({
      email: 'ada@example.com',
      first_name: 'Ada',
      last_name: 'Lovelace',
      cf_turnstile_response: 'turnstile-token',
    })
    expect(navigateMock).toHaveBeenCalledWith('/profileSetup', {
      replace: true,
    })
  })

  it('shows the server validation error and does not navigate on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        text: () =>
          Promise.resolve(
            JSON.stringify({ email: ['That email is already taken.'] }),
          ),
      }),
    )

    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )
    await fillAndSubmit()

    expect(
      await screen.findByText('That email is already taken.'),
    ).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('shows the password requirement hints only while the password field is focused', async () => {
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )

    expect(screen.queryByText(/at least 8 characters/i)).not.toBeInTheDocument()

    const user = userEvent.setup()
    await user.click(screen.getByLabelText(/^password$/i))
    expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()

    await user.tab()
    expect(screen.queryByText(/at least 8 characters/i)).not.toBeInTheDocument()
  })
})
