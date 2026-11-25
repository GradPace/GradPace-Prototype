import { apiGet } from './api'

// One autocomplete suggestion from GET /api/intelligence/places/. `label` is
// what gets saved as the profile's location ("Norfolk, VA").
export interface Place {
  label: string
  name: string
  state: string
}

export async function searchPlaces(query: string): Promise<Place[]> {
  const places = await apiGet<Place[]>(`/api/intelligence/places/?q=${encodeURIComponent(query)}`)
  // Suggestions are optional - anything unexpected just means none.
  return Array.isArray(places) ? places : []
}
