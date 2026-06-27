# Epic: Multi-Tenancy + Company-Admin Authorization

> Source design spec: `docs/superpowers/specs/2026-06-26-multi-tenancy-and-company-admin-design.md`

## Summary

Introduce true multi-tenancy and a second authorization tier across the Shepherd
platform. A new top-level **Company** tenant lets multiple companies share one
deployment with fully isolated data. A new **company admin** web role manages
everything within their own company but nothing across companies and no
system-ops. The existing single **system admin** becomes a platform operator who
works across companies via a company switcher and manages the tenants and logins
themselves. Identity and the login contract are **channel-agnostic** so a future
mobile app reuses them. The web console's information architecture is also
consolidated (fewer top-level tabs).

End state: a system admin can create companies and per-company logins; a company
admin logs in and sees only their company's vehicles, drivers, customers, events,
attendance, accidents, uploads, and their company's Telegram bot users/invites;
every fleet-api query and every Telegram bot flow is scoped to a `company_id`;
and the same `POST /auth/login` + `app_users` identity is ready to serve a mobile
client with only an additive token-verification change.

## Requirements

- New `companies` table (tenant root); `company_id` (NOT NULL) on every domain
  table, including config, maintenance_types, and the bot tables.
- New `company_admin` role (carries `company_id`) added to `Role`
  (`libs/shepherd_contracts/auth.py`) and the fleet-api permission matrix
  (`services/fleet-api/app/auth.py`); `CallerContext` gains `company_id`.
- Company admin surface: most operational tabs, all locked to their own company -
  Dashboard, Vehicles, Drivers, Customers, Events, Attendance, Accidents, Upload,
  and Bot (their company only). Denied: Health, Companies, Access, Config, and any
  cross-company data.
- System admin: a company switcher selects an active company; an "All companies"
  option only where cross-company reads are meaningful. Manages companies (new
  Companies tab) and logins (new Access tab).
- Channel-agnostic identity: `app_users` table (email, password_hash, role,
  nullable `company_id`, `is_active`, name). `POST /auth/login` is the single
  client-facing auth contract returning `{ user, token }`; `token` is a portable
  JWT (`sub`, `role`, `company_id`, `exp`) signed with `AUTH_JWT_SECRET`.
- Bcrypt password hashing via a shared util in the `db` package (used by both
  `db/seed.py` and fleet-api).
- Repo-layer tenant scoping (defense in depth): `company_admin` forced to their
  `company_id`; `admin` scoped to the selected company or unfiltered only on
  explicit cross-company overview reads.
- Bot management becomes per-company: company admins manage their own company's
  bot users/invites (scoped); system admin manages across all. All telegram-bot
  flows (whoami, enroll, attendance, vehicle issue, access requests) carry the
  enrolled user's `company_id`.
- Seeding: a Default Company; all existing seed rows attached to it; system admin
  seeded from `ADMIN_EMAIL`/`ADMIN_PASSWORD` (`company_id = null`); one demo
  `company_admin` login bound to the default company. Schema is rebuilt from
  models (no migrations).
- Nav consolidation: maintenance-types nested under Vehicles, accidents nested
  under Events, Chat/Assistant tab removed.
- Webui middleware hard-gates routes by role (central `route -> allowedRoles`
  map) in addition to nav filtering; backend 403 remains the final backstop.

## Scope

- **In scope**: the tenancy data foundation; the channel-agnostic app-user auth
  tier and its system-admin management UI (Companies + Access tabs, switcher);
  bot tenancy (permissions + all bot flows + the company-scoped Bot tab); and the
  nav consolidation including Chat/Assistant removal.
- **Out of scope (deferred)**:
  - Chat / fleet-agent + assistant tenancy - a **separate epic**. This epic only
    *removes* the Chat/Assistant tab; the agent/assistant services and their
    `company_id` scoping are not touched here (removing the tab moots the current
    `agent.ts` cross-tenant leak for now).
  - Mobile token *transport* - fleet-api verifying `Authorization: Bearer <jwt>`
    to derive `CallerContext`, and any mobile client. Login already *issues* the
    JWT, so this is purely additive later.
  - End-customer (`customer` role) web logins - role retained, not provisioned.

## Cross-Cutting Concerns

