import os

import pytest
from sqlalchemy import create_engine, text
from testcontainers.postgres import PostgresContainer

# Disable Ryuk cleanup container - not needed for local test runs and
# avoids pulling the ryuk image on first run.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


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
