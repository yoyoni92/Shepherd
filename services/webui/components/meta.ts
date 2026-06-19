// Presentational colour/label maps for the design's tinted pills.
import type { Mission } from '@/lib/preview'
import type { EmployeeStatus } from '@/lib/attendance'
import type { AlertSeverity } from '@/lib/alerts'

export interface Meta {
  color: string
  bg: string
  label: string
}

export const PRIORITY_META: Record<Mission['priority'], Meta> = {
  high: { color: '#f87171', bg: 'rgba(248,113,113,.13)', label: 'גבוהה' },
  medium: { color: '#fbbf24', bg: 'rgba(251,191,36,.13)', label: 'בינונית' },
  low: { color: '#60a5fa', bg: 'rgba(96,165,250,.13)', label: 'נמוכה' },
}

export const MISSION_STATUS_META: Record<Mission['status'], Meta> = {
  in_progress: { color: '#60a5fa', bg: 'rgba(96,165,250,.13)', label: 'בביצוע' },
  pending: { color: '#fbbf24', bg: 'rgba(251,191,36,.13)', label: 'ממתין' },
  done: { color: '#34d399', bg: 'rgba(52,211,153,.13)', label: 'הושלם' },
}

export const ATT_STATUS_META: Record<EmployeeStatus, Meta> = {
  ok: { color: '#34d399', bg: 'rgba(52,211,153,.12)', label: 'תקין' },
  late: { color: '#fbbf24', bg: 'rgba(251,191,36,.12)', label: 'איחורים' },
  absent: { color: '#f87171', bg: 'rgba(248,113,113,.12)', label: 'היעדרויות' },
}

export const ALERT_COLOR: Record<AlertSeverity, string> = {
  danger: '#f87171',
  orange: '#fb923c',
  warning: '#fbbf24',
  pink: '#f472b6',
}

/** Vehicle condition bar/text colour by score. */
export function conditionColor(score: number): string {
  return score >= 80 ? '#34d399' : score >= 60 ? '#fbbf24' : '#f87171'
}
