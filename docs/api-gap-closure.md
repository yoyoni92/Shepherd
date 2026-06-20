# WebUI ↔ Backend API Gap Closure — what was done

Closes every gap tracked in `services/webui/API_ALIGNMENT.md`. The Fleet Console was built from a
hi-fi design and ran on sample/preview data; this work grounds every surface to the real backend and
fills the missing backend pieces. Delivered in three phases, one commit each.

| Phase | Commit | Scope |
|-------|--------|-------|
| 1 | `align fleet console to real backend and add kpi_daily rollup` | webui alignment + KPI pipeline |
| 2 | `return RAG citations from the agent and show them in chat` | agent citations |
| 3 | `add driver licence expiry and attendance domain` | driver licence + attendance |

Verification per phase: `npm run typecheck · lint · test · build` (webui), plus `poetry run pytest`
against real Postgres (testcontainers) for `db`, `fleet-api`, and `langgraph-agent`.

---

## Phase 1 — Alignment + `kpi_daily` rollup

**Goal:** ground the UI to backend reality and stand up a real KPI pipeline.

### Data grounding
- **Vehicles** — dropped invented fields (`year`/`fuel`/`status`/`condition`); the card now shows only
  real DB columns (plate, vendor+model, current km, insurance/licence expiry, last/next maintenance).
  The assigned **driver name** is resolved by joining `driver_id` → the drivers list in the page.
- **Drivers** — assigned **vehicle** resolved by reverse-join (`vehicle.driver_id` → plate).
- **Config** — replaced invented keys with the real seeded numeric keys: `license_expiring_days`,
  `insurance_expiring_days`, `maintenance_km_buffer`, `image_confidence_min` (0–1 float stepper).

### Missions → Events (and Review removed)
- **Missions** removed entirely (no such table exists). Replaced by an **Events** section backed by the
  real `events` table: full list ordered by severity then recency, with type/severity/status/vehicle
  filters (`/events`, `EventRow`, `lib/events.ts`).
- **Review queue** removed (no endpoint); open events cover the attention list.
- Sidebar swaps משימות → **אירועים** (badge = open-events count); dashboard shows an alerts panel and a
  recent-activity panel, both from `/events`.

### Generic service proxy
- New same-origin proxy `app/api/proxy/[svc]/[...path]` for `agent`/`rag`/`gateway`/`assistant`.
  Service hostnames moved to server-only env (`AGENT_URL`/`RAG_URL`/`GATEWAY_URL`/`ASSISTANT_URL`) and
  never reach the browser. The DB-blind assistant rule is unchanged.

### KPI pipeline (`kpi_daily`)
- **DB** — new `kpi_daily` snapshot table + `refresh_kpi_daily()` SQL function aggregating fleet km/7d,
  avg km/driver, maintenance cadence, maintenance-due, docs-expiring, and top customer by km. Scheduled
  nightly via **pg_cron** (guarded on extension availability so plain Postgres still migrates); a custom
  `db/postgres.Dockerfile` ships pg_cron and compose preloads it.
- **Fleet API** — `GET /kpi/daily?limit=2` (admin-only) reads the latest snapshots.
- **WebUI** — `deriveKpiTiles` maps the latest two rows to six dashboard tiles and derives trend arrows
  (today vs yesterday); `useCustomers` resolves the top-customer name.

**Verified:** webui typecheck ✓, lint ✓, 65 tests (99% cov), build ✓ · db 26 tests ✓
(migration up/down cycle + `refresh_kpi_daily()` row math) · fleet-api 87 tests ✓.

---

## Phase 2 — Agent citations (gap D1)

**Goal:** surface the RAG citations the agent was silently dropping.

- **langgraph-agent** — the RAG tool already returns `citations` on `/query`. Added `_collect_citations`
  in the graph synthesiser node (deduped, order-preserving), threaded `citations` through agent state,
  and added a `citations` field to the `/agent/run` response.
- **WebUI** — the agent client maps `data.citations` into the reply; `ChatSurface` renders them as
  chips below the answer.

**Verified:** langgraph-agent 25 tests ✓ (citations flow through) · webui typecheck/lint/65 tests ✓.

---

## Phase 3 — Driver licence expiry + attendance

**Goal:** two nullable-everywhere additions plus a real attendance domain.

### Driver licence expiry (gaps C2/C4)
- **DB** — add nullable `drivers.license_valid_to` (migration 0004).
- **Fleet API** — `license_valid_to` on `DriverRead`/`DriverCreate` (optional); `license_number` stays
  optional.
- **WebUI** — `toUiDriver` maps `licExpiry` from `license_valid_to` (— when null); licence-expiry sort
  re-added; the add-driver form requires neither licence field.

### Attendance (gap B2) — drivers as employees
- **DB** — new `attendance_records` table (migration 0005): `(id, driver_id, work_date, clock_in,
  clock_out, status present|late|leave|absent)`, unique on `(driver_id, work_date)`.
- **Fleet API** — admin-only attendance router: `GET /attendance/{month}` returns the month's records;
  `PATCH /attendance/{driver_id}/{date}` upserts one day.
- **WebUI** — employees are drivers (role "נהג"); the weekday skeleton is generated client-side
  (`buildMonthSkeleton`) and overlaid with stored records; edits PATCH optimistically with the existing
  Zod time validation. The last preview sample data (`lib/preview.ts`, `PreviewBanner`) was deleted.

**Verified:** db 26 tests ✓ · fleet-api 91 tests ✓ (attendance upsert/month + driver licence round-trip)
· webui typecheck/lint/68 tests ✓ (100% lines), build ✓.

---

## Result

Every gap in `API_ALIGNMENT.md` is closed or resolved-by-decision. The console runs entirely on real
backend data; the only removed surfaces (Missions, Review) were dropped by design in favour of the real
`events` domain.
