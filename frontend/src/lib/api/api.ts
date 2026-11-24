import { rememberMe } from './me'

const API_URL = import.meta.env.VITE_API_URL

// http://localhost:8000/api/docs/#/

//below makes error easier to read.

// Carries the actual HTTP status + response body along with the error, so
// callers can inspect what the backend actually said
export class ApiError extends Error {
  status: number
  data: unknown

  constructor(status: number, data: unknown, message: string) {
    super(message)
    this.status = status
    this.data = data
  }
}

// DRF validation errors come back shaped like {"password": ["msg1", "msg2"]} instead 
// of the UI ever showing "[object Object]".
function messageFromResponseBody(data: unknown): string {
  if (data && typeof data === 'object') {
    const messages = Object.values(data as Record<string, unknown>)
      .flat()
      .filter((value): value is string => typeof value === 'string')
    if (messages.length > 0) return messages.join(' ')
  }
  return 'Something went wrong. Please try again.'
}

// T is the shape of a *successful* response's JSON - callers pass it as
// apiFetch<{ access: string; refresh: string }> so the returned data
// is typed instead of `unknown`, without loosening error handling above.
// The access token only lasts an hour and nothing renews it. If the server says
// 401 to a request that carried one, it is dead: drop it. Leaving it in
// localStorage made /login (which treats any stored token as "logged in") send
// the user straight back to /profile, whose 401 sent them to /login again, in a
// loop that never settled.
function dropDeadTokens(status: number, sentToken: boolean) {
  if (status === 401 && sentToken) {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    rememberMe(null)
  }
}

export async function apiFetch<T>(
  path: string,
  body: unknown,
  auth = false,
  method: 'POST' | 'PATCH' = 'POST',
): Promise<T> {
  return apiSend<T>(method, path, body, auth)
}

// PATCH/DELETE always send the access token - they only exist on a
// logged-in user's own records.
export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  return apiSend<T>('PATCH', path, body, true)
}

// A successful DELETE is 204 No Content, so this resolves to null
export async function apiDelete(path: string): Promise<null> {
  return apiSend<null>('DELETE', path, undefined, true)
}

async function apiSend<T>(
  method: 'POST' | 'PATCH' | 'DELETE',
  path: string,
  body: unknown,
  auth: boolean,
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (auth) {
    const access = localStorage.getItem('access')
    if (access) headers.Authorization = `Bearer ${access}`
  }
  const sentToken = Boolean(headers.Authorization)

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  // Read as text first, not res.json() directly - a non-JSON response (an
  // HTML error page, an empty body from a proxy/CORS failure, etc.) would
  // otherwise throw inside res.json() itself with no useful message at all.
  dropDeadTokens(res.status, sentToken)
  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      throw new ApiError(res.status, text, text.slice(0, 200) || `Request failed (${res.status})`)
    }
  }

  if (!res.ok) {
    throw new ApiError(res.status, data, messageFromResponseBody(data))
  }

  return data as T
}


export async function apiGet<T>(path: string): Promise<T> {
  const access = localStorage.getItem('access')
  const res = await fetch(`${API_URL}${path}`, {
    headers: access ? { Authorization: `Bearer ${access}` } : {},
  })
  dropDeadTokens(res.status, Boolean(access))
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, data, messageFromResponseBody(data))
  return data as T
}