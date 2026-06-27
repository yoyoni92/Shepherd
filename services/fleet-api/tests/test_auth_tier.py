"""Feature 2 - app auth tier: companies + app_users CRUD, login, company_admin scoping."""
import base64
import json
import uuid

from sqlalchemy.orm import Session

from shepherd_db.models import Company, Vehicle
from tests.conftest import (
    DEFAULT_COMPANY_ID,
    company_admin_headers,
    superadmin_headers,
)


def _decode_jwt(token: str) -> dict:
    """Tiny inline HS256 payload decoder (mirrors app.token, no verification)."""
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload))


def _new_company(engine, name: str) -> str:
    with Session(engine) as s:
        c = Company(name=name)
        s.add(c)
        s.commit()
        return str(c.company_id)


# --- B3: companies CRUD ---

def test_companies_crud_as_admin(client):
    created = client.post("/companies", json={"name": "Acme"}, headers=superadmin_headers())
    assert created.status_code == 201, created.text
    cid = created.json()["company_id"]
    assert created.json()["is_active"] is True

    listed = client.get("/companies", headers=superadmin_headers())
    assert listed.status_code == 200
    assert any(c["company_id"] == cid for c in listed.json())

    patched = client.patch(
        f"/companies/{cid}", json={"name": "Acme2", "is_active": False},
        headers=superadmin_headers(),
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Acme2" and patched.json()["is_active"] is False

    assert client.delete(f"/companies/{cid}", headers=superadmin_headers()).status_code == 204


def test_companies_forbidden_for_company_admin(client):
    headers = company_admin_headers(DEFAULT_COMPANY_ID)
    assert client.get("/companies", headers=headers).status_code == 403
    assert client.post("/companies", json={"name": "X"}, headers=headers).status_code == 403


# --- B4: app_users CRUD ---

def test_create_admin_app_user_no_company(client):
    email = f"admin-{uuid.uuid4().hex[:8]}@x.io"
    r = client.post(
        "/app-users",
        json={"email": email, "password": "pw", "role": "admin"},
        headers=superadmin_headers(),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["role"] == "admin" and body["company_id"] is None
    assert "password_hash" not in body and "password" not in body


def test_create_admin_with_company_rejected(client):
    r = client.post(
        "/app-users",
        json={"email": f"a-{uuid.uuid4().hex[:8]}@x.io", "password": "pw",
              "role": "admin", "company_id": DEFAULT_COMPANY_ID},
        headers=superadmin_headers(),
    )
    assert r.status_code == 400


def test_create_company_admin_requires_company(client):
    # Missing company_id -> 400.
    r = client.post(
        "/app-users",
        json={"email": f"ca-{uuid.uuid4().hex[:8]}@x.io", "password": "pw",
              "role": "company_admin"},
        headers=superadmin_headers(),
    )
    assert r.status_code == 400

    # With company_id -> 201.
    r2 = client.post(
        "/app-users",
        json={"email": f"ca-{uuid.uuid4().hex[:8]}@x.io", "password": "pw",
              "role": "company_admin", "company_id": DEFAULT_COMPANY_ID},
        headers=superadmin_headers(),
    )
    assert r2.status_code == 201
    assert r2.json()["company_id"] == DEFAULT_COMPANY_ID


def test_app_users_list_patch_delete(client):
    email = f"u-{uuid.uuid4().hex[:8]}@x.io"
    created = client.post(
        "/app-users",
        json={"email": email, "password": "pw", "role": "admin", "name": "U"},
        headers=superadmin_headers(),
    )
    uid = created.json()["user_id"]

    listed = client.get("/app-users", headers=superadmin_headers())
    assert listed.status_code == 200
    assert all("password_hash" not in u for u in listed.json())
    assert any(u["user_id"] == uid for u in listed.json())

    # Reset password + toggle is_active + rename.
    patched = client.patch(
        f"/app-users/{uid}",
        json={"password": "newpw", "is_active": False, "name": "U2"},
        headers=superadmin_headers(),
    )
    assert patched.status_code == 200
    assert patched.json()["is_active"] is False and patched.json()["name"] == "U2"
    assert "password_hash" not in patched.json()

    assert client.delete(f"/app-users/{uid}", headers=superadmin_headers()).status_code == 204
    assert client.delete(f"/app-users/{uid}", headers=superadmin_headers()).status_code == 404


def test_app_users_forbidden_for_company_admin(client):
    headers = company_admin_headers(DEFAULT_COMPANY_ID)
    assert client.get("/app-users", headers=headers).status_code == 403


# --- B5: login ---

def _create_login_user(client, password="pw", role="company_admin", company_id=DEFAULT_COMPANY_ID,
                       is_active=None):
    email = f"login-{uuid.uuid4().hex[:8]}@x.io"
    payload = {"email": email, "password": password, "role": role}
    if company_id is not None and role == "company_admin":
        payload["company_id"] = company_id
    created = client.post("/app-users", json=payload, headers=superadmin_headers())
    assert created.status_code == 201, created.text
    uid = created.json()["user_id"]
    if is_active is False:
        client.patch(f"/app-users/{uid}", json={"is_active": False}, headers=superadmin_headers())
    return email, uid


def test_login_success_returns_token(client):
    email, uid = _create_login_user(client, password="secret")
    r = client.post("/auth/login", json={"email": email, "password": "secret"},
                    headers=superadmin_headers())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["email"] == email
    assert "password_hash" not in body["user"]

    claims = _decode_jwt(body["token"])
    assert claims["sub"] == uid
    assert claims["role"] == "company_admin"
    assert claims["company_id"] == DEFAULT_COMPANY_ID
    assert isinstance(claims["exp"], int)


def test_login_admin_has_null_company_claim(client):
    email, uid = _create_login_user(client, password="secret", role="admin", company_id=None)
    r = client.post("/auth/login", json={"email": email, "password": "secret"},
                    headers=superadmin_headers())
    assert r.status_code == 200
    claims = _decode_jwt(r.json()["token"])
    assert claims["role"] == "admin" and claims["company_id"] is None


def test_login_wrong_password_401(client):
    email, _ = _create_login_user(client, password="right")
    r = client.post("/auth/login", json={"email": email, "password": "wrong"},
                    headers=superadmin_headers())
    assert r.status_code == 401


def test_login_unknown_email_401(client):
    r = client.post("/auth/login", json={"email": "nobody@x.io", "password": "x"},
                    headers=superadmin_headers())
    assert r.status_code == 401


def test_login_inactive_user_401(client):
    email, _ = _create_login_user(client, password="secret", is_active=False)
    r = client.post("/auth/login", json={"email": email, "password": "secret"},
                    headers=superadmin_headers())
    assert r.status_code == 401


# --- B7: company_admin end-to-end scoping (proves F1 repo scoping under the real role) ---

def test_company_admin_list_is_scoped(client, pg_engine):
    a_id = _new_company(pg_engine, "CA-A")
    b_id = _new_company(pg_engine, "CA-B")
    plate_a = f"CAA-{uuid.uuid4().hex[:6]}"
    plate_b = f"CAB-{uuid.uuid4().hex[:6]}"
    with Session(pg_engine) as s:
        s.add(Vehicle(licensing_plate=plate_a, company_id=uuid.UUID(a_id)))
        s.add(Vehicle(licensing_plate=plate_b, company_id=uuid.UUID(b_id)))
        s.commit()

    res = client.get("/vehicles", headers=company_admin_headers(a_id))
    assert res.status_code == 200
    plates = [v["licensing_plate"] for v in res.json()]
    assert plate_a in plates and plate_b not in plates


def test_company_admin_cross_tenant_by_pk_404(client, pg_engine):
    a_id = _new_company(pg_engine, "CA-A2")
    b_id = _new_company(pg_engine, "CA-B2")
    plate_b = f"CXB-{uuid.uuid4().hex[:6]}"
    with Session(pg_engine) as s:
        s.add(Vehicle(licensing_plate=plate_b, company_id=uuid.UUID(b_id)))
        s.commit()
    res = client.get(f"/vehicles/{plate_b}", headers=company_admin_headers(a_id))
    assert res.status_code == 404
