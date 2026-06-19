# WebUI ↔ Backend API Alignment

Tracks how the admin console (this service) maps onto the **real** backend services, and the
gaps where the UI needs data/endpoints that do not exist yet. Update this file as gaps close.

Legend: ✅ wired to real API · ⚠️ wired but with field gaps · ❌ no backend (mocked/placeholder)

## Auth model (applies to every Fleet API call)

`fleet-api` guards every route with two headers (`services/fleet-api/app/deps.py`):

- `X-Internal-Token` — must equal `INTERNAL_SERVICE_TOKEN`. **Secret**, must never reach the browser.
- `X-Caller-Context` — JSON `{ "role": "admin" }` (admin sees all; ownership scope enforced server-side).

The browser therefore does **not** call `fleet-api` directly. It calls the same-origin Next.js
proxy `app/api/fleet/[...path]/route.ts`, which injects both headers server-side and forwards to
`FLEET_API_URL`. Client base URL is `/api/fleet`.

`agent`, `rag`, `ollama-assistant`, `channel-gateway` do **not** require the internal token, but in
deployment they are private hostnames unreachable from the browser → they should be proxied the same
way (see gap A2).

## Section-by-section mapping

| UI section | Real endpoint(s) | Status | Notes |
|---|---|---|---|
| Login | NextAuth credentials (webui-local) | ✅ | Not a backend call. |
| Dashboard · KPIs | derived from `/vehicles` `/drivers` `/events` `/reports` `/config` | ✅ | No `/kpis` endpoint exists; computed client-side (`lib/kpis.ts` `deriveKpis`). |
| Dashboard · Alerts | `GET /events?status=open` | ✅ | Mapped from real events (`lib/alerts.ts` `alertsFromEvents`). |
| Dashboard · Urgent list | `GET /events` (open, by severity) | ⚠️ | Shown as "אירועים דחופים". No `missions` concept (gap B1). |
| Vehicles | `GET/POST /vehicles`, `DELETE /vehicles/{vehicle_id}` | ⚠️ | Field gaps C1. Delete by **UUID**. |
| Drivers | `GET/POST /drivers`, `DELETE /drivers/{driver_id}` | ⚠️ | Field gaps C2. |
| Missions | — | ❌ | No missions table/endpoint (gap B1). Page shows placeholder. |
| Attendance | — | ❌ | No employees/attendance domain at all (gap B2). Page shows placeholder. |
| Config | `GET /config`, `PUT /config/{key}` | ✅ | API returns a **list** of `{config_key,config_value,description}`; client maps to/from a record. PUT body is `{config_value}`. |
| Chat · Fleet Q&A | `POST /agent/run` | ⚠️ | Body `{query, caller_context}`; returns `{answer, tools_used, reasoning_steps}`. No citation list (gap D1) — `tools_used` shown instead. |
| Chat · Assistant | `POST /chat` (ollama-assistant) | ✅ | Body `{message}` → `{content}`. Matches. |
| Upload (hidden route) | `POST /webapp/ingest` (gateway) | ⚠️ | Multipart `phone`(req)/`text`/`file`; returns `{ok:true}` only — no sync classification result (gap D2). |
| Review queue (hidden route) | `GET /events` (candidate) | ❌ | No dedicated review-queue endpoint (gap B3). |

## Field-level gaps

### C1 — Vehicle (UI card vs `VehicleRead`)
Real fields: `vehicle_id, licensing_plate, nickname, vendor, model, current_km, insurance_valid_to,
license_valid_to, driver_id, customer_id, next_maintenance_km, next_maintenance_type,
last_maintenance_type, last_maintenance_km, last_maintenance_date, maintenance_type, allowed_driver`.

| UI field | Source | Gap |
|---|---|---|
| plate | `licensing_plate` | ✅ |
| make | `vendor` | ✅ |
| model | `model` | ✅ |
| insurance (expiry) | `insurance_valid_to` | ✅ |
| lastService | `last_maintenance_date` | ✅ |
| driver (name) | `driver_id` only | ❌ no name; needs join or embed |
| status (active/inactive) | — | ❌ vehicle has no status; UI assumes active |
| year | — | ❌ not stored |
| fuel | — | ❌ not stored |
| condition (0–100) | — | ❌ not stored; could derive from km vs next_maintenance_km |

### C2 — Driver (UI card vs `DriverRead`)
Real fields: `driver_id, full_name, phone_number, license_number, status(active|inactive)`.

| UI field | Source | Gap |
|---|---|---|
| name | `full_name` | ✅ |
| phone | `phone_number` | ✅ |
| license | `license_number` | ✅ |
| status (on/off) | `status` active→on / inactive→off | ✅ |
| licExpiry | — | ❌ lives on the vehicle (`license_valid_to`), not the driver |
| vehicle (assigned) | — | ❌ no reverse link on driver; needs vehicle→driver_id join |

## Missing endpoints (backend work, owner: fleet-api)

- **A1** Proxy auth — DONE in webui (`app/api/fleet`). Needs `INTERNAL_SERVICE_TOKEN` + `FLEET_API_URL` set.
- **A2** Proxy / CORS for `agent`, `rag`, `assistant`, `gateway` so the browser can reach them in prod.
- **B1** `missions` domain (title, priority, driver, vehicle, due, status) — or formal decision to render the Missions section from `events`.
- **B2** Attendance domain (employees + per-day clock-in/out records, monthly aggregation, PATCH day, CSV/PDF export endpoint). Entirely absent.
- **B3** Review-queue endpoint (low-confidence docs, plate mismatch, output-rail blocks) — or a documented `GET /events` filter contract.
- **C3** Vehicle: add `status`, `year`, `fuel`, `condition` (or a derivation rule), and embed assigned driver name.
- **C4** Driver: expose assigned vehicle + licence expiry (or document the join the UI must do).
- **D1** Citations on `POST /agent/run` (RAG returns `citations` on `/query`; agent drops them).
- **D2** Synchronous classification/extraction result from `POST /webapp/ingest` for the upload screen, or a status-polling contract.

## Done in this pass

- Fleet client (`lib/api/fleet.ts`) rewritten to real paths/shapes + `/api/fleet` proxy + admin caller context.
- Adapters map `VehicleRead`/`DriverRead`/`ConfigRead` → UI view models; gap fields render `—`.
- KPIs derived from real `/vehicles` `/drivers` `/events` `/reports` (`deriveKpis`); dashboard alerts from real `/events`.
- Agent / RAG / gateway / assistant clients aligned to real request/response bodies.
- Missions & Attendance pages show a "pending backend" banner pointing here.
