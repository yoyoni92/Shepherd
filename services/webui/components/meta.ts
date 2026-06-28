// Presentational colour/label maps for the design's tinted pills.
import type { EmployeeStatus } from '@/lib/attendance'
import type { HolidayKind } from '@/lib/holidays'
import type { AlertSeverity } from '@/lib/alerts'

export interface Meta {
  color: string
  bg: string
  label: string
}

// Real `events` domain (services/fleet-api): types, severity, status.
export const EVENT_TYPE_LABEL: Record<string, string> = {
  maintenance_due: 'טיפול נדרש',
  license_expiring: 'רישוי פג',
  insurance_expiring: 'ביטוח פג',
  ticket_received: 'דוח התקבל',
  accident_logged: 'תאונה',
}

export const SEVERITY_META: Record<string, Meta> = {
  critical: { color: '#f87171', bg: 'rgba(248,113,113,.13)', label: 'קריטי' },
  warning: { color: '#fbbf24', bg: 'rgba(251,191,36,.13)', label: 'אזהרה' },
  info: { color: '#60a5fa', bg: 'rgba(96,165,250,.13)', label: 'מידע' },
}

export const EVENT_STATUS_META: Record<string, Meta> = {
  open: { color: '#f87171', bg: 'rgba(248,113,113,.13)', label: 'פתוח' },
  acknowledged: { color: '#fbbf24', bg: 'rgba(251,191,36,.13)', label: 'בטיפול' },
  resolved: { color: '#34d399', bg: 'rgba(52,211,153,.13)', label: 'נפתר' },
  dismissed: { color: '#64748b', bg: 'rgba(100,116,139,.13)', label: 'נדחה' },
}

export const ATT_STATUS_META: Record<EmployeeStatus, Meta> = {
  ok: { color: '#34d399', bg: 'rgba(52,211,153,.12)', label: 'תקין' },
  late: { color: '#fbbf24', bg: 'rgba(251,191,36,.12)', label: 'איחורים' },
  absent: { color: '#f87171', bg: 'rgba(248,113,113,.12)', label: 'היעדרויות' },
}

// Holiday note pills: חג (no-work) red-toned, ערב חג amber, fasts violet, festive/minor blue.
export const HOLIDAY_META: Record<HolidayKind, Meta> = {
  chag: { color: '#f87171', bg: 'rgba(248,113,113,.12)', label: 'חג' },
  erev: { color: '#fbbf24', bg: 'rgba(251,191,36,.12)', label: 'ערב חג' },
  fast: { color: '#a78bfa', bg: 'rgba(167,139,250,.12)', label: 'צום' },
  minor: { color: '#60a5fa', bg: 'rgba(96,165,250,.12)', label: 'מועד' },
}

export const ALERT_COLOR: Record<AlertSeverity, string> = {
  danger: '#f87171',
  orange: '#fb923c',
  warning: '#fbbf24',
  pink: '#f472b6',
}