- **Tenant scoping must be exhaustive, including by-PK paths**: scoping lives at
  the repository layer so no router can bypass it. A single missed `company_id`
  filter is a cross-tenant data leak. The ~18 `session.get(Model, pk)` paths
  (detail/PATCH/DELETE) cannot carry a `WHERE company_id` and are the easiest to
  miss - the Feature 1 mechanism must cover them (filtered selects or post-fetch
  company assertions), and every later feature follows that pattern.
- **Non-model SQL is not "rebuilt from models"**: `db/bootstrap.sql`
  (`refresh_kpi_daily` pg_cron) and any composite-key changes for per-company
  `system_config` are hand-written SQL. Feature 1 owns rewriting them; later
  features must not assume a global config row or global KPI aggregation.
- **Schema changes require drop-and-recreate**: `Base.metadata.create_all` does
  not ALTER existing tables, so adding `company_id` means every environment
  drops and recreates the DB and re-seeds. Coordinate this as a one-time cutover.
- **`NavItem` shape ownership**: Feature 2 defines `NavItem` with BOTH
  `allowedRoles` and nested `children` (used by Feature 4) so the type and
  renderer are written once.
- **Permission matrix consistency**: every operational `Action` must have a
  correct `company_admin` entry; the matrix permits, the repo layer scopes. New
  actions (`MANAGE_APP_USERS`, `MANAGE_COMPANIES`) are admin-only; bot actions
  become `company_admin`-scoped.
- **Shared webui navigation/middleware**: Features 2, 3, and 4 all edit the
  sidebar `NAV` and route gating. Feature 2 establishes the `allowedRoles` nav
  structure and the central `route -> allowedRoles` middleware map; Features 3
  and 4 slot into that structure rather than inventing parallel mechanisms.
  Coordinate to avoid conflicting edits to `Sidebar.tsx`/`middleware.ts`.
- **Channel-agnostic auth**: do not recouple identity to the web client.
  next-auth wraps `POST /auth/login`; it does not own identity. The JWT format is
  the mobile interface - keep it documented and stable.
- **Webui DB-blind boundary**: the ESLint rule forbidding DB clients in the webui
  stays intact. All credential checks and tenant resolution go through fleet-api.
- **No DB migrations**: schema is rebuilt from `models.py` (`db/create_schema.py`)
  and re-seeded. Feature 1 owns the default-company backfill that every later
  feature's data depends on.
- **Testing**: TDD throughout. fleet-api uses pytest (see
  `services/fleet-api/tests`); webui uses Vitest (>= 85% on `lib/` + `hooks/`)
  and Playwright e2e; telegram-bot has its own pytest suite
  (`services/telegram-bot/tests`).

## Features

<!-- Status values: not-started | planning | planned | in-progress | done -->

### Feature 1: Tenancy foundation

**Status**: done (see `plans/implementation/mt-1-tenancy-foundation.md`; 120 fleet-api tests green)
**Dependencies**: None
**Skills**: superpowers:planning-project-features, superpowers:test-driven-development

**What & Why**: The data and authorization substrate every other feature builds
on. Introduces the `companies` tenant root, puts `company_id` on every domain
table, threads `company_id` through `CallerContext`, and enforces tenant scoping
at the repository layer. Distinct unit because the scoping strategy (where and how
every query is filtered, how the system admin's "selected vs all companies" reads
work) is a self-contained design problem with real trade-offs, and getting it
wrong is the epic's top risk.

**Context**:
- DB models: `db/shepherd_db/models.py`. Existing tenant-ish entity is `Customer`
  (lines ~249-265) and `Vehicle.customer_id` (~325). `Company` is a NEW top-level
  tenant ABOVE customers; `Customer` becomes a per-company entity
  (`customers.company_id`). Domain tables to carry `company_id` (verified against
  the model file): drivers, customers, vehicles, maintenance_types, accidents,
  `accident_attachments`, events, attendance, reports/tickets, `km_updates`,
  `vehicle_care`, `channel_identities`, config (`system_config`), kpi
  (`kpi_daily`), and the bot tables `users` (`BotUser`) + `bot_authorizations`.
  Note: there is **no** `documents` table (an earlier draft listed one - it does
  not exist); document data flows through events/reports/attachments. The bot
  tables get a **nullable** `company_id` in this feature; Feature 3 populates the
  writers and flips them NOT NULL (their company source is the matched
  driver / inviting caller, which is F3 behavior).
