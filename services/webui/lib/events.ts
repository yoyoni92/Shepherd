import type { EventRead } from './api/schemas'

const SEV_RANK: Record<string, number> = { critical: 0, warning: 1, info: 2 }

/** Events ordered most-severe first, then most-recent first (immutable). */
export function sortEvents(events: readonly EventRead[]): EventRead[] {
  return [...events].sort(
    (a, b) =>
      (SEV_RANK[a.severity] ?? 9) - (SEV_RANK[b.severity] ?? 9) ||
      b.triggered_ts.localeCompare(a.triggered_ts),
  )
}

export const openCount = (events: readonly EventRead[]): number =>
  events.filter((e) => e.status === 'open').length
