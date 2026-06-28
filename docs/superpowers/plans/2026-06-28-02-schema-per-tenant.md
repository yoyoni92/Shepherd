# Schema-per-Tenant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route each company's fleet-api domain data to a Postgres schema that is *looked up*
from the caller's company (many companies may share one schema), using SQLAlchemy
`schema_translate_map`. The schema name is data (`company_settings.schema_name`), never computed
from a format string. `company_id` columns and row-level scoping (`assert_company` / `WHERE
company_id`) are KEPT and become load-bearing: they isolate subcompanies that *share* a schema.

**Architecture:** The 11 fleet-api domain tables declare a symbolic schema token `"tenant"` in
`__table_args__`. Control-plane and identity tables stay in `public` (symbolic schema `None`).
`db/provisioning.py` exposes `TENANT_TABLES` and `provision_company(conn_or_engine, schema_name)`
which `CREATE SCHEMA IF NOT EXISTS` then creates the tenant `Table` objects into it via a
connection carrying `schema_translate_map={"tenant": schema_name, None: shared}` (idempotent,
`checkfirst=True`). fleet-api's `Db` dependency resolves `caller.company_id -> schema_name`
(cached) and binds the request `Session` on a connection with
`execution_options(schema_translate_map={"tenant": <schema>, None: <shared>})`. A company-less
caller (superadmin, or the company-less `whoami`/`bot-enroll` endpoints) binds `tenant -> shared`;
the one company-less path that must read tenant data across companies (driver-by-phone enrollment
scan) iterates the registered schemas explicitly.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x (schema_translate_map), Postgres, FastAPI, pytest + testcontainers.

## Global Constraints
- KEEP `company_id` + `assert_company` + repo `WHERE company_id` scoping (load-bearing).
- schema name is data (`company_settings.schema_name`), never derived in code.
- no DB migrations: wipe + rebuild from models.
- depends on plan 01 (`shepherd_config`) being implemented first. From plan 01 this plan
  consumes: `shepherd_config.get_config() -> Config` with `Config.database.url`,
  `Config.database.shared_schema` (`"public"`), `Config.companies: list[CompanyConfig(slug:str,
  schema_name:str)]`; and the DB column `CompanySettings.schema_name: str`.

## Resolved design decisions (read before starting)

**1. Final table placement.**

Tenant set (symbolic schema `"tenant"`, 11 tables) - the fleet-api domain tables:
`drivers`, `customers`, `maintenance_types`, `vehicles`, `accidents`, `accident_attachments`,
`km_updates`, `vehicle_care`, `reports`, `events`, `attendance_records`.

Public set (symbolic schema `None`): `companies`, `company_settings`, `app_users`,
`impersonation_audit`, `kpi_daily`, `system_config`, `channel_identities`, `users` (BotUser),
`bot_authorizations`, `bot_sessions`.

- `users`, `bot_authorizations`, `bot_sessions` stay public: they are read by a non-company key
  (`telegram_chat_id` / `phone`) before any company is known (`whoami`, `bot-enroll`, the bot's
  own `bot_sessions` pool).
- `channel_identities` stays public *deliberately*: it is an identity table keyed by
  `(channel, external_id)` - the same shape as `users` (resolved by an external id before a
  company is known). Keeping it public preserves the global `(channel, external_id)` uniqueness
  and avoids a cross-schema scan if/when a channel lookup precedes company resolution. It is
  currently unused by fleet-api app code (only seeded), so this carries no app-layer change.
- `system_config` stays public *deliberately*: its PK is composite `(company_id, config_key)` (a
  per-company config tag, like `kpi_daily`, not a domain row), `refresh_kpi_daily` joins it
  alongside `companies` in public, and `WHERE company_id` already isolates it
  (`test_per_company_config_isolation`). Lowest diff; no app-layer change.

**2. Named PG enums.** The named enum types (`driver_status_enum`, ...) keep `create_type=True`
and the SQLAlchemy default `inherit_schema=False`, so they are emitted *unqualified* and live
once in `public` (resolved via search_path), NOT replicated per schema. `provision_company`
creates tenant tables with `checkfirst=True`; on the first schema the enum already exists (public
tables, incl. the enum types, are created before any provisioning in `build()`), and on a 2nd /
shared schema `checkfirst` finds the existing type and skips `CREATE TYPE` - so provisioning a
second schema never raises "type already exists". The no-op-on-second-schema test (Task 2) guards
this. The enum definitions in `models.py` are left unchanged.

**3. Provisioning a subset of tables.** `TENANT_TABLES` is the list of the 11 tenant `Table`
objects, taken from `Base.metadata.sorted_tables` (topological FK order) filtered by name.
`provision_company` runs `CREATE SCHEMA IF NOT EXISTS "<schema_name>"` then iterates
`TENANT_TABLES` calling `table.create(conn, checkfirst=True)` on a connection carrying
`execution_options(schema_translate_map={"tenant": schema_name, None: shared})`. `build()` creates
the public tables with `Base.metadata.create_all(engine, tables=PUBLIC_TABLES)` so the literal
`"tenant"` token is never emitted by a plain `create_all`.

**4. Cross-schema FKs.** `tenant.<table>.company_id -> public.companies.company_id` works: symbolic
schema `None` maps to `public`, so the FK DDL emits `REFERENCES public.companies` and Postgres
enforces it natively (tenant -> public is the one allowed cross-schema FK direction; `companies`
is stable in public). Tenant -> tenant FKs (e.g. `vehicles.driver_id -> drivers.driver_id`)
collapse to same-schema FKs under the translate map. **Public -> tenant FKs cannot exist** (the
referenced tenant table may live in any schema), so three existing constraints are dropped to
plain `UUID` columns: `kpi_daily.top_customer_id`, `users.driver_id`, `bot_authorizations.driver_id`.
The ORM `Driver` relationships on `BotUser` / `BotAuthorization` become `viewonly` with an explicit
`primaryjoin` so they still lazy-load under whatever schema the session is bound to.

---

### Task 1 - Symbolic `tenant` schema on the domain models; drop public->tenant FKs

**Files:** `db/shepherd_db/models.py`, `db/tests/test_schema_tokens.py` (new).

**Interfaces:**
- Produces: the 11 tenant tables carry `Table.schema == "tenant"`; public tables carry
  `Table.schema is None`; `kpi_daily.top_customer_id`, `users.driver_id`,
  `bot_authorizations.driver_id` have no `ForeignKeyConstraint`.
- Consumes: nothing new.

Steps:

- [x] 1. Write the failing test `db/tests/test_schema_tokens.py`:

