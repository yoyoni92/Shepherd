"""bot-enroll runs company-less but must find a driver that lives in a dedicated
(non-public) schema, by scanning every registered schema."""
from pathlib import Path
import sys
import uuid

from sqlalchemy.orm import Session

from shepherd_db.models import Company, CompanySettings, Driver
from tests.conftest import TEST_TOKEN

sys.path.insert(0, str(Path(__file__).parents[3] / "db"))
from provisioning import provision_company  # noqa: E402


def _driver_in_schema(engine, schema: str, phone: str) -> str:
    provision_company(engine, schema)
    with Session(engine) as s:
        c = Company(name=f"enr-{schema}")
        s.add(c)
        s.flush()
        s.add(CompanySettings(company_id=c.company_id, schema_name=schema))
        s.commit()
        cid = c.company_id
    # Insert the driver under the dedicated schema.
    with engine.connect() as conn:
        tconn = conn.execution_options(schema_translate_map={"tenant": schema, None: "public"})
        with Session(bind=tconn) as s:
            s.add(Driver(company_id=cid, full_name="Enrolled", phone_number=phone, status="active"))
            s.commit()
    return str(cid)


def test_enroll_finds_driver_in_dedicated_schema(raw_client, pg_engine):
    phone = f"+97251{uuid.uuid4().int % 10**7:07d}"
    _driver_in_schema(pg_engine, "co_enroll", phone)
    r = raw_client.post(
        "/bot-enroll",
        json={"telegram_chat_id": uuid.uuid4().int % 10**9, "phone_number": phone},
        headers={"X-Internal-Token": TEST_TOKEN},
    )
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "driver"
