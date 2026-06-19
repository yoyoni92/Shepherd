import type { EventRead } from './api/schemas'

export type AlertSeverity = 'danger' | 'orange' | 'warning' | 'pink'

export interface Alert {
  id: string
  title: string
  meta: string
  severity: AlertSeverity
  tag: string
}

const SEVERITY_RANK: Record<AlertSeverity, number> = { danger: 0, orange: 1, warning: 2, pink: 3 }

const TYPE_LABEL: Record<string, string> = {
  insurance_expiring: 'ביטוח',
  license_expiring: 'רישיון',
  maintenance_due: 'תחזוקה',
  ticket_received: 'דוח',
  accident_logged: 'תאונה',
}

const SEV: Record<string, { severity: AlertSeverity; tag: string }> = {
  critical: { severity: 'danger', tag: 'דחוף' },
  warning: { severity: 'warning', tag: 'אזהרה' },
  info: { severity: 'pink', tag: 'מידע' },
}

/**
 * Dashboard alerts come from real open `events` (Fleet API has no dedicated alerts feed).
 * Pure mapping; sorted most-severe first. (See API_ALIGNMENT.md.)
 */
export function alertsFromEvents(events: readonly EventRead[]): Alert[] {
  return events
    .filter((e) => e.status === 'open')
    .map((e) => {
      const sev = SEV[e.severity] ?? { severity: 'warning' as AlertSeverity, tag: 'אזהרה' }
      return {
        id: e.event_id,
        title: e.message,
        meta: TYPE_LABEL[e.event_type] ?? e.event_type,
        severity: sev.severity,
        tag: sev.tag,
      }
    })
    .sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity])
}
