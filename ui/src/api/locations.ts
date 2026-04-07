import { apiFetch } from './client.ts'
import type { LocationCreate, LocationItem, LocationType, LocationTypeCreate, LocationUpdate, PathSegment } from './types.ts'

// --- Location Types ---

export function fetchLocationTypes(): Promise<LocationType[]> {
  return apiFetch('/location-types')
}

export function createLocationType(data: LocationTypeCreate): Promise<LocationType> {
  return apiFetch('/location-types', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateLocationType(id: number, data: Partial<LocationTypeCreate>): Promise<LocationType> {
  return apiFetch(`/location-types/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteLocationType(id: number): Promise<void> {
  return apiFetch(`/location-types/${id}`, { method: 'DELETE' })
}

export function fetchLocations(): Promise<LocationItem[]> {
  return apiFetch('/locations')
}

export function fetchLocationTree(): Promise<LocationItem[]> {
  return apiFetch('/locations/tree')
}

export function fetchLocation(id: number): Promise<LocationItem> {
  return apiFetch(`/locations/${id}`)
}

export function fetchLocationPath(id: number): Promise<PathSegment[]> {
  return apiFetch(`/locations/${id}/path`)
}

export function createLocation(data: LocationCreate): Promise<LocationItem> {
  return apiFetch('/locations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function updateLocation(id: number, data: LocationUpdate): Promise<LocationItem> {
  return apiFetch(`/locations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export function deleteLocation(id: number): Promise<void> {
  return apiFetch(`/locations/${id}`, { method: 'DELETE' })
}
