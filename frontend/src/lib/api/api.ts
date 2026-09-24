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
export async function apiFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  // Read as text first, not res.json() directly - a non-JSON response (an
  // HTML error page, an empty body from a proxy/CORS failure, etc.) would
  // otherwise throw inside res.json() itself with no useful message at all.
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
