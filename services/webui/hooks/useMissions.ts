'use client'
// Missions have no backend yet (API_ALIGNMENT.md gap B1). Preview/sample data only.
import { SAMPLE_MISSIONS } from '@/lib/preview'
import { sortByPriority } from '@/lib/domain'

export function useMissions() {
  return { missions: sortByPriority(SAMPLE_MISSIONS), loading: false, available: false }
}
