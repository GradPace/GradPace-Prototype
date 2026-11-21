import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import LocationInput from './LocationInput'

const NORFOLK = { label: 'Norfolk, VA', name: 'Norfolk', state: 'VA' }
const NORMAN = { label: 'Norman, OK', name: 'Norman', state: 'OK' }

function placesResponse(places: unknown) {
  return { ok: true, status: 200, json: () => Promise.resolve(places) }
}

function suggestions() {
  return Array.from(document.querySelectorAll('datalist option')).map((o) =>
    o.getAttribute('value'),
  )
}

function requestedUrls() {
  return vi.mocked(fetch).mock.calls.map(([url]) => url as string)
}

describe('LocationInput', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.clearAllMocks()
  })

  it('does not ask the backend until at least two letters are typed', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(placesResponse([])))
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={0} />)

    await user.type(screen.getByRole('combobox'), 'n')
    await new Promise((resolve) => setTimeout(resolve, 20))

    expect(fetch).not.toHaveBeenCalled()
  })

  it('shows the places the backend returns as suggestions, sending the access token', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(placesResponse([NORFOLK, NORMAN])))
    localStorage.setItem('access', 'my-token')
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={0} />)

    await user.type(screen.getByRole('combobox'), 'nor')

    await waitFor(() => expect(suggestions()).toEqual(['Norfolk, VA', 'Norman, OK']))
    const [url, options] = vi.mocked(fetch).mock.calls.at(-1)!
    expect(url).toContain('/api/intelligence/places/?q=nor')
    expect(options?.headers).toMatchObject({ Authorization: 'Bearer my-token' })
  })

  it('url-encodes what was typed, such as the comma and space in "norfolk, v"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(placesResponse([NORFOLK])))
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={0} />)

    await user.type(screen.getByRole('combobox'), 'norfolk, v')

    await waitFor(() => expect(requestedUrls().at(-1)).toContain('q=norfolk%2C%20v'))
  })

  it('waits for a pause in typing and asks once for the final text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(placesResponse([NORFOLK])))
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={100} />)

    await user.type(screen.getByRole('combobox'), 'norf')

    await waitFor(() => expect(suggestions()).toEqual(['Norfolk, VA']))
    expect(requestedUrls()).toHaveLength(1)
    expect(requestedUrls()[0]).toContain('q=norf')
  })

  it('ignores a slow reply for an older query that arrives after a newer one', async () => {
    const replies: Record<string, (value: unknown) => void> = {}
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(
        (url: string) =>
          new Promise((resolve) => {
            replies[url.split('q=')[1]] = resolve
          }),
      ),
    )
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={0} />)
    const input = screen.getByRole('combobox')

    await user.type(input, 'nor')
    await waitFor(() => expect(replies.nor).toBeDefined())
    await user.type(input, 'f')
    await waitFor(() => expect(replies.norf).toBeDefined())

    replies.norf(placesResponse([NORFOLK]))
    await waitFor(() => expect(suggestions()).toEqual(['Norfolk, VA']))
    replies.nor(placesResponse([NORMAN])) // the older, slower answer

    await new Promise((resolve) => setTimeout(resolve, 20))
    expect(suggestions()).toEqual(['Norfolk, VA'])
  })

  it('clears the suggestions when the text is cut back below two letters', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(placesResponse([NORFOLK])))
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={0} />)
    const input = screen.getByRole('combobox')

    await user.type(input, 'nor')
    await waitFor(() => expect(suggestions()).toHaveLength(1))
    await user.clear(input)
    await user.type(input, 'n')

    expect(suggestions()).toEqual([])
  })

  it('still works as a plain text box when the lookup fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const user = userEvent.setup()
    render(<LocationInput name="location" debounceMs={0} />)

    await user.type(screen.getByRole('combobox'), 'Norfolk, VA')

    await waitFor(() => expect(fetch).toHaveBeenCalled())
    expect(screen.getByRole('combobox')).toHaveValue('Norfolk, VA')
    expect(suggestions()).toEqual([])
  })

  it('submits what is in the box under its name, whether or not it was a suggestion', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(placesResponse([])))
    const user = userEvent.setup()
    render(
      <form data-testid="form">
        <LocationInput name="location" debounceMs={0} />
      </form>,
    )

    await user.type(screen.getByRole('combobox'), 'Somewhere else')

    const form = screen.getByTestId('form') as HTMLFormElement
    expect(new FormData(form).get('location')).toBe('Somewhere else')
  })
})
