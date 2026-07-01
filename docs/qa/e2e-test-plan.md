# Shepherd - End-to-End Test Plan (Pre-Customer Deployment)

**Owner:** QA
**Status:** Draft for first customer go-live
**Scope of the release under test:** the three active services - `fleet-api`,
`telegram-bot`, `webui` - on Postgres (schema-per-tenant), deployed via the
pull-only `deploy/` runbook to a single VPS.

This plan is the go/no-go gate for the first real customer. It covers the whole
product end to end, states what is already automated so we do not re-test it by
hand, and defines the manual and new-automated coverage needed to close the gaps
found during QA analysis.

---

## 1. Objectives

1. Confirm every customer-facing flow works end to end against a production-like
   stack (bot + Fleet API + Postgres + WebUI + Google Drive + LLM providers).
2. Prove tenant isolation: a customer can never read or write another company's
   data.
3. Prove the access model: drivers, company admins, and the Shepherd system
   admin each see and can do exactly what they should - no more.
4. Verify the deployment runbook produces a healthy stack from scratch on a
   clean host.
5. Regress the one known-broken flow and the untested error paths before a real
   driver hits them.

## 2. Out of scope

- Roadmap "Up Next" items that are not built: MkDocs site, Mobile app, Drive
  RAG, Gmail insurance listener, event alert pipeline, free-text guardrails,
  automatic document detection, image-to-PDF converter, bot action location
  capture. These are explicitly not in the release; do not test them as if they
  were.
- Load and performance testing beyond a light smoke (flagged as a follow-up, see
  section 11).
- Prompt-quality benchmarking of the LLMs (extraction accuracy is spot-checked
  manually, not benchmarked).

---

## 3. Test environment and setup

### 3.1 Environments

| Env | Purpose | Stack | Data |
| --- | --- | --- | --- |
| Local dev | Fast per-package runs and the bot e2e suite | `make up` (Postgres + db-init seed + fleet-api), bot in-process | Seeded Default Company `co_default` |
| Staging (prod-like) | Full manual E2E, deployment dry-run | `deploy/docker-compose.prod.yml` from GHCR images on a throwaway host | Fresh seed + one real test company |
| Production | Post-deploy smoke only | Live VPS | Real customer company |

### 3.2 Prerequisites for the full E2E pass

- Real `TELEGRAM_BOT_TOKEN` for a dedicated **QA** bot (never the production bot
  token) and a matching `TELEGRAM_BOT_USERNAME`.
- Real `OPENAI_API_KEY` (Whisper) and `GEMINI_API_KEY` (doc scan) so the two LLM
  touches run for real at least once - CI always mocks them.
- A Google Drive service-account JSON with a shared folder (`GDRIVE_FOLDER_ID`)
  so file upload is exercised against real Drive at least once.
- Two Telegram accounts (or two phones) to test driver vs admin roles and
  enrollment by phone.
- Seeded logins: system admin `admin@shepherd.ai` and a company admin
  `company@shepherd.ai` (password `shepherd` in seed), plus one real customer
  company created for the run.
- Ports reachable: Postgres `5432`, fleet-api `8000`, webui `3000`.

### 3.3 Test data

- Use the seeded Default Company for smoke, and provision **one dedicated QA
  customer company** with its own schema to test isolation for real.
- Provision a **second** company so cross-tenant tests have somewhere to leak to.
- At least one driver with an assigned vehicle, one customer, one maintenance
  type with both a km and a month interval, and the attendance feature flag
  toggled on for one company and off for the other.

---

## 4. Entry and exit criteria

### 4.1 Entry criteria (before manual E2E starts)

- CI is green on the release commit: all 5 Python packages (lint + typecheck +
  test) and WebUI (lint, typecheck, build, vitest) pass, and the cross-service
  `tests/e2e` job passes.
- The staging stack is deployed from GHCR images (not a local build) and all
  services report healthy.
- This plan's P0 test cases are assigned and the known-bug list (section 9) is
  reviewed.

