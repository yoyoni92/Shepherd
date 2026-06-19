import { z } from 'zod'
import {
  VehicleReadSchema,
  DriverReadSchema,
  ConfigReadSchema,
  EventReadSchema,
  ReportReadSchema,
  ReviewItemSchema,
  type VehicleRead,
  type VehicleCreate,
  type DriverRead,
  type DriverCreate,
  type EventRead,
  type ReportRead,
} from './schemas'

// Browser calls the same-origin Next proxy (`app/api/fleet/[...path]`), which injects the
// internal token + admin caller context. Tests/SSR can point straight at the Fleet host.
const BASE = process.env.NEXT_PUBLIC_FLEET_BASE ?? '/api/fleet'

async function get<T>(path: string, schema: z.ZodType<T>): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: 'no-store' })
  if (!res.ok) throw new Error(`Fleet API ${path}: ${res.status}`)
  return schema.parse(await res.json())
}

async function send<T>(
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  body: unknown,
  schema?: z.ZodType<T>,
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`Fleet API ${method} ${path}: ${res.status}`)
  if (!schema) return undefined as T
  return schema.parse(await res.json())
}

// Vehicles
export const fetchVehicles = () => get('/vehicles', z.array(VehicleReadSchema))
export const createVehicle = (v: VehicleCreate): Promise<VehicleRead> =>
  send('POST', '/vehicles', v, VehicleReadSchema)
export const deleteVehicle = (vehicleId: string) =>
  send('DELETE', `/vehicles/${vehicleId}`, undefined)

// Drivers
export const fetchDrivers = () => get('/drivers', z.array(DriverReadSchema))
export const createDriver = (d: DriverCreate): Promise<DriverRead> =>
  send('POST', '/drivers', d, DriverReadSchema)
export const deleteDriver = (driverId: string) => send('DELETE', `/drivers/${driverId}`, undefined)

// Events / reports (read-only; back KPIs + alerts)
export const fetchEvents = () => get('/events', z.array(EventReadSchema))
export const fetchReports = () => get('/reports', z.array(ReportReadSchema))

// Config: API returns a list of {config_key, config_value, description}; expose as a record.
export async function fetchConfig(): Promise<Record<string, unknown>> {
  const list = await get('/config', z.array(ConfigReadSchema))
  return Object.fromEntries(list.map((c) => [c.config_key, c.config_value]))
}
export const updateConfig = (key: string, value: unknown) =>
  send('PUT', `/config/${key}`, { config_value: value })

// Review queue: no real endpoint yet (gap B3); kept mocked behind the proxy.
export const fetchReviewQueue = () => get('/review-queue', z.array(ReviewItemSchema))
export const resolveReviewItem = (id: string, action: 'accept' | 'reject', payload?: unknown) =>
  send('PUT', `/review-queue/${id}/${action}`, payload ?? {})

export type { VehicleRead, DriverRead, EventRead, ReportRead }
