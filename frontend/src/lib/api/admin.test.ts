import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { listUsers, setUserActive } from './admin'

function mockFetch(body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      text: () => Promise.resolve(JSON.stringify(body)),
      json: () => Promise.resolve(body),
    }),
  )
}

function requestedUrl() {
  return new URL(vi.mocked(fetch).mock.calls[0][0] as string, 'http://x')
}

describe('admin api', () => {
  beforeEach(() => {
    localStorage.clear()
    mockFetch({ count: 0, next: null, previous: null, results: [] })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lists users with limit and offset, and no search when it is blank', async () => {
    await listUsers('  ', 50)

    const url = requestedUrl()
    expect(url.pathname).toContain('/api/auth/admin/users/')
    expect(url.searchParams.get('limit')).toBe('50')
    expect(url.searchParams.get('offset')).toBe('50')
    expect(url.searchParams.has('search')).toBe(false)
  })

  it('sends the search, encoded', async () => {
    await listUsers('ada+l@x.com', 0)

    expect(requestedUrl().searchParams.get('search')).toBe('ada+l@x.com')
  })

  it('sets is_active with a PATCH', async () => {
    localStorage.setItem('access', 'token')

    await setUserActive('abc', false)

    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/auth/admin/users/abc/')
    expect(options?.method).toBe('PATCH')
    expect(JSON.parse(options?.body as string)).toEqual({ is_active: false })
  })
})
