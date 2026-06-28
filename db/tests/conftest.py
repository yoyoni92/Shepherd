import atexit
import os
import tempfile

import pytest
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

# Disable Ryuk cleanup container - not needed for local test runs and
# avoids pulling the ryuk image on first run.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

# --- Schema-per-tenant test bootstrap ---
# build() provisions tenant tables into the schemas listed in config.  We map
# the sole test company to schema "public" so all 11 tenant tables land in
# public and the existing flat-schema tests continue to work unchanged.
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
# --- end bootstrap ---


@pytest.fixture(scope="session")
def pg_engine():
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        url = pg.get_connection_url()
        engine = create_engine(url)
        # Verify connection before yielding
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        yield engine
        engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def ensure_schema(pg_engine):
    # Schema is built from the models (no migrations); bootstrap.sql's pg_cron
    # scheduling is guarded, so it's a no-op on this plain test container.
    import sys

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from create_schema import build

    build(pg_engine)


@pytest.fixture
def conn(pg_engine):
    with pg_engine.connect() as connection:
        connection.begin()
        yield connection
        connection.rollback()


@pytest.fixture
def company_id(conn):
    """A tenant to satisfy the NOT NULL company_id on every domain table."""
    from sqlalchemy import text

    return conn.execute(
        text("INSERT INTO companies (name) VALUES ('Test Co') RETURNING company_id")
    ).scalar()