### 4.2 Exit criteria (go/no-go for customer)

- **All P0 cases pass.** No open P0 defect.
- **No open P1 defect** without a written, accepted workaround.
- The known `vehicle_issue` bug (BUG-1) is confirmed fixed by an end-to-end run,
  not just a unit test.
- Deployment runbook (section 5) executed clean on a fresh host with a healthy
  verify step.
- Tenant-isolation suite (section 7) passes with zero cross-company leakage.
- The WebUI Playwright suite has been run at least once against staging (it is
  **not** gated in CI - see gap G1).
- Sign-off recorded in section 12.

---

## 5. Test suites

Priorities: **P0** blocks the customer go-live, **P1** must ship or have an
accepted workaround, **P2** is desirable. "Automated" notes whether an existing
test already covers it (so we do not duplicate by hand) or whether new coverage
is proposed.

### TS-1 - Deployment and environment readiness (P0)

The `deploy/` job and runbook have **no automated coverage** (gap G4). This suite
is entirely manual, run on a fresh host.

| ID | Case | Steps | Expected | Priority |
| --- | --- | --- | --- | --- |
| DEP-1 | Clean bootstrap | Copy `deploy/` to a fresh host, fill `.env` + `config.toml`, place Drive SA key, run `./deploy.sh` | Images pull from GHCR; `db-init` exits 0; fleet-api and webui become healthy | P0 |
| DEP-2 | Health verify | `curl /health` (8000) and `/api/auth/session` (3000) | Both 200 | P0 |
| DEP-3 | Idempotent re-deploy | Run `./deploy.sh` again | No data loss; stack stays healthy; `db-init` re-runs safely | P0 |
| DEP-4 | Config resolution | Point `SHEPHERD_CONFIG` at `config.toml` with `${VAR}` refs | DB URL and company->schema map resolve from env at load | P0 |
| DEP-5 | Secret hygiene | Inspect running containers and images | No secrets baked into images; `.env`/`config.toml`/`secrets/` present only on host, git-ignored | P0 |
| DEP-6 | Upgrade path | Change `TAG` in `.env`, re-run `./deploy.sh` | New images pulled; pgdata volume preserved | P1 |
| DEP-7 | Reverse proxy / firewall | Confirm 3000 (and 8000 if exposed) sit behind proxy/firewall | Postgres and internal token not reachable from the public internet | P0 |
| DEP-8 | Fresh-DB migration | On an empty pgdata volume, deploy | Schema built from models + seed applied; all per-tenant schemas provisioned | P0 |

### TS-2 - Authentication and authorization (P0)

Strong existing unit coverage in `fleet-api` (`test_auth*`, `test_token`) and
webui (`auth.test.tsx`, `routeAccess`, `nav`). Manual E2E confirms the wiring end
to end and the role gates in the real UI.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| AUTH-1 | WebUI login with valid system-admin creds | Lands on `/dashboard`, sees system tabs (companies, access, health, config) | P0 | vitest + Playwright smoke |
| AUTH-2 | WebUI login with valid company-admin creds | Lands on dashboard, system-only tabs hidden | P0 | Playwright company-admin |
| AUTH-3 | WebUI login invalid creds | Shows "פרטי התחברות שגויים"; no session | P0 | vitest |
| AUTH-4 | Logout | Returns to login; protected routes redirect back to login | P0 | manual |
| AUTH-5 | Company admin hits `/companies`,`/access`,`/health` by URL | Middleware redirects to `/dashboard` | P0 | Playwright |
| AUTH-6 | Company admin hits `/config` by URL (gap: not in middleware gate) | Backend must reject `PUT /config/{key}` writes with 403 | **P0** | new - verify |
| AUTH-7 | Fleet API without `X-Internal-Token` | 401 | P0 | test_token |
| AUTH-8 | Fleet API with malformed `X-Caller-Context` | 400 "Invalid caller context" | P0 | test_token |
| AUTH-9 | JWT issued by `/auth/login` carries role + company + feature flags | Session reflects them | P1 | test_auth_tier |
| AUTH-10 | Company admin denied MANAGE_APP_USERS / MANAGE_COMPANIES | 403 | P0 | test_auth_tier |

