import { describe, it, expect } from 'vitest'
import { sortEvents, openCount } from '@/lib/events'
import type { EventRead } from '@/lib/api/schemas'

const ev = (over: Partial<EventRead>): EventRead => ({
  event_id: 'e', event_type: 'maintenance_due', severity: 'info',
  message: 'm', status: 'open', triggered_ts: '2026-06-01T00:00:00Z', ...over,
})

describe('sortEvents', () => {
  it('orders by severity (critical>warning>info) then most-recent first', () => {
    const out = sortEvents([
      ev({ event_id: 'a', severity: 'info', triggered_ts: '2026-06-10T00:00:00Z' }),
      ev({ event_id: 'b', severity: 'critical', triggered_ts: '2026-06-01T00:00:00Z' }),
      ev({ event_id: 'c', severity: 'warning', triggered_ts: '2026-06-05T00:00:00Z' }),
      ev({ event_id: 'd', severity: 'critical', triggered_ts: '2026-06-09T00:00:00Z' }),
    ])
    expect(out.map((e) => e.event_id)).toEqual(['d', 'b', 'c', 'a'])
  })

  it('does not mutate the input', () => {
    const input = [ev({ event_id: '1', severity: 'info' }), ev({ event_id: '2', severity: 'critical' })]
    sortEvents(input)
    expect(input[0].event_id).toBe('1')
  })
})

describe('openCount', () => {
  it('counts only open events', () => {
    expect(openCount([ev({ status: 'open' }), ev({ status: 'resolved' }), ev({ status: 'open' })])).toBe(2)
  })
})
