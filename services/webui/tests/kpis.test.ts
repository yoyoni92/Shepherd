import { describe, it, expect } from 'vitest'
import { computeKpis, type KpiRaw } from '@/lib/kpis'

const fixture: KpiRaw = {
  total_vehicles: 42,
  active_drivers: 28,
  docs_expiring_soon: 7,
  open_events: 5,
  unpaid_tickets: 3,
  maintenance_due: 4,
}

describe('T2 - computeKpis', () => {
  it('maps raw fields to kpi shape', () => {
    expect(computeKpis(fixture)).toEqual({
      vehicles: 42,
      activeDrivers: 28,
      docsExpiring30d: 7,
      openEvents: 5,
      unpaidTickets: 3,
      maintenanceDue: 4,
    })
  })

  it('handles all zeros', () => {
    const zeros: KpiRaw = { total_vehicles: 0, active_drivers: 0, docs_expiring_soon: 0, open_events: 0, unpaid_tickets: 0, maintenance_due: 0 }
    const kpis = computeKpis(zeros)
    expect(kpis.vehicles).toBe(0)
    expect(kpis.maintenanceDue).toBe(0)
  })

  it('does not mutate input', () => {
    const input = { ...fixture }
    computeKpis(input)
    expect(input).toEqual(fixture)
  })
})
