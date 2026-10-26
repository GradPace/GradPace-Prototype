import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiDelete, apiFetch, apiGet, apiPatch } from './api'

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

describe('apiPatch and apiDelete', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem('access', 'my-token')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('PATCHes the body as JSON with the access token', async () => {
    mockFetchOnce(200, { id: 's1', proficiency_level: 'expert' })

    const result = await apiPatch('/api/auth/profile/skills/s1/', {
      proficiency_level: 'expert',
    })

    expect(result).toEqual({ id: 's1', proficiency_level: 'expert' })
    const [url, options] = vi.mocked(fetch).mock.calls[0]
    expect(url).toContain('/api/auth/profile/skills/s1/')
    expect(options?.method).toBe('PATCH')
    expect(options?.headers).toMatchObject({ Authorization: 'Bearer my-token' })
    expect(JSON.parse(options?.body as string)).toEqual({ proficiency_level: 'expert' })
  })

  it('DELETEs with no body and resolves to null on 204', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, status: 204, text: () => Promise.resolve('') }),
    )

    await expect(apiDelete('/api/auth/profile/skills/s1/')).resolves.toBeNull()
    const [, options] = vi.mocked(fetch).mock.calls[0]
    expect(options?.method).toBe('DELETE')
    expect(options?.body).toBeUndefined()
    expect(options?.headers).toMatchObject({ Authorization: 'Bearer my-token' })
  })

  it('throws ApiError on failure', async () => {
    mockFetchOnce(404, { detail: 'Not found.' })

    await expect(apiDelete('/api/auth/profile/skills/nope/')).rejects.toMatchObject({
      status: 404,
      message: 'Not found.',
    })
  })
})
