"""refresh_kpi_daily reads tenant tables from each company's schema and writes a public
kpi_daily snapshot, so a company in a dedicated schema gets counted."""
import datetime
import sys
from pathlib import Path

from shepherd_db.models import Company, CompanySettings, Driver, Vehicle
from sqlalchemy import text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def test_kpi_counts_a_company_in_a_dedicated_schema(pg_engine):
    provision_company(pg_engine, "co_kpi")
    with Session(pg_engine) as s:
        c = Company(name="kpi-co")
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name="co_kpi"))
        s.commit()
        cid = c.company_id
    with pg_engine.connect() as conn:
        tconn = conn.execution_options(schema_translate_map={"tenant": "co_kpi", None: "public"})
        with Session(bind=tconn) as s:
            s.add(Driver(
                company_id=cid, full_name="D", phone_number="+972500000123", status="active"
            ))
            # Vehicle with insurance expiring in 5 days: falls within the default 30-day
            # window, so docs_expiring_count will be >= 1 ONLY if refresh_kpi_daily reads
            # from co_kpi.vehicles (not public.vehicles, which has no such vehicle).
            s.add(Vehicle(
                company_id=cid,
                licensing_plate="KPI-V1",
                insurance_valid_to=datetime.date.today() + datetime.timedelta(days=5),
            ))
            s.commit()

    with pg_engine.begin() as conn:
        conn.exec_driver_sql("SELECT refresh_kpi_daily()")
        row = conn.execute(
            text("SELECT docs_expiring_count FROM kpi_daily WHERE company_id = :c"),
            {"c": cid},
        ).first()
    assert row is not None
    assert row[0] >= 1, (
        "docs_expiring_count should be >= 1 because a vehicle with insurance "
        "expiring in 5 days was inserted into co_kpi.vehicles; a value of 0 "
        "means the function read public.vehicles instead of the tenant schema"
    )
