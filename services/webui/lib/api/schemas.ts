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
  phone_number: z.string().nullish(),
  driver_id: z.string().nullish(),
  driver_name: z.string().nullish(),
  expires_at: z.string().nullish(),
  created_at: z.string(),
})
export type BotUserRead = z.infer<typeof BotUserReadSchema>

export const BotAuthorizationReadSchema = z.object({
  id: z.string(),
  phone_number: z.string(),
  role: z.enum(['admin', 'driver']),
  driver_id: z.string().nullish(),
  driver_name: z.string().nullish(),
  expires_at: z.string().nullish(),
  created_at: z.string(),
})
export type BotAuthorizationRead = z.infer<typeof BotAuthorizationReadSchema>

// ───────────────────────── Companies + app users (system-admin only) ─────────────────────────

export const CompanyReadSchema = z.object({
  company_id: z.string(),
  name: z.string(),
  is_active: z.boolean(),
  created_at: z.string(),
})
export type CompanyRead = z.infer<typeof CompanyReadSchema>

export interface CompanyCreate {
  name: string
}
export interface CompanyUpdate {
  name?: string
  is_active?: boolean
}

// Per-company settings (Drive + feature flags). The raw credentials blob is never
// returned by reads - only `gdrive_configured` tells the UI whether it is set.
export const CompanySettingsReadSchema = z.object({
  company_id: z.string(),
  gdrive_folder_id: z.string().nullish(),
  gdrive_configured: z.boolean(),
  feature_flags: z.record(z.unknown()),
})
export type CompanySettingsRead = z.infer<typeof CompanySettingsReadSchema>

export interface CompanySettingsUpdate {
  gdrive_folder_id?: string | null
  gdrive_credentials_json?: string | null // write-only; never read back
  feature_flags?: Record<string, unknown> | null
}

export const AppUserReadSchema = z.object({
  user_id: z.string(),
  email: z.string(),
  role: z.string(), // admin | company_admin
  company_id: z.string().nullish(),
  is_active: z.boolean(),
  name: z.string().nullish(),
  created_at: z.string(),
})
export type AppUserRead = z.infer<typeof AppUserReadSchema>

export interface AppUserCreate {
  email: string
  password: string
  role: string
  company_id?: string | null
  name?: string | null
}
export interface AppUserUpdate {
  password?: string
  is_active?: boolean
  name?: string | null
}

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

export const AccidentAttachmentReadSchema = z.object({
  attachment_id: z.string(),
  category: z.string(),
  file_url: z.string(),
  uploaded_ts: z.string(),
})

export const AccidentReadSchema = z.object({
  accident_id: z.string(),
  vehicle_id: z.string(),
  driver_id: z.string().nullish(),
  datetime: z.string(),
  location: z.string().nullish(),
  description: z.string().nullish(),
  another_driver_licensing_plate: z.string().nullish(),
  another_driver_phone_number: z.string().nullish(),
  another_driver_id_number: z.string().nullish(),
  attachments: z.array(AccidentAttachmentReadSchema),
})

export type AccidentRead = z.infer<typeof AccidentReadSchema>
export type AccidentAttachmentRead = z.infer<typeof AccidentAttachmentReadSchema>

export interface UiAccidentAttachment {
  id: string
  category: string
  fileUrl: string
  uploadedTs: string
}

export interface UiAccident {
  id: string
  vehicleId: string
  vehiclePlate: string
  vehicleMake: string
  vehicleModel: string
  driverId: string | null
  driverName: string | null
  datetime: string
  location: string | null
  description: string | null
  anotherDriverPlate: string | null
  anotherDriverPhone: string | null
  anotherDriverIdNumber: string | null
  attachments: UiAccidentAttachment[]
}

export interface AccidentCreate {
  vehicle_id: string
  driver_id?: string
  datetime: string
  location?: string
  description?: string
  another_driver_licensing_plate?: string
  another_driver_phone_number?: string
  another_driver_id_number?: string
  attachments: { category: string; file_url: string }[]
}
