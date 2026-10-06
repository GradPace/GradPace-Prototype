import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ProfileSetupPage from './ProfileSetupPage'
import { logout } from '../../lib/api/auth'

const navigateMock = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

vi.mock('../../lib/api/auth', () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}))

function stubMe(firstName: string | null) {
  return vi.fn().mockImplementation((url: string) => {
    if (url.includes('/api/auth/me')) {
      return firstName
        ? Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ first_name: firstName }),
          })
        : Promise.resolve({ ok: false, status: 401, json: () => Promise.resolve(null) })
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      text: () => Promise.resolve('{}'),
    })
  })
}

describe('ProfileSetupPage', () => {
  beforeEach(() => {
    localStorage.clear()
    navigateMock.mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('greets the user by their first name once /api/auth/me resolves', async () => {
    vi.stubGlobal('fetch', stubMe('Ada'))

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    expect(await screen.findByText(/hi ada, welcome to gradpace/i)).toBeInTheDocument()
  })

  it('submits the profile form with the access token and navigates to /profile', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await user.type(screen.getByLabelText(/student id/i), 'S123')
    await user.type(screen.getByLabelText(/university/i), 'State U')
    await user.type(screen.getByLabelText(/major/i), 'CS')
    await user.click(screen.getByRole('button', { name: /create profile/i }))

    expect(navigateMock).toHaveBeenCalledWith('/profile', { replace: true })
    const profileCall = vi
      .mocked(fetch)
      .mock.calls.find(([url]) => (url as string).includes('/api/auth/profile/'))
    const [, options] = profileCall!
    expect(options?.headers).toMatchObject({ Authorization: 'Bearer my-token' })
    expect(JSON.parse(options?.body as string)).toMatchObject({
      student_id: 'S123',
      uni: 'State U',
      major: 'CS',
    })
  })

  it('logs out and redirects to /login when "Log out" is clicked', async () => {
    vi.stubGlobal('fetch', stubMe(null))
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <ProfileSetupPage />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: /log out/i }))

    expect(logout).toHaveBeenCalledTimes(1)
    expect(navigateMock).toHaveBeenCalledWith('/login', { replace: true })
  })
})