```python
"""The tenant domain tables carry the symbolic 'tenant' schema token; control-plane
and identity tables stay in public (schema None); no public->tenant FK survives."""
from shepherd_db.models import Base

TENANT = {
    "drivers", "customers", "maintenance_types", "vehicles", "accidents",
    "accident_attachments", "km_updates", "vehicle_care", "reports", "events",
    "attendance_records",
}
PUBLIC = {
    "companies", "company_settings", "app_users", "impersonation_audit", "kpi_daily",
    "system_config", "channel_identities", "users", "bot_authorizations", "bot_sessions",
}


def _table(name):
    return Base.metadata.tables[name] if name in Base.metadata.tables else \
        next(t for t in Base.metadata.tables.values() if t.name == name)


def test_tenant_tables_use_symbolic_schema():
    for name in TENANT:
        assert _table(name).schema == "tenant", name


def test_public_tables_have_no_schema():
    for name in PUBLIC:
        assert _table(name).schema is None, name


def test_no_public_to_tenant_foreign_keys():
    # kpi_daily.top_customer_id, users.driver_id, bot_authorizations.driver_id were FKs
    # to tenant tables; they must now be plain columns (no FK across the public/tenant line).
    for tname, col in [
        ("kpi_daily", "top_customer_id"),
        ("users", "driver_id"),
        ("bot_authorizations", "driver_id"),
    ]:
        assert not _table(tname).c[col].foreign_keys, f"{tname}.{col} still has a FK"
```

- [x] 2. Run, expect FAIL:
  `cd db && poetry run pytest tests/test_schema_tokens.py -q`
  Expected: `AssertionError: drivers` (the tenant tables have `schema is None`) /
  `... still has a FK`.

- [x] 3. Minimal impl in `db/shepherd_db/models.py`.

  Update `TenantMixin` docstring note (optional) and add the `"tenant"` token to each of the 11
  tenant tables' `__table_args__`. For the four tables that already have a tuple, append the dict:

```python
class Driver(TenantMixin, Base):
    __tablename__ = "drivers"
    # ... columns unchanged ...
    __table_args__ = (UniqueConstraint("company_id", "phone_number"), {"schema": "tenant"})
```

```python
class MaintenanceType(TenantMixin, Base):
    __tablename__ = "maintenance_types"
    # ... columns unchanged ...
    __table_args__ = (UniqueConstraint("company_id", "name"), {"schema": "tenant"})
```

```python
class Vehicle(TenantMixin, Base):
    __tablename__ = "vehicles"
    # ... columns + relationships unchanged ...
    __table_args__ = (UniqueConstraint("company_id", "licensing_plate"), {"schema": "tenant"})
```

```python
class AttendanceRecord(TenantMixin, Base):
    __tablename__ = "attendance_records"
    # ... columns unchanged ...
    __table_args__ = (UniqueConstraint("driver_id", "work_date"), {"schema": "tenant"})
```

  For the seven tenant tables with no existing `__table_args__`, add one. Insert this line into
  each class body (`Customer`, `Accident`, `AccidentAttachment`, `KmUpdate`, `VehicleCare`,
  `Report`, `Event`):

```python
    __table_args__ = {"schema": "tenant"}
```

  Drop the public->tenant FK on `kpi_daily.top_customer_id` (denormalized snapshot column):

```python
    top_customer_id = mapped_column(UUID(as_uuid=True), nullable=True)
```

  Drop the FK + rework the relationship on `BotAuthorization.driver_id`:

```python
    driver_id = mapped_column(UUID(as_uuid=True), nullable=True)
    # ... company_id, expires_at, created_at unchanged ...

    # ponytail: cross-schema (public->tenant) FK is impossible; viewonly relationship
    # resolves under whatever schema the session is bound to.
    driver = relationship(
        "Driver",
        primaryjoin="foreign(BotAuthorization.driver_id) == Driver.driver_id",
        viewonly=True,
        uselist=False,
    )
```

  Drop the FK + rework the relationship on `BotUser.driver_id`:

```python
    driver_id = mapped_column(UUID(as_uuid=True), nullable=True)
    # ... company_id, expires_at, created_at unchanged ...

    # ponytail: cross-schema (public->tenant) FK is impossible; viewonly relationship
    # resolves under whatever schema the session is bound to.
    driver = relationship(
        "Driver",
        primaryjoin="foreign(BotUser.driver_id) == Driver.driver_id",
        viewonly=True,
        uselist=False,
    )
```

- [x] 4. Run, expect PASS:
  `cd db && poetry run pytest tests/test_schema_tokens.py -q`

- [x] 5. Commit:

```
git add db/shepherd_db/models.py db/tests/test_schema_tokens.py
git commit -m "tag domain tables with the symbolic tenant schema

Add a {\"schema\": \"tenant\"} token to the 11 fleet-api domain tables so
schema_translate_map can route them per company, and drop the three
public->tenant foreign keys (kpi_daily.top_customer_id, users.driver_id,
bot_authorizations.driver_id) that cannot span the public/tenant line.
The dropped FK columns stay as plain UUIDs; the BotUser/BotAuthorization
driver relationships become viewonly so they resolve under the bound schema."
```

---

### Task 2 - `db/provisioning.py`: `TENANT_TABLES` + `provision_company`

**Files:** `db/provisioning.py` (new), `db/tests/test_provisioning.py` (new).

**Interfaces:**
- Produces:
  - `TENANT_TABLES: list[Table]` - the 11 tenant `Table` objects in FK-topological order.
  - `provision_company(conn_or_engine, schema_name: str, shared_schema: str = "public") -> None`
    - `CREATE SCHEMA IF NOT EXISTS <schema_name>`; creates `TENANT_TABLES` into it via
      `schema_translate_map={"tenant": schema_name, None: shared_schema}`; idempotent.
- Consumes: `shepherd_db.models.Base`.

Steps:

- [x] 1. Write the failing test `db/tests/test_provisioning.py`:

```python
"""provision_company creates the schema + the 11 tenant tables, idempotently, and a
second company sharing the same schema_name is a no-op (no error, no duplicate types)."""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, inspect, text
from testcontainers.postgres import PostgresContainer

sys.path.insert(0, str(Path(__file__).parents[1]))  # db/
from provisioning import TENANT_TABLES, provision_company  # noqa: E402
from shepherd_db.models import Base  # noqa: E402

TENANT_NAMES = {t.name for t in TENANT_TABLES}


@pytest.fixture(scope="module")
def engine():
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        eng = create_engine(pg.get_connection_url())
        # public tables first so the named enum types exist once in public.
        public = [t for t in Base.metadata.sorted_tables if t.name not in TENANT_NAMES]
        Base.metadata.create_all(eng, tables=public)
        yield eng
        eng.dispose()


def test_tenant_table_set_is_the_eleven_domain_tables(engine):
    assert TENANT_NAMES == {
        "drivers", "customers", "maintenance_types", "vehicles", "accidents",
        "accident_attachments", "km_updates", "vehicle_care", "reports", "events",
        "attendance_records",
    }


def test_provision_creates_schema_and_tenant_tables(engine):
    provision_company(engine, "co_acme")
    insp = inspect(engine)
    assert "co_acme" in insp.get_schema_names()
    tables = set(insp.get_table_names(schema="co_acme"))
    assert TENANT_NAMES <= tables


def test_second_company_sharing_a_schema_is_a_noop(engine):
    # First company provisions co_shared; a sibling pointing at the same schema must
    # not error (tables + enum types already exist -> checkfirst skips).
    provision_company(engine, "co_shared")
    provision_company(engine, "co_shared")  # must not raise
    insp = inspect(engine)
    assert {t.name for t in TENANT_TABLES} <= set(insp.get_table_names(schema="co_shared"))
```