### TS-3 - Multi-tenancy and isolation (P0)

Strongest existing coverage (`test_tenancy`, `test_schema_routing`,
`test_enroll_cross_schema`, `*_per_schema`). Re-verify manually against **two
real companies** because a leak here is catastrophic for a first customer.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| TEN-1 | Company A admin lists vehicles/drivers/customers | Sees only company A rows | P0 | test_tenancy |
| TEN-2 | Company A admin reads a company B record by PK | 404 (not 403 - no existence probe) | P0 | test_tenancy |
| TEN-3 | Company A admin writes to a company B record by PK | 404 | P0 | test_tenancy |
| TEN-4 | System admin lists across companies | Sees all; Playground/internal excluded from customer lists and overview counts | P0 | test_sysadmin |
| TEN-5 | Per-company config isolation | Company A config change does not affect B | P0 | test_tenancy |
| TEN-6 | Shared-schema sub-companies isolated by `company_id` | No leak when two companies share a schema | P0 | test_tenancy |
| TEN-7 | Driver phone in company A cannot enroll into company B | Enrollment matches only the owning company | P0 | test_enroll_cross_schema |
| TEN-8 | Schema-cache staleness (gap): change a company's `schema_name` at runtime | Document behavior; stale routing persists for process life - flag as risk R2 | P1 | new - verify |
| TEN-9 | Attendance/KPI counts scoped per schema | Counts never mix companies | P0 | *_per_schema |

### TS-4 - Telegram bot: enrollment and access (P0)

Covered by bot `test_flows`/`test_e2e` and cross-system `tests/e2e`, but run once
against the **real** Telegram + Fleet stack to confirm the phone-share round-trip.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| ENR-1 | Unknown user shares contact, matches active driver | Enrolled as driver; welcome + driver menu; `users` row written | P0 | tests/e2e |
| ENR-2 | Unknown user matched to admin authorization | Enrolled as admin; admin menu | P0 | tests/e2e |
| ENR-3 | Unknown phone, no match | `NOT_AUTHORIZED`; no `users` row | P0 | tests/e2e |
| ENR-4 | User types a phone number instead of tapping share-contact | `CLAIM_USE_BUTTON` nudge; not enrolled | P1 | tests/e2e |
| ENR-5 | System-admin phone precedence over driver/authorization | Enrolls as system admin; sysadmin menu | P0 | test_flows |
| ENR-6 | Expired temporary authorization | `whoami` 404; user re-prompted for phone | P0 | test_bot |
| ENR-7 | Deactivated driver | Access revoked immediately (defense in depth ahead of the sweep) | P0 | test_bot |
| ENR-8 | pg_cron sweep removes expired rows every 5 min | Expired `bot_authorizations` + `users` deleted (only where pg_cron available) | P1 | db test_time_maintenance / manual |
| ENR-9 | Wrong role for a feature | `ACCESS_DENIED` (driver blocked from admin feature) | P0 | tests/e2e |

### TS-5 - Telegram bot: driver flows (P0/P1)

