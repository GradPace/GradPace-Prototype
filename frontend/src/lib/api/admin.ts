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

// GET /api/intelligence/admin/data-health/ (backend/intelligence/data_health.py).

// Every source value in the table, plus 'unknown' for blank - always adds
// up to total. Not just official/generated: hand-made rows can hold anything.
export interface SourceTotals {
  total: number
  by_source: Record<string, number>
}

export interface CatalogTotals {
  jobs: SourceTotals
  // JobSkill has no source field.
  skills: { total: number }
  postings: SourceTotals
}

// One per Job, so a soc_code can appear once per source.
export interface OccupationHealth {
  soc_code: string
  title: string
  source: string
  posting_count: number
  skill_count: number
  median_annual_wage: number | null
  few_postings: boolean
  missing_wage: boolean
  no_skills: boolean
}

// Counts and the unrecognized values only - nothing that identifies a student.
export interface StudentLocations {
  profiles: number
  with_location: number
  recognized: number
  unrecognized: number
  // Most common first, at most 20.
  unrecognized_values: { location: string; count: number }[]
}

export interface DataHealth {
  totals: CatalogTotals
  // Latest updated_at across jobs, skills and postings; null when empty.
  catalog_updated_at: string | null
  occupations: OccupationHealth[]
  student_locations: StudentLocations
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
