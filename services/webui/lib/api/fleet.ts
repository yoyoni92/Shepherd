import { z } from 'zod'
import {
  VehicleReadSchema,
  DriverReadSchema,
  ConfigReadSchema,
  EventReadSchema,
  ReportReadSchema,
  KpiDailyReadSchema,
  CustomerReadSchema,
  AttendanceRecordReadSchema,
  AttendanceSettingsSchema,
  MaintenanceTypeReadSchema,
  BotUserReadSchema,
  BotAuthorizationReadSchema,
  AccidentReadSchema,
  CompanyReadSchema,
  CompanySettingsReadSchema,
  AppUserReadSchema,
  type CompanyRead,
  type CompanyCreate,
  type CompanyUpdate,
  type CompanySettingsRead,
  type CompanySettingsUpdate,
  type AppUserRead,
  type AppUserCreate,
  type AppUserUpdate,
  type VehicleRead,
  type MaintenanceTypeCreate,
  type VehicleCreate,
  type DriverRead,
  type DriverCreate,
  type CustomerRead,
  type CustomerCreate,
  type EventRead,
  type ReportRead,
  type BotUserRead,
  type BotAuthorizationRead,
  type AccidentCreate,
  type AttendanceSettings,
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
export const updateVehicle = (vehicleId: string, patch: Partial<VehicleCreate>): Promise<VehicleRead> =>
  send('PATCH', `/vehicles/${vehicleId}`, patch, VehicleReadSchema)
export const deleteVehicle = (vehicleId: string) =>
  send('DELETE', `/vehicles/${vehicleId}`, undefined)

// Drivers
export const fetchDrivers = () => get('/drivers', z.array(DriverReadSchema))
export const createDriver = (d: DriverCreate): Promise<DriverRead> =>
  send('POST', '/drivers', d, DriverReadSchema)
export const updateDriver = (driverId: string, patch: Partial<DriverRead>): Promise<DriverRead> =>
  send('PATCH', `/drivers/${driverId}`, patch, DriverReadSchema)
export const deleteDriver = (driverId: string) => send('DELETE', `/drivers/${driverId}`, undefined)

// Events / reports (read-only; back alerts)
export const fetchEvents = () => get('/events', z.array(EventReadSchema))
export const fetchReports = () => get('/reports', z.array(ReportReadSchema))

// Customers
export const fetchCustomers = () => get('/customers', z.array(CustomerReadSchema))
export const createCustomer = (c: CustomerCreate): Promise<CustomerRead> =>
  send('POST', '/customers', c, CustomerReadSchema)
export const updateCustomer = (customerId: string, patch: Partial<CustomerRead>): Promise<CustomerRead> =>
  send('PATCH', `/customers/${customerId}`, patch, CustomerReadSchema)
// Deleting a customer unlinks them from any vehicles server-side (cascade), then removes them.
export const deleteCustomer = (customerId: string) => send('DELETE', `/customers/${customerId}`, undefined)

// Maintenance types (admin catalog)
export const fetchMaintenanceTypes = () => get('/maintenance-types', z.array(MaintenanceTypeReadSchema))
export const createMaintenanceType = (m: MaintenanceTypeCreate) =>
  send('POST', '/maintenance-types', m, MaintenanceTypeReadSchema)
export const updateMaintenanceType = (id: string, patch: Partial<MaintenanceTypeCreate>) =>
  send('PATCH', `/maintenance-types/${id}`, patch, MaintenanceTypeReadSchema)
// Surfaces the server's Hebrew detail (e.g. "N רכבים משתמשים בסוג זה") on a blocked (409) delete.
export async function deleteMaintenanceType(id: string): Promise<void> {
  const res = await fetch(`${BASE}/maintenance-types/${id}`, { method: 'DELETE' })
  if (!res.ok) {
    let detail = `Fleet API DELETE /maintenance-types/${id}: ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* no JSON body */
    }
    throw new Error(detail)
  }
}

// KPI daily rollup: latest snapshots, newest first (dashboard tiles + trends)
export const fetchKpiDaily = (limit = 2) => get(`/kpi/daily?limit=${limit}`, z.array(KpiDailyReadSchema))

// Attendance: month is YYYY-MM; upsert one (driver, date=YYYY-MM-DD) day.
export const fetchAttendanceMonth = (month: string) =>
  get(`/attendance/${month}`, z.array(AttendanceRecordReadSchema))
export const patchAttendanceDay = (
  driverId: string,
  day: string,
  body: { clock_in?: string | null; clock_out?: string | null; status: string },
) => send('PATCH', `/attendance/${driverId}/${day}`, body, AttendanceRecordReadSchema)

// Attendance settings (company-scoped clock-in window; managed in the Attendance Configuration tab).
export const fetchAttendanceSettings = (): Promise<AttendanceSettings> =>
  get('/attendance/settings', AttendanceSettingsSchema)
export const updateAttendanceSettings = (s: AttendanceSettings): Promise<AttendanceSettings> =>
  send('PUT', '/attendance/settings', s, AttendanceSettingsSchema)

// Config: API returns a list of {config_key, config_value, description}; expose as a record.
export async function fetchConfig(): Promise<Record<string, unknown>> {
  const list = await get('/config', z.array(ConfigReadSchema))
  return Object.fromEntries(list.map((c) => [c.config_key, c.config_value]))
}
export const updateConfig = (key: string, value: unknown) =>
  send('PUT', `/config/${key}`, { config_value: value })

// Bot management
export const getBotUsers = (): Promise<BotUserRead[]> => get('/users', z.array(BotUserReadSchema))
export const updateBotUserRole = (userId: string, role: 'admin' | 'driver'): Promise<BotUserRead> =>
  send('PATCH', `/users/${userId}/role`, { role }, BotUserReadSchema)
export const getBotAuthorizations = (): Promise<BotAuthorizationRead[]> =>
  get('/bot-authorizations', z.array(BotAuthorizationReadSchema))
export const createBotAuthorization = (
  opts: { phoneNumber: string; role?: 'admin' | 'driver'; driverId?: string; expiresAt?: string },
): Promise<BotAuthorizationRead> =>
  send(
    'POST',
    '/bot-authorizations',
    {
      phone_number: opts.phoneNumber,
      role: opts.role ?? 'driver',
      driver_id: opts.driverId ?? null,
      expires_at: opts.expiresAt ?? null,
    },
    BotAuthorizationReadSchema,
  )
export const deleteBotAuthorization = (id: string): Promise<void> =>
  send('DELETE', `/bot-authorizations/${id}`, undefined)

// Accidents
export const fetchAccidents = () => get('/accidents', z.array(AccidentReadSchema))
export const createAccident = (a: AccidentCreate): Promise<{ accident_id: string }> =>
  send('POST', '/accidents', a, z.object({ accident_id: z.string() }))

// Companies (system-admin only)
export const fetchCompanies = (): Promise<CompanyRead[]> => get('/companies', z.array(CompanyReadSchema))
export const createCompany = (c: CompanyCreate): Promise<CompanyRead> =>
  send('POST', '/companies', c, CompanyReadSchema)
export const updateCompany = (companyId: string, patch: CompanyUpdate): Promise<CompanyRead> =>
  send('PATCH', `/companies/${companyId}`, patch, CompanyReadSchema)
export const deleteCompany = (companyId: string) => send('DELETE', `/companies/${companyId}`, undefined)

// Per-company settings (Drive + feature flags). Reads never expose the credentials blob.
export const fetchCompanySettings = (companyId: string): Promise<CompanySettingsRead> =>
  get(`/companies/${companyId}/settings`, CompanySettingsReadSchema)
// Surfaces the server's validate-then-persist 400 detail (e.g. "Drive folder not accessible: ...").
export async function updateCompanySettings(
  companyId: string,
  patch: CompanySettingsUpdate,
): Promise<CompanySettingsRead> {
  const res = await fetch(`${BASE}/companies/${companyId}/settings`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(patch),
  })
  if (!res.ok) {
    let detail = `Fleet API PATCH /companies/${companyId}/settings: ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* no JSON body */
    }
    throw new Error(detail)
  }
  return CompanySettingsReadSchema.parse(await res.json())
}

// App users / login management (system-admin only)
export const fetchAppUsers = (): Promise<AppUserRead[]> => get('/app-users', z.array(AppUserReadSchema))
export const createAppUser = (u: AppUserCreate): Promise<AppUserRead> =>
  send('POST', '/app-users', u, AppUserReadSchema)
export const updateAppUser = (userId: string, patch: AppUserUpdate): Promise<AppUserRead> =>
  send('PATCH', `/app-users/${userId}`, patch, AppUserReadSchema)
export const deleteAppUser = (userId: string) => send('DELETE', `/app-users/${userId}`, undefined)

export type { VehicleRead, DriverRead, EventRead, ReportRead, BotUserRead, BotAuthorizationRead }
export type { CompanyRead, AppUserRead }