Well covered by bot suites and `tests/e2e`. Manual pass confirms the real
Telegram UX (buttons, Hebrew, dice) once.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| DRV-1 | Clock in (attendance on) | `attendance_records` row; dice on success | P0 | tests/e2e |
| DRV-2 | Clock out | Row updated with out time + hours | P0 | tests/e2e |
| DRV-3 | Clock in when attendance disabled | `ATTENDANCE_DISABLED`; API not hit; clock buttons hidden in menu | P0 | test_flows |
| DRV-4 | Clock in twice | `already_in` | P1 | manual |
| DRV-5 | Clock out with no open record | `no_open` | P1 | manual |
| DRV-6 | Clock in outside window | `blocked` with window bounds | P1 | manual |
| DRV-7 | Report vehicle issue (**BUG-1 regression**) | `events` row with `event_type=vehicle_issue`, `source_type=telegram`; bot reports success only on 2xx; `VEHICLE_ISSUE_FAILED` otherwise | **P0** | tests/e2e (was masked - see G3) |
| DRV-8 | Vehicle issue when driver has no vehicle | `NO_VEHICLE` | P1 | tests/e2e |
| DRV-9 | Update details - valid phone/license/expiry | `PATCH /drivers`; dice | P1 | test_e2e |
| DRV-10 | Update details - invalid input | Per-field Hebrew error; stays on step; no API hit | P1 | test_e2e |
| DRV-11 | KM update - valid | `POST /km`; dice; may emit `maintenance_due` | P0 | test_e2e |
| DRV-12 | KM update below current | `KM_BELOW_CURRENT` local reject, no API hit | P1 | test_e2e |
| DRV-13 | KM update too high (over max increment) | 422 mapped to Hebrew `KM_TOO_HIGH` | P1 | test_e2e |
| DRV-14 | Monthly attendance CSV | UTF-8 BOM CSV document, Hebrew filename; empty -> `ATTENDANCE_EMPTY` | P1 | tests/e2e |
| DRV-15 | My vehicle card | Card with vendor/model/plate/type/km; none -> `NO_VEHICLE` | P1 | tests/e2e |

### TS-6 - Telegram bot: accident wizard (P0)

Multi-step, media-heavy, and the only flow that must not silently fail. Covered by
`test_e2e` (text + voice) and `tests/e2e` (attachments) but the media upload uses
real Drive only in manual.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| ACC-1 | Full wizard, text description | `accidents` row + attachments (3 photos + video); admins notified | P0 | tests/e2e |
| ACC-2 | Full wizard, **voice** description (Whisper) | Voice transcribed to `description`; rest identical | P0 | test_e2e (mocked) + manual real |
| ACC-3 | Location share step | Lat,lon stored; reply keyboard removed after share | P1 | test_flows |
| ACC-4 | Media uploaded to real Google Drive | Each photo/video returns a `file_url`; stored on `accident_attachments`; no LLM touches media | P0 | manual real Drive |
| ACC-5 | Admin notification fan-out | Every admin `telegram_chat_id` receives the alert | P0 | tests/e2e |
| ACC-6 | No dice on accident | Deliberately no dice flourish | P2 | test_e2e |

### TS-7 - Telegram bot: admin flows (P1)

Covered by bot suites. Manual spot-check of the real Hebrew output.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| ADM-1 | Attendance today | List of clocked-in drivers with Hebraized status; empty -> `ATTENDANCE_EMPTY` | P1 | tests/e2e |
| ADM-2 | Broadcast send | Recipient count confirm -> message delivered to all drivers; dice | P1 | tests/e2e |
| ADM-3 | Broadcast cancel | No messages sent | P2 | test_e2e |
| ADM-4 | Fleet summary | KPI figures (total km 7d, avg/driver, docs expiring); empty handled | P1 | tests/e2e |
| ADM-5 | Update driver (field) | `PATCH /drivers`; dice | P1 | test_e2e |
| ADM-6 | Maintenance overdue list | Vehicles at/over next-maintenance km, sorted; empty handled | P1 | tests/e2e |
| ADM-7 | Maintenance log care | `vehicle_care` row; resolves open `maintenance_due`; invalid km rejected | P1 | tests/e2e |
| ADM-8 | KM update as admin (any vehicle) | Same validation as driver path | P1 | test_e2e |

### TS-8 - System-admin capabilities: debug, live, impersonation, audit (P0)

