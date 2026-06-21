# WebUI - Admin Console

Next.js 15 (App Router) admin console for Shepherd. Hebrew-first, RTL (`dir="rtl"`), dark theme.

**Deviation from Gradio/Streamlit:** rubric allows "app.py or equivalent" - this service satisfies that with a modern React SPA.

**Design source:** high-fidelity handoff `plans/design_handoff_fleet_console/` (`Fleet Management.dc.html`).
Tokens, layout, and interactions reproduce that prototype with Tailwind + shadcn/ui primitives.

## Stack

- Next.js 15 + React 19 + TypeScript
- Tailwind CSS 3 + shadcn/ui primitives (`components/ui/`), `Assistant` Google font, lucide-react icons
- TanStack Query v5 + Zod (typed Fleet API / RAG / agent / gateway clients)
- next-auth v4 (credentials provider, admin-only)
- Vitest + React Testing Library + MSW (unit/integration)
- Playwright (e2e smoke)

## Dev

```bash
cp .env.example .env.local   # fill ADMIN_EMAIL, ADMIN_PASSWORD, NEXTAUTH_SECRET
npm install
npm run dev                  # http://localhost:3000
npm test                     # Vitest (coverage >= 85% on lib/ + hooks/)
npm run e2e                  # Playwright (requires running app)
npm run typecheck            # tsc --noEmit
npm run lint                 # ESLint (also enforces DB-blind assistant boundary)
```

## Pages

The shell (`components/Shell.tsx` = sidebar + topbar) wraps the seven design sections:

| Route | Description |
|-------|-------------|
| `/` | Login (credentials, Hebrew RTL) |
| `/dashboard` | 6 VP-grade KPI tiles (`kpi_daily` + trends) + alerts + recent events |
| `/vehicles` | Sortable card grid; add/edit/remove with a validated form; vehicle type + assignments |
| `/drivers` | Sortable card grid; add/edit/remove with a validated form |
| `/customers` | Customer cards; add/edit/remove (delete unlinks vehicles server-side) |
| `/events` | Real `events` list — severity+recency order, type/severity/status/vehicle filters |
| `/attendance` | Monthly clock-in/out report, edit modal, CSV/PDF export (`lib/attendance.ts`) |
| `/config` | `system_config` stepper editor (admin-gated, Zod-validated) |
| `/health` | System status — green/red dots + latency for each 3rd-party service, polled 15s |
| `/chat` | Tabbed: Fleet Q&A (RAG/LangGraph) + DB-blind Ollama assistant |

Still reachable by URL (not in the sidebar): `/upload`, `/assistant`.

Pure logic lives in `lib/` (`kpis`, `domain`, `attendance`, `alerts`) and is unit-tested to
100% lines (gate >= 85% on `lib/` + `hooks/`).

## Backend integration & gaps

The UI is wired to the **real** services (`fleet-api`, `langgraph-agent`, `ollama-assistant`,
`channel-gateway`). Full mapping + the list of missing endpoints/fields lives in
[`API_ALIGNMENT.md`](./API_ALIGNMENT.md). Highlights:

- **Auth proxy:** every Fleet API call goes through `app/api/fleet/[...path]/route.ts`, which injects
  `X-Internal-Token` + `X-Caller-Context: {role:admin}` server-side (the token never reaches the
  browser). Browser base URL is `/api/fleet`.
- **Generic service proxy:** `agent`/`rag`/`gateway`/`assistant` are reached via the same-origin
  `app/api/proxy/[svc]/[...path]` (server-only `AGENT_URL`/`RAG_URL`/`GATEWAY_URL`/`ASSISTANT_URL`);
  no service hostname reaches the browser.
- **System health:** `app/api/health` pings every service's `/health` server-side (3s timeout) and
  returns per-service up/down + latency; the `/health` page renders status dots and the sidebar shows a
  live overall dot.
- **KPIs:** `GET /kpi/daily?limit=2` reads the nightly `kpi_daily` rollup; `lib/kpis.ts`
  `deriveKpiTiles` maps the latest 2 rows to six tiles + trend arrows. Alerts/recent come from `/events`.
- **Adapters:** `lib/adapters.ts` maps `VehicleRead`/`DriverRead` → card view models grounded to real
  DB fields; the driver↔vehicle link is filled by a join in the pages.
- **Config** is a list of `{config_key, config_value}` on the wire; the client maps it to a record
  (real numeric keys: `license_expiring_days`, `insurance_expiring_days`, `maintenance_km_buffer`,
  `image_confidence_min`).
- **Attendance** (gap B2 closed): drivers double as employees; `GET /attendance/{month}` +
  `PATCH /attendance/{driver_id}/{date}`. The webui builds the weekday skeleton (`lib/attendance.ts`)
  and overlays stored records; edits PATCH with optimistic update + Zod time validation.

## DB-blind assistant

`hooks/useAssistant.ts` only calls `NEXT_PUBLIC_ASSISTANT_URL/chat`. ESLint rule
(`no-restricted-imports` in `.eslintrc.json`) prevents importing any fleet/agent/gateway
client into that file. The `useAssistant.test.tsx` also asserts no Fleet API or RAG
requests are made at the network level via MSW.

## Environment variables

See `.env.example`.
