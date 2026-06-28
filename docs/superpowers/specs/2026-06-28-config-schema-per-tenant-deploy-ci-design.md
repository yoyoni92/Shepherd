# Design: Central Config, Schema-per-Tenant, Deploy Folder, CI

Date: 2026-06-28
Status: Approved (pending spec review)

## Summary

Four coupled deliverables, built as one plan:

1. **Central config file** - a single structured `config.toml` (the source of truth for
   the DB connection string and per-company schema mapping), loaded by a shared
   `shepherd_config` package; secrets stay in the environment via `${VAR}` interpolation.
2. **Schema-per-tenant with a many-to-one company -> schema map** - tenant data lives in a
   Postgres schema chosen by looking up the caller's company, routed via SQLAlchemy
   `schema_translate_map`. The mapping is **many-to-one**: several companies (e.g. subcompanies
   of one large company) can resolve to the **same** schema. The existing `company_id` columns
   and row-level scoping are **kept and load-bearing** - the schema picks the physical location,
   and `WHERE company_id` separates tenants that share a schema.
3. **Deploy folder** - a `deploy/` directory that runs the stack from **pre-built images
   pulled from Docker Hub**, with no `git clone` and no source on the destination host.
4. **CI pipeline** - a path-filtered per-package GitHub Actions matrix that lints, typechecks,
   tests, and (on merge to `main`) builds and pushes service images to Docker Hub.

## Core principle: the schema name is data, not a format

The application **never computes a schema name from a hardcoded format**. There is no
`f"co_{slug}"` anywhere in application code. Instead:

- The per-company schema name is an **opaque string** stored as data: in `config.toml` for
  seeded companies, and in `company_settings.schema_name` (the runtime source of truth).
- Routing always **looks up** the schema name for a company; it never derives it. If a
  company's schema were named `acme_prod` instead of `co_acme`, the app must behave identically.
- The `co_<slug>` convention is only how a human (or the one-time provisioning default) fills
  in the value. Once written, the stored value is canonical and is always read back, never
  reconstructed.

This keeps the app decoupled from any naming scheme and lets the config file fully control
the company -> schema mapping.

### Corollary: the map is many-to-one

The fleet-api determines "where to read/write the data" by **looking up the schema for the
caller's company**. Because the lookup is data, several companies can point at the same schema:
a large company can run two subcompanies inside one shared schema. Consequences:

- `company_id` row scoping is **mandatory for correctness**, not optional. Two subcompanies in a
  shared schema are kept apart solely by `WHERE company_id` / `assert_company`; sharing a schema
  is **physical colocation only**, never shared visibility - each subcompany sees only its own rows.
- Provisioning must not assume one-new-schema-per-company. The target schema may already exist
  (shared with a sibling); create it only if absent, then point the company at it.
- No formal parent/subcompany entity is added (flat model). "Subcompany" is just a company whose
  schema happens to match another's; there is no `parent_company_id`.

## Current state (what we build on)

- **Tenancy today is row-level.** Every tenant table uses `TenantMixin` -> a `company_id` UUID
  FK to `public.companies`. Isolation is enforced by `WHERE company_id = ...` in
  `services/fleet-api/app/repo.py` and `assert_company()` in `services/fleet-api/app/auth.py`
  (cross-tenant by-PK access returns 404). `CallerContext.company_id`
  (`libs/shepherd_contracts/auth.py`) drives scoping.
- **Config is flat and divergent.** A single `DATABASE_URL` is read three ways: `fleet-api`
  reads `os.environ` directly (`app/deps.py`), `telegram-bot` uses `pydantic-settings`
  (`app/config.py`), `webui` uses Next env.
- **No migrations.** `db/create_schema.py` runs `Base.metadata.create_all()` then applies
  `db/bootstrap.sql` (pg_cron jobs). Project rule: wipe and rebuild from models until prod.
- **Docker exists.** `docker-compose.yml` builds postgres (+pg_cron), db-init, fleet-api,
  telegram-bot, webui from per-service `Dockerfile`s.
- **CI is a stub.** `.github/workflows/ci.yml` runs only `libs/` pytest. `Makefile` exposes
  `lint`, `typecheck`, `test` (per package via `SVC=`).

## 1. Central config (`config.toml` + `shepherd_config`)

### Package

New `libs/shepherd_config/` package (published like `shepherd-contracts` / `shepherd-db`,
consumed by `fleet-api` and `telegram-bot` via path deps). Exposes `get_config()` returning a
cached, typed Pydantic model.