Per CONTEXT.md this is the trust-sensitive area. Audit is tested (bot + fleet-api)
but the **live banner persistence** and **destructive-action confirmation** are
only unit-level (gap G5) - verify end to end.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| SA-1 | System overview | Read-only per-company cards; Playground/internal excluded; no mutation possible | P0 | test_sysadmin, test_flows |
| SA-2 | Debug mode enters Playground persona | Acts as driver/admin in Playground company; banner `🛠 Playground`; **not audited** | P0 | test_flows |
| SA-3 | Customer-Live enter | Picks real company + persona; banner `🎭 פועל כ… · company`; start audit posted | P0 | test_flows |
| SA-4 | Customer-Live destructive action (broadcast) | Confirmation shown; extra write/broadcast audit row posted | P0 | test_flows |
| SA-5 | Customer-Live non-destructive action | No write audit | P1 | test_flows |
| SA-6 | Exit impersonation | Stop audit posted; session cleared; menu + keyboard reset | P0 | test_flows |
| SA-7 | Impersonated call carries operator id | Every Customer-Live write ties back to the operator | P0 | test_flows |
| SA-8 | WebUI act-as banner persists across navigation | Amber banner stays on every page while acting-as | **P0** | new - Playwright/manual |
| SA-9 | WebUI act-as destructive confirmation | Confirm dialog warns real+audited before entering act-as | P1 | actAs.test |
| SA-10 | Playground unguarded + unaudited contract | No audit rows for Playground actions | P1 | test_flows |

### TS-9 - Fleet API business rules (P0/P1)

Strong unit coverage. E2E confirms the rules through the real surfaces that drive
them (bot + webui).

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| BIZ-1 | KM update emits `maintenance_due` at threshold, dedups per cycle | One open event per cycle; none below buffer | P0 | test_km |
| BIZ-2 | Log care advances step cycle and resolves open due | Cycle wraps; next km/date recomputed | P1 | test_care |
| BIZ-3 | Dual-interval maintenance (km OR months, whichever first) | Correct next-due; time path via cron `emit_time_maintenance_due` | P0 | test_care, test_maintenance_time_per_schema |
| BIZ-4 | Maintenance type requires at least one interval | DB CHECK enforced; clearing both rejected | P1 | test_maintenance_types |
| BIZ-5 | Document extraction applies to matched vehicle; mismatch -> review event | No silent drop | P1 | test_documents |
| BIZ-6 | Duplicate plate within company | 409 | P1 | test_vehicles |
| BIZ-7 | Attendance clock-in idempotent + window + feature gate | Typed results (disabled/blocked/already_in/no_open) not HTTP errors | P0 | test_attendance, test_company_settings |
| BIZ-8 | File upload requires company + configured Drive | 400 otherwise; link returned on success | P1 | test_files |
| BIZ-9 | Company settings Drive validate-then-persist; creds never returned | Only `gdrive_configured` bool exposed | P0 | test_company_settings |
| BIZ-10 | Expiry events (`license_expiring`/`insurance_expiring`) (gap) | **No code emits these today** - they surface only as `docs_expiring_count`. Confirm the customer does not expect proactive alerts; flag as R3 | P1 | none - by design |

### TS-10 - WebUI admin console (P1)

Vitest + MSW cover hooks and adapters; Playwright covers navigation and two F5
flows. Manual pass covers the CRUD forms and validations against the live API.

