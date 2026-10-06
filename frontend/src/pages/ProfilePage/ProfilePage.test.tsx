import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import ProfilePage from './ProfilePage'

const navigateMock = vi.fn()

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => navigateMock }
})

function stubProfileResponse(response: {
  ok: boolean
  status: number
  body: unknown
}) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: response.ok,
      status: response.status,
      json: () => Promise.resolve(response.body),
    }),
  )
}

describe('ProfilePage', () => {
  beforeEach(() => {
    navigateMock.mockClear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('renders the fetched profile fields', async () => {
    stubProfileResponse({
      ok: true,
      status: 200,
      body: {
        first_name: 'Ada',
        last_name: 'Lovelace',
        student_id: 'S123',
        uni: 'State University',
        major: 'Computer Science',
        location: 'Remote',
      },
    })

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    expect(await screen.findByText('Ada Lovelace')).toBeInTheDocument()
    expect(screen.getByText('S123')).toBeInTheDocument()
    expect(screen.getByText('State University')).toBeInTheDocument()
    expect(screen.getByText('Computer Science')).toBeInTheDocument()
    expect(screen.getByText('Remote')).toBeInTheDocument()
  })

  it('redirects to /profileSetup when no profile exists yet (404)', async () => {
    stubProfileResponse({ ok: false, status: 404, body: null })

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith('/profileSetup', {
        replace: true,
      }),
    )
  })

  it('redirects to /login when unauthenticated (401)', async () => {
    stubProfileResponse({ ok: false, status: 401, body: null })

    render(
      <MemoryRouter>
        <ProfilePage />
      </MemoryRouter>,
    )

    await vi.waitFor(() =>
      expect(navigateMock).toHaveBeenCalledWith('/login', { replace: true }),
    )
  })
})
