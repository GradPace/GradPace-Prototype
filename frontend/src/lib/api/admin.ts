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

// GET /api/survey/admin/results/ (backend/surveys/results.py) - the Alumni
// Survey summed up. Aggregates only: no names, emails, ids or job titles.

export interface RatingSummary {
  // Null when there are no responses.
  average: number | null
  // Always all five values 1-5, in order.
  distribution: { value: number; count: number }[]
}

export interface IndustryResult {
  code: string
  label: string
  count: number
  // Null below 3 responses in the industry, so they can't be traced to one alum.
  preparedness_average: number | null
  platform_helpfulness_average: number | null
}

export interface TopSkillCount {
  name: string
  label: string
  count: number
}

export interface SuggestedSkillCount {
  skill: string
  count: number
}

export interface SurveyFeedback {
  text: string
  submitted_at: string
}

export interface SurveyResults {
  response_count: number
  latest_submitted_at: string | null
  ratings: {
    preparedness_rating: RatingSummary
    platform_helpfulness_rating: RatingSummary
  }
  // Every industry choice, in choice order, even at 0.
  by_industry: IndustryResult[]
  top_skills: TopSkillCount[]
  // At most 20.
  suggested_skills: SuggestedSkillCount[]
  feedback_count: number
  // Newest first, at most 50.
  feedback: SurveyFeedback[]
}

export function getSurveyResults(): Promise<SurveyResults> {
  return apiGet<SurveyResults>('/api/survey/admin/results/')
}

// GET/PATCH /api/auth/admin/settings/ - the site-wide switches (one row).
export interface SiteSettings {
  require_email_verification: boolean
  updated_at: string
  // Email of the admin who last changed them; null if nobody has yet.
  updated_by: string | null
}

export function getSettings(): Promise<SiteSettings> {
  return apiGet<SiteSettings>('/api/auth/admin/settings/')
}

export function updateSettings(changes: {
  require_email_verification: boolean
}): Promise<SiteSettings> {
  return apiFetch<SiteSettings>('/api/auth/admin/settings/', changes, true, 'PATCH')
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
