import { z } from 'zod'

// ───────────────────────── Real Fleet API shapes ─────────────────────────
// Mirrors services/fleet-api/app/schemas.py. UUIDs are strings; dates are ISO.

export const VehicleReadSchema = z.object({
  vehicle_id: z.string(),
  licensing_plate: z.string(),
  nickname: z.string().nullish(),
  vehicle_type: z.string().nullish(),
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
  maintenance_type_id: z.string().nullish(),
  maintenance_type_name: z.string().nullish(),
  allowed_driver: z.string().nullish(),
})

export const VehicleCreateSchema = z.object({
  licensing_plate: z.string(),
  nickname: z.string().nullish(),
  vehicle_type: z.string().nullish(),
  vendor: z.string().nullish(),
  model: z.string().nullish(),
  current_km: z.number().nullish(),
  allowed_driver: z.string().nullish(),
  driver_id: z.string().nullish(),
  customer_id: z.string().nullish(),
  maintenance_type_id: z.string().nullish(),
  insurance_valid_to: z.string().nullish(),
  license_valid_to: z.string().nullish(),
})

export const MaintenanceTypeReadSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string().nullish(),
  interval_km: z.number(),
  steps: z.array(z.string()),
})

export const MaintenanceTypeCreateSchema = z.object({
  name: z.string(),
  description: z.string().nullish(),
  interval_km: z.number(),
  steps: z.array(z.string()),
})

export const DriverReadSchema = z.object({
  driver_id: z.string(),
  full_name: z.string(),
  phone_number: z.string(),
  license_number: z.string().nullish(),
  license_valid_to: z.string().nullish(),
  status: z.string(), // 'active' | 'inactive'
})

export const DriverCreateSchema = z.object({
  full_name: z.string(),
  phone_number: z.string(),
  license_number: z.string().nullish(),
  license_valid_to: z.string().nullish(),
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
  phone_number: z.string().nullish(),
  email: z.string().nullish(),
  status: z.string().nullish(),
})

export const CustomerCreateSchema = z.object({
  full_name: z.string(),
  phone_number: z.string().nullish(),
  email: z.string().nullish(),
})

export const AttendanceRecordReadSchema = z.object({
  driver_id: z.string(),
  work_date: z.string(), // YYYY-MM-DD
  clock_in: z.string().nullish(),
  clock_out: z.string().nullish(),
  status: z.string(), // present | late | leave | absent
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
export type CustomerCreate = z.infer<typeof CustomerCreateSchema>
export type MaintenanceTypeRead = z.infer<typeof MaintenanceTypeReadSchema>
export type MaintenanceTypeCreate = z.infer<typeof MaintenanceTypeCreateSchema>
export type AttendanceRecordRead = z.infer<typeof AttendanceRecordReadSchema>

export const BotUserReadSchema = z.object({
  user_id: z.string(),
  telegram_chat_id: z.number(),
  role: z.enum(['admin', 'driver']),
  driver_id: z.string().nullish(),
  driver_name: z.string().nullish(),
  created_at: z.string(),
})
export type BotUserRead = z.infer<typeof BotUserReadSchema>

export const BotInviteReadSchema = z.object({
  token: z.string(),
  driver_id: z.string().nullish(),
  driver_name: z.string().nullish(),
  role: z.enum(['admin', 'driver']),
  expires_at: z.string(),
  created_at: z.string(),
})
export type BotInviteRead = z.infer<typeof BotInviteReadSchema>

export const BotInviteResponseSchema = z.object({
  token: z.string(),
  deep_link: z.string(),
  expires_at: z.string(),
})
export type BotInviteResponse = z.infer<typeof BotInviteResponseSchema>

// ───────────────────────── UI view models ─────────────────────────
// Component-facing shapes. Fields the backend does not provide are nullable
// and render as "—" (tracked in API_ALIGNMENT.md gaps C1/C2).

export interface UiVehicle {
  id: string
  plate: string
  vehicleType: string | null // enum value (motorcycle|car|van|bus|truck)
  make: string // vendor
  model: string
  driverId: string | null // assigned driver, resolved to a name via the drivers list
  customerId: string | null
  currentKm: number | null
  insurance: string | null // insurance_valid_to
  licenseValidTo: string | null // annual רישוי (not a driver's licence)
  lastService: string | null // last_maintenance_date
  nextMaintenanceKm: number | null
  nextMaintenanceType: string | null
  maintenanceTypeId: string | null // FK into the maintenance_types catalog
  maintenanceTypeName: string | null // resolved name for display
}

export interface UiMaintenanceType {
  id: string
  name: string
  description: string | null
  intervalKm: number
  steps: string[]
}

export interface UiDriver {
  id: string
  name: string
  phone: string
  license: string
  licExpiry: string | null // drivers.license_valid_to (nullable)
  status: 'on' | 'off'
}

export interface UiCustomer {
  id: string
  name: string
  phone: string | null
  email: string | null
  status: 'active' | 'inactive'
}
