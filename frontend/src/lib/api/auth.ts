import { apiFetch } from './api'
import { rememberMe } from './me'

export async function logout() {
  const refresh = localStorage.getItem('refresh')
  try {
    if (refresh) await apiFetch('/api/auth/logout/', { refresh }, true)
  } catch {
    // Server-side blacklist failed (expired access token, offline, etc.) -
    // still log out locally below.
  } finally {
    localStorage.removeItem('access')
    localStorage.removeItem('refresh')
    rememberMe(null)
  }
}