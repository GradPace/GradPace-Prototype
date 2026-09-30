import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { logout } from './auth'

describe('logout', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('access', 'a')
    localStorage.setItem('refresh', 'r')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs the refresh token to the logout endpoint and clears local storage', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        text: () => Promise.resolve(''),
      }),
    )

    await logout()

    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/auth/logout/')
    expect(JSON.parse(options?.body as string)).toEqual({ refresh: 'r' })
    expect(localStorage.getItem('access')).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })

  it('still clears local storage when the server request fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))

    await logout()

    expect(localStorage.getItem('access')).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })

  it('does not call fetch when there is no refresh token stored', async () => {
    localStorage.removeItem('refresh')
    vi.stubGlobal('fetch', vi.fn())

    await logout()

    expect(fetch).not.toHaveBeenCalled()
  })
})