- Config file path resolved from `SHEPHERD_CONFIG` env; default `config.toml` at repo root
  (local) or `/etc/shepherd/config.toml` (container).
- TOML holds non-secret structure. Secret values are written as `${VAR}` and resolved from the
  environment at load time, so secrets live in exactly one place (`deploy/.env`) and are never
  committed. Missing required `${VAR}` is a load-time error.

### Shape

```toml
# config.toml   (committed template: config.example.toml)
[database]
url = "${DATABASE_URL}"            # postgresql+psycopg://...
shared_schema = "public"          # where control-plane tables live

[services]
fleet_api_url = "${FLEET_API_URL}"

# Seeded companies: explicit schema name (data, not derived).
# The map is many-to-one: two companies may share a schema (subcompanies).
[[company]]
slug = "default"
schema = "co_default"
[[company]]
slug = "internal"                 # playground / sandbox
schema = "co_internal"
[[company]]
slug = "bigcorp-a"
schema = "co_bigcorp"             # subcompany A and B share one schema
[[company]]
slug = "bigcorp-b"
schema = "co_bigcorp"
```

- `[[company]]` entries seed `company_settings.schema_name`. The same `schema` value may appear on
  multiple entries (shared schema). Runtime-created companies get a default schema name generated
  **once** at provisioning time and then persisted; the app reads the persisted value thereafter.
- Typed model (sketch): `Config(database: DatabaseConfig, services: ServicesConfig,
  companies: list[CompanyConfig])`, each `CompanyConfig(slug: str, schema: str)`.

### Service adoption

- `fleet-api/app/deps.py`: replace `os.environ["DATABASE_URL"]` with `get_config().database.url`.
- `telegram-bot/app/config.py`: source `database_url` / `fleet_api_url` from `get_config()`,
  keeping bot-only env (token, model keys) as-is.
- `webui`: unchanged - keeps reading env, injected by compose from the same `deploy/.env`, so
  the single source of secret values is preserved.

## 2. Schema-per-tenant

### Mechanism

SQLAlchemy **`schema_translate_map`** (idiomatic ORM schema-per-tenant, cleaner than raw
`SET search_path`):

- The 14 `TenantMixin` tables declare a **symbolic** schema token `"tenant"` in
  `__table_args__`. `company_id` columns **stay**.
- Control-plane tables stay in `public` (symbolic schema `None`): `companies`,
  `company_settings`, `app_user`, `bot_session`, `system_config`.
- Cross-schema FK `<<tenant>>.<table>.company_id -> public.companies.company_id` works natively
  in Postgres and preserves referential integrity.

Tenant tables (symbolic schema `"tenant"`): drivers, customers, vehicles, accidents,
accident_attachments, km_updates, vehicle_care, reports, events, maintenance_types,
attendance_records, channel_identity, bot_authorization, bot_user.

### Per-request routing (fleet-api)

- After the caller is resolved, the request's DB session applies
  `connection.execution_options(schema_translate_map={"tenant": <schema_name>, None: "public"})`,
  where `<schema_name>` is **looked up** from `company_settings.schema_name` for
  `caller.company_id` (cached per company). The lookup never reconstructs the name from a format.
- Implemented as a FastAPI dependency wrapping the existing `Db` session dependency, sequenced
  after `Caller`. Use `SET LOCAL`-style per-transaction scoping so a pooled connection never
  leaks one tenant's mapping into another request.
- Row-level scoping (`WHERE company_id`, `assert_company`) is **unchanged** and continues to run.
  It is now load-bearing rather than redundant: when several companies share a schema, it is the
  only thing separating them, so it must always apply (no shared-visibility shortcut).

### Superadmin (`caller.company_id is None`)

- Tenant-table operations require an explicit or impersonated company (matching today's
  impersonation model); the impersonated company selects the schema.
- Genuinely global views read from aggregated tables in `public` (e.g. the KPI snapshot table).
- Where a cross-company tenant-table read is unavoidable, iterate the registered company schemas
  (bounded loop over `company_settings`), set the map per company, union in the app layer. This
  is the documented, bounded exception.

### Provisioning

