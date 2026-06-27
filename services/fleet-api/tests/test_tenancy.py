"""Feature 1 - tenant (company) scoping. Scope predicate = CallerContext.company_id presence.

These are the security contract: a missed company filter is a cross-tenant data leak.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from shepherd_db.models import Accident, Company, Event, KmUpdate, Vehicle
from tests.conftest import company_headers, superadmin_headers


def _new_company(engine, name: str) -> str:
    """Insert a bare company directly (companies CRUD lands in Feature 2)."""
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.commit()
        return str(c.company_id)


def _make_vehicle(client, company_id: str, plate: str) -> str:
    r = client.post(
        "/vehicles", json={"licensing_plate": plate}, headers=company_headers(company_id)
    )
    assert r.status_code == 201, r.text
    return r.json()["vehicle_id"]


def _seed_two_companies(engine) -> tuple[str, str]:
    """Insert company A + B each with one vehicle, directly."""
    with Session(engine) as s:
        a, b = Company(name="A"), Company(name="B")
        s.add_all([a, b])
        s.flush()
        s.add(Vehicle(licensing_plate=f"AAA-{uuid.uuid4().hex[:6]}", company_id=a.company_id))
        s.add(Vehicle(licensing_plate=f"BBB-{uuid.uuid4().hex[:6]}", company_id=b.company_id))
        s.commit()
        return str(a.company_id), str(b.company_id)


# --- S1: list scoping (tracer) ---

def test_company_scoped_list_sees_only_its_vehicles(client, pg_engine):
    a_id, _b_id = _seed_two_companies(pg_engine)
    res = client.get("/vehicles", headers=company_headers(a_id))
    assert res.status_code == 200
    plates = [v["licensing_plate"] for v in res.json()]
    assert any(p.startswith("AAA-") for p in plates)
    assert not any(p.startswith("BBB-") for p in plates)


# --- S2: by-PK read leak -> 404 ---

def test_by_pk_read_leak_returns_404(client, pg_engine):
    a = _new_company(pg_engine, "A-read")
    b = _new_company(pg_engine, "B-read")
    plate_b = f"BRD-{uuid.uuid4().hex[:6]}"
    _make_vehicle(client, b, plate_b)
    # Company A caller fetching B's plate must not learn it exists.
    res = client.get(f"/vehicles/{plate_b}", headers=company_headers(a))
    assert res.status_code == 404


# --- S3: by-PK write leak -> 404 ---

def test_by_pk_write_leak_returns_404(client, pg_engine):
    a = _new_company(pg_engine, "A-write")
    b = _new_company(pg_engine, "B-write")
    vid_b = _make_vehicle(client, b, f"BWR-{uuid.uuid4().hex[:6]}")
    patch = client.patch(
        f"/vehicles/{vid_b}", json={"current_km": 999}, headers=company_headers(a)
    )
    assert patch.status_code == 404
    delete = client.delete(f"/vehicles/{vid_b}", headers=company_headers(a))
    assert delete.status_code == 404
    # The row is untouched - B still sees it.
    with Session(pg_engine) as s:
        veh = s.get(Vehicle, uuid.UUID(vid_b))
        assert veh is not None and veh.current_km != 999


# --- S4: admin breadth ---

def test_superadmin_sees_all_scoped_sees_one(client, pg_engine):
    a = _new_company(pg_engine, "A-breadth")
    b = _new_company(pg_engine, "B-breadth")
    pa = f"ABR-{uuid.uuid4().hex[:6]}"
    pb = f"BBR-{uuid.uuid4().hex[:6]}"
    _make_vehicle(client, a, pa)
    _make_vehicle(client, b, pb)

    allv = client.get("/vehicles", headers=superadmin_headers())
    plates = [v["licensing_plate"] for v in allv.json()]
    assert pa in plates and pb in plates

    only_a = client.get("/vehicles", headers=company_headers(a))
    plates_a = [v["licensing_plate"] for v in only_a.json()]
    assert pa in plates_a and pb not in plates_a


# --- S5: derived writes inherit the parent's company ---

def test_derived_write_inherits_company(client, pg_engine):
    a = _new_company(pg_engine, "A-derived")
    vid = _make_vehicle(client, a, f"ADV-{uuid.uuid4().hex[:6]}")

    km = client.post(
        "/km", json={"vehicle_id": vid, "km": 12345, "source": "admin_ui"},
        headers=company_headers(a),
    )
    assert km.status_code == 200
    km_id = km.json()["km_update_id"]

    acc = client.post(
        "/accidents",
        json={"vehicle_id": vid, "datetime": datetime.now(tz=timezone.utc).isoformat()},
        headers=company_headers(a),
    )
    assert acc.status_code == 201
    acc_id = acc.json()["accident_id"]

    with Session(pg_engine) as s:
        assert str(s.get(KmUpdate, uuid.UUID(km_id)).company_id) == a
        assert str(s.get(Accident, uuid.UUID(acc_id)).company_id) == a
        ev = s.execute(
            select(Event).where(Event.source_id == uuid.UUID(acc_id))
        ).scalar_one()
        assert str(ev.company_id) == a


# --- S3b: cross-tenant attendance upsert (write by caller-supplied driver_id) -> 404 ---

def test_cross_tenant_attendance_upsert_returns_404(client, pg_engine):
    a = _new_company(pg_engine, "A-att")
    b = _new_company(pg_engine, "B-att")
    drv_b = client.post(
        "/drivers",
        json={"full_name": "B Driver", "phone_number": f"+972{uuid.uuid4().int % 10**9:09d}"},
        headers=company_headers(b),
    ).json()["driver_id"]
    # Company A admin must not write attendance onto company B's driver.
    res = client.patch(
        f"/attendance/{drv_b}/2026-01-05",
        json={"clock_in": "08:00", "status": "present"},
        headers=company_headers(a),
    )
    assert res.status_code == 404


# --- S6: per-company config isolation ---

def test_per_company_config_isolation(client, pg_engine):
    a = _new_company(pg_engine, "A-config")
    b = _new_company(pg_engine, "B-config")
    key = f"k-{uuid.uuid4().hex[:6]}"

    put = client.put(f"/config/{key}", json={"config_value": "A-only"}, headers=company_headers(a))
    assert put.status_code == 200

    # B cannot see A's key.
    assert client.get(f"/config/{key}", headers=company_headers(b)).status_code == 404
    # A can.
    got = client.get(f"/config/{key}", headers=company_headers(a))
    assert got.status_code == 200 and got.json()["config_value"] == "A-only"
