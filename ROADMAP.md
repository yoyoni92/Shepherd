# Shepherd - Roadmap

## Done

### Phase 1 - Foundation
- `libs/` shared Pydantic contracts and provider interfaces
- `db/` Postgres schema, migrations 0001-0009, seed data
- `services/fleet-api` - REST API, SQLAlchemy ORM, 85 tests

### Phase 2 - AI Services
- `services/channel-gateway` - Telegram + webapp inbound, S3 media, n8n forwarding
- `services/doc-extractor` - Bedrock + Gemini vision extractors, reconcile-by-plate
- `services/rag` - multilingual embeddings, Chroma vector index, LangChain/Claude generator
- `services/langgraph-agent` - LangGraph planner -> tool-exec -> synthesiser, Fleet API + RAG tools
- `services/guardrails` - auth + language pre-checks, topic + grounding rails

### Phase 3 - UX + Operations
- `services/webui` - Next.js 15 admin console (dashboard, Fleet Chat, Upload, Review Queue, Bot Management)
- `services/telegram-bot` - invite-only Hebrew Telegram bot (aiogram 3, long-polling), driver + admin flows (replaces n8n)

---

## Up Next

### CI/CD - Full Lifecycle Pipeline

**What**: Replace the stub `.github/workflows/ci.yml` (today it only runs `libs/` tests) with a
complete GitHub Actions pipeline that covers every package: **lint (ruff) -> typecheck (mypy) ->
test (pytest) -> build Docker image -> push to Docker Hub**.

**Why**: All 11 services plus `libs/` share one Poetry/ruff/mypy/pytest toolchain, yet CI only
exercises `libs/`. The `Makefile` already exposes `lint`, `typecheck`, and `test` targets, so CI
should run them uniformly to catch regressions before merge and publish images automatically.

**Scope**:

| Layer | What |
|-------|------|
| Matrix | One job per package (`libs/` + each `services/*`), path-filtered so only changed packages run |
| Quality gates | Reuse Makefile targets: `make lint`, `make typecheck`, `make test` per package |
| Build + push | On merge to `main`, build each service's `Dockerfile` and push to the Docker Hub global registry, tagged `org/shepherd-<service>:<git-sha>` and `:latest` |
| Secrets | `DOCKERHUB_USERNAME` / `DOCKERHUB_TOKEN` as repo secrets |

**Approach**:
1. Path-filtered matrix discovers changed packages.
2. Each matrix leg runs `make lint typecheck test` against its package.
3. A build-and-push stage gated on `main` uses `docker/build-push-action` to publish images.

**Outcome**: every push is lint-, type-, and test-checked; every merge to `main` publishes fresh
service images to the Docker Hub global registry.

---

### MkDocs - Unified Monorepo Documentation Site

**What**: A single browsable docs site built with **MkDocs + Material theme**, using
**mkdocstrings[python]** to auto-generate API reference from docstrings across `libs/` and every
service, alongside the existing narrative docs (`docs/`, service READMEs, `plans/`).

**Why**: Documentation is scattered across the root README, per-service READMEs, `docs/`, and
`plans/`. mkdocstrings turns the Python packages' docstrings into live API reference, and Material
gives one navigable, searchable home for everything in the monorepo.

**Scope**:

| Layer | What |
|-------|------|
| Site config | `mkdocs.yml` + a `docs/` nav structure spanning guides and API reference |
| Auto API ref | mkdocstrings `[python]` handler pointing at each package's `app/` / `libs/` modules |
| Theme | Material (search, dark mode), aligned to the project's existing dark, Hebrew-aware aesthetic where reasonable |
| Publish | CI job that builds the site and deploys to GitHub Pages on merge to `main` |

**Approach**:
1. Add `mkdocs`, `mkdocs-material`, `mkdocstrings[python]` as a docs dependency group.
2. Author `mkdocs.yml` with auto-reference pages per package.
3. Run `mkdocs gh-deploy` from the CI pipeline (above) on merge to `main`.

**Outcome**: one published docs site, auto-refreshed on every merge, combining hand-written guides
with docstring-driven API reference for the whole monorepo.

---

### Observability - Langfuse