- `provision_company(company_id)` (in `db/` or fleet-api repo layer): resolve the company's
  `schema_name` (which may be a schema **already shared** with a sibling company),
  `CREATE SCHEMA IF NOT EXISTS`, then `create_all` the tenant tables into it via the translate
  map (idempotent - no-op when the shared schema's tables already exist).
- Called on company creation (fleet-api) and during seed for `[[company]]` entries. Two companies
  pointing at the same schema provision it once; the second simply attaches to the existing schema.

### pg_cron

`db/bootstrap.sql` functions (`refresh_kpi_daily`, `cleanup_expired_bot_access`,
`emit_time_maintenance_due`) currently scan one shared set of tables. Rewrite each to loop over
the registered company schemas (driven by `company_settings.schema_name`) with dynamic SQL,
executing the per-company logic against each schema.

### Rebuild (no migration)

`db/create_schema.py` and `db/seed.py` updated to: create `public` control-plane tables, then
for each seeded company create its schema and provision tenant tables, then seed per-company
data into the right schema. Consistent with the wipe-and-rebuild rule.

## 3. Deploy folder (`deploy/`, no git clone)

```
deploy/
  docker-compose.prod.yml   # image: ${REGISTRY}/shepherd-<svc>:${TAG}  (pull, not build)
  config.example.toml       # central config template
  .env.example              # REGISTRY, TAG, DATABASE_URL, all secrets
  deploy.sh                 # docker compose pull && up -d  (+ db-init / provision)
  README.md                 # destination host needs only Docker + this folder
```

- `docker-compose.prod.yml` mirrors the dev compose but replaces every `build:` with
  `image: ${REGISTRY}/shepherd-<svc>:${TAG}` and mounts the filled `config.toml` into the
  Python services at `/etc/shepherd/config.toml`.
- Flow: copy **only `deploy/`** (or a tarball of it) to the host -> fill `config.toml` and
  `.env` -> run `./deploy.sh`, which pulls images from Docker Hub and starts the stack. No
  source, no clone, no build on the host.

## 4. CI pipeline (`.github/workflows/ci.yml`)

- **Path-filtered matrix**, one leg per package (`libs`, `db`, `fleet-api`, `telegram-bot`,
  `webui`); only changed packages run (e.g. `dorny/paths-filter`).
- Each Python leg runs `make lint typecheck test` for its `SVC`. The `webui` leg runs
  `npm ci && npm run lint && npm run build`.
- **Build + push** stage gated on merge to `main`: `docker/build-push-action` builds each
  service `Dockerfile` and pushes `<org>/shepherd-<svc>:<git-sha>` and `:latest` to Docker Hub.
- Secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (repo secrets).

## 5. Testing & impact

- Extend `services/fleet-api/tests/test_tenancy.py`: assert **physical** schema isolation
  (writes land in the company's schema; a query under company A's map cannot see company B's
  rows in a different schema) on top of the existing 404 row checks.
- New **shared-schema** case: two companies mapped to the same schema still isolate by
  `company_id` - subcompany A cannot read subcompany B's rows even though they share a schema,
  and provisioning the second company does not duplicate the schema's tables.
- New tests: `shepherd_config` loader (TOML parse + `${VAR}` interpolation + missing-var error),
  `provision_company` (schema created, tenant tables present), and the routing dependency
  (correct map applied per caller, no leak across requests).
- Update `testcontainers` fixtures to provision per-company schemas before tests run.

## 6. Build order (within the single plan)

1. `shepherd_config` package + `config.toml` / `config.example.toml` + service adoption.
2. Schema-per-tenant: symbolic schema on tenant models -> routing dependency -> `provision_company`
   -> pg_cron rewrite -> `create_schema.py` / `seed.py` -> tests.
3. `deploy/` folder (`docker-compose.prod.yml`, `deploy.sh`, examples, README).
4. CI rewrite (matrix + quality gates + build/push).

Config lands first because the DB URL and the company -> schema mapping feed everything after it.

## Doc-sync obligations (per CLAUDE.md)

Implementation commits must update, in the same commit: `.env.example` / new `deploy/.env.example`
and `config.example.toml` (new config + secrets), root and service `README.md` (deploy + config
commands), `ROADMAP.md` (CI item moves from "Up Next" to "Done"), and any `plans/` docs that
reference tenancy or config.

## Open questions

- None blocking. Schema naming convention resolved: human-readable `co_<slug>` by convention,
  but stored as data and never derived in code (see Core principle).
- Company -> schema is many-to-one; subcompanies sharing a schema stay isolated by `company_id`;
  no formal parent entity (flat model). See "Corollary: the map is many-to-one".
