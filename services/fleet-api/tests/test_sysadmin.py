"""Feature 6 - System Admin (Telegram) backend.

System-admin identity at whoami/enroll (precedence over tenant matches) + the
company-less-admin-gated /sysadmin/* endpoints and the impersonation audit trail.
"""
import datetime
import uuid

from shepherd_contracts.auth import CallerContext, Role
from shepherd_db.models import Accident, Customer, Report, Vehicle
from sqlalchemy import text
from sqlalchemy.orm import Session

from tests.conftest import (
    DEFAULT_COMPANY_ID,
    TEST_TOKEN,
    admin_headers,
    company_admin_headers,
    company_headers,
    make_company_in_schema,
    superadmin_headers,
)


def _make_system_admin(client, phone: str) -> str:
    email = f"op-{uuid.uuid4().hex[:8]}@shepherd.ai"
    r = client.post(
        "/app-users",
        headers=superadmin_headers(),
        json={
            "email": email,
            "password": "pw-secret",
            "role": "admin",
            "is_system_admin": True,
            "phone_number": phone,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["is_system_admin"] is True
    assert body["phone_number"] == phone
    return body["user_id"]


def _new_company(client, name: str) -> str:
    r = client.post("/companies", json={"name": name}, headers=superadmin_headers())
    assert r.status_code == 201, r.text
    return r.json()["company_id"]


def _impersonating_headers(operator_id: str) -> dict:
    return {
        "X-Internal-Token": TEST_TOKEN,
        "X-Caller-Context": CallerContext(
            role=Role.admin, impersonator=operator_id
        ).model_dump_json(),
    }


# --- whoami / enroll: system-admin identity ---


def test_enroll_then_whoami_returns_system_admin(client):
    _make_system_admin(client, "+972500000111")
    e = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 9001, "phone_number": "0500000111"},
        headers=admin_headers(),
    )
    assert e.status_code == 200, e.text
    assert e.json()["is_system_admin"] is True
    assert e.json()["role"] == "admin"

    w = client.get("/whoami", params={"chat_id": 9001}, headers=admin_headers())
    assert w.status_code == 200
    body = w.json()
    assert body["is_system_admin"] is True
    assert body["role"] == "admin"
    assert body["company_id"] is None


def test_whoami_returns_playground_company_id(client, pg_engine):
    """The system admin's whoami carries the built-in Playground company id so the
    bot's Debug mode knows which company to impersonate within."""
    _make_system_admin(client, "+972500000444")
    client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 9004, "phone_number": "0500000444"},
        headers=admin_headers(),
    )
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO companies (company_id, name, is_internal) "
                "VALUES (:id, :name, true)"
            ),
            {"id": str(uuid.uuid4()), "name": f"Playground {uuid.uuid4().hex[:6]}"},
        )
    w = client.get("/whoami", params={"chat_id": 9004}, headers=admin_headers())
    assert w.status_code == 200
    returned = w.json()["playground_company_id"]
    assert returned is not None
    # The id the bot is handed must belong to an internal (Playground) company.
    with pg_engine.connect() as conn:
        is_internal = conn.execute(
            text("SELECT is_internal FROM companies WHERE company_id = :id"),
            {"id": returned},
        ).scalar_one()
    assert is_internal is True


def test_enroll_system_admin_precedence_over_driver(client):
    """A phone that matches both a driver and a system-admin app_user enrolls as the
    system admin (its path is checked first)."""
    phone = "0500000222"
    client.post(
        "/drivers",
        json={"full_name": "Dual Phone", "phone_number": phone},
        headers=admin_headers(),
    )
    _make_system_admin(client, "+972500000222")
    e = client.post(
        "/bot-enroll",
        json={"telegram_chat_id": 9002, "phone_number": phone},
        headers=admin_headers(),
    )
    assert e.status_code == 200
    assert e.json()["is_system_admin"] is True
    assert e.json()["driver_id"] is None


# --- /sysadmin/* gate: company-less admin only ---


def test_overview_requires_company_less_admin(client):
    # company_admin -> 403
    ca = client.get("/sysadmin/overview", headers=company_admin_headers(DEFAULT_COMPANY_ID))
    assert ca.status_code == 403
    # company-scoped admin -> 403
    assert client.get("/sysadmin/overview", headers=admin_headers()).status_code == 403
    # company-less admin -> 200
    assert client.get("/sysadmin/overview", headers=superadmin_headers()).status_code == 200


