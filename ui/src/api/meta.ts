import { apiFetch } from './client.ts'
import type { OverviewStats, LocationStat, UserInfo } from './types.ts'

export function fetchMe(): Promise<UserInfo> {
  return apiFetch('/auth/me')
}

export function fetchOverview(): Promise<OverviewStats> {
  return apiFetch('/stats/overview')
}

export function fetchStatsByLocation(): Promise<LocationStat[]> {
  return apiFetch('/stats/by-location')
}
