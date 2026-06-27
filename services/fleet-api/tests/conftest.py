import os
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


@pytest.fixture(scope="session")
def pg_engine():
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        url = pg.get_connection_url()
        engine = create_engine(url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def apply_schema(pg_engine):
    # Schema is built from the models (migrations were removed); bootstrap.sql's
    # pg_cron scheduling is guarded, so it's a no-op on this plain test container.
    import sys

    db_dir = Path(__file__).parents[3] / "db"
    sys.path.insert(0, str(db_dir))
    from create_schema import build

    build(pg_engine)
    # Insert the Default Company first (idempotent) so tenant FKs resolve and
    # refresh_kpi_daily (now per-company) produces at least one snapshot row.
    with pg_engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO companies (company_id, name) VALUES (%(id)s, 'Default Company') "
            "ON CONFLICT (company_id) DO NOTHING",
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
