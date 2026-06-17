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
    from alembic import command
    from alembic.config import Config

    ini_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
    cfg = Config(os.path.abspath(ini_path))
    url = pg_engine.url.render_as_string(hide_password=False)
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


@pytest.fixture
def conn(pg_engine):
    with pg_engine.connect() as connection:
        connection.begin()
        yield connection
        connection.rollback()
