import { apiFetch, apiGet } from './api'

// The admin dashboard's endpoints (admins only - see backend/accounts/views.py
// AdminUser*View and backend/intelligence/views.py DataHealthView).

export interface AdminUser {
  id: string
  first_name: string
  last_name: string
  email: string
  role: string | null
  date_joined: string
  is_active: boolean
}

// DRF's LimitOffsetPagination response.
export interface Page<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export interface SourceTotals {
  total: number
  by_source: Record<string, number>
}

export interface DataHealth {
  totals: { jobs: SourceTotals; skills: { total: number }; postings: SourceTotals }
  catalog_updated_at: string | null
  occupations: {
    soc_code: string
    title: string
    source: string
    posting_count: number
    skill_count: number
    median_annual_wage: number | null
    few_postings: boolean
    missing_wage: boolean
    no_skills: boolean
  }[]
  student_locations: {
    profiles: number
    with_location: number
    recognized: number
    unrecognized: number
    unrecognized_values: { location: string; count: number }[]
  }
}

// The backend's PAGE_SIZE. Sent as `limit` so Prev/Next steps match the server.
export const USERS_PAGE_SIZE = 50

export function listUsers(search: string, offset: number): Promise<Page<AdminUser>> {
  const params = new URLSearchParams({ limit: String(USERS_PAGE_SIZE), offset: String(offset) })
  if (search.trim()) params.set('search', search.trim())
  return apiGet<Page<AdminUser>>(`/api/auth/admin/users/?${params}`)
}

export function setUserActive(id: string, isActive: boolean): Promise<AdminUser> {
  return apiFetch<AdminUser>(`/api/auth/admin/users/${id}/`, { is_active: isActive }, true, 'PATCH')
}

export function getDataHealth(): Promise<DataHealth> {
  return apiGet<DataHealth>('/api/intelligence/admin/data-health/')
}
