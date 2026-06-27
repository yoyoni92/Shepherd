# Impl: Feature 2 - App Auth Tier (channel-agnostic)

**Status**: done (backend + webui) - F1 done
**Epic**: `plans/epics/multi-tenancy-and-company-admin.md` (Feature 2)
**Mode**: ponytail (full) + TDD
**Depends on**: Feature 1

## Goal

Real DB-backed multi-role login. `app_users` table, channel-agnostic
`POST /auth/login` returning `{ user, token }` (portable JWT), `company_admin` role,
app-user + company management routers, and the webui wiring (auth, proxy caller
context, middleware role-gate, company switcher, Companies + Access tabs).

## Ponytail guardrails (decided)

- **No new deps.** Hashing = stdlib `hashlib.pbkdf2_hmac` (salted, ~200k iters),
  stored `pbkdf2_sha256$iters$salt_hex$hash_hex`; util in the `db` package so seed +
  api share it. JWT = ~12-line stdlib HS256 encoder (base64url header.payload.sig);
  **issue only** (mobile Bearer-verify deferred). Secret `AUTH_JWT_SECRET` (env;
  test default in conftest). (Spec said bcrypt/PyJWT - stdlib is the lazier, dep-free,
  still-by-the-book choice in ponytail mode.)
- next-auth keeps server-side `X-Caller-Context` injection; it just wraps `POST /auth/login`.
  Don't rebuild the proxy model.
- `NavItem` gets `allowedRoles` + `children` in ONE type here (F4 reuses).
- Access tab = plain table + a dialog, reuse existing shadcn components and the
  `useBotManagement`-style hook pattern. No new data-layer abstraction.
- Pydantic schemas live in `app/schemas.py` (consistent with the rest); webui mirrors
  with Zod in its own slice. Login response NEVER includes `password_hash`.

## Backend slices (TDD) - DOING NOW

Test home: `services/fleet-api/tests/test_auth_tier.py` (new). Companies CRUD must
land before app_users (company_admin references a company).
- [x] **B1** `Role.company_admin` added; `CallerContext` validator: company_admin requires company_id.
- [x] **B2** `app_users` model (email uniq, password_hash, role admin|company_admin,
      company_id nullable, is_active, name, created_at) + pbkdf2 util in `db`.
- [x] **B3** `/companies` CRUD, admin-only (`MANAGE_COMPANIES`); company_admin -> 403.
- [x] **B4** `/app-users` CRUD, admin-only (`MANAGE_APP_USERS`); create validates
      company_admin requires company_id; responses never leak password_hash.
- [x] **B5** `POST /auth/login` (X-Internal-Token only) -> `{user, token}`; bad creds /
      inactive -> 401; JWT decodes to sub/role/company_id/exp.
- [x] **B6** permission matrix: company_admin mirrors admin for operational actions
      (repo layer still scopes by company_id); denied MANAGE_APP_USERS/MANAGE_COMPANIES.
- [x] **B7** end-to-end: a real `company_admin` caller is forced to its company
      (cross-tenant list empty + by-PK 404) - proves F1 scoping under the real role.
- [x] **B8** seed `_seed_app_users`: env admin (no company) + demo company_admin (default company).

## Webui slices (TDD) - AFTER backend
- [x] proxy builds `X-Caller-Context` from session (admin vs company_admin+company_id).
- [x] `lib/auth.ts` calls `/auth/login`; session carries role/company_id/id.
- [x] middleware route->allowedRoles redirects company_admin off system-only routes.
- [x] `NavItem` allowedRoles+children; nav filtered by role.
- [x] Companies + Access tabs; company switcher; role-based landing.

## Verify command

`cd services/fleet-api && poetry run pytest -q` ; `cd services/webui && npm test`.

## Running log / decisions

- 2026-06-26: stdlib hashing+JWT (no bcrypt/PyJWT) chosen in ponytail mode. Backend
  before webui. Companies before app_users.
- 2026-06-26: backend B1-B8 landed. `AppUser`/`app_user_role_enum` model + pbkdf2
  `shepherd_db.security`; `app/token.py` HS256 issue-only encoder; `/companies`,
  `/app-users`, `/auth/login` routers; matrix gained `MANAGE_APP_USERS`/`MANAGE_COMPANIES`
  and a `company_admin` column on every row. `_seed_app_users` (env admin + demo
  company_admin). `AUTH_JWT_SECRET` added to `.env.example`. New `tests/test_auth_tier.py`;
  full fleet-api suite green (134 passed). Kept `datetime.now(timezone.utc)` to match the
  existing codebase convention (repo-wide UP017, not newly introduced).
- 2026-06-26: webui slice landed. `lib/auth.ts` now wraps `POST /auth/login` (server-side
  `X-Internal-Token`); session/JWT carry role/company_id/id/token (`types/next-auth.d.ts`).
  Fleet proxy builds `X-Caller-Context` from the session via pure `lib/callerContext.ts`
  (company_admin locked to own company; admin scoped to the `active_company_id` switcher
  cookie, omitted for "all"/cross-company). `middleware.ts` hard-gates via `lib/routeAccess.ts`
  (company_admin denied /companies,/access,/health,/config -> redirect /dashboard; /bot allowed).
  `NavItem` gained `allowedRoles`+`children`; nav filtered via `lib/nav.ts`. New Companies +
  Access tabs (hooks `useCompanies`/`useAppUsers`, fleet client fns, Zod schemas) and the
  system-admin company switcher in the Topbar. Pure logic is TDD-covered; `npm test` 99 passed
  (coverage 93%), typecheck + lint + `npm run build` all green. No new deps; no fleet-api change.

## E2E (Playwright) - cross-feature browser coverage (2026-06-26)

Live-stack Playwright proof of the multi-tenancy + company-admin epic, run against
`docker compose up postgres db-init fleet-api webui` (the heavy bot/agent/rag services
are not needed). Specs in `services/webui/e2e/`, asserting by nav `href` so they are
robust to the Hebrew labels:

- `smoke.spec.ts` - system admin reaches every section by URL with no "Application error"
  (maintenance-types/accidents thin-wrapper routes still resolve).
- `system-admin.spec.ts` - admin lands on /dashboard; sidebar exposes
  /companies,/access,/health,/config,/vehicles,/drivers,/bot; has no top-level
  /maintenance-types,/accidents,/chat; maintenance-types is a tab under Vehicles and
  accidents a tab under Events.
- `company-admin.spec.ts` - company@fleetops.io: sidebar hides the system-only sections,
  keeps /vehicles,/drivers,/bot; navigating to /companies is redirected to /dashboard
  (middleware role gate); their company vehicles load without error.
- `helpers.ts` - shared NextAuth login driver + seeded-user constants.

Result: `9 passed`.

Compose wiring fix (required for /auth/login): `docker-compose.yml` fleet-api was missing
`AUTH_JWT_SECRET` (login 500s without it). Added
`AUTH_JWT_SECRET: ${AUTH_JWT_SECRET:-change-me-jwt-secret}`; it was already in
`.env.example`. INTERNAL_SERVICE_TOKEN is shared fleet-api<->webui via the root `.env`.
The persisted `pgdata` volume from a pre-tenancy schema had to be dropped once so
`create_schema.py` + `seed.py` could build the company_id-bearing schema.
