"""T4 - Vehicles CRUD with ownership enforcement (T3 integration)."""
import uuid
from datetime import date, timedelta

from tests.conftest import admin_headers, customer_headers, driver_headers


def _plate(suffix: str) -> str:
    return f"VT-{suffix}"


def _make_driver(client) -> str:
    r = client.post(
        "/drivers",
        json={"full_name": "Test Driver", "phone_number": f"+1{uuid.uuid4().int % 10**10:010d}"},
        headers=admin_headers(),
    )
    return r.json()["driver_id"]


def _make_customer(client) -> str:
    r = client.post(
        "/customers",
        json={"full_name": "Test Customer", "email": f"c{uuid.uuid4().hex[:6]}@test.com"},
        headers=admin_headers(),
    )
    return r.json()["customer_id"]


def test_create_vehicle_admin(client):
    plate = _plate(uuid.uuid4().hex[:6])
    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    assert r.status_code == 201
    data = r.json()
    assert data["licensing_plate"] == plate
    assert "vehicle_id" in data


def test_create_vehicle_duplicate_plate(client):
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    assert r.status_code == 409


def test_get_vehicle_admin(client):
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    r = client.get(f"/vehicles/{plate}", headers=admin_headers())
    assert r.status_code == 200
    assert r.json()["licensing_plate"] == plate


def test_get_vehicle_driver_own(client):
    driver_id = _make_driver(client)
    plate = _plate(uuid.uuid4().hex[:6])
    client.post(
        "/vehicles",
        json={"licensing_plate": plate, "driver_id": driver_id},
        headers=admin_headers(),
    )
    r = client.get(f"/vehicles/{plate}", headers=driver_headers(driver_id))
    assert r.status_code == 200


def test_get_vehicle_driver_not_own(client):
    plate = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    other_driver_id = str(uuid.uuid4())
    r = client.get(f"/vehicles/{plate}", headers=driver_headers(other_driver_id))
    assert r.status_code == 403


def test_get_vehicle_not_found(client):
    r = client.get("/vehicles/NONEXISTENT-9999", headers=admin_headers())
    assert r.status_code == 404


def test_delete_vehicle_admin(client):
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.delete(f"/vehicles/{vehicle_id}", headers=admin_headers())
    assert r.status_code == 204


def test_delete_vehicle_driver_forbidden(client):
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.delete(f"/vehicles/{vehicle_id}", headers=driver_headers(str(uuid.uuid4())))
    assert r.status_code == 403


def test_delete_vehicle_customer_forbidden(client):
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post("/vehicles", json={"licensing_plate": plate}, headers=admin_headers())
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.delete(f"/vehicles/{vehicle_id}", headers=customer_headers(str(uuid.uuid4())))
    assert r.status_code == 403


def test_list_vehicles_admin_sees_all(client):
    # Create 2 vehicles
    p1 = _plate(uuid.uuid4().hex[:6])
    p2 = _plate(uuid.uuid4().hex[:6])
    client.post("/vehicles", json={"licensing_plate": p1}, headers=admin_headers())
    client.post("/vehicles", json={"licensing_plate": p2}, headers=admin_headers())
    r = client.get("/vehicles", headers=admin_headers())
    assert r.status_code == 200
    plates = [v["licensing_plate"] for v in r.json()]
    assert p1 in plates
    assert p2 in plates


def test_list_vehicles_driver_sees_own_only(client):
    driver_id = _make_driver(client)
    p_own = _plate(uuid.uuid4().hex[:6])
    p_other = _plate(uuid.uuid4().hex[:6])
    client.post(
        "/vehicles",
        json={"licensing_plate": p_own, "driver_id": driver_id},
        headers=admin_headers(),
    )
    client.post("/vehicles", json={"licensing_plate": p_other}, headers=admin_headers())
    r = client.get("/vehicles", headers=driver_headers(driver_id))
    assert r.status_code == 200
    plates = [v["licensing_plate"] for v in r.json()]
    assert p_own in plates
    assert p_other not in plates


def _make_cycle(client, steps, interval_km=10000):
    r = client.post(
        "/maintenance-types",
        json={"name": f"cyc-{uuid.uuid4().hex[:6]}", "interval_km": interval_km, "steps": steps},
        headers=admin_headers(),
    )
    return r.json()["id"]