- [x] 2. Run, expect FAIL:
  `cd db && poetry run pytest tests/test_provisioning.py -q`
  Expected: `ModuleNotFoundError: No module named 'provisioning'`.

- [x] 3. Minimal impl `db/provisioning.py`:

```python
"""Provision a Postgres schema with the tenant (domain) tables.

The schema name is data (read from config / company_settings), never derived here.
Provisioning is idempotent: CREATE SCHEMA IF NOT EXISTS + create_all(checkfirst) of just
the tenant tables under a schema_translate_map. A second company that shares a schema_name
re-attaches to the existing schema (no-op)."""
from sqlalchemy.engine import Connection, Engine

from shepherd_db.models import Base

# The fleet-api domain tables that live in a per-company (symbolic "tenant") schema.
_TENANT_NAMES = {
    "drivers", "customers", "maintenance_types", "vehicles", "accidents",
    "accident_attachments", "km_updates", "vehicle_care", "reports", "events",
    "attendance_records",
}

# Table objects in FK-topological order (sorted_tables) so create runs parent-first.
TENANT_TABLES = [t for t in Base.metadata.sorted_tables if t.name in _TENANT_NAMES]


def _provision(conn: Connection, schema_name: str, shared_schema: str) -> None:
    # ponytail: schema_name is config data; quote it for SQL-safety, never format a name.
    conn.exec_driver_sql(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
    tconn = conn.execution_options(
        schema_translate_map={"tenant": schema_name, None: shared_schema}
    )
    for table in TENANT_TABLES:
        table.create(tconn, checkfirst=True)


def provision_company(
    conn_or_engine, schema_name: str, shared_schema: str = "public"
) -> None:
    """Create <schema_name> and the tenant tables in it. Idempotent."""
    if isinstance(conn_or_engine, Engine):
        with conn_or_engine.begin() as conn:
            _provision(conn, schema_name, shared_schema)
    else:
        _provision(conn_or_engine, schema_name, shared_schema)
```

- [x] 4. Run, expect PASS:
  `cd db && poetry run pytest tests/test_provisioning.py -q`

- [x] 5. Commit:

```
git add db/provisioning.py db/tests/test_provisioning.py
git commit -m "add provision_company for per-tenant schema creation

Introduce TENANT_TABLES (the 11 domain Table objects in FK order) and
provision_company, which creates a schema and the tenant tables in it via
schema_translate_map with checkfirst, so provisioning is idempotent and a
second company sharing a schema name is a no-op."
```

---

### Task 3 - `build()` creates public-only + provisions config schemas; `seed.py` writes tenant rows under each company's schema

**Files:** `db/create_schema.py`, `db/seed.py`.

**Interfaces:**
- Consumes: `shepherd_config.get_config()` (plan 01); `provision_company`, `TENANT_TABLES`.
- Produces: `build(engine)` creates public tables (via `create_all(tables=PUBLIC)`), applies
  `bootstrap.sql`, then provisions each distinct `schema_name` from config. `seed(engine)` upserts
  `company_settings.schema_name` from config and seeds domain rows under the company's schema.

Steps:

- [x] 1. Write the failing test `db/tests/test_build_provisions.py`:

```python
"""build() creates only public tables in public, then provisions each config schema
with the tenant tables; tenant tables are NOT created in public."""
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, inspect
from testcontainers.postgres import PostgresContainer

sys.path.insert(0, str(Path(__file__).parents[1]))  # db/
from create_schema import build  # noqa: E402


@pytest.fixture(scope="module")
def engine(monkeypatch_module):
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        eng = create_engine(pg.get_connection_url())
        yield eng
        eng.dispose()


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


def test_build_keeps_tenant_tables_out_of_public_and_provisions_config_schema(engine, monkeypatch_module):
    # Point config at one dedicated schema for the default company.
    from types import SimpleNamespace
    import shepherd_config

    cfg = SimpleNamespace(
        database=SimpleNamespace(url=str(engine.url), shared_schema="public"),
        companies=[SimpleNamespace(slug="default", schema_name="co_default")],
    )
    monkeypatch_module.setattr(shepherd_config, "get_config", lambda: cfg)

    build(engine)
    insp = inspect(engine)
    public_tables = set(insp.get_table_names(schema="public"))
    assert "companies" in public_tables          # control-plane lands in public
    assert "drivers" not in public_tables         # tenant table NOT in public
    assert "co_default" in insp.get_schema_names()
    assert "drivers" in set(insp.get_table_names(schema="co_default"))
```

- [x] 2. Run, expect FAIL:
  `cd db && poetry run pytest tests/test_build_provisions.py -q`
  Expected: `assert 'drivers' not in public_tables` fails (today `create_all` creates every table
  in public).

- [x] 3. Minimal impl `db/create_schema.py`:

```python
#!/usr/bin/env python3
"""Build the schema straight from the models (no migrations - pre-prod, DB is disposable).

Public (control-plane + identity) tables are created in public; each distinct schema named
in config is provisioned with the tenant tables. bootstrap.sql holds the non-model SQL.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from shepherd_config import get_config
from shepherd_db.models import Base

from provisioning import TENANT_TABLES, provision_company

_BOOTSTRAP = os.path.join(os.path.dirname(__file__), "bootstrap.sql")
_TENANT = {t.name for t in TENANT_TABLES}
PUBLIC_TABLES = [t for t in Base.metadata.sorted_tables if t.name not in _TENANT]


def build(engine: Engine) -> None:
    """create public tables + bootstrap.sql, then provision each config schema."""
    Base.metadata.create_all(engine, tables=PUBLIC_TABLES)
    with engine.begin() as conn:
        conn.exec_driver_sql(open(_BOOTSTRAP).read())
    cfg = get_config()
    for schema in {c.schema_name for c in cfg.companies}:
        provision_company(engine, schema, shared_schema=cfg.database.shared_schema)


def main() -> None:
    build(create_engine(get_config().database.url))
    print("Schema created from models.")


if __name__ == "__main__":
    main()
```

  Note: `create_schema.py` lives in `db/` (same dir as `provisioning.py`); `import provisioning`
  resolves because db-init and the test fixtures put `db/` on `sys.path` (existing pattern in
  `conftest.apply_schema`).

- [x] 4. Run, expect PASS:
  `cd db && poetry run pytest tests/test_build_provisions.py -q`

- [x] 5. Update `db/seed.py` so tenant rows land in the company's schema. Replace the imports and
  add a search_path helper + per-company seeding. At the top, after the existing imports:

```python
from shepherd_config import get_config


def _schema_for(conn, company_id) -> str:
    """The company's schema_name (data), falling back to the shared schema."""
    shared = get_config().database.shared_schema
    row = conn.execute(
        text("SELECT schema_name FROM company_settings WHERE company_id = :id"),
        {"id": company_id},
    ).scalar()
    return row or shared


def _use_schema(conn, schema: str) -> None:
    # Tenant inserts resolve to <schema>; companies/enum types fall back to public.
    conn.exec_driver_sql(f'SET search_path TO "{schema}", public')


def _use_public(conn) -> None:
    conn.exec_driver_sql("SET search_path TO public")
```

  Replace `_seed_company_settings` so it writes the config schema name:

```python
def _seed_company_settings(conn):
    # schema_name comes from config (data). Default Company -> its configured schema.
    schema = next(
        (c.schema_name for c in get_config().companies if c.slug == "default"),
        get_config().database.shared_schema,
    )
    conn.execute(
        text("""
            INSERT INTO company_settings (company_id, schema_name, feature_flags)
            VALUES (:id, :schema, '{}'::jsonb)
            ON CONFLICT (company_id) DO UPDATE SET schema_name = EXCLUDED.schema_name
        """),
        {"id": DEFAULT_COMPANY_ID, "schema": schema},
    )
```

  In `_seed_playground`, set its schema on the settings insert (Playground uses the shared schema
  by default - it is internal and need not have a dedicated schema):

```python
    conn.execute(
        text("""
            INSERT INTO company_settings (company_id, schema_name, feature_flags)
            VALUES (:id, :schema, '{"attendance": true}'::jsonb)
            ON CONFLICT (company_id) DO UPDATE SET schema_name = EXCLUDED.schema_name
        """),
        {"id": PLAYGROUND_COMPANY_ID, "schema": get_config().database.shared_schema},
    )
```

  Rewrite `seed()` to provision schemas and wrap each company's tenant inserts in its schema. The
  Playground driver/vehicle inserts inside `_seed_playground` run under its schema, so split
  `_seed_playground` into its public part (company + settings) and its tenant part, or simply set
  search_path around it. Minimal version - set search_path around the per-company tenant helpers:

```python
def seed(engine):
    cfg = get_config()
    for schema in {c.schema_name for c in cfg.companies}:
        provision_company(engine, schema, shared_schema=cfg.database.shared_schema)
    with engine.connect() as conn:
        # ---- public rows (no schema routing) ----
        _seed_companies(conn)
        _seed_company_settings(conn)
        _seed_playground(conn)            # company + settings rows (public) + playground tenant rows
        _seed_system_config(conn)         # system_config is public
        _seed_channel_identities(conn)    # channel_identities is public
        _seed_app_users(conn)             # app_users is public
        # ---- Default Company tenant rows, under its schema ----
        _use_schema(conn, _schema_for(conn, DEFAULT_COMPANY_ID))
        _seed_drivers(conn)
        _seed_customers(conn)
        _seed_maintenance_types(conn)
        _seed_vehicles(conn)
        _seed_accidents(conn)
        _seed_accident_attachments(conn)
        _seed_km_updates(conn)
        _seed_vehicle_care(conn)
        _seed_reports(conn)
        _seed_events(conn)
        _use_public(conn)
        conn.commit()
```

  In `_seed_playground`, wrap its driver/vehicle inserts (tenant) with the schema. Right before its
  `for i in range(1, 4):` driver loop add `_use_schema(conn, _schema_for(conn, PLAYGROUND_COMPANY_ID))`
  and after the vehicle loop add `_use_public(conn)`. The company + settings inserts at the top of
  `_seed_playground` stay under public. Add the import for `provision_company` in `seed.py`:
  `from provisioning import provision_company`. Update `main()` to use
  `create_engine(get_config().database.url)`.

  `# ponytail:` seed still seeds only the Default + Playground companies; multi-company seeding from
  every `[[company]]` entry is the ceiling, not built here. When a config schema equals the shared
  schema, search_path routing is a no-op and behaviour matches today.

- [x] 6. Run the db test suite (ensure seed still imports/parses and existing db tests are green):
  `cd db && poetry run pytest -q`

- [x] 7. Commit:

```
git add db/create_schema.py db/seed.py db/tests/test_build_provisions.py
git commit -m "build public tables then provision per-company schemas

create_schema.build now creates only the public (control-plane + identity)
tables in public, applies bootstrap.sql, and provisions each distinct schema
named in config with the tenant tables. seed writes company_settings.schema_name
from config and routes each company's domain inserts under its schema via
search_path, so tenant rows land in the right schema."
```

---

### Task 4 - Scoped `Db`: resolve `caller.company_id -> schema_name` and bind the request session

**Files:** `services/fleet-api/app/deps.py`, `services/fleet-api/tests/test_schema_routing.py` (new).

**Interfaces:**
- Consumes: `shepherd_config.get_config()`; `CompanySettings.schema_name`; `CallerContext`.
- Produces: `get_db` yields a `Session` bound to a connection carrying
  `execution_options(schema_translate_map={"tenant": <schema>, None: <shared>})`, where `<schema>`
  is looked up (cached) from `company_settings.schema_name` for `caller.company_id` (shared schema
  when company-less or unset). `Db = Annotated[Session, Depends(get_db)]` is unchanged in name, so
  every router gets routing for free (lowest diff - no router edits).

Steps:

- [ ] 1. Write the failing test `services/fleet-api/tests/test_schema_routing.py`:

```python
"""A row written under company A's schema is physically absent from company B's
different schema; the scoped Db binds the right schema per caller."""
from pathlib import Path
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from shepherd_db.models import Company, CompanySettings
from tests.conftest import company_headers

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def _company_in_schema(engine, name: str, schema: str) -> str:
    provision_company(engine, schema)
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name=schema))
        s.commit()
        return str(c.company_id)


def test_physical_isolation_across_distinct_schemas(client, pg_engine):
    a = _company_in_schema(pg_engine, "phys-A", "co_phys_a")
    b = _company_in_schema(pg_engine, "phys-B", "co_phys_b")
    plate = f"PHY-{uuid.uuid4().hex[:6]}"

    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=company_headers(a))
    assert r.status_code == 201, r.text

    # Present in A's schema, physically absent from B's schema (raw, schema-qualified).
    with pg_engine.connect() as conn:
        in_a = conn.execute(
            text('SELECT count(*) FROM co_phys_a.vehicles WHERE licensing_plate = :p'),
            {"p": plate},
        ).scalar()
        in_b = conn.execute(
            text('SELECT count(*) FROM co_phys_b.vehicles WHERE licensing_plate = :p'),
            {"p": plate},
        ).scalar()
    assert in_a == 1
    assert in_b == 0

    # B's caller (bound to co_phys_b) cannot see it either.
    assert plate not in [v["licensing_plate"] for v in client.get("/vehicles", headers=company_headers(b)).json()]
```

