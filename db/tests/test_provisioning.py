"""provision_company creates the schema + the 11 tenant tables, idempotently, and a
second company sharing the same schema_name is a no-op (no error, no duplicate types)."""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
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
