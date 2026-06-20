import { http, HttpResponse } from 'msw'

const FLEET = process.env.NEXT_PUBLIC_FLEET_BASE ?? process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8003'
const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'
const ASSISTANT = process.env.NEXT_PUBLIC_ASSISTANT_URL ?? 'http://localhost:8006'

// Real fleet-api shapes (services/fleet-api/app/schemas.py).
const VEHICLES = [
  { vehicle_id: 'v1', licensing_plate: '12-345-67', vendor: 'Toyota', model: 'Corolla', current_km: 60000, insurance_valid_to: '2026-09-02', license_valid_to: '2026-12-01', driver_id: 'd1', next_maintenance_km: 65000, last_maintenance_date: '2026-04-12' },
  { vehicle_id: 'v2', licensing_plate: '88-201-55', vendor: 'Hyundai', model: 'Tucson', current_km: 70000, insurance_valid_to: '2026-07-05', license_valid_to: '2027-01-01', driver_id: 'd2', next_maintenance_km: 68000, last_maintenance_date: '2026-03-28' },
  { vehicle_id: 'v3', licensing_plate: '45-990-12', vendor: 'Ford', model: 'Transit', current_km: 120000, insurance_valid_to: '2026-06-29', license_valid_to: '2026-06-30', driver_id: null, next_maintenance_km: 130000, last_maintenance_date: '2026-01-15' },
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

const CUSTOMERS = [
  { customer_id: 'c1', full_name: 'אלקטרה מערכות', phone_number: null, email: null, status: 'active' },
  { customer_id: 'c2', full_name: 'מובילי הצפון', phone_number: null, email: null, status: 'active' },
]

const KPI_DAILY = [
  { snapshot_date: '2026-06-19', total_km_7d: 1200, avg_km_per_driver_7d: 300, avg_days_between_maintenance: 45, maintenance_due_count: 2, docs_expiring_count: 3, top_customer_id: 'c1', top_customer_km: 800, top_customer_vehicle_count: 2, computed_ts: '2026-06-19T03:00:00Z' },
  { snapshot_date: '2026-06-18', total_km_7d: 1000, avg_km_per_driver_7d: 250, avg_days_between_maintenance: 45, maintenance_due_count: 4, docs_expiring_count: 3, top_customer_id: 'c1', top_customer_km: 700, top_customer_vehicle_count: 2, computed_ts: '2026-06-18T03:00:00Z' },
]

const CONFIG = [
  { config_key: 'license_expiring_days', config_value: 30, description: 'days ahead to warn on רישוי' },
  { config_key: 'insurance_expiring_days', config_value: 30, description: 'days ahead to warn on insurance' },
  { config_key: 'maintenance_km_buffer', config_value: 1000, description: 'km before next service to alert' },
  { config_key: 'image_confidence_min', config_value: 0.7, description: 'min classifier confidence' },
]

export const handlers = [
  // Vehicles
  http.get(`${FLEET}/vehicles`, () => HttpResponse.json(VEHICLES)),
  http.post(`${FLEET}/vehicles`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ vehicle_id: 'v99', ...body }, { status: 201 })
  }),
  http.delete(`${FLEET}/vehicles/:id`, () => new HttpResponse(null, { status: 204 })),

  // Drivers
  http.get(`${FLEET}/drivers`, () => HttpResponse.json(DRIVERS)),
  http.post(`${FLEET}/drivers`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>
    return HttpResponse.json({ driver_id: 'd99', status: 'active', ...body }, { status: 201 })
  }),
  http.delete(`${FLEET}/drivers/:id`, () => new HttpResponse(null, { status: 204 })),

  // Events / reports
  http.get(`${FLEET}/events`, () => HttpResponse.json(EVENTS)),
  http.get(`${FLEET}/reports`, () => HttpResponse.json(REPORTS)),

  // Customers + KPI daily rollup
  http.get(`${FLEET}/customers`, () => HttpResponse.json(CUSTOMERS)),
  http.get(`${FLEET}/kpi/daily`, () => HttpResponse.json(KPI_DAILY)),

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

  // Agent (real contract)
  http.post(`${AGENT}/agent/run`, () =>
    HttpResponse.json({
      answer: 'רכב 12-345-67: הביטוח בתוקף עד 02/09/2026.',
      tools_used: ['fleet_api', 'rag'],
      reasoning_steps: [],
      citations: ['vehicle-profile-12-345-67'],
    }),
  ),
  // Gateway (real contract)
  http.post(`${GATEWAY}/webapp/ingest`, () => HttpResponse.json({ ok: true })),
  // Ollama assistant
  http.post(`${ASSISTANT}/chat`, () => HttpResponse.json({ content: 'מחליפים שמן כל 10-15 אלף ק״מ.' })),
]