- [ ] 2. Run, expect FAIL:
  `cd services/fleet-api && poetry run pytest tests/test_schema_routing.py -q`
  Expected: `assert in_a == 1` fails (today the row lands in public, not `co_phys_a`).

- [ ] 3. Minimal impl `services/fleet-api/app/deps.py`. Replace the engine/session block:

```python
"""FastAPI dependencies: schema-scoped DB session, internal token guard, caller context."""
import json
from typing import Annotated, Generator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from shepherd_config import get_config
from shepherd_contracts.auth import CallerContext
from shepherd_db.models import CompanySettings

_engine: Engine | None = None
# company_id -> schema_name. Schema names are stable data; cache for the process lifetime.
_schema_cache: dict[str, str] = {}


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_config().database.url)
    return _engine


def _resolve_schema(engine: Engine, company_id: str | None) -> str:
    """Look up the company's schema_name (never derived). Shared schema when company-less."""
    shared = get_config().database.shared_schema
    if company_id is None:
        return shared
    if company_id in _schema_cache:
        return _schema_cache[company_id]
    with engine.connect() as conn:
        name = conn.execute(
            select(CompanySettings.schema_name).where(
                CompanySettings.company_id == company_id
            )
        ).scalar_one_or_none()
    schema = name or shared
    _schema_cache[company_id] = schema
    return schema


def verify_internal_token(
    x_internal_token: Annotated[str | None, Header(alias="X-Internal-Token")] = None,
) -> None:
    import os
    expected = os.environ.get("INTERNAL_SERVICE_TOKEN", "")
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


def get_caller(
    _: Annotated[None, Depends(verify_internal_token)],
    x_caller_context: Annotated[str, Header(alias="X-Caller-Context")],
) -> CallerContext:
    try:
        return CallerContext.model_validate(json.loads(x_caller_context))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid caller context")


def get_caller_optional(
    x_caller_context: Annotated[str | None, Header(alias="X-Caller-Context")] = None,
) -> CallerContext | None:
    """Caller context when present (whoami / bot-enroll send none)."""
    if x_caller_context is None:
        return None
    try:
        return CallerContext.model_validate(json.loads(x_caller_context))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid caller context")


def get_db(
    engine: Engine = Depends(get_engine),
    caller: CallerContext | None = Depends(get_caller_optional),
) -> Generator[Session, None, None]:
    company_id = caller.company_id if caller else None
    shared = get_config().database.shared_schema
    schema = _resolve_schema(engine, company_id)
    # Fresh connection per request; schema_translate_map is a per-statement compile option,
    # so it cannot leak into another request's pooled connection.
    with engine.connect() as conn:
        conn = conn.execution_options(
            schema_translate_map={"tenant": schema, None: shared}
        )
        with Session(bind=conn) as session:
            yield session


Db = Annotated[Session, Depends(get_db)]
Caller = Annotated[CallerContext, Depends(get_caller)]
```

  Note: `get_caller` (the strict variant used by routers that declare `caller: Caller`) is
  unchanged, so existing behaviour for those routers is preserved. Only the session binding moved.

- [ ] 4. Run, expect PASS:
  `cd services/fleet-api && poetry run pytest tests/test_schema_routing.py -q`

- [ ] 5. Run the full fleet-api suite to confirm no regression (existing companies have no
  `schema_name`, so they resolve to the shared schema = public and behave exactly as before):
  `cd services/fleet-api && poetry run pytest -q`

- [ ] 6. Commit:

```
git add services/fleet-api/app/deps.py services/fleet-api/tests/test_schema_routing.py
git commit -m "bind the request session to the caller's tenant schema

get_db now looks up the caller's schema_name from company_settings (cached,
never derived) and binds the Session on a connection carrying
schema_translate_map={tenant: <schema>, None: shared}. Company-less callers
bind the shared schema. Because every router already depends on Db, this routes
all domain reads/writes per company with no router changes; the translate map is
a per-statement option so it cannot leak across pooled requests."
```

---

### Task 5 - Company-less enrollment scans every registered schema for the driver match

**Files:** `services/fleet-api/app/repo.py`, `services/fleet-api/tests/test_enroll_cross_schema.py` (new).

**Interfaces:**
- Consumes: `get_config()`, `provision_company`, `get_engine`.
- Produces: `find_enrollment_by_phone(session, phone)` resolves an active driver by phone across
  *all* registered schemas (the bounded cross-schema exception for a company-less read);
  `bot_authorizations` is public so its scan is unchanged.

Steps:

- [ ] 1. Write the failing test `services/fleet-api/tests/test_enroll_cross_schema.py`:

```python
"""bot-enroll runs company-less but must find a driver that lives in a dedicated
(non-public) schema, by scanning every registered schema."""
from pathlib import Path
import sys
import uuid

from sqlalchemy.orm import Session

from shepherd_db.models import Company, CompanySettings, Driver
from tests.conftest import TEST_TOKEN

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def _driver_in_schema(engine, schema: str, phone: str) -> str:
    provision_company(engine, schema)
    with Session(engine) as s:
        c = Company(name=f"enr-{schema}")
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name=schema))
        s.commit()
        cid = c.company_id
    # Insert the driver under the dedicated schema.
    with engine.connect() as conn:
        tconn = conn.execution_options(schema_translate_map={"tenant": schema, None: "public"})
        with Session(bind=tconn) as s:
            s.add(Driver(company_id=cid, full_name="Enrolled", phone_number=phone, status="active"))
            s.commit()
    return str(cid)


def test_enroll_finds_driver_in_dedicated_schema(raw_client, pg_engine):
    phone = f"+97251{uuid.uuid4().int % 10**7:07d}"
    _driver_in_schema(pg_engine, "co_enroll", phone)
    r = raw_client.post(
        "/bot-enroll",
        json={"telegram_chat_id": uuid.uuid4().int % 10**9, "phone_number": phone},
        headers={"X-Internal-Token": TEST_TOKEN},
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "driver"
```

- [ ] 2. Run, expect FAIL:
  `cd services/fleet-api && poetry run pytest tests/test_enroll_cross_schema.py -q`
  Expected: `assert r.status_code == 200` fails with 404 (the company-less session binds public, so
  the driver in `co_enroll` is never scanned).

- [ ] 3. Minimal impl in `services/fleet-api/app/repo.py`. Add a schema-iteration helper and route
  the driver scan through it. Above `find_enrollment_by_phone`, add:

```python
def _registered_schemas(session: Session) -> list[str]:
    """Distinct schema_names from company_settings, plus the shared schema."""
    from shepherd_config import get_config

    rows = session.execute(
        select(CompanySettings.schema_name).distinct()
    ).scalars().all()
    schemas = {s for s in rows if s}
    schemas.add(get_config().database.shared_schema)
    return sorted(schemas)
```

  Replace the driver loop inside `find_enrollment_by_phone` (keep the `bot_authorizations` scan
  exactly as-is - it is a public table read on the request session):

