"""Phone-match enrollment + bot authorizations (the no-invite flow)."""
from tests.conftest import (
    DEFAULT_COMPANY_ID,
    admin_headers,
    company_admin_headers,
    superadmin_headers,
)


def _new_company(client, name: str) -> str:
    r = client.post("/companies", json={"name": name}, headers=superadmin_headers())
    assert r.status_code == 201, r.text
    return r.json()["company_id"]


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


def _set_attendance(client, enabled: bool) -> None:
    r = client.patch(
        f"/companies/{DEFAULT_COMPANY_ID}/settings",
        headers=superadmin_headers(),
        json={"feature_flags": {"attendance": enabled}},
    )
    assert r.status_code == 200, r.text


def test_enroll_response_carries_attendance_flag(client):
    # The bot renders its post-enroll menu from this flag, so it must reflect the
    # company's attendance setting (regression: it was absent and the bot defaulted on).
    _set_attendance(client, False)
    did = _driver(client, "0501114455", name="Att Off")
    r = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 2020, "phone_number": "0501114455"},
        headers=admin_headers(),
    )
    assert r.status_code == 200 and r.json()["driver_id"] == did
    assert r.json()["attendance_enabled"] is False

    _set_attendance(client, True)
    _driver(client, "0501114466", name="Att On")
    r2 = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 2021, "phone_number": "0501114466"},
        headers=admin_headers(),
    )
    assert r2.status_code == 200
    assert r2.json()["attendance_enabled"] is True


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
        json={
            "phone_number": "0505556677",
            "role": "admin",
            "expires_at": "2000-01-01T00:00:00+00:00",
        },
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


# --- Feature 3: bot tenancy ---

def test_enrolled_user_inherits_matched_drivers_company(client):
    """A bot user is bound to the company of the driver it matched."""
    _driver(client, "0521000001")
    client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 2001, "phone_number": "0521000001"},
        headers=admin_headers(),
    )
    w = client.get("/whoami", params={"chat_id": 2001}, headers=admin_headers())
    assert w.status_code == 200
    assert w.json()["company_id"] == DEFAULT_COMPANY_ID


def test_company_admin_lists_only_its_bot_users(client):
    """A company_admin must not see another company's bot users/authorizations."""
    b = _new_company(client, "Bot-B")
    # A driver + enrolled bot user in the Default Company.
    _driver(client, "0521000002")
    client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 2002, "phone_number": "0521000002"},
        headers=admin_headers(),
    )
    # Company B's admin sees neither the user nor an authorization from Default.
    client.post(
        "/bot-authorizations",
        json={"phone_number": "0521000003", "role": "admin"},
        headers=admin_headers(),
    )
    users_b = client.get("/users", headers=company_admin_headers(b))
    assert users_b.status_code == 200
    assert all(u["telegram_chat_id"] != 2002 for u in users_b.json())
    authz_b = client.get("/bot-authorizations", headers=company_admin_headers(b))
    assert all(a["phone_number"] != "0521000003" for a in authz_b.json())
    # The Default-company admin does see its own user.
    users_a = client.get("/users", headers=admin_headers())
    assert any(u["telegram_chat_id"] == 2002 for u in users_a.json())


def test_cross_tenant_role_change_blocked(client):
    """A company_admin cannot flip the role of another company's bot user (404)."""
    b = _new_company(client, "Bot-B2")
    _driver(client, "0521000004")
    e = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 2004, "phone_number": "0521000004"},
        headers=admin_headers(),
    )
    user_id = e.json()["user_id"]
    blocked = client.patch(
        f"/users/{user_id}/role", json={"role": "admin"},
        headers=company_admin_headers(b),
    )
    assert blocked.status_code == 404
    # The Default company_admin (same tenant) can.
    ok = client.patch(
        f"/users/{user_id}/role", json={"role": "admin"},
        headers=company_admin_headers(DEFAULT_COMPANY_ID),
    )
    assert ok.status_code == 200 and ok.json()["role"] == "admin"


def test_company_admin_can_manage_bot_invites(client):
    """company_admin is now permitted bot-invite management (scoped to its company)."""
    r = client.post(
        "/bot-authorizations",
        json={"phone_number": "0521000005", "role": "driver"},
        headers=company_admin_headers(DEFAULT_COMPANY_ID),
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    listed = client.get("/bot-authorizations", headers=company_admin_headers(DEFAULT_COMPANY_ID))
    assert any(a["id"] == aid for a in listed.json())
    # Another company's admin cannot revoke it.
    b = _new_company(client, "Bot-B3")
    assert client.delete(
        f"/bot-authorizations/{aid}", headers=company_admin_headers(b)
    ).status_code == 404
