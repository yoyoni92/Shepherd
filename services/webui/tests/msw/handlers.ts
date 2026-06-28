import { http, HttpResponse } from 'msw'

const FLEET = process.env.NEXT_PUBLIC_FLEET_BASE ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'

// Real fleet-api shapes (services/fleet-api/app/schemas.py).
const VEHICLES = [
  { vehicle_id: 'v1', licensing_plate: '12-345-67', vehicle_type: 'car', vendor: 'Toyota', model: 'Corolla', current_km: 60000, insurance_valid_to: '2026-09-02', license_valid_to: '2026-12-01', driver_id: 'd1', customer_id: 'c1', next_maintenance_km: 65000, last_maintenance_date: '2026-04-12' },
  { vehicle_id: 'v2', licensing_plate: '88-201-55', vehicle_type: 'van', vendor: 'Hyundai', model: 'Tucson', current_km: 70000, insurance_valid_to: '2026-07-05', license_valid_to: '2027-01-01', driver_id: 'd2', customer_id: 'c1', next_maintenance_km: 68000, last_maintenance_date: '2026-03-28' },
  { vehicle_id: 'v3', licensing_plate: '45-990-12', vehicle_type: 'truck', vendor: 'Ford', model: 'Transit', current_km: 120000, insurance_valid_to: '2026-06-29', license_valid_to: '2026-06-30', driver_id: null, customer_id: null, next_maintenance_km: 130000, last_maintenance_date: '2026-01-15' },
]

const DRIVERS = [
  { driver_id: 'd1', full_name: 'דנה לוי', phone_number: '050-123-4567', license_number: 'IL-4485219', license_valid_to: '2027-03-01', status: 'active' },
  { driver_id: 'd2', full_name: 'יוסי מזרחי', phone_number: '052-998-1120', license_number: 'IL-3320981', license_valid_to: null, status: 'inactive' },
]

const EVENTS = [
  { event_id: 'e1', vehicle_id: 'v3', event_type: 'insurance_expiring', severity: 'critical', message: 'ביטוח חובה פג בקרוב', status: 'open', triggered_ts: '2026-06-18T08:00:00Z' },
  { event_id: 'e2', vehicle_id: 'v2', event_type: 'maintenance_due', severity: 'warning', message: 'טיפול תקופתי נדרש', status: 'open', triggered_ts: '2026-06-17T08:00:00Z' },
  { event_id: 'e3', vehicle_id: 'v1', event_type: 'ticket_received', severity: 'info', message: 'דוח חניה התקבל', status: 'resolved', triggered_ts: '2026-06-10T08:00:00Z' },
]

const REPORTS = [
  { report_id: 'r1', vehicle_id: 'v2', ticket_type: 'parking', status: 'unpaid', amount: 500 },
  { report_id: 'r2', vehicle_id: 'v1', ticket_type: 'traffic', status: 'paid', amount: 250 },
]

const MAINTENANCE_TYPES = [
  { id: 'mt1', name: 'קטן ואז גדול', description: null, interval_km: 10000, steps: ['קטן', 'גדול'] },
  { id: 'mt2', name: 'שניים קטנים ואז גדול', description: null, interval_km: 10000, steps: ['קטן א׳', 'קטן ב׳', 'גדול'] },
]

const CUSTOMERS = [
  { customer_id: 'c1', full_name: 'אלקטרה מערכות', phone_number: null, email: null, status: 'active' },
  { customer_id: 'c2', full_name: 'מובילי הצפון', phone_number: null, email: null, status: 'active' },
]

const KPI_DAILY = [
  { snapshot_date: '2026-06-19', total_km_7d: 1200, avg_km_per_driver_7d: 300, avg_days_between_maintenance: 45, docs_expiring_count: 3, top_customer_id: 'c1', top_customer_km: 800, top_customer_vehicle_count: 2, computed_ts: '2026-06-19T03:00:00Z' },
  { snapshot_date: '2026-06-18', total_km_7d: 1000, avg_km_per_driver_7d: 250, avg_days_between_maintenance: 45, docs_expiring_count: 3, top_customer_id: 'c1', top_customer_km: 700, top_customer_vehicle_count: 2, computed_ts: '2026-06-18T03:00:00Z' },
]