def test_create_vehicle_with_cycle_position_derives_next(client):
    mt = _make_cycle(client, ["small", "big", "huge"])
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "maintenance_type_id": mt,
            "last_maintenance_type": "big",
            "last_maintenance_km": 50000,
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["last_maintenance_type"] == "big"
    assert data["next_maintenance_type"] == "huge"      # step after "big"
    assert data["next_maintenance_km"] == 60000          # 50000 + 10000 interval


def test_create_vehicle_without_position_leaves_next_unset(client):
    mt = _make_cycle(client, ["small", "big"])
    r = client.post(
        "/vehicles",
        json={"licensing_plate": _plate(uuid.uuid4().hex[:6]), "maintenance_type_id": mt},
        headers=admin_headers(),
    )
    assert r.status_code == 201
    assert r.json()["next_maintenance_type"] is None     # unchanged behavior


def test_create_three_vehicles_each_at_a_different_cycle_position(client):
    # One 3-care cycle; three cars added, each set to a different last-done care.
    # Each must derive the correct next-due care, including the wrap from the
    # last step back to the first.
    mt = _make_cycle(client, ["small", "big", "huge"])
    cases = [
        ("small", 10000, "big", 20000),
        ("big", 20000, "huge", 30000),
        ("huge", 30000, "small", 40000),  # wraps to the first step
    ]
    for last_step, last_km, want_next, want_next_km in cases:
        r = client.post(
            "/vehicles",
            json={
                "licensing_plate": _plate(uuid.uuid4().hex[:6]),
                "maintenance_type_id": mt,
                "last_maintenance_type": last_step,
                "last_maintenance_km": last_km,
            },
            headers=admin_headers(),
        )
        assert r.status_code == 201, (last_step, r.text)
        data = r.json()
        assert data["next_maintenance_type"] == want_next, last_step
        assert data["next_maintenance_km"] == want_next_km, last_step


def test_create_vehicle_position_without_km_derives_from_zero(client):
    # Position given but no km: next_km is computed off a 0 baseline (0 + interval).
    mt = _make_cycle(client, ["small", "big"], interval_km=15000)
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "maintenance_type_id": mt,
            "last_maintenance_type": "small",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201
    data = r.json()
    assert data["next_maintenance_type"] == "big"
    assert data["next_maintenance_km"] == 15000


def test_create_vehicle_position_without_maintenance_type_400(client):
    r = client.post(
        "/vehicles",
        json={"licensing_plate": _plate(uuid.uuid4().hex[:6]), "last_maintenance_type": "big"},
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_create_vehicle_position_not_in_cycle_400(client):
    mt = _make_cycle(client, ["small", "big"])
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "maintenance_type_id": mt,
            "last_maintenance_type": "nope",
        },
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_update_vehicle_sets_cycle_position(client):
    mt = _make_cycle(client, ["small", "big", "huge"])
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "maintenance_type_id": mt},
        headers=admin_headers(),
    )
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.patch(
        f"/vehicles/{vehicle_id}",
        json={"last_maintenance_type": "small", "last_maintenance_km": 10000},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["next_maintenance_type"] == "big"        # step after "small"
    assert data["next_maintenance_km"] == 20000


def test_update_vehicle_position_not_in_cycle_400(client):
    mt = _make_cycle(client, ["small", "big"])
    plate = _plate(uuid.uuid4().hex[:6])
    create_r = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "maintenance_type_id": mt},
        headers=admin_headers(),
    )
    vehicle_id = create_r.json()["vehicle_id"]
    r = client.patch(
        f"/vehicles/{vehicle_id}",
        json={"last_maintenance_type": "nope"},
        headers=admin_headers(),
    )
    assert r.status_code == 400


def _make_vehicle_on_cycle(client, mt) -> str:
    r = client.post(
        "/vehicles",
        json={"licensing_plate": _plate(uuid.uuid4().hex[:6]), "maintenance_type_id": mt},
        headers=admin_headers(),
    )
    return r.json()["vehicle_id"]


