# Multi-Tenancy + Company-Admin Authorization - Design

Date: 2026-06-26
Status: Approved design, pending epic decomposition
Scope: epic (three features on a shared tenancy foundation)

## 1. Goal

Introduce a second authorization tier in the web console and the multi-tenant
data foundation it depends on:

- A new top-level tenant, **Company**, so multiple companies can share one
  deployment with fully isolated data.
- A **company admin** ("client admin") web role: an admin of one company who
  sees and manages everything belonging to their company, but not system-ops,
  company management, or any other company's data.
- A **system admin** (platform/super admin) who operates across companies via a
  company switcher, manages the tenants themselves, and retains system-ops.
- A leaner web-console information architecture (fewer top-level tabs).

The identity and auth contract are deliberately **channel-agnostic**: the web
console is one client of a `POST /auth/login` endpoint over an `app_users`
identity, so a future mobile app reuses the same identity, roles, and login with
only an additive token-transport change. See sections 3 (`app_users`) and 4
(login / mobile readiness).

This supersedes an earlier, narrower interpretation in which "client admin"
mapped to the backend's locked-down `customer` role (a vehicles-and-upload-only
console). With true multi-tenancy, the company admin is a near-full operational
admin scoped to their own company.

## 2. Roles and permission model

| Role | Tenant scope | Console |
| --- | --- | --- |
| `admin` (system) | none; selects an active company via a switcher | All companies (overview) + all company-scoped screens for the active company + bot management across all companies + system-ops (Health, Config) + Companies tab + Access tab |
| `company_admin` (new) | own `company_id` (required) | All company-scoped screens, locked to their own company: Dashboard, Vehicles, Drivers, Customers, Events, Attendance, Accidents, Upload, **Bot (manage their own company's bot users/invites)**. No switcher. |
| `customer` (existing) | own `customer_id` | Unchanged; reserved for future end-customer use. Not provisioned as a web login here. |
| `driver` (existing) | own `driver_id` | Unchanged (telegram bot). |

`company_admin` is a new value added to `Role` (`libs/shepherd_contracts/auth.py`)
and to the fleet-api permission matrix (`services/fleet-api/app/auth.py`).
`CallerContext` gains an optional `company_id`.

### Permission intent for `company_admin`

The company admin is allowed the operational actions an `admin` has, but every
allowed action is **forced to their `company_id`** at the repository layer. This
**includes bot management** (`MANAGE_BOT_USERS`, `MANAGE_BOT_INVITES`): a company
admin invites/manages bot users for their own company only, while the system
admin manages across all companies.
Denied entirely: `MANAGE_APP_USERS`, company CRUD, `MANAGE_COMPANIES`, system-ops
(Health), and anything that would read or write across companies.

## 3. Data model

### New `companies` table (tenant root)
- `company_id` UUID pk
- `name`
- `status` / `is_active`
- `created_at`
- (contact fields optional)

### `company_id` on all domain tables
Add a `company_id` FK -> `companies.company_id` to every domain table: drivers,
customers, vehicles, maintenance_types, accidents, accident_attachments, events,
attendance, reports/tickets, km_updates, vehicle_care, channel_identities, config
(`system_config`), kpi (`kpi_daily`), the bot tables `users` (`BotUser`) +
`bot_authorizations`, and the new app_users. (There is no `documents` table.)
Config and maintenance_types are therefore **per-company**. The column is NOT NULL
everywhere except the bot tables, which start nullable and are flipped to NOT NULL
once the bot writers populate them (see Out of scope / bot tenancy work). Note
`db/bootstrap.sql` (`refresh_kpi_daily`) is hand-written SQL not rebuilt from
models - it must be reworked to partition by `company_id`.

No migrations: schema is rebuilt from `models.py` (`db/create_schema.py`), and the
seed assigns all existing rows to a default company (see Seeding).

### New `app_users` table (channel-agnostic identity)
Deliberately **not** named `web_users`: this is the credentialed application
identity that any first-party client - the web console today, a mobile app later
- authenticates against. The Telegram `bot_users` remains a separate channel
identity. Columns:
- `id` UUID pk
- `email` (unique, not null)
- `password_hash` (not null)
- `role` (enum: `admin` | `company_admin`)
- `company_id` FK -> companies (nullable; required when `role = company_admin`,
  null when `role = admin`)
- `is_active` boolean (default true)
- `name` (nullable display name)
- `created_at`

### Password hashing
Add `bcrypt` as a dependency. A small `hash_password` / `verify_password` util
lives in the shared `db` package so both `db/seed.py` and fleet-api use the same
implementation.

## 4. Backend (fleet-api)

### Authentication / login (channel-agnostic)
- `POST /auth/login` `{ email, password }` -> requires **X-Internal-Token only**
  (no `X-Caller-Context`; this endpoint establishes identity). This is the single
  client-facing auth contract - the web console and any future mobile client use
  it identically. Returns `{ user: { user_id, email, name, role, company_id },
  token }`. Returns 401 on bad credentials or inactive user.
- `token` is a signed JWT with claims `sub = user_id`, `role`, `company_id`,
  `exp`, signed with a fleet-api secret (`AUTH_JWT_SECRET`, new env; lib: PyJWT).
  It is the portable, channel-agnostic credential.
- **Mobile readiness (Option 1):** the JWT is *issued* now and locks the token
  format. fleet-api *verifying* a `Authorization: Bearer <jwt>` to derive
  `CallerContext` is deferred to the mobile feature (see Out of scope). The web
  console keeps its existing server-side `X-Caller-Context` injection unchanged;
  the JWT rides along until mobile consumes it. Adding Bearer verification later
  is purely additive - no change to `app_users`, login, or the permission matrix.

### Tenant scoping
- `verify_internal_token` / `get_caller` (`app/deps.py`) unchanged in shape;
  `CallerContext` now carries `company_id`.
- Every repository read/write that touches a tenant-scoped table filters by
  `company_id` when the caller is company-scoped. Defense in depth: scoping lives
  in the repo layer, not only the router.
  - `company_admin`: always filtered to `caller.company_id`.
  - `admin`: filtered to the **selected** company when the switcher provides a
    `company_id`; unfiltered only on explicit cross-company overview reads.

### App-user management (system-admin only)
- New `Action.MANAGE_APP_USERS` (matrix: `admin: True`, others forbidden).
- Router (requires `X-Caller-Context`, `assert_permitted(MANAGE_APP_USERS)`):
  - `GET /app-users`
  - `POST /app-users` (validates `company_admin` requires `company_id`)
  - `PATCH /app-users/{id}` (reset password, toggle `is_active`)
  - `DELETE /app-users/{id}`

### Company management (system-admin only)
- New `Action.MANAGE_COMPANIES` (matrix: `admin: True`, others forbidden).
- Router: `GET/POST/PATCH/DELETE /companies`.

### Bot tenancy (fleet-api + telegram-bot)
- `MANAGE_BOT_USERS` / `MANAGE_BOT_INVITES` matrix updated to allow
  `company_admin` (scoped) in addition to `admin`. Bot routers filter by
  `company_id`: a `company_admin` sees/creates bot users + authorizations only
  within their company; `admin` operates across companies (or the active company
  via the switcher). `bot_authorizations` and `bot_users` carry `company_id`.
- **All bot flows are company-aware**: every telegram-bot -> fleet-api call
  (`whoami`, `enroll`, attendance clock-in/out, vehicle issue, access requests)
  resolves and carries the enrolled user's `company_id`. Enrollment/authorization
  sets the user's company; `whoami` returns it; downstream flows scope to it.
  This touches the `services/telegram-bot` flows, not just the schema.

### Contracts/schemas
- Pydantic models for `AppUserRead/Create/Update`, `CompanyRead/Create/Update`,
  and the login request/response (incl. `token`), mirrored as Zod schemas in the
  webui.

## 5. WebUI

### Auth
- `lib/auth.ts`: `authorize()` calls the channel-agnostic `POST /auth/login`
  server-side (holds `INTERNAL_SERVICE_TOKEN`) and consumes the `{ user, token }`
  response. next-auth *wraps* this contract - it does not own user identity. The
  next-auth session carries `role`, `company_id`, `id` (and may stash `token` for
  a future mobile-shared path). next-auth types augmented. The plaintext env
  comparison is removed; the env credentials now only seed the DB admin.

### Caller context injection
- Fleet proxy (`app/api/fleet/[...path]/route.ts`): builds `X-Caller-Context`
  from the session - `{ role, company_id? }` - replacing the hardcoded
  `{ role: 'admin' }`. For a system admin, `company_id` is the **active company**
  from the switcher (or omitted for cross-company overview reads).

### Company switcher (system admin only)
- A switcher in the topbar selects the active company; selection is stored in the
  session/context and injected as `company_id`. An "All companies" option is
  available only where cross-company reads are meaningful (Companies tab, global
  overviews). Company admins have no switcher - context is fixed to their company.

### Route enforcement
- Middleware holds a central `route -> allowedRoles` map and hard-gates by
  `token.role`. A `company_admin` hitting a system-only route (`/health`,
  `/companies`, `/access`, `/config`) is redirected to their landing page before
  the page loads. `/bot` is **allowed for both roles** (company-scoped for
  `company_admin`). Brings `/health` and the new tabs under the gate (today they
  are not in the matcher). Backend 403 remains the final backstop.

### Navigation
- `Sidebar` `NAV` items gain `allowedRoles`; filtered by session role.
- Role-based landing: `admin` -> `/dashboard`, `company_admin` -> `/dashboard`
  (company-scoped) — both land on Dashboard, which renders scoped to context.
- `/bot` is visible to `company_admin` (scoped to their company); `/health`,
  `/companies`, `/access`, `/config` remain system-admin only.

### New tabs (system-admin only)
- **Companies** (`/companies`): CRUD tenants.
- **Access** (`/access`): CRUD app-user logins - create (email, password, role,
  company for `company_admin`), list, reset password, toggle active, delete.

### Nav consolidation
- **סוגי טיפול** maintenance-types -> a section inside **Vehicles** (drop the
  top-level tab).
- **תאונות** accidents -> a section inside **Events** (drop the top-level tab).
- **Remove the Chat / Assistant tab entirely** (`/chat`, `/assistant`). The
  fleet-agent + assistant tenancy is handled in a separate epic; this epic just
  removes the tab (which also moots the current `agent.ts` cross-tenant leak).

## 6. Seeding (`db/seed.py`)
- Seed one **Default Company**; assign all existing seeded rows
  (drivers/customers/vehicles/etc.) to it.
- `_seed_app_users()` (idempotent): seed the system `admin` from
  `ADMIN_EMAIL`/`ADMIN_PASSWORD` (hashed, `company_id = null`), and seed one demo
  `company_admin` login bound to the default company.

## 7. Epic decomposition (features)

1. **Tenancy foundation** - `companies` table, `company_id` on all domain tables
   (incl. bot tables), repo-layer scoping, `CallerContext.company_id`,
   default-company seed and backfill of existing seed rows. (Foundation; all
   others depend on it.)
2. **App auth tier** - `app_users` table + bcrypt util, channel-agnostic
   `POST /auth/login` (issues portable JWT), app-user + company management
   routers, webui auth/proxy/middleware/switcher, Companies + Access tabs,
   role-based landing.
3. **Bot tenancy** - company-aware bot management permissions (company_admin
   scoped, admin across all) + the Bot tab visible/scoped for company admins, and
   all telegram-bot flows (whoami, enroll, attendance, vehicle issue, access
   requests) carrying the user's `company_id`. Touches `services/telegram-bot`.
4. **Nav consolidation** - fold maintenance-types into Vehicles, accidents into
   Events, and remove the Chat/Assistant tab. Separable cleanup; can ship
   independently of 2 and 3.

## 8. Out of scope (deferred)
- **Mobile token transport**: fleet-api verifying `Authorization: Bearer <jwt>`
  to derive `CallerContext` (and any mobile client itself). The login endpoint
  already *issues* the JWT, so this is additive - no change to `app_users`,
  login, or the permission matrix.
- **Chat / fleet-agent + assistant tenancy**: handled in a **separate epic**.
  This epic *removes* the Chat/Assistant tab from the webui; the agent/assistant
  services, their `company_id` scoping, and any re-introduction of a scoped Chat
  are out of scope here. (Removing the tab moots the current `agent.ts`
  cross-tenant leak for now.)
- **End-customer (`customer`) web logins**: role retained, not provisioned here.

## 9. Risks / notes
- Blast radius: adding required `company_id` to every domain table touches all
  repos, routers, and seeds. Repo-layer scoping must be exhaustive - a missed
  filter is a cross-tenant data leak.
- `assert_permitted` must reflect `company_admin` for every operational action,
  with repo scoping enforcing the tenant boundary the matrix alone cannot.
- The webui ESLint DB-blind boundary stays intact: all credential checks and
  tenant resolution go through fleet-api, never direct DB access from the webui.