const ACCIDENTS = [
  {
    accident_id: 'a1', vehicle_id: 'v1', driver_id: 'd1',
    datetime: '2026-06-10T09:30:00', location: 'תל אביב', description: 'פגיעה קלה',
    another_driver_licensing_plate: null, another_driver_phone_number: null, another_driver_id_number: null,
    attachments: [
      { attachment_id: 'att1', category: 'photo_our_vehicle', file_url: 's3://shepherd-accidents/a1/photo.jpg', uploaded_ts: '2026-06-10T10:00:00' },
    ],
  },
  {
    accident_id: 'a2', vehicle_id: 'v2', driver_id: null,
    datetime: '2026-05-20T14:00:00', location: null, description: null,
    another_driver_licensing_plate: '77-777-77', another_driver_phone_number: '054-111-2222', another_driver_id_number: '123456789',
    attachments: [],
  },
]

const COMPANIES = [
  { company_id: 'co1', name: 'ברירת מחדל', is_active: true, created_at: '2026-01-01T00:00:00Z' },
  { company_id: 'co2', name: 'מובילי הדרום', is_active: false, created_at: '2026-02-01T00:00:00Z' },
]

const APP_USERS = [
  { user_id: 'au1', email: 'admin@fleetops.io', role: 'admin', company_id: null, is_active: true, name: 'מנהל', is_system_admin: true, phone_number: '+972500000000', created_at: '2026-01-01T00:00:00Z' },
  { user_id: 'au2', email: 'ca@co1.io', role: 'company_admin', company_id: 'co1', is_active: true, name: 'מנהל חברה', is_system_admin: false, phone_number: null, created_at: '2026-01-02T00:00:00Z' },
]

const CONFIG = [
  { config_key: 'license_expiring_days', config_value: 30, description: 'days ahead to warn on רישוי' },
  { config_key: 'insurance_expiring_days', config_value: 30, description: 'days ahead to warn on insurance' },
  { config_key: 'maintenance_km_buffer', config_value: 1000, description: 'km before next service to alert' },
  { config_key: 'km_max_increment', config_value: 10000, description: 'max km increase per update' },
  { config_key: 'image_confidence_min', config_value: 0.7, description: 'min classifier confidence' },
]