def test_update_three_vehicles_each_at_a_different_cycle_position(client):
    # One 3-care cycle; three cars edited, each set to a different last-done care.
    # Each must derive the correct next-due care, including the wrap from the
    # last step back to the first.
    mt = _make_cycle(client, ["small", "big", "huge"])
    cases = [
        ("small", 10000, "big", 20000),
        ("big", 20000, "huge", 30000),
        ("huge", 30000, "small", 40000),  # wraps to the first step
    ]
    for last_step, last_km, want_next, want_next_km in cases:
        vehicle_id = _make_vehicle_on_cycle(client, mt)
        r = client.patch(
            f"/vehicles/{vehicle_id}",
            json={"last_maintenance_type": last_step, "last_maintenance_km": last_km},
            headers=admin_headers(),
        )
        assert r.status_code == 200, (last_step, r.text)
        data = r.json()
        assert data["next_maintenance_type"] == want_next, last_step
        assert data["next_maintenance_km"] == want_next_km, last_step


def test_update_vehicle_position_without_km_derives_from_zero(client):
    # Position given but no km: next_km is computed off a 0 baseline (0 + interval).
    mt = _make_cycle(client, ["small", "big"], interval_km=15000)
    vehicle_id = _make_vehicle_on_cycle(client, mt)
    r = client.patch(
        f"/vehicles/{vehicle_id}",
        json={"last_maintenance_type": "small"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["next_maintenance_type"] == "big"
    assert data["next_maintenance_km"] == 15000


def test_update_repositioning_same_vehicle_recomputes_including_wrap(client):
    # Editing the same vehicle again re-derives next-due each time; the second
    # edit sets the last step, so the next wraps back to the first.
    mt = _make_cycle(client, ["small", "big", "huge"])
    vehicle_id = _make_vehicle_on_cycle(client, mt)

    r1 = client.patch(
        f"/vehicles/{vehicle_id}",
        json={"last_maintenance_type": "small", "last_maintenance_km": 10000},
        headers=admin_headers(),
    )
    assert r1.status_code == 200
    assert r1.json()["next_maintenance_type"] == "big"

    r2 = client.patch(
        f"/vehicles/{vehicle_id}",
        json={"last_maintenance_type": "huge", "last_maintenance_km": 30000},
        headers=admin_headers(),
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["next_maintenance_type"] == "small"      # wraps
    assert data["next_maintenance_km"] == 40000


# --- last-care km/date bounds: last_maintenance_km <= current_km, date not in the future ---

def test_create_vehicle_last_km_above_current_400(client):
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "current_km": 20000,
            "last_maintenance_km": 30000,
        },
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_create_vehicle_last_km_equal_current_ok(client):
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "current_km": 20000,
            "last_maintenance_km": 20000,  # equal is allowed
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201


def test_create_vehicle_future_last_date_400(client):
    tomorrow = date.today() + timedelta(days=1)
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "last_maintenance_date": tomorrow.isoformat(),
        },
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_create_vehicle_today_last_date_ok(client):
    r = client.post(
        "/vehicles",
        json={
            "licensing_plate": _plate(uuid.uuid4().hex[:6]),
            "last_maintenance_date": date.today().isoformat(),  # today is allowed
        },
        headers=admin_headers(),
    )
    assert r.status_code == 201


def test_update_last_km_above_current_400(client):
    plate = _plate(uuid.uuid4().hex[:6])
    vid = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "current_km": 20000},
        headers=admin_headers(),
    ).json()["vehicle_id"]
    r = client.patch(
        f"/vehicles/{vid}",
        json={"last_maintenance_km": 30000},
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_update_current_km_below_existing_last_400(client):
    # Lowering current_km below the already-recorded last-care km must be rejected.
    plate = _plate(uuid.uuid4().hex[:6])
    vid = client.post(
        "/vehicles",
        json={"licensing_plate": plate, "current_km": 20000, "last_maintenance_km": 10000},
        headers=admin_headers(),
    ).json()["vehicle_id"]
    r = client.patch(
        f"/vehicles/{vid}",
        json={"current_km": 5000},
        headers=admin_headers(),
    )
    assert r.status_code == 400


def test_update_future_last_date_400(client):
    plate = _plate(uuid.uuid4().hex[:6])
    vid = client.post(
        "/vehicles",
        json={"licensing_plate": plate},
        headers=admin_headers(),
    ).json()["vehicle_id"]
    tomorrow = date.today() + timedelta(days=1)
    r = client.patch(
        f"/vehicles/{vid}",
        json={"last_maintenance_date": tomorrow.isoformat()},
        headers=admin_headers(),
    )
    assert r.status_code == 400
