import { http, HttpResponse } from 'msw'

const FLEET = process.env.NEXT_PUBLIC_FLEET_API_URL ?? 'http://localhost:8000'
const AGENT = process.env.NEXT_PUBLIC_AGENT_URL ?? 'http://localhost:8003'
const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? 'http://localhost:8001'
const ASSISTANT = process.env.NEXT_PUBLIC_ASSISTANT_URL ?? 'http://localhost:8006'

export const handlers = [
  http.get(`${FLEET}/kpis`, () =>
    HttpResponse.json({
      total_vehicles: 42,
      active_drivers: 28,
      docs_expiring_soon: 7,
      open_events: 5,
      unpaid_tickets: 3,
      maintenance_due: 4,
    }),
  ),
  http.get(`${FLEET}/config`, () =>
    HttpResponse.json({
      license_expiring_days: 30,
      insurance_expiring_days: 30,
      maintenance_km_buffer: 500,
    }),
  ),
  http.put(`${FLEET}/config/:key`, () => HttpResponse.json({ ok: true })),
  http.get(`${FLEET}/review-queue`, () =>
    HttpResponse.json([
      { id: '1', file_name: 'scan_blur.jpg', reason: 'low_confidence', confidence: 0.48, message: 'Classifier unsure of document type.', doc_type: 'uncertain' },
      { id: '2', file_name: 'doc_99x.pdf', reason: 'plate_mismatch', message: 'Extracted plate not in fleet.' },
    ]),
  ),
  http.put(`${FLEET}/review-queue/:id/:action`, () => HttpResponse.json({ ok: true })),
  http.post(`${AGENT}/agent/run`, () =>
    HttpResponse.json({
      content: 'Vehicle 12-345-67: insurance valid to 2026-09-01.',
      citations: ['vehicles · plate 12-345-67'],
      tool_calls: [],
    }),
  ),
  http.post(`${GATEWAY}/ingest/webapp`, () =>
    HttpResponse.json({
      doc_type: 'insurance_cert',
      confidence: 0.97,
      plate: '12-345-67',
      status: 'insurance_valid_to updated',
      flagged: false,
    }),
  ),
  http.post(`${ASSISTANT}/chat`, () =>
    HttpResponse.json({ content: 'Rotate every 8,000-10,000 km or with each minor service.' }),
  ),
]
