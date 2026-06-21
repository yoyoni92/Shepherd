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
| Vehicles | `GET/POST/PATCH /vehicles`, `DELETE /vehicles/{vehicle_id}` | ✅ | Full CRUD; `vehicle_type` enum (אופנוע/רכב פרטי/מסחרית/אוטובוס/משאית); driver name via `driver_id`→join. Add/edit form with strict IL guards (plate 7–8 digits). |
| Drivers | `GET/POST/PATCH /drivers`, `DELETE /drivers/{driver_id}` | ✅ | Full CRUD; add/edit form (phone 05X, licence 7–9 digits); assigned vehicle via reverse-join. |
| Customers | `GET/POST/PATCH /customers`, `DELETE /customers/{id}` | ✅ | Full CRUD section; delete unlinks vehicles (server cascade) then removes. Fields name/phone/email/status. |
| Maintenance types | `GET/POST/PATCH /maintenance-types`, `DELETE /{id}` | ✅ | Admin catalog (סוגי טיפול): name, interval_km, ordered unique step labels. `next_maintenance()` is data-driven. Vehicle references one via `maintenance_type_id`; delete blocked (409) if in use. |
| Events | `GET /events` | ✅ | Replaces Missions. Full list, severity+recency order, type/severity/status/vehicle filters. |
| Attendance | `GET /attendance/{month}`, `PATCH /attendance/{driver_id}/{date}` | ✅ | Drivers as employees; webui builds the weekday skeleton and overlays records (gap B2 closed). |
| Config | `GET /config`, `PUT /config/{key}` | ✅ | Real numeric keys only: `license_expiring_days`, `insurance_expiring_days`, `maintenance_km_buffer`, `image_confidence_min`. PUT body `{config_value}`. |
| System health | `GET /health` on each service, via `app/api/health` | ✅ | Server-side aggregator pings fleet/agent/rag/gateway/assistant `/health`; `/health` page shows status dots + latency, polls 15s. |
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

### C2 — Driver (UI card vs `DriverRead`) — RESOLVED
Assigned vehicle resolved via reverse-join (`vehicle.driver_id`→plate). Licence expiry now maps from the
nullable `drivers.license_valid_to` column (renders `—` when null).

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
- **B2** DONE — `attendance_records` table (drivers as employees) + `GET /attendance/{month}` and
  `PATCH /attendance/{driver_id}/{date}`; webui builds the weekday skeleton and overlays records.
- **B3** RESOLVED by decision — Review queue removed; open `events` cover the attention list.
- **C1** DONE — vehicle card shows real DB fields; assigned driver name via `driver_id`→drivers join.
- **C2/C4** DONE — assigned vehicle via reverse-join; driver licence expiry via nullable `drivers.license_valid_to`.
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
