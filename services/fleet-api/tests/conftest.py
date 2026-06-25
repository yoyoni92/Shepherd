import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

from shepherd_contracts.auth import CallerContext, Role

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
TEST_TOKEN = "test-internal-token"


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
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(role=Role.admin).model_dump_json(),
    }


def driver_headers(driver_id: str) -> dict:
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(role=Role.driver, driver_id=driver_id).model_dump_json(),
    }


def customer_headers(customer_id: str) -> dict:
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(role=Role.customer, customer_id=customer_id).model_dump_json(),
    }