def test_overview_excludes_internal_company(client, pg_engine):
    visible = _new_company(client, f"Visible {uuid.uuid4().hex[:6]}")
    internal_id = str(uuid.uuid4())
    with pg_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO companies (company_id, name, is_internal) "
                "VALUES (:id, :name, true)"
            ),
            {"id": internal_id, "name": f"Internal {uuid.uuid4().hex[:6]}"},
        )

    r = client.get("/sysadmin/overview", headers=superadmin_headers())
    assert r.status_code == 200
    ids = {c["company_id"] for c in r.json()["companies"]}
    assert visible in ids
    assert internal_id not in ids


# --- /sysadmin/* list endpoints scoped to a company ---


def test_list_company_admins_scoped(client):
    company_a = _new_company(client, f"Co-A {uuid.uuid4().hex[:6]}")
    company_b = _new_company(client, f"Co-B {uuid.uuid4().hex[:6]}")
    email_a = f"ca-{uuid.uuid4().hex[:8]}@shepherd.ai"
    client.post(
        "/app-users",
        headers=superadmin_headers(),
        json={"email": email_a, "password": "pw", "role": "company_admin", "company_id": company_a},
    )
    client.post(
        "/app-users",
        headers=superadmin_headers(),
        json={
            "email": f"cb-{uuid.uuid4().hex[:8]}@shepherd.ai",
            "password": "pw",
            "role": "company_admin",
            "company_id": company_b,
        },
    )
    r = client.get(f"/sysadmin/companies/{company_a}/admins", headers=superadmin_headers())
    assert r.status_code == 200
    emails = {u["email"] for u in r.json()}
    assert email_a in emails
    assert all(u["company_id"] == company_a for u in r.json())


def test_list_company_drivers_scoped(client):
    company_a = _new_company(client, f"Drv-A {uuid.uuid4().hex[:6]}")
    phone = f"+97250{uuid.uuid4().int % 10_000_000:07d}"
    drv = client.post(
        "/drivers",
        headers=company_headers(company_a),
        json={"full_name": "Scoped Driver", "phone_number": phone},
    )
    driver_id = drv.json()["driver_id"]
    r = client.get(f"/sysadmin/companies/{company_a}/drivers", headers=superadmin_headers())
    assert r.status_code == 200
    assert [d["driver_id"] for d in r.json()] == [driver_id]


# --- impersonation audit ---


def test_impersonation_audit_written(client, pg_engine):
    operator_id = _make_system_admin(client, "+972500000333")
    company_id = _new_company(client, f"Audit {uuid.uuid4().hex[:6]}")
    r = client.post(
        "/sysadmin/impersonation-audit",
        headers=_impersonating_headers(operator_id),
        json={
            "company_id": company_id,
            "effective_role": "company_admin",
            "action": "start",
            "detail": "began live session",
        },
    )
    assert r.status_code == 201, r.text
    with pg_engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT effective_role, action, detail FROM impersonation_audit "
                "WHERE operator_id = :op AND company_id = :co"
            ),
            {"op": operator_id, "co": company_id},
        ).one()
    assert row.effective_role == "company_admin"
    assert row.action == "start"
    assert row.detail == "began live session"


def test_impersonation_audit_requires_operator(client):
    company_id = _new_company(client, f"NoOp {uuid.uuid4().hex[:6]}")
    r = client.post(
        "/sysadmin/impersonation-audit",
        headers=superadmin_headers(),
        json={"company_id": company_id, "effective_role": "driver", "action": "start"},
    )
    assert r.status_code == 400


# --- per-schema correctness: dedicated schema companies must be counted ---