export const handlers = [
  // Vehicles
  http.get(`${FLEET}/vehicles`, () => HttpResponse.json(VEHICLES)),
  http.post(`${FLEET}/vehicles`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ vehicle_id: 'v99', ...body }, { status: 201 })
  }),
  http.patch(`${FLEET}/vehicles/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ vehicle_id: params.id, licensing_plate: '12-345-67', ...body })
  }),
  http.delete(`${FLEET}/vehicles/:id`, () => new HttpResponse(null, { status: 204 })),

  // Drivers
  http.get(`${FLEET}/drivers`, () => HttpResponse.json(DRIVERS)),
  http.post(`${FLEET}/drivers`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ driver_id: 'd99', status: 'active', ...body }, { status: 201 })
  }),
  http.patch(`${FLEET}/drivers/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ driver_id: params.id, full_name: 'n', phone_number: 'p', status: 'active', ...body })
  }),
  http.delete(`${FLEET}/drivers/:id`, () => new HttpResponse(null, { status: 204 })),

  // Accidents
  http.get(`${FLEET}/accidents`, () => HttpResponse.json(ACCIDENTS)),
  http.post(`${FLEET}/accidents`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ accident_id: 'a99', ...body }, { status: 201 })
  }),

  // Events / reports
  http.get(`${FLEET}/events`, () => HttpResponse.json(EVENTS)),
  http.get(`${FLEET}/reports`, () => HttpResponse.json(REPORTS)),

  // Customers + KPI daily rollup
  http.get(`${FLEET}/customers`, () => HttpResponse.json(CUSTOMERS)),
  http.post(`${FLEET}/customers`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ customer_id: 'c99', status: 'active', ...body }, { status: 201 })
  }),
  http.patch(`${FLEET}/customers/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ customer_id: params.id, full_name: 'n', status: 'active', ...body })
  }),
  http.delete(`${FLEET}/customers/:id`, () => new HttpResponse(null, { status: 204 })),

  // Maintenance types (admin catalog)
  http.get(`${FLEET}/maintenance-types`, () => HttpResponse.json(MAINTENANCE_TYPES)),
  http.post(`${FLEET}/maintenance-types`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ id: 'mt99', ...body }, { status: 201 })
  }),
  http.patch(`${FLEET}/maintenance-types/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ id: params.id, name: 'n', interval_km: 10000, steps: ['x'], ...body })
  }),
  http.delete(`${FLEET}/maintenance-types/:id`, () => new HttpResponse(null, { status: 204 })),

  http.get(`${FLEET}/kpi/daily`, () => HttpResponse.json(KPI_DAILY)),

  // Attendance settings (company-scoped window) - must precede the :month read below
  http.get(`${FLEET}/attendance/settings`, () =>
    HttpResponse.json({
      enabled: false,
      start: '07:00',
      end: '17:00',
      work_days: [0, 1, 2, 3, 4],
      chag_working: false,
      erev_chag_working: true,
    }),
  ),
  http.put(`${FLEET}/attendance/settings`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json(body)
  }),

  // Attendance: month read returns one stored record for d1; PATCH echoes the upsert
  http.get(`${FLEET}/attendance/:month`, ({ params }) =>
    HttpResponse.json([
      { driver_id: 'd1', work_date: `${params.month}-02`, clock_in: '08:05', clock_out: '17:00', status: 'late' },
    ]),
  ),
  http.patch(`${FLEET}/attendance/:driverId/:day`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ driver_id: params.driverId, work_date: params.day, ...body })
  }),

  // Config (list shape)
  http.get(`${FLEET}/config`, () => HttpResponse.json(CONFIG)),
  http.put(`${FLEET}/config/:key`, async ({ params, request }) => {
    const body = (await request.json()) as { config_value: unknown }
    return HttpResponse.json({ config_key: params.key, config_value: body.config_value, description: null })
  }),

  // Companies (system-admin only)
  http.get(`${FLEET}/companies`, () => HttpResponse.json(COMPANIES)),
  http.post(`${FLEET}/companies`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ company_id: 'co99', is_active: true, created_at: '2026-06-26T00:00:00Z', ...body }, { status: 201 })
  }),
  http.patch(`${FLEET}/companies/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ company_id: params.id, name: 'n', is_active: true, created_at: '2026-06-26T00:00:00Z', ...body })
  }),
  http.delete(`${FLEET}/companies/:id`, () => new HttpResponse(null, { status: 204 })),

  // Per-company settings (Drive credentials redacted to gdrive_configured + feature flags)
  http.get(`${FLEET}/companies/:id/settings`, ({ params }) =>
    HttpResponse.json({
      company_id: params.id,
      gdrive_folder_id: 'folder-1',
      gdrive_configured: true,
      feature_flags: { attendance: false },
    }),
  ),
  http.patch(`${FLEET}/companies/:id/settings`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({
      company_id: params.id,
      gdrive_folder_id: (body.gdrive_folder_id as string) ?? null,
      gdrive_configured: true,
      feature_flags: (body.feature_flags as Record<string, unknown>) ?? {},
    })
  }),

  // App users (system-admin only)
  http.get(`${FLEET}/app-users`, () => HttpResponse.json(APP_USERS)),
  http.post(`${FLEET}/app-users`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ user_id: 'au99', is_active: true, is_system_admin: false, phone_number: null, created_at: '2026-06-26T00:00:00Z', ...body }, { status: 201 })
  }),
  http.patch(`${FLEET}/app-users/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ user_id: params.id, email: 'e@x.io', role: 'company_admin', company_id: 'co1', is_active: true, name: null, is_system_admin: false, phone_number: null, created_at: '2026-06-26T00:00:00Z', ...body })
  }),
  http.delete(`${FLEET}/app-users/:id`, () => new HttpResponse(null, { status: 204 })),

  // System health aggregator (same-origin Next route)
  http.get('*/api/health', () =>
    HttpResponse.json({
      services: [{ key: 'fleet', status: 'up', latencyMs: 12 }],
      checkedAt: '2026-06-20T10:00:00Z',
    }),
  ),
]
