import { describe, it, expect } from 'vitest'
import { deriveKpis } from '@/lib/kpis'
import type { VehicleRead, DriverRead, EventRead, ReportRead } from '@/lib/api/schemas'

const TODAY = new Date('2026-06-19T00:00:00')

const veh = (over: Partial<VehicleRead>): VehicleRead => ({
  vehicle_id: 'v', licensing_plate: 'p', current_km: 0, next_maintenance_km: 999999,
  insurance_valid_to: '2030-01-01', license_valid_to: '2030-01-01', ...over,
})
const drv = (status: string): DriverRead => ({ driver_id: 'd', full_name: 'n', phone_number: 'p', status })
const ev = (status: string): EventRead => ({ event_id: 'e', event_type: 'maintenance_due', severity: 'info', message: 'm', status, triggered_ts: 't' })
const rep = (status: string): ReportRead => ({ report_id: 'r', vehicle_id: 'v', ticket_type: 'parking', status })

describe('deriveKpis (no /kpis endpoint — derived from real lists)', () => {
  it('counts vehicles, active drivers, open events, unpaid tickets', () => {
    const k = deriveKpis(
      [veh({}), veh({})],
      [drv('active'), drv('inactive')],
      [ev('open'), ev('open'), ev('resolved')],
      [rep('unpaid'), rep('paid')],
      { docs_expiry_warning_days: 30 },
      TODAY,
    )
    expect(k.vehicles).toBe(2)
    expect(k.activeDrivers).toBe(1)
    expect(k.openEvents).toBe(2)
    expect(k.unpaidTickets).toBe(1)
  })

  it('counts expiring insurance and licence within the warning window', () => {
    const k = deriveKpis(
      [veh({ insurance_valid_to: '2026-06-29', license_valid_to: '2026-07-05' })],
      [], [], [],
      { docs_expiry_warning_days: 30 },
      TODAY,
    )
    expect(k.docsExpiring30d).toBe(2)
  })

  it('flags maintenance when current_km has reached next_maintenance_km', () => {
    const k = deriveKpis(
      [veh({ current_km: 70000, next_maintenance_km: 68000 }), veh({ current_km: 100, next_maintenance_km: 5000 })],
      [], [], [],
      { docs_expiry_warning_days: 30 },
      TODAY,
    )
    expect(k.maintenanceDue).toBe(1)
  })

  it('ignores null km / dates safely', () => {
    const k = deriveKpis(
      [veh({ current_km: null, next_maintenance_km: null, insurance_valid_to: null, license_valid_to: null })],
      [], [], [],
      { docs_expiry_warning_days: 30 },
      TODAY,
    )
    expect(k.docsExpiring30d).toBe(0)
    expect(k.maintenanceDue).toBe(0)
  })
})
