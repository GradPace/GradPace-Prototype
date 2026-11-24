import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import Navbar from './Navbar'
import { logout } from '../../lib/api/auth'
import { rememberMe } from '../../lib/api/me'

vi.mock('../../lib/api/auth', () => ({
  logout: vi.fn().mockResolvedValue(undefined),
}))

describe('Navbar', () => {
  beforeEach(() => {
    localStorage.clear()
    rememberMe(null)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('shows Log in and Sign up links when logged out', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /log in/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /log out/i }),
    ).not.toBeInTheDocument()
  })

  it('shows the marketing links when logged out', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /features/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /how it works/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /about/i })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /profile/i })).not.toBeInTheDocument()
  })

  it('shows Profile, Feedback and Events links when logged in', () => {
    localStorage.setItem('access', 'fake-token')

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: /profile/i })).toHaveAttribute('href', '/profile')
    expect(screen.getByRole('link', { name: /feedback/i })).toHaveAttribute('href', '/feedback')
    expect(screen.getByRole('link', { name: /events/i })).toHaveAttribute('href', '/events')
    expect(screen.queryByRole('link', { name: /features/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /how it works/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /about/i })).not.toBeInTheDocument()
  })

  it('shows a Log out button when an access token is present', () => {
    localStorage.setItem('access', 'fake-token')

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('button', { name: /log out/i }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: /log in/i }),
    ).not.toBeInTheDocument()
  })

  it('shows an Admin link in place of Profile to an admin', () => {
    localStorage.setItem('access', 'fake-token')
    rememberMe({ email: 'a@b.com', email_verified: true, role: 'admin', email_verification_required: true })

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Admin' })).toHaveAttribute(
      'href',
      '/admin-dashboard',
    )
    expect(
      screen.queryByRole('link', { name: 'Profile' }),
    ).not.toBeInTheDocument()
  })

  it('shows Profile and no Admin link to a student', () => {
    localStorage.setItem('access', 'fake-token')
    rememberMe({ email: 'a@b.com', email_verified: true, role: 'student', email_verification_required: true })

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute(
      'href',
      '/profile',
    )
    expect(
      screen.queryByRole('link', { name: 'Admin' }),
    ).not.toBeInTheDocument()
  })

  it('shows no Admin link when logged out', () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    expect(
      screen.queryByRole('link', { name: 'Admin' }),
    ).not.toBeInTheDocument()
  })

  it('calls logout when the Log out button is clicked', async () => {
    localStorage.setItem('access', 'fake-token')
    const user = userEvent.setup()

    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    )

    await user.click(screen.getByRole('button', { name: /log out/i }))

    expect(logout).toHaveBeenCalledTimes(1)
  })
})