- **Scope predicate**: implement tenant scoping keyed on the *presence* of
  `CallerContext.company_id`, NOT on `Role.company_admin` (that enum value lands
  in Feature 2). This keeps Feature 1 testable in isolation. End-to-end
  verification that `company_admin` is forced to its company lands in Feature 2.
- **By-PK paths are the hard part**: `services/fleet-api/app/repo.py` is ~40 free
  functions and ~18 high-risk paths use `session.get(Model, pk)` for
  detail/PATCH/DELETE - these cannot carry a `WHERE company_id`. A single list
  helper does not cover them; design a mechanism (company-filtered selects or a
  post-fetch company assertion) that also covers by-PK access, or a
  company_admin can act on another company's row by guessing its UUID.
- **Derived / caller-less writes need company inheritance**: `process_extracted_doc`
  creates an `Event` with no vehicle when a plate is unknown (a designed path);
  km-update, accident logging, and doc-extraction events/reports must inherit
  `company_id` from the related vehicle/driver, or NOT NULL inserts fail.
- **Per-company `system_config`**: `SystemConfig.config_key` is the sole PK -
  becomes composite `(company_id, config_key)`. Readers with no caller company
  (attendance clock, `update_km`/`get_maintenance_buffer`) must resolve a company
  from the driver/vehicle first.
- **Non-model SQL (`db/bootstrap.sql`)**: `refresh_kpi_daily()` (pg_cron,
  ~lines 8-84) aggregates globally, keys on `snapshot_date` alone, and reads
  `system_config` as one global row. "Rebuild from models" does NOT touch this
  file - it must be rewritten to partition by `company_id` (composite key, config
  read per company) or it both breaks and leaks aggregates across companies.
- **Global unique constraints become cross-tenant collisions**:
  `Driver.phone_number`, `Vehicle.licensing_plate`, `MaintenanceType.name` are
  globally unique today - they should become unique *per company*.
  `find_enrollment_by_phone` scans drivers across all companies (a mis-tenant
  enrollment vector, sharpened by the recent auto-enroll-by-phone commit).
- Auth contracts: `libs/shepherd_contracts/auth.py` - `Role` and `CallerContext`
  (currently validates driver/customer id presence). Add optional `company_id`;
  `company_admin` role value is added in Feature 2's auth work but the
  `CallerContext.company_id` field belongs here.
- Permission enforcement: `services/fleet-api/app/auth.py` (`Action` enum,
  `_MATRIX`, `assert_permitted`) and the routers under
  `services/fleet-api/app/routers/` that already branch on role (e.g.
  `vehicles.py` filters by `customer_id`).
- Schema build + seed: `db/create_schema.py` (`Base.metadata.create_all` +
  executes `bootstrap.sql`) and `db/seed.py` (`seed()` with ~12 `_seed_*`
  functions). No migrations - rebuild from models; note `create_all` does NOT add
  columns to an existing DB, so every environment must drop-and-recreate. Seeding
  is a **rewrite of all `_seed_*` INSERTs** to include `company_id` (not a
  post-hoc backfill): seed the Default Company first, then attach every seeded row
  to it.

**Scope Boundaries**:
- Includes: `companies` table; `company_id` columns + FKs on all domain tables
  (bot tables nullable for now); `CallerContext.company_id`; the scoping mechanism
  covering BOTH list and by-PK paths; derived-write company inheritance;
  per-company `system_config` (composite PK) and its caller-less readers;
  per-company unique constraints; the `bootstrap.sql` `refresh_kpi_daily` rewrite;
  the system-admin selected-vs-all-companies read semantics (defined once here);
  Default Company seed + rewrite of all `_seed_*` INSERTs.
- Excludes: the `app_users` table and login (Feature 2); company-aware bot *flows*,
  setting `company_id` on bot writers, and flipping bot columns NOT NULL
  (Feature 3); any webui changes. Adding the `company_admin` role VALUE and its
  matrix rows is Feature 2; this feature only ensures `CallerContext` can carry
  `company_id` and that scoping reads it.

---

### Feature 2: App auth tier (channel-agnostic) + admin management UI

