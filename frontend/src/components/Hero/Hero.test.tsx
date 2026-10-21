import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Hero from './Hero'

describe('Hero', () => {
  it('renders the headline and links to signup and login', () => {
    render(
      <MemoryRouter>
        <Hero />
      </MemoryRouter>,
    )

    expect(
      screen.getByText(/your path from classroom to career/i),
    ).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /get started/i })).toHaveAttribute(
      'href',
      '/signup',
    )
    expect(
      screen.getByRole('link', { name: /already have an account/i }),
    ).toHaveAttribute('href', '/login')
  })
})