def test_overview_per_schema_dedicated_company(client, pg_engine):
    """A company in a dedicated schema must appear with non-zero tenant counts.

    The current implementation reads all tenant tables on the request session
    (which resolves to public for a company-less system admin) - this test
    will FAIL (all counts are 0 or KeyError) until system_overview is rewritten
    to open a per-schema translated connection for each company.
    """
    cid = make_company_in_schema(pg_engine, f"PerSchemaCo {uuid.uuid4().hex[:6]}", "co_ov1")

    shared = "public"
    veh_id = uuid.uuid4()
    with pg_engine.connect() as raw_conn:
        tconn = raw_conn.execution_options(
            schema_translate_map={"tenant": "co_ov1", None: shared}
        )
        with Session(bind=tconn) as s:
            veh = Vehicle(
                vehicle_id=veh_id,
                company_id=uuid.UUID(cid),
                licensing_plate=f"OV-{uuid.uuid4().hex[:6]}",
                # maintenance due: current_km >= next_maintenance_km
                current_km=50000,
                next_maintenance_km=40000,
                # docs expiring: insurance valid in 5 days
                insurance_valid_to=datetime.date.today() + datetime.timedelta(days=5),
            )
            s.add(veh)
            s.flush()

            s.add(Customer(
                company_id=uuid.UUID(cid),
                full_name="Test Customer",
            ))

            s.add(Accident(
                company_id=uuid.UUID(cid),
                vehicle_id=veh_id,
                datetime=datetime.datetime.now(datetime.UTC),
            ))

            s.add(Report(
                company_id=uuid.UUID(cid),
                vehicle_id=veh_id,
                ticket_type="traffic",
            ))

            s.commit()

    r = client.get("/sysadmin/overview", headers=superadmin_headers())
    assert r.status_code == 200

    companies = {c["company_id"]: c for c in r.json()["companies"]}
    assert cid in companies, f"Company {cid} not found in overview"

    item = companies[cid]

    # New fields must be present
    assert "schema_name" in item, "schema_name field missing from SystemOverviewItem"
    assert "is_active" in item, "is_active field missing from SystemOverviewItem"
    assert "customer_count" in item, "customer_count field missing"
    assert "accident_count" in item, "accident_count field missing"
    assert "maintenance_due_count" in item, "maintenance_due_count field missing"
    assert "docs_expiring_count" in item, "docs_expiring_count field missing"
    assert "unpaid_report_count" in item, "unpaid_report_count field missing"
    assert "total_km_7d" in item, "total_km_7d field missing"
    assert "bot_user_count" in item, "bot_user_count field missing"

    # These will be 0 with the current public-only impl (RED assertions):
    assert item["customer_count"] >= 1, (
        "customer_count should be >=1 (inserted into co_ov1.customers); "
        "0 means the overview read public.customers instead"
    )
    assert item["accident_count"] >= 1, (
        "accident_count should be >=1 (inserted into co_ov1.accidents); "
        "0 means the overview read public.accidents instead"
    )
    assert item["unpaid_report_count"] >= 1, (
        "unpaid_report_count should be >=1 (inserted into co_ov1.reports); "
        "0 means the overview read public.reports instead"
    )
    assert item["maintenance_due_count"] >= 1, (
        "maintenance_due_count should be >=1 (vehicle with current_km>=next_maintenance_km "
        "inserted into co_ov1.vehicles); 0 means the overview read public.vehicles"
    )
    assert item["docs_expiring_count"] >= 1, (
        "docs_expiring_count should be >=1 (insurance valid in 5 days inserted into "
        "co_ov1.vehicles); 0 means the overview read public.vehicles instead"
    )
    assert item["vehicle_count"] >= 1, (
        "vehicle_count should be >=1; 0 means overview read public.vehicles"
    )
    assert item["schema_name"] == "co_ov1"
    assert item["is_active"] is True


def test_overview_default_company_still_counts(client, pg_engine):
    """The default company (public schema) must still appear with correct counts.

    Guards against the per-schema refactor breaking the shared-schema path.
    """
    # Insert a vehicle in the default (public) company.
    with Session(pg_engine) as s:
        s.add(Vehicle(
            company_id=uuid.UUID(DEFAULT_COMPANY_ID),
            licensing_plate=f"DEF-{uuid.uuid4().hex[:6]}",
        ))
        s.commit()

    r = client.get("/sysadmin/overview", headers=superadmin_headers())
    assert r.status_code == 200
    companies = {c["company_id"]: c for c in r.json()["companies"]}
    assert DEFAULT_COMPANY_ID in companies
    item = companies[DEFAULT_COMPANY_ID]
    assert item["vehicle_count"] >= 1
    assert item["schema_name"] == "public"
