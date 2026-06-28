"""emit_time_maintenance_due reads tenant tables from each company's schema, so a
company in a dedicated schema gets its maintenance_due events emitted."""
import datetime
import sys
from pathlib import Path

from shepherd_db.models import Company, CompanySettings, Vehicle
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def test_time_maintenance_due_in_dedicated_schema(pg_engine):
    provision_company(pg_engine, "co_maint")
    with Session(pg_engine) as s:
        c = Company(name="maint-co")
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name="co_maint"))
        s.commit()
        cid = c.company_id
    with pg_engine.connect() as conn:
        tconn = conn.execution_options(
            schema_translate_map={"tenant": "co_maint", None: "public"}
        )
        with Session(bind=tconn) as s:
            s.add(Vehicle(
                company_id=cid,
                licensing_plate="MAINT-V1",
                next_maintenance_date=datetime.date.today(),
            ))
            s.commit()

    with pg_engine.begin() as conn:
        conn.exec_driver_sql("SELECT emit_time_maintenance_due()")
        row = conn.execute(
            text(
                "SELECT event_type, source_type FROM co_maint.events "
                "WHERE event_type = 'maintenance_due' AND source_type = 'scheduler'"
            )
        ).first()
    assert row is not None, (
        "Expected a maintenance_due event in co_maint.events; "
        "a None result means emit_time_maintenance_due read public.vehicles "
        "instead of the co_maint tenant schema"
    )
    assert row[0] == "maintenance_due"
    assert row[1] == "scheduler"