| ID | Case | Expected | Priority | Automated |
| --- | --- | --- | --- | --- |
| WEB-1 | Dashboard KPIs render with real data | 5 KPI tiles, trends, alerts, recent activity; empty states correct | P1 | vitest |
| WEB-2 | Vehicle CRUD | Create (plate 7-8 digits, type required), edit (blanks unchanged), delete (optimistic) | P1 | useVehicles + manual |
| WEB-3 | Driver CRUD + validations | phoneIL `^05\d{8}$`, license 7-9 digits, expiry amber < 30 days | P1 | validation.test + manual |
| WEB-4 | Customer CRUD | email regex, phoneIL; delete unlinks vehicles | P1 | manual |
| WEB-5 | Events list + filters | type/severity/status/vehicle filters; read-only; sorted severe-then-recent | P2 | events.test |
| WEB-6 | Accident create with 7 upload slots | Uploads then create with URLs; submit disabled mid-upload | P1 | accidentUpload.test + manual |
| WEB-7 | Attendance records + edit modal | Month picker, KPIs, holidays, per-day edit with time validation | P1 | attendance.test |
| WEB-8 | Attendance settings (feature flag) | Toggling flag hides/reveals nav after re-login | P0 | Playwright f5-attendance-flag |
| WEB-9 | Maintenance type form | positive-int intervals, at least one interval, unique steps; delete blocked 409 with Hebrew detail | P1 | useMaintenanceTypes + manual |
| WEB-10 | Config editor | Stepper fields save via `PUT /config/{key}`; image_confidence clamps 0-1 | P1 | useConfig |
| WEB-11 | Bot Management | Bot users table role toggle; add authorization (phone required, expiry optional); pending invites | P1 | manual |
| WEB-12 | Companies (system admin) | Add, toggle active, attendance switch, settings dialog Drive validation | P0 | Playwright f5-drive-validation |
| WEB-13 | App users (system admin) | Create system/company admin; role+company immutable after create; reset password | P1 | useAppUsers + manual |
| WEB-14 | Health page auto-refresh | Per-service status, latency; refresh every 15s | P2 | health.test |
| WEB-15 | System-admin company switcher | Scopes reads to selected company or all | P1 | manual |

### TS-11 - Hebrew and RTL correctness (P1)

Cross-cutting. Verify on the real UI and the bot output; automated coverage is
indirect (`test_fmt`, `holidays.test`).

| ID | Case | Expected | Priority |
| --- | --- | --- | --- |
| RTL-1 | Global layout `dir=rtl`, Assistant font | UI reads right-to-left throughout | P1 |
| RTL-2 | Forced-LTR fields (email, phone, plate, license, dates, IDs, time, folder id, creds) | Render left-aligned within RTL layout | P1 |
| RTL-3 | Date/number formats | Dates DD/MM/YYYY; numbers with thousands separators; Hebrew unit suffixes | P1 |
| RTL-4 | Directional controls | Month prev/next chevrons and attendance toggle knob read correctly RTL | P2 |
| RTL-5 | CSV export opens correctly in Excel (UTF-8 BOM) | Hebrew columns readable | P1 |
| RTL-6 | PDF export via `window.print()` | Print stylesheet renders RTL correctly | P2 |
| RTL-7 | Hebrew calendar (chag / erev chag / rest days) | Attendance working-day rules and holiday pills correct (e.g. Pesach 2026) | P1 |
| RTL-8 | Bot Hebrew messages and RTL formatting | All flow prompts, errors, cards render correctly (LRI/PDI wrapping) | P1 |

### TS-12 - Cross-surface consistency (P0)

This is the biggest true-E2E gap (G2): no test drives WebUI + bot on the same
data. These are new manual E2E cases against staging.

| ID | Case | Expected | Priority |
| --- | --- | --- | --- |
| X-1 | Driver enrolls via bot -> appears in WebUI Bot Users table | Same driver, correct role, phone, Telegram id, join date | P0 |
| X-2 | Admin edits driver in WebUI -> bot "update details" / "my vehicle" reflect it | Bot reads the updated value | P0 |
| X-3 | Driver clocks in via bot -> WebUI attendance "today" shows them | Consistent record and hours | P0 |
| X-4 | Driver logs accident via bot -> WebUI accidents list + Drive links | Accident and attachment URLs visible | P0 |
| X-5 | Admin adds authorization in WebUI -> user can enroll via bot | New admin/temporary role works in bot | P0 |
| X-6 | KM update via bot crosses maintenance threshold -> WebUI events + maintenance overdue reflect it | `maintenance_due` visible in both surfaces | P1 |
| X-7 | Company attendance flag off in WebUI -> bot hides clock + denies clock-in | Flag change propagates to bot on next enroll/whoami | P0 |

