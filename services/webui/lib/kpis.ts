import type { KpiRaw } from './api/schemas'

export type { KpiRaw }

export interface Kpis {
  vehicles: number
  activeDrivers: number
  docsExpiring30d: number
  openEvents: number
  unpaidTickets: number
  maintenanceDue: number
}

export function computeKpis(data: KpiRaw): Kpis {
  return {
    vehicles: data.total_vehicles,
    activeDrivers: data.active_drivers,
    docsExpiring30d: data.docs_expiring_soon,
    openEvents: data.open_events,
    unpaidTickets: data.unpaid_tickets,
    maintenanceDue: data.maintenance_due,
  }
}
