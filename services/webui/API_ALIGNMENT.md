# WebUI ↔ Backend API Alignment

Tracks how the admin console (this service) maps onto the **real** backend services, and the
gaps where the UI needs data/endpoints that do not exist yet. Update this file as gaps close.

Legend: ✅ wired to real API · ⚠️ wired but with field gaps · ❌ no backend (mocked/placeholder) · 🗑 removed

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
| Dashboard · KPIs | `GET /kpi/daily?limit=2` (+ `/customers` for the top-customer name) | ✅ | Six VP-grade tiles from the nightly `kpi_daily` rollup; trends derived from the latest 2 rows (`lib/kpis.ts` `deriveKpiTiles`). |
| Dashboard · Alerts | `GET /events?status=open` | ✅ | Mapped from real events (`lib/alerts.ts` `alertsFromEvents`). |
| Dashboard · Recent activity | `GET /events` (severity, then recency) | ✅ | `lib/events.ts` `sortEvents`; replaced the demo missions list. |
| Vehicles | `GET/POST /vehicles`, `DELETE /vehicles/{vehicle_id}` | ✅ | Gap C1 closed: real DB fields only; driver name via `driver_id`→drivers join. Delete by **UUID**. |
| Drivers | `GET/POST /drivers`, `DELETE /drivers/{driver_id}` | ⚠️ | Gap C2: assigned vehicle via reverse-join (done); licence expiry waits on `drivers.license_valid_to` (Phase 3). |
| Events | `GET /events` | ✅ | Replaces Missions. Full list, severity+recency order, type/severity/status/vehicle filters. |
| Attendance | — | ❌ | No employees/attendance domain yet (gap B2 → Phase 3). Page shows placeholder. |
| Config | `GET /config`, `PUT /config/{key}` | ✅ | Real numeric keys only: `license_expiring_days`, `insurance_expiring_days`, `maintenance_km_buffer`, `image_confidence_min`. PUT body `{config_value}`. |
| Chat · Fleet Q&A | `POST /agent/run` (via `/api/proxy/agent`) | ✅ | Returns `{answer, tools_used, reasoning_steps, citations}`; RAG citations render as chips (gap D1 closed). |
| Chat · Assistant | `POST /chat` (via `/api/proxy/assistant`) | ✅ | Body `{message}` → `{content}`. DB-blind. |
| Upload (hidden route) | `POST /webapp/ingest` (via `/api/proxy/gateway`) | ⚠️ | Returns `{ok:true}`; async pipeline, outcomes surface in Events (gap D2). |
| Review queue | — | 🗑 | Removed; open events in `/events` cover the attention list (gap B3 resolved by decision). |

## Field-level gaps

### C1 — Vehicle (UI card vs `VehicleRead`) — RESOLVED
The card now shows only real DB fields (plate, vendor+model, current_km, insurance/licence expiry,
last/next maintenance) and resolves the assigned driver name via `driver_id`→drivers. The invented
`year`/`fuel`/`status`/`condition` fields were dropped. Original gap detail kept below for history.

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

### C2 — Driver (UI card vs `DriverRead`) — PARTIAL
Assigned vehicle now resolved via reverse-join (`vehicle.driver_id`→plate). Licence expiry still has no
source on the driver; renders `—` until `drivers.license_valid_to` lands in Phase 3.

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
- **A2** DONE — generic same-origin proxy `app/api/proxy/[svc]/[...path]` for `agent`/`rag`/`gateway`/`assistant`
  (server-only `AGENT_URL`/`RAG_URL`/`GATEWAY_URL`/`ASSISTANT_URL`).
- **B1** RESOLVED by decision — Missions removed; the Events section renders the real `events` domain.
- **B2** Attendance domain (reuse drivers as employees + `attendance_records` table + endpoints) — Phase 3.
- **B3** RESOLVED by decision — Review queue removed; open `events` cover the attention list.
- **C1** DONE — vehicle card shows real DB fields; assigned driver name via `driver_id`→drivers join.
- **C2** Partial — assigned vehicle via reverse-join DONE; driver licence expiry needs `drivers.license_valid_to` (Phase 3).
- **D1** DONE — `POST /agent/run` returns `citations` collected from the RAG tool results;
  the webui maps them to chips in `ChatSurface`.
- **D2** Async ingest — outcomes surface in Events; no synchronous classification result by design.
- **KPIs** DONE — `kpi_daily` nightly rollup (`refresh_kpi_daily()` on pg_cron) + `GET /kpi/daily`;
  webui maps the latest 2 rows to six tiles + trend arrows (`deriveKpiTiles`).

## Done in this pass

- Fleet client (`lib/api/fleet.ts`) rewritten to real paths/shapes + `/api/fleet` proxy + admin caller context.
- Adapters map `VehicleRead`/`DriverRead`/`ConfigRead` → UI view models; gap fields render `—`.
- KPIs derived from real `/vehicles` `/drivers` `/events` `/reports` (`deriveKpis`); dashboard alerts from real `/events`.
- Agent / RAG / gateway / assistant clients aligned to real request/response bodies.
- Missions & Attendance pages show a "pending backend" banner pointing here.
