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
def apply_migrations(pg_engine):
    from alembic import command
    from alembic.config import Config

    db_dir = Path(__file__).parents[3] / "db"
    cfg = Config(str(db_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(db_dir / "migrations"))
    cfg.set_main_option("sqlalchemy.url", pg_engine.url.render_as_string(hide_password=False))
    command.upgrade(cfg, "head")


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
