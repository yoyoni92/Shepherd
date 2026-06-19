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

export const ReportReadSchema = z.object({
  report_id: z.string(),
  vehicle_id: z.string(),
  ticket_type: z.string(), // traffic | parking
  status: z.string(), // unpaid | paid | contested | transferred_to_driver
  amount: z.number().nullish(),
})

// Review queue has no real endpoint yet (gap B3) — kept mocked.
export const ReviewItemSchema = z.object({
  id: z.string(),
  file_name: z.string(),
  reason: z.enum(['low_confidence', 'plate_mismatch', 'output_blocked']),
  doc_type: z.string().optional(),
  confidence: z.number().optional(),
  message: z.string(),
})

export type ReviewItem = z.infer<typeof ReviewItemSchema>
export type VehicleRead = z.infer<typeof VehicleReadSchema>
export type VehicleCreate = z.infer<typeof VehicleCreateSchema>
export type DriverRead = z.infer<typeof DriverReadSchema>
export type DriverCreate = z.infer<typeof DriverCreateSchema>
export type ConfigRead = z.infer<typeof ConfigReadSchema>
export type EventRead = z.infer<typeof EventReadSchema>
export type ReportRead = z.infer<typeof ReportReadSchema>

// ───────────────────────── UI view models ─────────────────────────
// Component-facing shapes. Fields the backend does not provide are nullable
// and render as "—" (tracked in API_ALIGNMENT.md gaps C1/C2).

export interface UiVehicle {
  id: string
  plate: string
  make: string
  model: string
  year: number | null // gap C1
  fuel: string | null // gap C1
  driver: string | null // gap C1 (only driver_id available)
  status: 'active' | 'inactive' // gap C1 (assumed active)
  lastService: string | null
  insurance: string | null
  condition: number | null // gap C1
}

export interface UiDriver {
  id: string
  name: string
  phone: string
  license: string
  licExpiry: string | null // gap C2
  vehicle: string | null // gap C2
  status: 'on' | 'off'
}
