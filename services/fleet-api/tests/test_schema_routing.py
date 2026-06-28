"""A row written under company A's schema is physically absent from company B's
different schema; the scoped Db binds the right schema per caller."""
from pathlib import Path
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from shepherd_db.models import Company, CompanySettings
from tests.conftest import company_headers

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def _company_in_schema(engine, name: str, schema: str) -> str:
    provision_company(engine, schema)
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name=schema))
        s.commit()
        return str(c.company_id)


def test_physical_isolation_across_distinct_schemas(client, pg_engine):
    a = _company_in_schema(pg_engine, "phys-A", "co_phys_a")
    b = _company_in_schema(pg_engine, "phys-B", "co_phys_b")
    plate = f"PHY-{uuid.uuid4().hex[:6]}"

    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=company_headers(a))
    assert r.status_code == 201, r.text

    # Present in A's schema, physically absent from B's schema (raw, schema-qualified).
    with pg_engine.connect() as conn:
        in_a = conn.execute(
            text('SELECT count(*) FROM co_phys_a.vehicles WHERE licensing_plate = :p'),
            {"p": plate},
        ).scalar()
        in_b = conn.execute(
            text('SELECT count(*) FROM co_phys_b.vehicles WHERE licensing_plate = :p'),
            {"p": plate},
        ).scalar()
    assert in_a == 1
    assert in_b == 0

    # B's caller (bound to co_phys_b) cannot see it either.
    assert plate not in [v["licensing_plate"] for v in client.get("/vehicles", headers=company_headers(b)).json()]