**What**: Integrate [Langfuse](https://langfuse.com) as the LLM observability layer across all AI services.

**Why**: The project has four independent AI surfaces (rag, langgraph-agent, guardrails, doc-extractor) each logging prompts locally (V1-V5 prompt logs). Langfuse replaces ad-hoc logging with a unified trace/span model, eval scores, and a cost dashboard - all without changing inference code.

**Scope**:

| Service | What to instrument |
|---------|--------------------|
| `langgraph-agent` | Trace per `/agent/run` call; spans for planner, each tool, synthesiser |
| `rag` | Span per `/query`; log retrieved chunks + rerank scores as observations |
| `guardrails` | Spans for input-check + output-check; score pass/fail + detected language |
| `doc-extractor` | Span per extraction; log provider (Bedrock/Gemini), plate, confidence |

**Approach**:
1. Add `langfuse` to each affected service's `pyproject.toml`.
2. Use `langfuse.decorators.observe` on the function boundaries above - zero boilerplate.
3. Pass `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` via `.env` (self-hosted or cloud).
4. Add Langfuse container to `docker-compose.yml` for local dev (Postgres backend already present).
5. Wire evals: thumbs-up/down from WebUI Fleet Chat -> `langfuse.score()`.

**Outcome**: single pane of glass for latency, cost, prompt regressions, and user satisfaction scores across all AI surfaces.

---

### Mobile App - Driver + Admin on Mobile

**What**: One installable iOS/Android app with **two role-aware surfaces** built on the
existing WebUI design system: an **admin** surface (the `services/webui` console) and a
**driver** surface that brings today's Telegram-bot driver flows into the same UI. Both
run over the same Fleet API.

**Why**: Shepherd's two audiences are split across two front-ends - admins use the Next.js
console, drivers use the Telegram bot. A single app puts both on the phone, **fully aligned
to the UI**: the Hebrew-first RTL layout, dark theme, `Assistant` font, and shadcn/ui
components are reused for the driver screens too, so the driver experience looks and feels
like the console instead of a chat thread. The bot stays as-is; the app is an additional,
richer surface over the same backend.

**Scope**:

| Surface / Layer | What |
|-----------------|------|
| Admin surface | The existing console - dashboard, vehicles, drivers, customers, events, accidents, maintenance, upload/review, bot management, chat/assistant, config - reused unchanged |
| Driver surface | The bot's driver activities as native screens in the WebUI design system: clock in/out, report vehicle issue, accident wizard (photos/video), update my details, monthly attendance, my vehicle - all via the same Fleet API endpoints the bot calls |
| Role + auth | Drivers authenticate by phone (Fleet `/bot-enroll` + `/whoami`, mirroring the bot); admins via `next-auth` credentials. Role decides which surface (and nav) is shown. Secure token storage (Keychain / Keystore) |
| Responsive pass | Adapt the desktop-first `Shell` (sidebar + topbar) to mobile - drawer / bottom-nav, touch targets, mobile breakpoints - and design the driver surface mobile-first |
| PWA baseline | `manifest.webmanifest` (icons, theme color, RTL, dark) + service worker: installable, offline-tolerant app shell, no store required |
| Native shell | Wrap the same web app with **Capacitor** to ship signed iOS/Android store binaries |
| Native bridges | Push notifications (admin alerts/events; driver broadcasts), camera (accident photos + doc upload), geolocation (feeds the **Bot Action Location Capture** item) |

**Approach**:
1. Build the driver surface as new routes/screens in `services/webui`, reusing its Fleet API
   clients + design system - no new UI language. Gate by role alongside the admin routes.
2. Make the whole app responsive - it must look right in a phone viewport before wrapping.
3. Add the PWA manifest + service worker (installable, ~zero native code).
4. Add a Capacitor project pointing at the deployed WebUI; integrate
   `@capacitor/push-notifications`, `@capacitor/camera`, `@capacitor/geolocation`.
5. CI to produce signed builds; distribute via TestFlight / Play internal testing.

**Outcome**: a store-installable app where drivers and admins each get a role-appropriate
view - the driver flows that used to be Telegram-only now rendered in the same design system
as the console - plus native push, camera, and location, with one UI codebase over one API.

**Open questions**: do the Telegram bot and the driver app **coexist** indefinitely, or is the
app meant to eventually replace the bot for drivers? Distribution model (internal/enterprise vs
public stores)? Driver session lifetime / re-auth policy on mobile (the bot has no logout)?

---

### Evals - Automated Regression Suite

Run the existing `eval/` harness on every CI push against a golden fixture set; gate merges on pass rate >= 95%.

### Image Analyser

`services/image-analyser` skeleton exists. Wire it into the bot's accident flow as a vision step after photo upload.

### RAG - Incremental Index Updates

Currently the Chroma index is rebuilt from scratch. Add a diff-based update triggered by Fleet API vehicle-profile change events.

### WhatsApp Channel

Channel-gateway has a WhatsApp seam (stub). Implement the provider and wire Twilio/WhatsApp Business credentials.

### Bot Action Location Capture (admin-only)

**What**: Whenever a driver taps a bot button that writes to the backend (clock
in/out, accident, vehicle issue, maintenance, detail updates, doc scan), record the
driver's location with that action and **store it for later use**. Best-effort and
optional; kept admin-side, never shown to the driver. No reporting/geofencing required
up front - just capture and store the point per action.

**Constraint (researched)**: Telegram has **no silent location**. The plain chat bot
only gets one-shot, user-initiated shares (`request_location` button or user-started
live location, ≤8h); a bot never sees the user's IP. The only persistent "allow once"
is the Mini App `LocationManager` (Bot API 8.0) - but it works only while the Mini App
is open and requires building a Mini App. Full analysis:
[`docs/research/2026-06-26-telegram-location-options.md`](docs/research/2026-06-26-telegram-location-options.md).

**Recommended approach** (no Mini App): capture a location share **once** (a
`request_location` button at clock-in, or accept a user-started live location), cache
the **last-known point per chat**, and attach it to every subsequent bot DB write -
best-effort and optional (null when never shared). Store via a single admin-only
**activity/location log** (driver_id, action, timestamp, lat/lon, optional
reverse-geocoded address) rather than adding lat/lon to six domain tables.

**Scope**: `normalize_message` to capture `m.location`; a per-chat last-known-location
cache; a Fleet API endpoint + `bot_activity` table; reverse-geocode the point to an
address; admin-only display in the WebUI attendance/activity views. Reverse geocoding
adds an external geocoding API dependency.

**Open question**: which event triggers the one-time share (clock-in vs enrollment),
and the staleness budget before re-prompting.
