import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ForgotPasswordPage from './ForgotPasswordPage'

function reply(status: number, body: unknown = null) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: () => Promise.resolve(body === null ? '' : JSON.stringify(body)),
  }
}

async function submit(email = 'ada@example.com') {
  const user = userEvent.setup()
  render(
    <MemoryRouter>
      <ForgotPasswordPage />
    </MemoryRouter>,
  )
  await user.type(screen.getByLabelText(/email/i), email)
  await user.click(screen.getByRole('button', { name: /send reset link/i }))
}

describe('ForgotPasswordPage', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('asks the backend to email a reset link and says to check the inbox', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(200)))

    await submit('ada@example.com')

    expect(await screen.findByRole('heading', { name: /check your email/i })).toBeInTheDocument()
    expect(screen.getByText(/if an account exists for ada@example.com/i)).toBeInTheDocument()
    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(String(url)).toContain('/api/auth/password/reset/')
    expect(JSON.parse(options?.body as string)).toEqual({ email: 'ada@example.com' })
  })

  it('shows the same message whatever the backend decides about the address', async () => {
    // The backend answers 200 for unknown addresses too; nothing here may
    // hint at whether an account exists.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(reply(200)))

    await submit('nobody@example.com')

    expect(await screen.findByText(/if an account exists for nobody@example.com/i)).toBeInTheDocument()
  })

  it('shows the server message when too many requests were made', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValueOnce(
        reply(429, { detail: 'Request was throttled. Expected available in 60 seconds.' }),
      ),
    )

    await submit()

    expect(await screen.findByText(/request was throttled/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: /check your email/i })).not.toBeInTheDocument()
  })

  it('links back to the login page', () => {
    render(
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>,
    )

    expect(within(screen.getByRole('main')).getByRole('link', { name: /^log in$/i })).toHaveAttribute('href', '/login')
  })
})