**Status**: done (backend: 134 fleet-api tests; webui: 99 tests, build/typecheck/lint clean)
**Dependencies**: Feature 1
**Skills**: superpowers:planning-project-features, superpowers:test-driven-development, frontend-design

**What & Why**: Turns "logged in" from a single hardcoded admin into real,
DB-backed, multi-role identity, and gives the system admin the UI to manage
tenants and logins. Distinct unit because the auth contract (channel-agnostic
login, portable JWT, how next-auth wraps it, how the webui proxy injects the real
caller context, and how the company switcher feeds an active `company_id`) is a
cohesive design problem spanning backend and frontend.

**Context**:
- Backend: new `app_users` table in `db/shepherd_db/models.py` (email,
  password_hash, role `admin|company_admin`, nullable `company_id`, `is_active`,
  name). Add `company_admin` to `Role` (`libs/shepherd_contracts/auth.py`) and to
  the fleet-api `_MATRIX` (`services/fleet-api/app/auth.py`) for every operational
  action (permits; Feature 1's repo layer scopes). New
  `Action.MANAGE_APP_USERS` and `Action.MANAGE_COMPANIES` (admin-only). New
  routers: `POST /auth/login` (X-Internal-Token only, no caller context; returns
  `{ user, token }`), `/app-users` CRUD, `/companies` CRUD. Bcrypt hashing util
  in the shared `db` package; `_seed_app_users()` in `db/seed.py` seeds the env
  system admin and a demo company_admin. JWT signed with `AUTH_JWT_SECRET` (new
  env; add to `.env.example`); lib PyJWT.
- Webui: `services/webui`. Replace the plaintext env check in `lib/auth.ts` with a
  server-side call to `POST /auth/login`; carry `role`, `company_id`, `id` in the
  next-auth session (augment next-auth types). Change the fleet proxy
  (`app/api/fleet/[...path]/route.ts`) to build `X-Caller-Context` from the
  session instead of the hardcoded `{ role:'admin' }`. Add the company switcher
  (topbar) feeding the active `company_id`. Establish the central
  `route -> allowedRoles` middleware map (`middleware.ts`) and the nav structure
  in `components/Sidebar.tsx`. The current `NAV` is a flat array of a simple
  `NavItem`; this feature must define the FULL `NavItem` shape up front -
  `allowedRoles` AND nested `children` - because Feature 4 nests
  maintenance-types/accidents as sub-sections. Defining only `allowedRoles` here
  would force Feature 4 to re-type `NavItem` and rework the renderer. New
  system-admin-only tabs: Companies (`/companies`) and Access (`/access`, full
  lifecycle: create, list, reset password, toggle active, delete). Role-based
  post-login landing.
- This feature OWNS the nav/middleware role-gating mechanism (the `NavItem` shape
  incl. children, and the `route -> allowedRoles` map) that Features 3 and 4
  extend (see Cross-Cutting Concerns).
- Note: end-to-end verification of `company_admin` forced-company scoping (the
  riskiest behavior, mechanically built in Feature 1) first becomes possible here,
  since this feature introduces the role value and a real company_admin login.
  Include cross-tenant access tests (a company_admin must not read/write another
  company's rows, including by-PK detail/PATCH/DELETE).

**Scope Boundaries**:
- Includes: `app_users` + hashing; `company_admin` role value + matrix entries;
  login/JWT; app-user + company management routers; all webui auth/proxy/
  middleware/switcher wiring; Companies + Access tabs; role-based landing; the
  shared `allowedRoles` nav + `route -> allowedRoles` map.
- Excludes: fleet-api Bearer-token VERIFICATION (deferred mobile transport - JWT
  is only issued here); bot-management permission changes and the Bot tab gating
  (Feature 3); the maintenance-types/accidents nesting and Chat removal
  (Feature 4).

---

### Feature 3: Bot tenancy

**Status**: done (see `plans/implementation/mt-3-bot-tenancy.md`; 138 fleet-api + 53 telegram-bot tests green)
**Dependencies**: Feature 1 (hard); Feature 2 (for the webui Bot-tab role gating)
**Skills**: superpowers:planning-project-features, superpowers:test-driven-development

**What & Why**: Makes the Telegram bot multi-tenant and turns bot management into
a per-company capability. Distinct unit because it spans a different service
(`services/telegram-bot`) with its own flows and tests, and because "which
company does an enrolling phone belong to, and how does every downstream flow stay
scoped" is a self-contained design problem.

**Context**:
- fleet-api: update `MANAGE_BOT_USERS` / `MANAGE_BOT_INVITES` in `_MATRIX`
  (`services/fleet-api/app/auth.py`) to allow `company_admin` (scoped) alongside
  `admin`. Bot routers (`services/fleet-api/app/routers/bot.py`, attendance) must
  filter by `company_id` via Feature 1's scoping. This feature SETS the writers
  that Feature 1 left unfilled: `repo.enroll_bot_user` and `create_bot_authorization`
  build rows with no `company_id` today, and `POST /bot-enroll` carries no caller
  context to derive one. Resolve the source per table - `users` (BotUser) can
  derive from the matched driver; `bot_authorizations` derives from the inviting
  caller's company. Once both writers set it, flip the bot columns to NOT NULL.
- `whoami` currently returns no company - it must return the user's `company_id`,
  and the bot's generic caller context (`admin_ctx()` defaults to
  `{"role":"admin"}` with no company) must become company-aware, or admin-side bot
  flows run cross-company under the "admin unfiltered unless company supplied"
  rule.
- telegram-bot surface is larger than a token change: ~73 fleet-api calls across
  ~13 flows with ~52 tests (`services/telegram-bot/app/flows/*` - access,
  attendance_csv, vehicle_issue, etc., plus enroll/whoami). Every call must
  resolve and pass the enrolled user's `company_id`. Combined with the recent
  auto-enroll-by-phone behavior and `find_enrollment_by_phone` scanning across
  companies (Feature 1 scopes phone uniqueness per company), enrollment must match
  within the correct company.
- Webui: make the Bot tab (`app/(admin)/bot/page.tsx`) visible to `company_admin`
  scoped to their company (uses Feature 2's nav/middleware gating + `NavItem`
  shape); system admin manages across companies (or the active company via the
  switcher). The `useBotManagement` hook and fleet bot client calls already exist.
- Models (`db/shepherd_db/models.py`): the bot users table is named `users`
  (`BotUser`, ~656-680); `BotAuthorization` (~625-654). Both carry `role`
  (admin|driver) + phone and gain a `company_id` column (nullable) in Feature 1.

**Scope Boundaries**:
- Includes: bot-management permission changes; company-scoped bot routers; setting
  `company_id` on enrollment/authorization writers and flipping those columns NOT
  NULL; returning `company_id` from `whoami`; making `admin_ctx()` / all
  telegram-bot flows company-aware; per-company enrollment matching; the
  company-scoped Bot tab in the webui.
- Excludes: the `company_id` COLUMN additions themselves and the nullable schema
  (Feature 1); the auth/role/middleware/`NavItem` mechanism the Bot tab rides on
  (Feature 2). Driver/customer web logins remain out of scope for the whole epic.

---

### Feature 4: Nav consolidation

**Status**: done (see `plans/implementation/mt-4-nav-consolidation.md`; webui: 25 vitest files green, typecheck/lint/build clean)
**Dependencies**: None (hard); coordinate webui nav edits with Feature 2
**Skills**: superpowers:planning-project-features, superpowers:test-driven-development, frontend-design

**What & Why**: Reduce top-level tab sprawl in the web console. Distinct unit
because it is pure information-architecture/UX work with no tenancy or auth
dependency, and it can ship independently. Kept separate so it does not entangle
the riskier tenancy/auth features.

**Context**:
- Webui `services/webui`. Current nav is a flat `NAV` array in
  `components/Sidebar.tsx`. Three moves: (1) nest maintenance-types
  (`/maintenance-types`, "סוגי טיפול") as a section inside Vehicles
  (`app/(admin)/vehicles`); (2) nest accidents (`/accidents`, "תאונות") as a
  section inside Events (`app/(admin)/events`); (3) remove the Chat/Assistant tab
  entirely (`/chat`, `/assistant`).
- The Chat removal is a deliberate deletion: the fleet-agent + assistant tenancy
  is a separate epic. Removing the tab also moots the current `agent.ts`
  hardcoded-admin cross-tenant leak until that epic.
- Nesting requires a `NavItem` with `children`. Feature 2 owns that shape (it
  defines `NavItem` with `allowedRoles` + `children` up front); this feature
  populates the children and adjusts the renderer/pages. Plan/execute this after
  or alongside Feature 2 to avoid conflicting `Sidebar.tsx` rewrites (see
  Cross-Cutting Concerns). If this feature is taken FIRST, it must itself
  introduce the `children` shape and Feature 2 reuses it.

**Scope Boundaries**:
- Includes: moving maintenance-types under Vehicles; moving accidents under
  Events; removing the Chat/Assistant tab and its nav entry; populating the
  nested-section UI.
- Excludes: any role-based nav filtering mechanism and the `NavItem` shape
  (Feature 2 owns them); any agent/assistant service work (separate epic);
  backend changes.

---

## Sequencing

- **Feature 1 (Tenancy foundation)** first - it is the hard dependency for
  Features 2 and 3 (columns, `CallerContext.company_id`, repo scoping, default
  company).
- **After Feature 1**: Feature 2 (app auth tier) and the fleet-api/telegram-bot
  portions of Feature 3 can be planned in parallel - Feature 3's backend/bot work
  needs only Feature 1.
- **Feature 3's webui Bot-tab gating** needs Feature 2 (role + middleware). So
  finish Feature 2's nav/middleware mechanism before Feature 3's webui slice.
- **Feature 4 (Nav consolidation)** has no hard dependency and can be planned any
  time, but shares `Sidebar.tsx` with Feature 2 - sequence it after (or together
  with) Feature 2 to avoid rework.
- **Independent of each other** once Feature 1 lands: Feature 2 and Feature 3
  (backend/bot). **Coupled by shared webui files**: Features 2, 3 (webui slice),
  and 4.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| A missed `company_id` filter leaks data across tenants | Scoping mechanism (Feature 1) must cover BOTH list selects and by-PK access (`session.get`); review every read/write path; cross-tenant tests asserting empty/403 (incl. by-PK detail/PATCH/DELETE), end-to-end in Feature 2 once the role exists. |
| `db/bootstrap.sql` `refresh_kpi_daily` (pg_cron) is not model-rebuilt and aggregates globally | Feature 1 rewrites it to partition by `company_id` and read per-company config; otherwise nightly KPI both breaks and leaks cross-company aggregates. |
| By-PK routes let a company_admin act on another company's row via a guessed UUID | Feature 1 adds post-fetch company assertions (or filtered fetches) on every detail/PATCH/DELETE path, not just list endpoints. |
| Per-company `system_config` / NOT NULL on derived writes break caller-less paths | Feature 1 makes `system_config` PK composite and adds company inheritance for derived writes (doc-extraction events with unknown plate, km-update, accidents); config readers resolve company from driver/vehicle. |
| Global unique constraints collide across tenants; phone enrollment mis-tenants | Feature 1 scopes `Driver.phone_number`/`Vehicle.licensing_plate`/`MaintenanceType.name` uniqueness per company; Feature 3 matches enrollment within the correct company (guards the auto-enroll-by-phone path). |
| Making `company_id` NOT NULL breaks the existing seed/rebuild | Bot columns stay nullable in Feature 1 (Feature 3 flips them); all `_seed_*` INSERTs are rewritten to set `company_id` after seeding the Default Company; drop-and-recreate + reseed verified in Feature 1. |
| Bot tenancy touches the core telegram-bot service and could regress flows | Feature 3 is isolated; rely on the existing telegram-bot pytest suite and add company-scoping tests per flow; keep schema (Feature 1) separate from behavior (Feature 3). |
| Features 2, 3, 4 conflict editing `Sidebar.tsx`/`middleware.ts` | Feature 2 establishes the `allowedRoles` + `route->allowedRoles` structures first; Features 3 and 4 slot in; sequence the webui slices rather than parallelizing them. |
| JWT issued-but-unused bit-rots before mobile arrives | Keep the token format documented in the spec; Feature 2 includes a unit test asserting issuance/claims so the contract stays exercised. |
| Conflating the `Customer` billing entity with the `Company` tenant | Spec fixes Company as a NEW level above Customer; Feature 1 adds `customers.company_id` rather than repurposing `customer_id`. |
| System-admin "all companies vs active company" reads become inconsistent | Define the selected-vs-all read semantics once in Feature 1's scoping helper; the switcher (Feature 2) only chooses the `company_id` value passed in. |
