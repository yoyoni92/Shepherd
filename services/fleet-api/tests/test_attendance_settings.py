"""F7 - company-scoped attendance window settings (managed by the company admin)."""
from sqlalchemy.orm import Session

from shepherd_db.models import Company
from tests.conftest import company_admin_headers, superadmin_headers


def _company(engine, name: str) -> str:
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.commit()
        return str(c.company_id)


def test_attendance_settings_roundtrip_and_isolation(client, pg_engine):
    a = _company(pg_engine, "att-A")
    b = _company(pg_engine, "att-B")

    put = client.put(
        "/attendance/settings",
        json={"enabled": True, "start": "06:00", "end": "18:00"},
        headers=company_admin_headers(a),
    )
    assert put.status_code == 200, put.text

    got = client.get("/attendance/settings", headers=company_admin_headers(a)).json()
    assert got == {"enabled": True, "start": "06:00", "end": "18:00"}

    # Company B does not see A's window (its own defaults).
    other = client.get("/attendance/settings", headers=company_admin_headers(b)).json()
    assert other["enabled"] is False

    # A system admin with no active company must select one first.
    assert client.get("/attendance/settings", headers=superadmin_headers()).status_code == 400
