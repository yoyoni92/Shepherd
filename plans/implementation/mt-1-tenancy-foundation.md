# Impl: Feature 1 - Tenancy Foundation

**Status**: done
**Epic**: `plans/epics/multi-tenancy-and-company-admin.md` (Feature 1)
**Spec**: `docs/superpowers/specs/2026-06-26-multi-tenancy-and-company-admin-design.md`
**Mode**: ponytail (full) + TDD (vertical slices, one test -> one impl)

## Goal

`companies` tenant root + `company_id` on every domain table + tenant scoping in
fleet-api keyed on `CallerContext.company_id` presence. DB rebuilds and seeds with
a Default Company. No webui, no app_users, no bot behavior (later features).

## Ponytail guardrails (decided once)

- Scope predicate = **`caller.company_id is not None`**, not `Role.company_admin`
  (that enum lands in F2). One scoping helper for selects; one assert for by-PK.
- One helper `scoped(stmt, model, caller)` adds `WHERE company_id = caller.company_id`
  when caller is company-scoped; admin with no `company_id` -> unfiltered. `# ponytail`.
- By-PK paths: don't rewrite all `session.get` calls. One `assert_company(row, caller)`
  raised after fetch. Smaller diff than threading filters through every getter.
- Derived writes inherit `company_id` from the parent row already being loaded
  (vehicle/driver) - no new lookups.
- **POC, disposable DB**: no backward-compat, no nullable transition, no backfill.
  `company_id` goes **NOT NULL** on every tenant table now (incl. bot tables);
  drop-and-recreate + reseed. Default Company has a fixed UUID so tests + seed are
  deterministic.
- Writes happen *within a company*: create endpoints set `company_id` from
  `caller.company_id`; derived writes (km/accident/doc events, attachments) inherit
  from the parent vehicle/driver. Tests' `admin_headers()` carries the Default
  Company id so existing creates keep working; `superadmin_headers()` (no company)
  covers the cross-company case.
- Seed: rewrite the `_seed_*` INSERTs to carry `company_id` of the Default Company.
  No backfill migration - drop & recreate (the team's model already).
- `refresh_kpi_daily` (bootstrap.sql): add `company_id` to the partition + composite
  key. Minimal rewrite, not a redesign.

## TDD slices (RED -> GREEN, tick as done)

Test home: `services/fleet-api/tests/` (pytest). Use existing `*_headers()` helpers in
`conftest.py`; add a `company_admin`-style header (role admin + `company_id`) - we only
need `company_id` presence here, role value is F2.

- [x] **S1** list scoping: caller with `company_id=A` lists vehicles -> only A's rows.
      (tracer bullet - `test_tenancy.py`; 12 passed incl. vehicles suite, no regression)
- [x] **S2** cross-company by-PK read: caller A GETs B's vehicle by plate -> 404.
- [x] **S3** cross-company by-PK write: caller A PATCH/DELETE B's vehicle -> 404 (404 not
      403 - probing existence is itself a leak).
- [x] **S4** admin breadth: no `company_id` (superadmin) -> all rows; `company_id=A` -> only A.
- [x] **S5** derived write inherits tenant: km-update/accident on A's vehicle writes a
      row with `company_id=A` (no caller company needed); the accident_logged event inherits too.
- [x] **S6** per-company config: `system_config` keyed `(company_id, config_key)`;
      reads for A don't see B's value.
- [x] **S7** rebuild+seed: building the schema + seed yields a Default Company with all
      seeded vehicles/drivers/customers attached to it (verified on a fresh container:
      0 null company_ids, 5 per-company config rows, 1 per-company kpi_daily row).

## Non-TDD verification

- [x] `refresh_kpi_daily` produces `kpi_daily` rows carrying `company_id` (rewritten to
      partition every aggregate by `company_id`, driven off the `companies` table, with
      per-company alert thresholds from `system_config`; `ON CONFLICT (snapshot_date,
      company_id)`). Verified: 1 row, non-null company_id on the seeded DB.
- [x] Full rebuild: `create_schema.build()` + `seed.seed()` runs clean with `company_id`
      NOT NULL on non-bot tables (verified on a fresh testcontainer).

