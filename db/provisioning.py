"""Provision a Postgres schema with the tenant (domain) tables.

The schema name is data (read from config / company_settings), never derived here.
Provisioning is idempotent: CREATE SCHEMA IF NOT EXISTS + create_all(checkfirst) of just
the tenant tables under a schema_translate_map. A second company that shares a schema_name
re-attaches to the existing schema (no-op)."""
from shepherd_db.models import Base
from sqlalchemy.engine import Connection, Engine

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
