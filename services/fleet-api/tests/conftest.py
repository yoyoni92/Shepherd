import atexit
import os
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from shepherd_contracts.auth import CallerContext, Role

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
os.environ.setdefault("AUTH_JWT_SECRET", "test-jwt-secret")
TEST_TOKEN = "test-internal-token"
# Fixed Default Company id - seed.py uses the same value so tests + seed are deterministic.
DEFAULT_COMPANY_ID = "00000000-0000-0000-0000-0000000000c0"

# --- Schema-per-tenant test bootstrap ---
# build() provisions tenant tables per schema from config.  We map the sole
# test company to schema "public" so all 11 tenant tables land in public and
# the existing flat-schema tests continue to work unchanged.
_TEST_CONFIG = """\
[database]
url = "postgresql+psycopg://test:test@localhost:5432/test"
shared_schema = "public"
[services]
fleet_api_url = "http://fleet-api:8000"
[[company]]
slug = "default"
schema = "public"
"""
_fd, _CONF_PATH = tempfile.mkstemp(suffix=".toml", prefix="shepherd_test_")
with os.fdopen(_fd, "w") as _fh:
    _fh.write(_TEST_CONFIG)
atexit.register(lambda: os.path.exists(_CONF_PATH) and os.unlink(_CONF_PATH))
os.environ["SHEPHERD_CONFIG"] = _CONF_PATH

import shepherd_config as _sc  # noqa: E402
_sc.get_config.cache_clear()

_DB_DIR = Path(__file__).parents[3] / "db"
sys.path.insert(0, str(_DB_DIR))
from provisioning import provision_company  # noqa: E402
# --- end bootstrap ---


@pytest.fixture(scope="session")
def pg_engine():
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        url = pg.get_connection_url()
        _base = create_engine(url)
        # Translate "tenant" -> "public" so ORM queries resolve against the
        # tenant tables provisioned into public by build() in apply_schema.
        # Include None: "public" so the key set is consistent with the
        # per-request schema_translate_map set by get_db; SA caches compiled
        # SQL by bool(schema_translate_map) not by the key set, so all users
        # of this engine must carry the same keys to avoid __[SCHEMA__none]
        # token mismatches when statements are served from cache.
        engine = _base.execution_options(
            schema_translate_map={"tenant": "public", None: "public"}
        )
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        _base.dispose()


@pytest.fixture(scope="session", autouse=True)
def apply_schema(pg_engine):
    # Schema is built from the models (migrations were removed); bootstrap.sql's
    # pg_cron scheduling is guarded, so it's a no-op on this plain test container.
    from create_schema import build

    build(pg_engine)
    # Insert the Default Company and its schema_name so tenant FKs resolve and
    # refresh_kpi_daily (now per-company) produces at least one snapshot row.
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
    # The KPI endpoint reads the latest snapshot without seeding one; backfill a row
    # (the old 0003 migration did this at upgrade time).
    with pg_engine.begin() as conn:
        conn.exec_driver_sql("SELECT refresh_kpi_daily()")


@pytest.fixture
def client(pg_engine):
    """Authenticated test client - DB injected, internal token check skipped."""
    from app.main import app
    from app.deps import get_engine, verify_internal_token

    os.environ["INTERNAL_SERVICE_TOKEN"] = TEST_TOKEN
    app.dependency_overrides[get_engine] = lambda: pg_engine
    app.dependency_overrides[verify_internal_token] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def raw_client(pg_engine):
    """Test client with real token enforcement - used for T10."""
    from app.main import app
    from app.deps import get_engine

    os.environ["INTERNAL_SERVICE_TOKEN"] = TEST_TOKEN
    app.dependency_overrides[get_engine] = lambda: pg_engine
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def admin_headers() -> dict:
    # Admin acting within the Default Company - existing create tests write into it.
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(
            role=Role.admin, company_id=DEFAULT_COMPANY_ID
        ).model_dump_json(),
    }


def superadmin_headers() -> dict:
    # Admin with no company - cross-company read-all (system superadmin).
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(role=Role.admin).model_dump_json(),
    }


def driver_headers(driver_id: str) -> dict:
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(
            role=Role.driver, driver_id=driver_id, company_id=DEFAULT_COMPANY_ID
        ).model_dump_json(),
    }


def customer_headers(customer_id: str) -> dict:
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(
            role=Role.customer, customer_id=customer_id, company_id=DEFAULT_COMPANY_ID
        ).model_dump_json(),
    }


def company_headers(company_id: str) -> dict:
    # admin acting within one company (Feature 2 adds the company_admin role; same scoping).
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(role=Role.admin, company_id=company_id).model_dump_json(),
    }


def company_admin_headers(company_id: str) -> dict:
    # A real company_admin caller - always bound to its own company.
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(
            role=Role.company_admin, company_id=company_id
        ).model_dump_json(),
    }


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
