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
  { driver_id: 'd1', full_name: 'דנה לוי', phone_number: '050-123-4567', license_number: 'IL-4485219', status: 'active' },
  { driver_id: 'd2', full_name: 'יוסי מזרחי', phone_number: '052-998-1120', license_number: 'IL-3320981', status: 'inactive' },
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

const CONFIG = [
  { config_key: 'docs_expiry_warning_days', config_value: 30, description: 'days ahead to warn' },
  { config_key: 'condition_min_alert', config_value: 60, description: 'maintenance threshold' },
  { config_key: 'low_confidence_threshold', config_value: 70, description: 'review queue threshold' },
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

  // Config (list shape)
  http.get(`${FLEET}/config`, () => HttpResponse.json(CONFIG)),
  http.put(`${FLEET}/config/:key`, async ({ params, request }) => {
    const body = (await request.json()) as { config_value: unknown }
    return HttpResponse.json({ config_key: params.key, config_value: body.config_value, description: null })
  }),

  // Review queue (gap B3 — still mocked)
  http.get(`${FLEET}/review-queue`, () =>
    HttpResponse.json([
      { id: '1', file_name: 'scan_blur.jpg', reason: 'low_confidence', confidence: 0.48, message: 'Classifier unsure.', doc_type: 'uncertain' },
      { id: '2', file_name: 'doc_99x.pdf', reason: 'plate_mismatch', message: 'Plate not in fleet.' },
    ]),
  ),
  http.put(`${FLEET}/review-queue/:id/:action`, () => HttpResponse.json({ ok: true })),

  // Agent (real contract)
  http.post(`${AGENT}/agent/run`, () =>
    HttpResponse.json({
      answer: 'רכב 12-345-67: הביטוח בתוקף עד 02/09/2026.',
      tools_used: ['fleet_api', 'rag'],
      reasoning_steps: [],
    }),
  ),
  // Gateway (real contract)
  http.post(`${GATEWAY}/webapp/ingest`, () => HttpResponse.json({ ok: true })),
  // Ollama assistant
  http.post(`${ASSISTANT}/chat`, () => HttpResponse.json({ content: 'מחליפים שמן כל 10-15 אלף ק״מ.' })),
]