### TS-13 - Negative, error, and resilience paths (P1)

Identified gaps: bot write paths lack try/except (Fleet 5xx/LLM/Drive exceptions
propagate with no Hebrew error); Fleet API has unvalidated-enum 500 paths.

| ID | Case | Expected | Priority | Notes |
| --- | --- | --- | --- | --- |
| ERR-1 | Fleet API down during a bot write (clock/accident/PATCH/POST) | Bot should surface a Hebrew error, not silently drop or crash | **P1** | gap - currently propagates (see G6) |
| ERR-2 | Whisper/Gemini/Drive raises during a flow | Graceful Hebrew error; user can retry | P1 | gap - no in-flow catch |
| ERR-3 | `EventCreate` with invalid enum (severity/type/source) | Should be 422, not 500 | P1 | gap - free-string fields hit DB enum |
| ERR-4 | Free-string status fields (driver/customer/attendance/report/role) invalid value | 422 preferred over 500 | P2 | gap |
| ERR-5 | `PUT /config/{key}` with malformed/untyped value | Validated or safely rejected | P2 | gap - accepts arbitrary JSON |
| ERR-6 | Overnight clock-out (out < in) | No negative hours | P2 | gap - no overnight handling |
| ERR-7 | WebUI list page when Fleet API is down | Visible error state, not a blank/broken page | P1 | gap - list errors largely silent |
| ERR-8 | Mid-flow cancellation / command interrupt in bot | Flow abandoned cleanly; state cleared; impersonation preserved | P1 | partially covered |
| ERR-9 | Attendance edit modal time-range error | Error surfaced to user (verify `patchError` reaches modal) | P2 | possible silent failure |

### TS-14 - Security and data safety (P0/P1)

| ID | Case | Expected | Priority |
| --- | --- | --- | --- |
| SEC-1 | Internal token never reaches the browser | Only the Next proxy holds it; not in client bundle or network tab | P0 |
| SEC-2 | Drive credentials write-only | Never returned by the API or shown in UI | P0 |
| SEC-3 | `password_hash` never exposed by `/app-users` | Absent from all responses | P0 |
| SEC-4 | Cross-tenant probe returns 404 not 403 | No existence leakage | P0 |
| SEC-5 | Login does not enumerate users | Generic 401 for wrong password vs unknown email | P1 |
| SEC-6 | Impersonation audit trail complete | Operator, company, effective persona, start/stop, each confirmed write | P0 |
| SEC-7 | Free-text input safety (unbuilt) | Only `.strip()` today; no length/injection/PII checks - flag as R4 | P1 |
| SEC-8 | Postgres and fleet-api not publicly exposed | Behind firewall/proxy in prod | P0 |

---

## 6. Coverage summary by surface

| Surface | Existing automated coverage | Confidence | Primary residual risk |
| --- | --- | --- | --- |
| Fleet API | ~147 unit tests, strong tenancy + auth | High | Unvalidated-enum 500 paths; schema-cache staleness |
| Telegram bot | ~89 unit + 16 cross-system e2e | High | No try/except on write/LLM paths; real Telegram/LLM only manual |
| WebUI | ~140 vitest + 5 Playwright (not in CI) | Medium | Playwright not gated; silent list errors |
| DB / schema | 38 tests, provisioning + constraints + pg_cron SQL | High | pg_cron only real in prod |
| Deployment | none | Low | Entire runbook manual-only |
| Cross-surface E2E | none (bot-only e2e) | Low | No WebUI+bot same-data test |
| LLM (Whisper/Gemini) | mocked everywhere | Low (by design) | Real accuracy/failure only manual |

---

## 7. Known bugs and gaps carried into this release

Tracked from analysis and `.scratch/telegram-bot/bugs.md`:

- **BUG-1 (vehicle_issue)** - was: invalid event enum -> `POST /events` 500 ->
  no row, bot falsely reports success. Marked fixed; **must be confirmed by
  DRV-7 end to end**, since the bot-side unit test passed against a mock and
  masked the real failure.