```python
def find_enrollment_by_phone(session: Session, phone: str):
    """(role, driver_id, expires_at, company_id) for a phone, or None.

    An active driver wins (permanent driver role); otherwise a non-expired
    bot_authorization. Drivers live in per-company schemas, so the driver match scans
    every registered schema (the bounded cross-schema exception for this company-less read);
    bot_authorizations is public and scanned once on the request session.
    """
    from datetime import datetime, timezone

    from shepherd_config import get_config
    from app.deps import get_engine

    target = _normalize_phone(phone)
    engine = get_engine()
    shared = get_config().database.shared_schema
    for schema in _registered_schemas(session):
        with engine.connect() as conn:
            conn = conn.execution_options(
                schema_translate_map={"tenant": schema, None: shared}
            )
            for d in conn.execute(
                select(Driver).where(Driver.status == "active")
            ).scalars():
                if _normalize_phone(d.phone_number) == target:
                    return ("driver", d.driver_id, None, d.company_id)
    now = datetime.now(timezone.utc)
    for a in session.execute(
        select(BotAuthorization).where(
            (BotAuthorization.expires_at.is_(None)) | (BotAuthorization.expires_at > now)
        )
    ).scalars():
        if _normalize_phone(a.phone_number) == target:
            role = a.role.value if hasattr(a.role, "value") else a.role
            return (role, a.driver_id, a.expires_at, a.company_id)
    return None
```

  `# ponytail:` O(schemas x drivers) phone scan - fleets are small and schemas few; a normalized
  phone index per schema is the ceiling if a deployment ever grows large.

- [ ] 4. Run, expect PASS:
  `cd services/fleet-api && poetry run pytest tests/test_enroll_cross_schema.py -q`

- [ ] 5. Run the full fleet-api suite (the default-schema enrollment path still works because
  public is always in `_registered_schemas`):
  `cd services/fleet-api && poetry run pytest -q`

- [ ] 6. Commit:

```
git add services/fleet-api/app/repo.py services/fleet-api/tests/test_enroll_cross_schema.py
git commit -m "scan every schema for the enrollment driver match

bot-enroll runs company-less, so find_enrollment_by_phone now iterates the
registered schemas (the bounded cross-schema exception) to match an active
driver by phone, even when that driver lives in a dedicated schema. The
bot_authorizations scan stays a single public read on the request session."
```

---

### Task 6 - Extend `test_tenancy.py`: shared-schema isolation + provisioning no-op

**Files:** `services/fleet-api/tests/test_tenancy.py`.

**Interfaces:**
- Consumes: `provision_company`; `company_headers`.
- Produces: tests proving two companies that SHARE a schema still isolate by `company_id`, and
  that provisioning the second sharer does not duplicate tables.

Steps:

- [ ] 1. Append the failing tests to `services/fleet-api/tests/test_tenancy.py`. Add at the top
  (after the existing imports):

```python
import sys
from pathlib import Path

from shepherd_db.models import CompanySettings

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import TENANT_TABLES, provision_company  # noqa: E402


def _company_sharing_schema(engine, name: str, schema: str) -> str:
    provision_company(engine, schema)  # idempotent: 2nd sharer is a no-op
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name=schema))
        s.commit()
        return str(c.company_id)
```

  Then add the test functions:

```python
# --- S7: two companies SHARING a schema still isolate by company_id ---

def test_shared_schema_subcompanies_isolate_by_company_id(client, pg_engine):
    a = _company_sharing_schema(pg_engine, "share-A", "co_shared_pair")
    b = _company_sharing_schema(pg_engine, "share-B", "co_shared_pair")  # same schema
    pa = f"SHA-{uuid.uuid4().hex[:6]}"
    pb = f"SHB-{uuid.uuid4().hex[:6]}"
    _make_vehicle(client, a, pa)
    _make_vehicle(client, b, pb)

    # Physically colocated (both rows live in co_shared_pair) ...
    with pg_engine.connect() as conn:
        from sqlalchemy import text
        total = conn.execute(
            text('SELECT count(*) FROM co_shared_pair.vehicles WHERE licensing_plate IN (:a, :b)'),
            {"a": pa, "b": pb},
        ).scalar()
    assert total == 2

    # ... but A's caller sees only A's row (company_id row scoping).
    plates_a = [v["licensing_plate"] for v in client.get("/vehicles", headers=company_headers(a)).json()]
    assert pa in plates_a and pb not in plates_a
    plates_b = [v["licensing_plate"] for v in client.get("/vehicles", headers=company_headers(b)).json()]
    assert pb in plates_b and pa not in plates_b


# --- S8: by-PK read across shared-schema subcompanies still 404s ---

def test_shared_schema_by_pk_read_leak_returns_404(client, pg_engine):
    a = _company_sharing_schema(pg_engine, "share-A2", "co_shared_pk")
    b = _company_sharing_schema(pg_engine, "share-B2", "co_shared_pk")
    plate_b = f"SPK-{uuid.uuid4().hex[:6]}"
    _make_vehicle(client, b, plate_b)
    # Same schema, but A must not read B's row.
    assert client.get(f"/vehicles/{plate_b}", headers=company_headers(a)).status_code == 404


# --- S9: provisioning the second sharer does not duplicate tables ---

def test_provisioning_shared_schema_is_idempotent(pg_engine):
    from sqlalchemy import inspect
    provision_company(pg_engine, "co_idem")
    before = inspect(pg_engine).get_table_names(schema="co_idem")
    provision_company(pg_engine, "co_idem")  # must not raise / duplicate
    after = inspect(pg_engine).get_table_names(schema="co_idem")
    assert sorted(before) == sorted(after)
    assert {t.name for t in TENANT_TABLES} <= set(after)
```

- [ ] 2. Run, expect FAIL (before this task's helper/imports exist the new tests cannot resolve
  `provision_company` / `CompanySettings.schema_name`):
  `cd services/fleet-api && poetry run pytest tests/test_tenancy.py -k "shared or idempotent" -q`
  Expected first failure surfaces while the imports/helpers are absent (ImportError) or, once
  added, the shared-schema assertions confirm behaviour. If the assertions fail it means routing or
  row-scoping regressed.

- [ ] 3. Minimal impl: there is no production code change in this task - the shared-schema
  behaviour is delivered by Tasks 1-4. This task only adds the tests above. If
  `test_shared_schema_subcompanies_isolate_by_company_id` fails on the `count(*) == 2`
  colocation assertion, confirm both companies' `company_settings.schema_name` equals
  `co_shared_pair` and that `_resolve_schema` is reading it; if it fails on the per-caller plate
  assertions, the row-level `WHERE company_id` scoping regressed (it must not have).

- [ ] 4. Run, expect PASS:
  `cd services/fleet-api && poetry run pytest tests/test_tenancy.py -q`

- [ ] 5. Commit:

