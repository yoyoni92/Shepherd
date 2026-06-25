"""Phone-match enrollment + bot authorizations (the no-invite flow)."""
from tests.conftest import admin_headers


def _driver(client, phone, status="active", name="Bot Tester"):
    r = client.post(
        "/drivers", json={"full_name": name, "phone_number": phone}, headers=admin_headers()
    )
    assert r.status_code == 201
    did = r.json()["driver_id"]
    if status != "active":
        client.patch(f"/drivers/{did}", json={"status": status}, headers=admin_headers())
    return did


def test_active_driver_auto_enrolls_as_driver(client):
    did = _driver(client, "0501112233")
    r = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 1011, "phone_number": "050-111-2233"},
        headers=admin_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "driver"
    assert body["driver_id"] == did
    w = client.get("/whoami", params={"chat_id": 1011}, headers=admin_headers())
    assert w.status_code == 200 and w.json()["role"] == "driver"


def test_unknown_phone_not_authorized(client):
    r = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 1012, "phone_number": "0509999999"},
        headers=admin_headers(),
    )
    assert r.status_code == 404


def test_inactive_driver_not_enrolled(client):
    _driver(client, "0503334455", status="inactive")
    r = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 1013, "phone_number": "0503334455"},
        headers=admin_headers(),
    )
    assert r.status_code == 404


def test_admin_authorization_enrolls_as_admin(client):
    a = client.post(
        "/bot-authorizations",
        json={"phone_number": "0504445566", "role": "admin"},
        headers=admin_headers(),
    )
    assert a.status_code == 201
    e = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 1014, "phone_number": "0504445566"},
        headers=admin_headers(),
    )
    assert e.status_code == 200 and e.json()["role"] == "admin"


def test_expired_authorization_rejected(client):
    client.post(
        "/bot-authorizations",
        json={"phone_number": "0505556677", "role": "admin", "expires_at": "2000-01-01T00:00:00+00:00"},
        headers=admin_headers(),
    )
    e = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 1015, "phone_number": "0505556677"},
        headers=admin_headers(),
    )
    assert e.status_code == 404


def test_whoami_revokes_when_driver_deactivated(client):
    did = _driver(client, "0506667788")
    client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 1016, "phone_number": "0506667788"},
        headers=admin_headers(),
    )
    client.patch(f"/drivers/{did}", json={"status": "inactive"}, headers=admin_headers())
    w = client.get("/whoami", params={"chat_id": 1016}, headers=admin_headers())
    assert w.status_code == 404


def test_authorizations_list_and_revoke(client):
    r = client.post(
        "/bot-authorizations",
        json={"phone_number": "0507778899", "role": "driver"},
        headers=admin_headers(),
    )
    aid = r.json()["id"]
    listed = client.get("/bot-authorizations", headers=admin_headers())
    assert any(a["id"] == aid for a in listed.json())
    d = client.delete(f"/bot-authorizations/{aid}", headers=admin_headers())
    assert d.status_code == 204
