import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch, apiGet } from './api'

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      status,
      ok: status >= 200 && status < 300,
      text: () => Promise.resolve(JSON.stringify(body)),
      json: () => Promise.resolve(body),
    }),
  )
}

describe('apiFetch', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('POSTs the given body as JSON and returns the parsed response', async () => {
    mockFetchOnce(200, { access: 'a', refresh: 'b' })

    const result = await apiFetch<{ access: string; refresh: string }>(
      '/api/auth/login/',
      { email: 'a@b.com', password: 'pw' },
    )

    expect(result).toEqual({ access: 'a', refresh: 'b' })
    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/auth/login/')
    expect(options?.method).toBe('POST')
    expect(options?.headers).not.toHaveProperty('Authorization')
  })

  it('attaches a Bearer token when auth=true and a token is stored', async () => {
    localStorage.setItem('access', 'my-token')
    mockFetchOnce(200, {})

    await apiFetch('/api/auth/profile/', { student_id: '1' }, true)

    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect(options?.headers).toMatchObject({
      Authorization: 'Bearer my-token',
    })
  })

  it('throws an ApiError with the status and joined validation messages on failure', async () => {
    mockFetchOnce(400, { password: ['Too short.', 'Needs a number.'] })

    await expect(
      apiFetch('/api/auth/register/', { password: 'x' }),
    ).rejects.toMatchObject({
      status: 400,
      message: 'Too short. Needs a number.',
    })
  })

  it('is thrown as an instance of ApiError', async () => {
    mockFetchOnce(401, {})

    await expect(apiFetch('/api/auth/login/', {})).rejects.toBeInstanceOf(
      ApiError,
    )
  })
})

describe('apiGet', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('returns parsed JSON on success', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ first_name: 'Ada' }),
      }),
    )

    const result = await apiGet<{ first_name: string }>('/api/auth/me/')

    expect(result).toEqual({ first_name: 'Ada' })
  })

  it('throws ApiError with the response status on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () => Promise.resolve(null),
      }),
    )

    await expect(apiGet('/api/auth/profile/')).rejects.toMatchObject({
      status: 404,
    })
  })
})

describe('expired login tokens', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('apiGet drops the stored tokens when the server answers 401', async () => {
    localStorage.setItem('access', 'old')
    localStorage.setItem('refresh', 'old-refresh')
    mockFetchOnce(401, { detail: 'Given token not valid for any token type' })

    await expect(apiGet('/api/auth/profile/')).rejects.toMatchObject({ status: 401 })

    expect(localStorage.getItem('access')).toBeNull()
    expect(localStorage.getItem('refresh')).toBeNull()
  })

  it('apiFetch drops the stored tokens on a 401 to an authenticated request', async () => {
    localStorage.setItem('access', 'old')
    localStorage.setItem('refresh', 'old-refresh')
    mockFetchOnce(401, { detail: 'nope' })

    await expect(apiFetch('/api/auth/verify-email/resend/', {}, true)).rejects.toMatchObject({
      status: 401,
    })

    expect(localStorage.getItem('access')).toBeNull()
  })

  it('a 401 from login (wrong password, no token sent) leaves storage alone', async () => {
    localStorage.setItem('access', 'other')
    mockFetchOnce(401, { detail: 'No active account found with the given credentials' })

    await expect(apiFetch('/api/auth/login/', { email: 'a@b.com', password: 'x' })).rejects.toMatchObject({
      status: 401,
    })

    expect(localStorage.getItem('access')).toBe('other')
  })
})