```
git add services/fleet-api/tests/test_tenancy.py
git commit -m "prove shared-schema subcompanies isolate by company_id

Extend the tenancy suite: two companies pointing at one schema are physically
colocated yet each caller sees only its own rows, by-PK reads across the pair
still 404, and provisioning the second sharer is idempotent. These lock in that
company_id row scoping is load-bearing once a schema is shared."
```

---

### Task 7 - Rewrite `refresh_kpi_daily` to loop per company schema

**Files:** `db/bootstrap.sql`, `services/fleet-api/tests/test_kpi_per_schema.py` (new).

**Interfaces:**
- Produces: `refresh_kpi_daily()` computes per-company KPIs by reading each company's tenant tables
  from its `company_settings.schema_name` via dynamic SQL, writing to `public.kpi_daily`.
  `cleanup_expired_bot_access()` is unchanged (it operates on `users` + `bot_authorizations`, both
  public).

Steps:

- [ ] 1. Write the failing test `services/fleet-api/tests/test_kpi_per_schema.py`:

```python
"""refresh_kpi_daily reads tenant tables from each company's schema and writes a public
kpi_daily snapshot, so a company in a dedicated schema gets counted."""
from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.orm import Session

from shepherd_db.models import Company, CompanySettings, Driver

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def test_kpi_counts_a_company_in_a_dedicated_schema(pg_engine):
    provision_company(pg_engine, "co_kpi")
    with Session(pg_engine) as s:
        c = Company(name="kpi-co")
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name="co_kpi"))
        s.commit()
        cid = c.company_id
    with pg_engine.connect() as conn:
        tconn = conn.execution_options(schema_translate_map={"tenant": "co_kpi", None: "public"})
        with Session(bind=tconn) as s:
            s.add(Driver(company_id=cid, full_name="D", phone_number="+972500000123", status="active"))
            s.commit()

    with pg_engine.begin() as conn:
        conn.exec_driver_sql("SELECT refresh_kpi_daily()")
        row = conn.execute(
            text("SELECT 1 FROM kpi_daily WHERE company_id = :c"), {"c": cid}
        ).first()
    assert row is not None  # the dedicated-schema company produced a snapshot row
```

- [ ] 2. Run, expect FAIL:
  `cd services/fleet-api && poetry run pytest tests/test_kpi_per_schema.py -q`
  Expected: `assert row is not None` fails - the current `refresh_kpi_daily` reads `vehicles` /
  `drivers` only from public, so `co_kpi`'s company gets no row (or errors on missing public rows).

- [ ] 3. Minimal impl: replace the `refresh_kpi_daily()` function body in `db/bootstrap.sql` with a
  per-company loop that runs the existing per-company computation against each company's schema via
  dynamic SQL. Keep `cleanup_expired_bot_access()` and the `DO $do$` pg_cron block unchanged.

```sql
-- Daily KPI rollup, per company. Tenant tables live in per-company schemas
-- (company_settings.schema_name); read each company's schema with dynamic SQL and
-- write the snapshot into public.kpi_daily. company_id row-scoping keeps shared-schema
-- subcompanies apart.
CREATE OR REPLACE FUNCTION refresh_kpi_daily() RETURNS void AS $fn$
DECLARE
  v_window_start timestamptz := (current_date - interval '7 days');
  c record;
  v_schema text;
BEGIN
  FOR c IN SELECT company_id FROM companies LOOP
    SELECT COALESCE(s.schema_name, 'public') INTO v_schema
      FROM company_settings s WHERE s.company_id = c.company_id;
    IF v_schema IS NULL THEN
      v_schema := 'public';
    END IF;

    EXECUTE format($q$
      INSERT INTO kpi_daily (
        snapshot_date, company_id, total_km_7d, avg_km_per_driver_7d,
        avg_days_between_maintenance, maintenance_due_count, docs_expiring_count,
        top_customer_id, top_customer_km, top_customer_vehicle_count, computed_ts
      )
      WITH cfg AS (
        SELECT
          COALESCE((SELECT (config_value #>> '{}')::int FROM system_config s
                    WHERE s.company_id = %1$L AND s.config_key = 'license_expiring_days'), 30) AS license_days,
          COALESCE((SELECT (config_value #>> '{}')::int FROM system_config s
                    WHERE s.company_id = %1$L AND s.config_key = 'insurance_expiring_days'), 30) AS insurance_days
      ),
      vkm AS (
        SELECT v.vehicle_id, v.customer_id,
          GREATEST(
            COALESCE((SELECT max(k.km) FROM %2$I.km_updates k
                      WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts >= %3$L), 0)
            - COALESCE(
                (SELECT k.km FROM %2$I.km_updates k
                 WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts < %3$L
                 ORDER BY k.recorded_ts DESC LIMIT 1),
                (SELECT max(k.km) FROM %2$I.km_updates k
                 WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts >= %3$L),
                0),
            0) AS km_7d
        FROM %2$I.vehicles v WHERE v.company_id = %1$L
      ),
      totals AS (SELECT COALESCE(SUM(km_7d), 0)::int AS total_km FROM vkm),
      drv AS (SELECT COUNT(*)::int AS n FROM %2$I.drivers WHERE company_id = %1$L),
      gaps AS (
        SELECT AVG(gap) AS avg_gap FROM (
          SELECT (service_date - LAG(service_date)
                  OVER (PARTITION BY vehicle_id ORDER BY service_date)) AS gap
          FROM %2$I.vehicle_care WHERE company_id = %1$L
        ) g WHERE gap IS NOT NULL
      ),
      maint AS (
        SELECT COUNT(*)::int AS n FROM %2$I.vehicles
        WHERE company_id = %1$L AND current_km IS NOT NULL AND next_maintenance_km IS NOT NULL
          AND current_km >= next_maintenance_km
      ),
      docs AS (
        SELECT COUNT(*)::int AS n FROM %2$I.vehicles v, cfg
        WHERE v.company_id = %1$L
          AND ((v.insurance_valid_to IS NOT NULL AND v.insurance_valid_to <= current_date + cfg.insurance_days)
            OR (v.license_valid_to IS NOT NULL AND v.license_valid_to <= current_date + cfg.license_days))
      ),
      topc AS (
        SELECT customer_id, SUM(km_7d)::int AS km FROM vkm WHERE customer_id IS NOT NULL
        GROUP BY customer_id ORDER BY SUM(km_7d) DESC NULLS LAST LIMIT 1
      )
      SELECT current_date, %1$L,
             COALESCE(totals.total_km, 0),
             COALESCE(totals.total_km, 0)::numeric / NULLIF(drv.n, 0),
             gaps.avg_gap,
             COALESCE(maint.n, 0),
             COALESCE(docs.n, 0),
             topc.customer_id, topc.km,
             (SELECT COUNT(*)::int FROM %2$I.vehicles vv
              WHERE vv.customer_id = topc.customer_id AND vv.company_id = %1$L),
             now()
      FROM totals, drv, gaps, maint, docs
      LEFT JOIN topc ON true
      ON CONFLICT (snapshot_date, company_id) DO UPDATE SET
        total_km_7d = EXCLUDED.total_km_7d,
        avg_km_per_driver_7d = EXCLUDED.avg_km_per_driver_7d,
        avg_days_between_maintenance = EXCLUDED.avg_days_between_maintenance,
        maintenance_due_count = EXCLUDED.maintenance_due_count,
        docs_expiring_count = EXCLUDED.docs_expiring_count,
        top_customer_id = EXCLUDED.top_customer_id,
        top_customer_km = EXCLUDED.top_customer_km,
        top_customer_vehicle_count = EXCLUDED.top_customer_vehicle_count,
        computed_ts = EXCLUDED.computed_ts;
    $q$, c.company_id, v_schema, v_window_start);
  END LOOP;
END;
$fn$ LANGUAGE plpgsql;
```

  `# ponytail:` one company at a time with `format()`/`EXECUTE` (`%I` quotes the schema identifier,
  `%L` literalises the company id and window). Schemas shared by sibling companies are visited once
  per company and kept apart by `WHERE company_id`, so the snapshot stays per-company-correct.

