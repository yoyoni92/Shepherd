import { describe, it, expect } from 'vitest'
import { alertsFromEvents } from '@/lib/alerts'
import type { EventRead } from '@/lib/api/schemas'

const ev = (over: Partial<EventRead>): EventRead => ({
  event_id: 'e', vehicle_id: 'v', event_type: 'maintenance_due', severity: 'warning',
  message: 'm', status: 'open', triggered_ts: 't', ...over,
})

describe('alertsFromEvents (dashboard alerts from real /events)', () => {
  it('keeps only open events', () => {
    const a = alertsFromEvents([ev({ status: 'open' }), ev({ status: 'resolved' }), ev({ status: 'dismissed' })])
    expect(a).toHaveLength(1)
  })

  it('maps severity to UI severity + tag', () => {
    const [a] = alertsFromEvents([ev({ severity: 'critical', event_type: 'insurance_expiring', message: 'ביטוח' })])
    expect(a.severity).toBe('danger')
    expect(a.tag).toBe('דחוף')
    expect(a.title).toBe('ביטוח')
    expect(a.meta).toBe('ביטוח')
  })

  it('sorts most-severe first', () => {
    const a = alertsFromEvents([ev({ event_id: '1', severity: 'info' }), ev({ event_id: '2', severity: 'critical' })])
    expect(a[0].severity).toBe('danger')
    expect(a[a.length - 1].severity).toBe('pink')
  })

  it('falls back to warning for unknown severity', () => {
    const [a] = alertsFromEvents([ev({ severity: 'bogus' })])
    expect(a.severity).toBe('warning')
  })
})
