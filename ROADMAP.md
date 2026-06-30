# Shepherd - Roadmap

## Done

### Phase 1 - Foundation
- `libs/` shared Pydantic contracts and provider interfaces
- `db/` Postgres schema, migrations 0001-0009, seed data
- `services/fleet-api` - REST API, SQLAlchemy ORM, 85 tests

### Phase 2 - AI Services (removed)
An earlier doc-ingest pipeline (channel-gateway, doc-extractor) and chat/RAG stack
(rag, langgraph-agent, guardrails, ollama-assistant) were built and later removed -
the bot's native Gemini doc scan superseded the pipeline, and a fresh
Google-Drive-files RAG is planned to replace the chat/RAG stack.

### Phase 3 - UX + Operations
- `services/webui` - Next.js 15 admin console (dashboard, entity CRUD, Config, Bot Management, health)
- `services/telegram-bot` - phone-enrolled Hebrew Telegram bot (aiogram 3, long-polling), driver + admin flows

### Phase 4 - Delivery
- `.github/workflows/ci.yml` - full lifecycle CI pipeline: path-filtered per-package quality gates
  (lint/typecheck/test reusing the Makefile, one leg per changed package), lint and mypy enforced
  repo-wide across all 5 packages, and a build/push matrix publishing
  `ghcr.io/<owner>/shepherd-<svc>:<sha>` + `:latest` as private GHCR packages on merge to main.
  Auth uses the built-in `GITHUB_TOKEN` (`packages: write`); no registry secrets required.
- `deploy/` - production operator runbook: pull-only `docker-compose.prod.yml` (pre-built GHCR
  images, no git clone), `deploy.sh` idempotent deploy script, `config.example.toml` and
  `.env.example` templates.
- `libs/shepherd_config` - central `config.toml` (path via `SHEPHERD_CONFIG`) holds the DB
  connection string and company-to-schema map; loaded with `${VAR}` env interpolation. Fleet-api
  and telegram-bot source all connection config from it.
- Schema-per-tenant: domain tables live in per-company Postgres schemas, routed via
  `schema_translate_map`; `company_id` row scoping is still enforced and is load-bearing when
  companies share a schema.

---

## Up Next

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
| Admin surface | The existing console - dashboard, vehicles, drivers, customers, events, accidents, maintenance, bot management, config - reused unchanged |
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

### Free-Text Guardrails (bot input, enforced in Fleet API)

**What**: Add input guardrails to the free-text the `services/telegram-bot` accepts from drivers and
admins (vehicle-issue descriptions, broadcasts, detail updates, future chat), with the **enforcement
authority living in `services/fleet-api`** so every channel - bot today, mobile app later - is
validated the same way.

**Why**: Today free text gets only `.strip()` in `telegram-bot/app/main.py:normalize_message`, then
flows straight to the Fleet API (e.g. `flows/vehicle_issue.py`). Nothing checks length, language,
injection attempts, abusive content, or PII before it is stored. Centralizing the rules in the
Fleet API means the bot can give fast inline feedback while the backend stays the single source of
truth no client can bypass.

**Scope**:

| Layer | What |
|-------|------|
| Rule set | Length/empty bounds, allowed-script (Hebrew/Latin/digits) checks, profanity + abuse filter, prompt-injection heuristics, and PII redaction policy for free-text fields |
| Fleet API enforcement | A shared validation/sanitization layer applied to every endpoint that accepts free text; reject with a structured error or store a sanitized value |
| Bot pre-check | Lightweight client-side mirror in the bot for instant Hebrew feedback, but never the only gate |
| Observability | Log rejected/redacted inputs (admin-only) for tuning thresholds |

**Approach**:
1. Define the rule set as a reusable validator in `libs/` or `fleet-api/app`, unit-tested against
   Hebrew and edge-case inputs.
2. Wire it into the Fleet API request path for all free-text endpoints.
3. Add a thin mirror in the bot's `validate.py` for UX, delegating the authoritative verdict to the API.

**Outcome**: no unbounded or unsafe free text reaches the database, and the same guardrails protect
every current and future client because they live behind the Fleet API.

---

### Automatic Document Detection (incoming photos/files)

**What**: Auto-detect the **type** of each incoming photo/document in the bot (vehicle license,
insurance, driver license, ticket, accident photo, "other") instead of asking the admin to pick it
from an inline keyboard.

**Why**: `telegram-bot/app/flows/doc_scan.py` currently makes the user choose the document type
manually before the Gemini scan, and `vision.py` ships a hardcoded prompt per type. Drivers sending
a photo have no doc-type picker at all. Classifying the file first lets the right extraction prompt
run automatically and routes the file to the correct flow.

**Scope**:

| Layer | What |
|-------|------|
| Classifier | A first-pass Gemini-vision (or lightweight) call that labels the document type and confidence before extraction |
| Routing | Map the detected type to the matching extraction prompt / flow; fall back to manual selection on low confidence |
| Coverage | Handle photos and PDFs, single and multi-page, with graceful "unrecognized document" handling |
| Validation | Cross-check detected type against the flow the user is in (e.g. reject a license when insurance was requested) |

