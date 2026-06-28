"""The conftest exposes a helper that provisions a company in a given schema and
returns its id, used by the routing/tenancy tests."""
import uuid

from sqlalchemy import inspect

from tests.conftest import make_company_in_schema


def test_make_company_in_schema_provisions_and_links(pg_engine):
    schema = f"co_h_{uuid.uuid4().hex[:6]}"
    cid = make_company_in_schema(pg_engine, "helper-co", schema)
    assert schema in inspect(pg_engine).get_schema_names()
    from sqlalchemy import text
    with pg_engine.connect() as conn:
        got = conn.execute(
            text("SELECT schema_name FROM company_settings WHERE company_id = :c"),
            {"c": cid},
        ).scalar()
    assert got == schema
