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
    # Window persisted; working-day rules fall back to their defaults when omitted.
    assert got == {
        "enabled": True,
        "start": "06:00",
        "end": "18:00",
        "work_days": [0, 1, 2, 3, 4],
        "chag_working": False,
        "erev_chag_working": True,
    }

    # Company B does not see A's window (its own defaults).
    other = client.get("/attendance/settings", headers=company_admin_headers(b)).json()
    assert other["enabled"] is False


def test_attendance_working_day_rules_roundtrip(client, pg_engine):
    c = _company(pg_engine, "att-work")

    put = client.put(
        "/attendance/settings",
        json={
            "enabled": False,
            "start": "00:00",
            "end": "23:59",
            "work_days": [0, 1, 2, 3],
            "chag_working": True,
            "erev_chag_working": False,
        },
        headers=company_admin_headers(c),
    )
    assert put.status_code == 200, put.text

    got = client.get("/attendance/settings", headers=company_admin_headers(c)).json()
    assert got["work_days"] == [0, 1, 2, 3]
    assert got["chag_working"] is True
    assert got["erev_chag_working"] is False

    # A system admin with no active company must select one first.
    assert client.get("/attendance/settings", headers=superadmin_headers()).status_code == 400