**Approach**:
1. Add a classification step in front of the existing extraction in `doc_scan.py` / `vision.py`.
2. Select the extraction prompt from the detected type; keep the manual picker as a low-confidence fallback.
3. Extend the bot so a driver-sent photo is classified and routed without an admin in the loop.

**Outcome**: documents are recognized and processed automatically, with manual selection reserved
for ambiguous cases.

---

### Image/Document to PDF Converter

**What**: A proper converter that turns incoming images and documents into normalized **PDFs**
before they are stored in Google Drive.

**Why**: Today files are uploaded as-is - `doc_scan.py` only checks `endswith(".pdf")` to set the
MIME type and `fleet-api/app/drive.py` stores the original bytes. There is **no conversion**, so a
glovebox photo of an insurance card and a real PDF live side by side in inconsistent formats, which
hurts archival, multi-page handling, and downstream RAG over Drive files.

**Scope**:

| Layer | What |
|-------|------|
| Conversion | JPEG/PNG/HEIC images and Office-style docs to PDF; combine multiple photos of one document into a single multi-page PDF |
| Normalization | Sensible page sizing, orientation/auto-rotate, optional compression |
| Pipeline placement | Convert after capture and before `drive.upload`, so Drive holds a consistent PDF per document |
| Metadata | Preserve doc type, entity linkage, and original capture timestamp on the stored PDF |

**Approach**:
1. Add a conversion utility (Fleet API side, near `drive.py`) accepting image/doc bytes and emitting a PDF.
2. Call it from the upload path so stored artifacts are uniformly PDF.
3. Support batching several images into one PDF for multi-page documents.

**Outcome**: every stored document is a consistent, archival-quality PDF, simplifying viewing,
multi-page handling, and future Drive-files RAG.

---

### Gmail Insurance Listener

**What**: A listener on a team Gmail inbox that watches for incoming **insurance** emails/attachments,
extracts the insurance document, and feeds it into the same ingestion pipeline (detect to convert to
extract to store, link to the right vehicle).

**Why**: Insurance policies frequently arrive by email, not through the bot. There is **no Gmail
integration anywhere** today (`fleet-api` only talks to Google Drive). Watching the inbox closes the
gap so insurance renewals are captured automatically instead of relying on someone forwarding a photo
to the bot.

**Scope**:

| Layer | What |
|-------|------|
| Inbox watch | Gmail API push (Pub/Sub `watch`) or polling for messages matching insurer senders/subjects |
| Filter + extract | Identify insurance mail, pull PDF/image attachments, run them through document detection + extraction |
| Linkage | Match the policy to a vehicle (plate/policy number) and create/update the insurance record + `insurance_expiring` event |
| Auth + safety | Service-account / OAuth setup, dedupe already-processed messages, quarantine unrecognized mail for admin review |

**Approach**:
1. Stand up Gmail API auth and a `watch`/poll loop in a small listener (Fleet API service or worker).
2. Filter to insurance mail, extract attachments, and route them through the shared detect/convert/extract pipeline.
3. Reconcile against vehicles and write the insurance record + expiry event, deduping by message id.

**Outcome**: insurance documents that arrive by email are ingested automatically and kept in sync
with each vehicle's insurance record, with no manual forwarding.

---

### Event Alert Pipeline

**What**: A real alert/notification **pipeline** over the existing `events` table so that
maintenance-due, license/insurance-expiring, ticket, accident, and vehicle-issue events reliably
reach the right admins through one path.

**Why**: Events are already modeled (`db/shepherd_db/models.py`, `fleet-api/app/routers/events.py`)
and carry an unused `notified` boolean, but there is **no alerting service**: notifications happen
only as ad-hoc direct Telegram sends inside individual flows (e.g. `flows/accident.py`). Time-based
events (expiries, maintenance due) are never proactively pushed at all.

**Scope**:

| Layer | What |
|-------|------|
| Dispatcher | A service that scans for unnotified/triggered events and fans them out, flipping `notified` once delivered |
| Channels | Telegram admin messages today; pluggable for email / mobile push (ties into the Mobile App's push) later |
| Routing + severity | Map event type + severity to recipients and urgency; throttle/group to avoid spam |
| Scheduling | A periodic job that generates time-based events (expiries, maintenance windows) and feeds them into the same pipeline |
| Reliability | Idempotent delivery, retries, and an admin-visible delivery log |

**Approach**:
1. Build a dispatcher that consumes events and sets `notified` on successful delivery.
2. Move the inline Telegram sends behind this single pipeline.
3. Add a scheduled generator for expiry/maintenance events; design channels so mobile push slots in later.

**Outcome**: one reliable, auditable path from event to alert - no missed expiries, no scattered
notification code - and a foundation the mobile app's push notifications can reuse.

**Producers already in place**: `maintenance_due` events are emitted today on the KM path
(`fleet-api/app/repo.py` `update_km`) and, with the dual-interval maintenance feature, on a daily
pg_cron sweep for the time-based ("every X km or every Y months, whichever first") due date. Both
land in the `events` table with `notified=false` and reach only the events feed / dashboard - no one
is pushed yet. This pipeline is what turns those existing producers into actual admin notifications.

---

### Drive-files RAG

Build a retrieval-augmented chat over the team's Google Drive files, with a new webui chat
tab (reusing `ChatSurface`) and a fresh vector/ingestion pipeline. To be designed separately.

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
