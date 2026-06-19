import type { VehicleRead, DriverRead, EventRead, ReportRead } from './api/schemas'
import { daysTo } from './domain'

export interface Kpis {
  vehicles: number
  activeDrivers: number
  docsExpiring30d: number
  openEvents: number
  unpaidTickets: number
  maintenanceDue: number
}

export interface KpiConfig {
  docs_expiry_warning_days: number
}

/**
 * Fleet API exposes no `/kpis` endpoint — the six dashboard numbers are derived from the
 * real `/vehicles`, `/drivers`, `/events` and `/reports` lists plus config thresholds.
 * Pure & deterministic given `today`. (See API_ALIGNMENT.md.)
 */
export function deriveKpis(
  vehicles: readonly VehicleRead[],
  drivers: readonly DriverRead[],
  events: readonly EventRead[],
  reports: readonly ReportRead[],
  config: KpiConfig,
  today: Date = new Date(),
): Kpis {
  const warn = config.docs_expiry_warning_days
  const expiring = (d: string | null | undefined) => d != null && daysTo(d, today) < warn

  let docsExpiring30d = 0
  let maintenanceDue = 0
  for (const v of vehicles) {
    if (expiring(v.insurance_valid_to)) docsExpiring30d++
    if (expiring(v.license_valid_to)) docsExpiring30d++
    if (v.current_km != null && v.next_maintenance_km != null && v.current_km >= v.next_maintenance_km) {
      maintenanceDue++
    }
  }

  return {
    vehicles: vehicles.length,
    activeDrivers: drivers.filter((d) => d.status === 'active').length,
    docsExpiring30d,
    openEvents: events.filter((e) => e.status === 'open').length,
    unpaidTickets: reports.filter((r) => r.status === 'unpaid').length,
    maintenanceDue,
  }
}