- [ ] 4. Run, expect PASS:
  `cd services/fleet-api && poetry run pytest tests/test_kpi_per_schema.py -q`

- [ ] 5. Run the existing KPI test + conftest backfill to confirm the default (public-schema)
  company still produces a snapshot:
  `cd services/fleet-api && poetry run pytest tests/ -k "kpi" -q`

- [ ] 6. Commit:

```
git add db/bootstrap.sql services/fleet-api/tests/test_kpi_per_schema.py
git commit -m "compute kpi_daily per company schema

Rewrite refresh_kpi_daily to loop companies, read each one's tenant tables from
its company_settings.schema_name via dynamic SQL (quoted %I schema, %L company),
and upsert into public.kpi_daily. cleanup_expired_bot_access is untouched - it
sweeps the public users/bot_authorizations tables."
```

---

### Task 8 - Conftest: keep `apply_schema` green and add a schema-provisioning test helper

**Files:** `services/fleet-api/tests/conftest.py`.

**Interfaces:**
- Consumes: `build`, `provision_company`.
- Produces: `apply_schema` builds public + (config) schemas; a reusable
  `make_company_in_schema(engine, name, schema)` helper for routing tests; the Default Company's
  `company_settings.schema_name` is set so its seeded/derived rows resolve consistently.

Steps:

- [x] 1. Write a failing guard test inline in conftest by asserting the helper exists - add
  `services/fleet-api/tests/test_conftest_helper.py`:

```python
"""The conftest exposes a helper that provisions a company in a given schema and
returns its id, used by the routing/tenancy tests."""
import uuid

from sqlalchemy import inspect

from tests.conftest import make_company_in_schema


def test_make_company_in_schema_provisions_and_links(pg_engine):
    schema = f"co_h_{uuid.uuid4().hex[:6]}"
    cid = make_company_in_schema(pg_engine, "helper-co", schema)
    assert schema in inspect(pg_engine).get_schema_names()
    from sqlalchemy import text
    with pg_engine.connect() as conn:
        got = conn.execute(
            text("SELECT schema_name FROM company_settings WHERE company_id = :c"),
            {"c": cid},
        ).scalar()
    assert got == schema
```

- [x] 2. Run, expect FAIL:
  `cd services/fleet-api && poetry run pytest tests/test_conftest_helper.py -q`
  Expected: `ImportError: cannot import name 'make_company_in_schema'`.

- [x] 3. Minimal impl in `services/fleet-api/tests/conftest.py`. Add the db dir to `sys.path` at
  import time and add the helper. Near the top (after existing imports) add:

```python
import sys

_DB_DIR = Path(__file__).parents[3] / "db"
sys.path.insert(0, str(_DB_DIR))
from provisioning import provision_company  # noqa: E402
```

  Update `apply_schema` so the Default Company gets a `company_settings` row carrying its schema
  (shared/public by default in tests, so existing behaviour is unchanged), replacing the bare
  company insert block:

```python
    with pg_engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO companies (company_id, name) VALUES (%(id)s, 'Default Company') "
            "ON CONFLICT (company_id) DO NOTHING",
            {"id": DEFAULT_COMPANY_ID},
        )
        conn.exec_driver_sql(
            "INSERT INTO company_settings (company_id, schema_name) "
            "VALUES (%(id)s, 'public') ON CONFLICT (company_id) DO NOTHING",
            {"id": DEFAULT_COMPANY_ID},
        )
```

  Add the helper at module scope:

```python
def make_company_in_schema(engine, name: str, schema: str) -> str:
    """Provision <schema>, insert a company linked to it, return the company id."""
    from sqlalchemy.orm import Session
    from shepherd_db.models import Company, CompanySettings

    provision_company(engine, schema)
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name=schema))
        s.commit()
        return str(c.company_id)
```

  Note: `apply_schema` calls `build(pg_engine)`, which (Task 3) now needs `get_config()`. The test
  environment must provide a config whose `database.shared_schema` is `"public"` and whose
  `companies` either is empty or lists only public-schema entries, so `build` provisions nothing
  extra in the bare test container. If plan 01's `get_config()` reads `SHEPHERD_CONFIG`, point it at
  a minimal test `config.toml` via an autouse env fixture, or rely on plan 01's default. Confirm
  `build(pg_engine)` succeeds before the rest of the suite runs.

- [x] 4. Run, expect PASS:
  `cd services/fleet-api && poetry run pytest tests/test_conftest_helper.py -q`

- [x] 5. Run the FULL fleet-api suite to confirm nothing regressed end-to-end:
  `cd services/fleet-api && poetry run pytest -q`

- [ ] 6. Optionally refactor `test_schema_routing.py`, `test_enroll_cross_schema.py`,
  `test_tenancy.py` to use `make_company_in_schema` instead of their local copies (pure cleanup;
  keep if it reduces duplication, skip if it risks churn).

- [x] 7. Commit:

```
git add services/fleet-api/tests/conftest.py services/fleet-api/tests/test_conftest_helper.py
git commit -m "give the test suite a schema-provisioning helper

Put db/ on sys.path at conftest import, set the Default Company's
company_settings.schema_name to public so its rows resolve consistently, and add
make_company_in_schema for the routing and tenancy tests to provision a company
in a dedicated schema."
```

---

## Doc-sync (per CLAUDE.md, do in the relevant task commit)

- `db/README.md` / root `README.md`: note that `build()` provisions per-company schemas and that
  domain tables live in tenant schemas (Task 3 commit).
- `.env.example` / `config.example.toml`: no new vars in this plan (the DB url + schema map come
  from plan 01); confirm "no doc impact" at each commit.
- This plan file: tick the checkboxes as tasks complete.
- `plans/` tenancy references: update any doc that claimed tenancy is row-level-only to note the
  schema-per-tenant routing now sits above row scoping (Task 4 commit).
</content>
</invoke>