- **G1** - WebUI Playwright e2e exists but is **not gated in CI** (`npm test`
  runs vitest only). Run it manually against staging every release until gated.
- **G2** - No full-stack test drives WebUI + bot on the same data (TS-12 covers
  this manually).
- **G3** - Bot-side `vehicle_issue` unit test passed against a mocked Fleet API,
  hiding the real enum failure. Prefer the cross-system assertion.
- **G4** - Deployment runbook, `deploy.sh`, prod compose, secret injection, and
  fresh-DB migration have no automated coverage (TS-1 covers manually).
- **G5** - Live banner persistence and destructive-action confirmation are only
  unit-level (SA-8/SA-9 cover manually).
- **G6** - Several bot write/LLM/Drive paths await without try/except; a provider
  5xx/exception propagates with no Hebrew error (ERR-1/ERR-2).

---

## 8. Risk register

| ID | Risk | Impact | Likelihood | Mitigation |
| --- | --- | --- | --- | --- |
| R1 | Cross-tenant data leak | Critical | Low | TS-3 + SEC-4 against two real companies before go-live |
| R2 | Schema-cache staleness after a company's schema changes at runtime | Medium | Low | Avoid runtime schema renames; restart process if changed; TEN-8 documents behavior |
| R3 | Customer expects expiry alerts that are not emitted | Medium | Medium | Confirm expectations; BIZ-10 flags; alert pipeline is roadmap-only |
| R4 | Unbounded/unsafe free text stored (no guardrails) | Medium | Medium | Manual abuse pass SEC-7; guardrails are roadmap-only |
| R5 | LLM/Drive outage breaks a driver mid-accident with no error | High | Medium | ERR-1/ERR-2; consider adding in-flow catches before go-live |
| R6 | Deployment misconfig (secrets, ports, Drive key) | High | Medium | TS-1 full dry-run on a fresh host |

---

## 9. Test execution strategy

1. **Pre-flight (automated):** confirm CI green on the release commit; run the
   WebUI Playwright suite against staging (closes G1 for the release).
2. **Deploy dry-run (manual):** TS-1 on a fresh host.
3. **Isolation and auth first (P0):** TS-2, TS-3, SEC-* - stop go-live if any
   leak.
4. **Bot E2E on real Telegram (P0):** TS-4, TS-5 incl. DRV-7 regression, TS-6,
   TS-8; run the two LLM touches for real once (ACC-2, and doc scan in ADM/DRV).
5. **WebUI E2E (P1):** TS-10, TS-11.
6. **Cross-surface (P0):** TS-12 on the same data.
7. **Negative/resilience (P1):** TS-13.
8. **Prod smoke:** DEP-2 + a single enroll/clock/accident and one WebUI login on
   the real customer stack.

Log each case as Pass / Fail / Blocked with evidence (screenshot, DB row, or log
line). File failures as `.scratch/<feature>/bugs.md` entries using the repo's
`BUG-N` format.

---

## 10. Follow-ups to raise (not blocking unless promoted to P0/P1 above)

- Gate the WebUI Playwright suite in CI (closes G1 permanently).
- Add a WebUI+bot cross-surface e2e to `tests/e2e` (closes G2).
- Add Fleet API tests + Pydantic validation for the free-string enum fields
  (closes ERR-3/ERR-4).
- Add try/except with Hebrew fallback on bot write/LLM/Drive paths
  (closes ERR-1/ERR-2).
- Smoke-test `deploy.sh` in CI against a throwaway compose target (closes G4).
- Light load/concurrency test (simultaneous clock-in, pg_cron under load).

---

## 11. Sign-off

| Role | Name | Go / No-go | Date | Notes |
| --- | --- | --- | --- | --- |
| QA | | | | All P0 pass, no open P1 without workaround |
| Eng lead | | | | |
| Product | | | | Expiry-alert + guardrail expectations confirmed |
