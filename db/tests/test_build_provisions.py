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
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="module")
def engine(monkeypatch_module):
    with PostgresContainer("postgres:16", driver="psycopg") as pg:
        eng = create_engine(pg.get_connection_url())
        yield eng
        eng.dispose()


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