## Verify command

`cd services/fleet-api && pytest -q` (+ the db rebuild/seed entry once wired).

## Running log / decisions

- 2026-06-26: models.py read. Tenant tables confirmed: drivers, customers, vehicles,
  maintenance_types, accidents, accident_attachments, km_updates, vehicle_care, reports,
  events, system_config, kpi_daily, attendance_records, channel_identities, + bot `users`
  & `bot_authorizations` (nullable). `bot_sessions` is chat-state only -> **no** tenant
  column (ponytail: skip, it's not domain data).
- 2026-06-26: **scoping mechanism decided + proven (S1 tracer).** Thread `company_id`
  through repo fns exactly like the existing `customer_id`/`driver_id` kwargs; router
  reads `caller.company_id`. No global ORM filter (it's bypassed by `session.get` and is a
  3am surprise). By-PK paths get a post-fetch `assert_company` (S2/S3, not yet built).
- Tests run via `cd services/fleet-api && poetry run pytest` (Python 3.14 poetry venv;
  bare `python` is pyenv 3.14 without pytest). Docker present for testcontainers PG.
- `Vehicle.company_id` is **nullable** right now so existing create paths/tests still pass;
  NOT NULL flips only after every writer + seed set it (later slices).
- 2026-06-26: user approved full F1 ("set it all", POC, disposable DB). Mechanism fixed =
  explicit threading (S1 pattern) + `assert_company` for by-PK. Read every router/repo/seed/
  bootstrap. Broad mechanical rollout delegated to one impl agent against this spec with the
  pytest suite as the contract; I review the diff + rerun for leaks after.
- Bot tables (`users`, `bot_authorizations`): `company_id` stays **nullable** in F1 (their
  writers are F3); seed sets them to Default Company. All other tenant tables NOT NULL.
- Default Company fixed UUID `00000000-0000-0000-0000-0000000000c0`. conftest `admin_headers()`
  carries it (so existing creates keep passing); `superadmin_headers()` = no company (read-all).
- Caller-less config readers resolve company from the row they already hold: `update_km` ->
  vehicle.company_id; attendance clock -> driver.company_id.
- 2026-06-26: impl agent landed the rollout (119 green). **Independent review found 1 leak the
  agent missed**: `PATCH /attendance/{driver_id}/{day}` wrote by a caller-supplied driver_id with
  no company check (company-A admin could write onto company-B's driver). Added RED test
  `test_cross_tenant_attendance_upsert_returns_404`, then guarded `upsert_day` with
  `assert_company(driver, caller)`. Full suite now **120 passed**.
- Known POC edge (acceptable): `get_vehicle_by_plate` for a superadmin (no company) would raise if
  two companies ever share a plate; seed plates are unique, so not hit. `# ponytail`.
- F1 status: **done**. Bot-table `company_id` stays nullable for F3 to populate.
- 2026-06-26: **full F1 rollout landed (S2-S7 + non-TDD checks).** `TenantMixin` (NOT NULL
  `company_id`) mixed into all 12 domain tables; Vehicle's tracer column dropped for the mixin;
  per-company unique constraints on driver phone / vehicle plate / maintenance-type name;
  `system_config` + `kpi_daily` got composite PKs `(company_id, ...)`; bot `users` +
  `bot_authorizations` got a direct nullable `company_id` (writers are F3). `assert_company`
  added to `auth.py` and wired into every by-PK read/write (vehicles/drivers/customers/
  maintenance-types) plus the vehicle-keyed derived writes (km/accident/care) so a scoped
  caller can't touch another tenant's row (404). Every `list_*` got a `company_id` kwarg;
  routers thread `caller.company_id`; creates inject it; derived writes inherit from the
  parent vehicle/driver. `refresh_kpi_daily` rewritten per-company. seed.py + conftest carry
  the fixed Default Company id `...00c0`. Full suite: **119 passed**. Judgment call (noted to
  user): added `assert_company` to km/accident/care derived-write routes too (spec only
  itemised it for the CRUD routers) to close an admin-cross-tenant write path.
