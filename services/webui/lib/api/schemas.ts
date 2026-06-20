import { z } from 'zod'

// ───────────────────────── Real Fleet API shapes ─────────────────────────
// Mirrors services/fleet-api/app/schemas.py. UUIDs are strings; dates are ISO.

export const VehicleReadSchema = z.object({
  vehicle_id: z.string(),
  licensing_plate: z.string(),
  nickname: z.string().nullish(),
  vendor: z.string().nullish(),
  model: z.string().nullish(),
  current_km: z.number().nullish(),
  insurance_valid_to: z.string().nullish(),
  license_valid_to: z.string().nullish(),
  driver_id: z.string().nullish(),
  customer_id: z.string().nullish(),
  next_maintenance_km: z.number().nullish(),
  next_maintenance_type: z.string().nullish(),
  last_maintenance_type: z.string().nullish(),
  last_maintenance_km: z.number().nullish(),
  last_maintenance_date: z.string().nullish(),
  maintenance_type: z.string().nullish(),
  allowed_driver: z.string().nullish(),
})

export const VehicleCreateSchema = z.object({
  licensing_plate: z.string(),
  nickname: z.string().nullish(),
  vendor: z.string().nullish(),
  model: z.string().nullish(),
  allowed_driver: z.string().nullish(),
  driver_id: z.string().nullish(),
  customer_id: z.string().nullish(),
  maintenance_type: z.string().nullish(),
  insurance_valid_to: z.string().nullish(),
  license_valid_to: z.string().nullish(),
})

export const DriverReadSchema = z.object({
  driver_id: z.string(),
  full_name: z.string(),
  phone_number: z.string(),
  license_number: z.string().nullish(),
  status: z.string(), // 'active' | 'inactive'
})

export const DriverCreateSchema = z.object({
  full_name: z.string(),
  phone_number: z.string(),
  license_number: z.string().nullish(),
})

export const ConfigReadSchema = z.object({
  config_key: z.string(),
  config_value: z.unknown(),
  description: z.string().nullish(),
})

export const EventReadSchema = z.object({
  event_id: z.string(),
  vehicle_id: z.string().nullish(),
  event_type: z.string(), // maintenance_due | license_expiring | insurance_expiring | ticket_received | accident_logged
  severity: z.string(), // info | warning | critical
  message: z.string(),
  status: z.string(), // open | acknowledged | resolved | dismissed
  triggered_ts: z.string(),
})

// Numeric fields may arrive as a JSON number or a Decimal-as-string (Pydantic serializes
// Decimal as a string); coerce to number, but keep null.
const numish = z.coerce.number().nullable()

export const KpiDailyReadSchema = z.object({
  snapshot_date: z.string(),
  total_km_7d: numish,
  avg_km_per_driver_7d: numish,
  avg_days_between_maintenance: numish,
  maintenance_due_count: numish,
  docs_expiring_count: numish,
  top_customer_id: z.string().nullish(),
  top_customer_km: numish,
  top_customer_vehicle_count: numish,
  computed_ts: z.string(),
})

export const CustomerReadSchema = z.object({
  customer_id: z.string(),
  full_name: z.string(),
})

export const ReportReadSchema = z.object({
  report_id: z.string(),
  vehicle_id: z.string(),
  ticket_type: z.string(), // traffic | parking
  status: z.string(), // unpaid | paid | contested | transferred_to_driver
  amount: z.number().nullish(),
})

export type VehicleRead = z.infer<typeof VehicleReadSchema>
export type VehicleCreate = z.infer<typeof VehicleCreateSchema>
export type DriverRead = z.infer<typeof DriverReadSchema>
export type DriverCreate = z.infer<typeof DriverCreateSchema>
export type ConfigRead = z.infer<typeof ConfigReadSchema>
export type EventRead = z.infer<typeof EventReadSchema>
export type ReportRead = z.infer<typeof ReportReadSchema>
export type KpiDailyRead = z.infer<typeof KpiDailyReadSchema>
export type CustomerRead = z.infer<typeof CustomerReadSchema>

// ───────────────────────── UI view models ─────────────────────────
// Component-facing shapes. Fields the backend does not provide are nullable
// and render as "—" (tracked in API_ALIGNMENT.md gaps C1/C2).

export interface UiVehicle {
  id: string
  plate: string
  make: string // vendor
  model: string
  driverId: string | null // assigned driver, resolved to a name via the drivers list
  currentKm: number | null
  insurance: string | null // insurance_valid_to
  licenseValidTo: string | null // annual רישוי (not a driver's licence)
  lastService: string | null // last_maintenance_date
  nextMaintenanceKm: number | null
  nextMaintenanceType: string | null
}

export interface UiDriver {
  id: string
  name: string
  phone: string
  license: string
  licExpiry: string | null // drivers.license_valid_to (added in Phase 3; null until then)
  status: 'on' | 'off'
}
