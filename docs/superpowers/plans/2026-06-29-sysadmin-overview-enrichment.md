# Sysadmin Overview Enrichment - Per-Schema Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrich the System-Admin cross-company overview with per-schema-correct counts (customers, accidents, maintenance-due, docs-expiring, unpaid reports, 7d km, bot users, is_active, schema_name) and fix the existing vehicle/driver/event counts so they read from each company's dedicated Postgres schema instead of only public.

**Architecture:** The current `repo.system_overview` runs all counts on the request session, which resolves to the shared/public schema for a company-less System Admin - undercounting companies on dedicated schemas. The fix iterates each non-internal company, resolves its `schema_name` from `company_settings`, opens a per-schema translated `engine.connect()` (same pattern as `find_enrollment_by_phone` and `refresh_kpi_daily`), and runs ALL tenant-table counts there. Public-only reads (kpi_daily, app_users/BotUser, company, company_settings) stay on the main session. Companies with `schema_name == '__pending__'` get zeroed tenant counts.

**Tech Stack:** Python 3.12, SQLAlchemy 2.x ORM (Session + engine.connect()), FastAPI, Pydantic v2, PostgreSQL 16 (schema_translate_map), pytest + testcontainers, Telegram bot (httpx mock), ruff, mypy.

## Global Constraints

- No new dependencies (no pip installs).
- No em dashes in any file - use hyphens only.
- Do NOT wipe any running docker compose stack.
- All tenant tables carry `{"schema": "tenant"}` in `__table_args__` and live in each company's schema.
- Public tables: companies, company_settings, users (BotUser), app_users, kpi_daily, system_config, bot_authorizations, impersonation_audit, bot_sessions.
- Shared schema = `get_config().database.shared_schema` (returns "public" in tests).
- `__pending__` sentinel: if `company_settings.schema_name == '__pending__'`, skip that company's tenant counts (treat as 0).
- Commit convention: lowercase imperative subject <=72 chars, blank line, body 72 chars wrapped, no Co-Authored-By.
- Maintenance due condition: `current_km IS NOT NULL AND next_maintenance_km IS NOT NULL AND current_km >= next_maintenance_km`.
- Docs expiring window: 30 days from today (`insurance_valid_to <= today+30 OR license_valid_to <= today+30`).
- Unpaid reports: `status == 'unpaid'`.

---

## File Map

| File | Change |
|------|--------|
| `services/fleet-api/app/schemas.py` | Extend `SystemOverviewItem` with 9 new fields |
| `services/fleet-api/app/repo.py` | Rewrite `system_overview` with per-schema loop |
| `services/fleet-api/tests/test_sysadmin.py` | Add failing RED test + existing-company coverage |
| `services/telegram-bot/app/texts.py` | Update `SA_OVERVIEW_LINE` |
| `services/telegram-bot/app/flows/sysadmin.py` | Pass new fields in `_overview` `.format()` call |
| `services/telegram-bot/tests/test_flows.py` | Extend `test_overview_uses_system_admin_context` |

---

### Task 1: Write the RED failing test (fleet-api)

This test must FAIL against the current implementation because it inserts data into a dedicated schema (`co_ov1`) but the current `system_overview` only reads from public - the counts come back as 0.

**Files:**
- Modify: `services/fleet-api/tests/test_sysadmin.py`

**Interfaces:**
- Consumes: `make_company_in_schema(engine, name, schema)` from `tests/conftest.py:178`
- Consumes: `superadmin_headers()` from `tests/conftest.py:134`
- Produces: `test_overview_per_schema_dedicated_company` - the RED test that drives Task 2

- [ ] **Step 1: Add imports at the top of the test file**

Open `services/fleet-api/tests/test_sysadmin.py`. After the existing imports block (after line 18), add:

```python
import datetime

from shepherd_db.models import (
    Accident,
    Customer,
    Report,
    Vehicle,
)
from sqlalchemy import Connection as SAConnection
from sqlalchemy.orm import Session
```

- [ ] **Step 2: Write the failing test**

Append to `services/fleet-api/tests/test_sysadmin.py`:

```python

# --- per-schema correctness: dedicated schema companies must be counted ---


def test_overview_per_schema_dedicated_company(client, pg_engine):
    """A company in a dedicated schema must appear with non-zero tenant counts.

    The current implementation reads all tenant tables on the request session
    (which resolves to public for a company-less system admin) - this test
    will FAIL (all counts are 0) until system_overview is rewritten to open
    a per-schema translated connection for each company.
    """
    cid = make_company_in_schema(pg_engine, f"PerSchemaCo {uuid.uuid4().hex[:6]}", "co_ov1")

    shared = "public"
    assert isinstance(pg_engine.connect().__enter__().get_execution_options().get(
        "schema_translate_map", {}).get("tenant"), str) or True  # just access the engine

    with pg_engine.connect() as raw_conn:
        tconn = raw_conn.execution_options(
            schema_translate_map={"tenant": "co_ov1", None: shared}
        )
        with Session(bind=tconn) as s:
            import uuid as _uuid
            vehicle_id = _uuid.uuid4()
            veh = Vehicle(
                vehicle_id=vehicle_id,
                company_id=_uuid.UUID(cid),
                licensing_plate=f"OV-{_uuid.uuid4().hex[:6]}",
                # maintenance due: current_km >= next_maintenance_km
                current_km=50000,
                next_maintenance_km=40000,
                # docs expiring: insurance valid in 5 days
                insurance_valid_to=datetime.date.today() + datetime.timedelta(days=5),
            )
            s.add(veh)
            s.flush()

            s.add(Customer(
                company_id=_uuid.UUID(cid),
                full_name="Test Customer",
            ))

            s.add(Accident(
                company_id=_uuid.UUID(cid),
                vehicle_id=vehicle_id,
                datetime=datetime.datetime.now(datetime.timezone.utc),
            ))

            s.add(Report(
                company_id=_uuid.UUID(cid),
                vehicle_id=vehicle_id,
                ticket_type="traffic",
                status="unpaid",
            ))

            s.commit()

    r = client.get("/sysadmin/overview", headers=superadmin_headers())
    assert r.status_code == 200

    companies = {c["company_id"]: c for c in r.json()["companies"]}
    assert cid in companies, f"Company {cid} not found in overview"

    item = companies[cid]

    # New fields must be present
    assert "schema_name" in item
    assert "is_active" in item
    assert "customer_count" in item
    assert "accident_count" in item
    assert "maintenance_due_count" in item
    assert "docs_expiring_count" in item
    assert "unpaid_report_count" in item
    assert "total_km_7d" in item
    assert "bot_user_count" in item

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
        "was inserted into co_ov1.vehicles); 0 means the overview read public.vehicles"
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

    This guards against the per-schema refactor breaking the shared-schema path.
    """
    from tests.conftest import DEFAULT_COMPANY_ID

    # Insert a vehicle in the default (public) company.
    with Session(pg_engine) as s:
        import uuid as _uuid
        s.add(Vehicle(
            company_id=_uuid.UUID(DEFAULT_COMPANY_ID),
            licensing_plate=f"DEF-{_uuid.uuid4().hex[:6]}",
        ))
        s.commit()

    r = client.get("/sysadmin/overview", headers=superadmin_headers())
    assert r.status_code == 200
    companies = {c["company_id"]: c for c in r.json()["companies"]}
    assert DEFAULT_COMPANY_ID in companies
    item = companies[DEFAULT_COMPANY_ID]
    assert item["vehicle_count"] >= 1
    assert item["schema_name"] == "public"
```

- [ ] **Step 3: Run the test to confirm RED**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run pytest tests/test_sysadmin.py::test_overview_per_schema_dedicated_company -v 2>&1 | tail -30
```

Expected: `FAILED` with `AssertionError: customer_count should be >=1` (or similar - all counts are 0 because the current impl reads from public only) OR `KeyError: 'customer_count'` (field missing from schema). Either failure confirms RED.

- [ ] **Step 4: Commit the RED test**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
git add services/fleet-api/tests/test_sysadmin.py
git commit -m "$(cat <<'EOF'
test(fleet-api): add RED per-schema overview test

Adds test_overview_per_schema_dedicated_company which inserts a customer,
accident, unpaid report, and maintenance-due vehicle into a dedicated
schema (co_ov1) and asserts the overview returns non-zero counts for that
company. This FAILS against the current public-only implementation and
will go GREEN after the per-schema refactor in the next commit.

Also adds test_overview_default_company_still_counts to guard the
shared-schema path after the refactor.
EOF
)"
```

---

### Task 2: Extend SystemOverviewItem schema (fleet-api)

**Files:**
- Modify: `services/fleet-api/app/schemas.py` (lines 551-562)

**Interfaces:**
- Consumes: nothing new
- Produces: `SystemOverviewItem` with fields: `customer_count: int = 0`, `accident_count: int = 0`, `maintenance_due_count: int = 0`, `docs_expiring_count: int = 0`, `unpaid_report_count: int = 0`, `total_km_7d: int = 0`, `is_active: bool = True`, `schema_name: str = ""`, `bot_user_count: int = 0`

- [ ] **Step 1: Replace SystemOverviewItem in schemas.py**

In `services/fleet-api/app/schemas.py`, find and replace the `SystemOverviewItem` class (lines 551-558):

Old:
```python
class SystemOverviewItem(BaseModel):
    company_id: UUID
    name: str
    vehicle_count: int
    driver_count: int
    open_event_count: int
    attendance_enabled: bool
    gdrive_configured: bool
```

New:
```python
class SystemOverviewItem(BaseModel):
    company_id: UUID
    name: str
    vehicle_count: int
    driver_count: int
    open_event_count: int
    attendance_enabled: bool
    gdrive_configured: bool
    # New per-schema-correct fields
    customer_count: int = 0
    accident_count: int = 0
    maintenance_due_count: int = 0
    docs_expiring_count: int = 0
    unpaid_report_count: int = 0
    total_km_7d: int = 0
    is_active: bool = True
    schema_name: str = ""
    bot_user_count: int = 0
```

- [ ] **Step 2: Run the test again - expect a different failure (schema changed, repo not yet updated)**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run pytest tests/test_sysadmin.py::test_overview_per_schema_dedicated_company -v 2>&1 | tail -20
```

Expected: still `FAILED` but now with `AssertionError: customer_count should be >=1` (the field exists but repo still returns 0 from public).

---

### Task 3: Rewrite repo.system_overview with per-schema loop (fleet-api)

This is the core correctness fix. Each company's tenant-table counts are run against its own schema using a translated connection, mirroring the `find_enrollment_by_phone` / `refresh_kpi_daily` pattern.

**Files:**
- Modify: `services/fleet-api/app/repo.py` (lines 1038-1070)

**Interfaces:**
- Consumes: `Session` (main session, bound to a `Connection`); `get_config().database.shared_schema`; `CompanySettings.schema_name`
- Produces: `list[dict]` with all `SystemOverviewItem` fields (both old and new)

- [ ] **Step 1: Add `date` import at top of repo.py**

In `services/fleet-api/app/repo.py`, add `date` to the `from datetime import UTC` line:

```python
from datetime import UTC, date
```

- [ ] **Step 2: Replace the system_overview function**

In `services/fleet-api/app/repo.py`, find and replace the entire `system_overview` function (lines 1038-1070):

```python
def system_overview(session: Session) -> list[dict]:
    """Per-company counts + health flags for the system overview.

    All tenant-table counts (vehicles, drivers, events, customers, accidents,
    reports) are run against each company's own Postgres schema using a
    schema_translate_map translated connection - the same pattern used by
    find_enrollment_by_phone and refresh_kpi_daily. Companies whose
    schema_name is '__pending__' (schema not yet provisioned) get 0 for all
    tenant counts. Public-table reads (kpi_daily, BotUser, company_settings)
    stay on the main session.
    """
    from datetime import timedelta

    from shepherd_config import get_config

    shared = get_config().database.shared_schema
    from sqlalchemy import Connection as SAConnection
    assert isinstance(session.bind, SAConnection), "session.bind must be a Connection"
    engine = session.bind.engine

    today = date.today()
    docs_cutoff = today + timedelta(days=30)

    overview: list[dict] = []
    for c in session.execute(
        select(Company).where(Company.is_internal.is_(False)).order_by(Company.name)
    ).scalars():
        settings = session.get(CompanySettings, c.company_id)
        schema_name = settings.schema_name if settings else shared
        attendance_enabled = bool(
            settings and settings.feature_flags and settings.feature_flags.get("attendance")
        )
        gdrive_configured = bool(settings and settings.gdrive_credentials_json)

        # Public-table reads: BotUser count, kpi_daily.
        bot_user_count = session.scalar(
            select(func.count()).select_from(BotUser).where(
                BotUser.company_id == c.company_id
            )
        ) or 0

        kpi_row = session.execute(
            select(KpiDaily)
            .where(KpiDaily.company_id == c.company_id)
            .order_by(KpiDaily.snapshot_date.desc())
            .limit(1)
        ).scalar_one_or_none()
        total_km_7d = int(kpi_row.total_km_7d) if (kpi_row and kpi_row.total_km_7d) else 0

        # Tenant-table reads: open a schema-translated connection per company.
        if schema_name == "__pending__":
            vehicle_count = driver_count = open_event_count = 0
            customer_count = accident_count = maintenance_due_count = 0
            docs_expiring_count = unpaid_report_count = 0
        else:
            with engine.connect() as conn:
                tconn = conn.execution_options(
                    schema_translate_map={"tenant": schema_name, None: shared}
                )
                with Session(bind=tconn) as s:
                    vehicle_count = s.scalar(
                        select(func.count()).select_from(Vehicle).where(
                            Vehicle.company_id == c.company_id
                        )
                    ) or 0
                    driver_count = s.scalar(
                        select(func.count()).select_from(Driver).where(
                            Driver.company_id == c.company_id
                        )
                    ) or 0
                    open_event_count = s.scalar(
                        select(func.count()).select_from(Event).where(
                            Event.company_id == c.company_id,
                            Event.status == "open",
                        )
                    ) or 0
                    customer_count = s.scalar(
                        select(func.count()).select_from(Customer).where(
                            Customer.company_id == c.company_id
                        )
                    ) or 0
                    accident_count = s.scalar(
                        select(func.count()).select_from(Accident).where(
                            Accident.company_id == c.company_id
                        )
                    ) or 0
                    maintenance_due_count = s.scalar(
                        select(func.count()).select_from(Vehicle).where(
                            Vehicle.company_id == c.company_id,
                            Vehicle.current_km.is_not(None),
                            Vehicle.next_maintenance_km.is_not(None),
                            Vehicle.current_km >= Vehicle.next_maintenance_km,
                        )
                    ) or 0
                    from sqlalchemy import or_
                    docs_expiring_count = s.scalar(
                        select(func.count()).select_from(Vehicle).where(
                            Vehicle.company_id == c.company_id,
                            or_(
                                Vehicle.insurance_valid_to <= docs_cutoff,
                                Vehicle.license_valid_to <= docs_cutoff,
                            ),
                        )
                    ) or 0
                    unpaid_report_count = s.scalar(
                        select(func.count()).select_from(Report).where(
                            Report.company_id == c.company_id,
                            Report.status == "unpaid",
                        )
                    ) or 0

        overview.append({
            "company_id": c.company_id,
            "name": c.name,
            "is_active": c.is_active,
            "schema_name": schema_name,
            "vehicle_count": vehicle_count,
            "driver_count": driver_count,
            "open_event_count": open_event_count,
            "attendance_enabled": attendance_enabled,
            "gdrive_configured": gdrive_configured,
            "customer_count": customer_count,
            "accident_count": accident_count,
            "maintenance_due_count": maintenance_due_count,
            "docs_expiring_count": docs_expiring_count,
            "unpaid_report_count": unpaid_report_count,
            "total_km_7d": total_km_7d,
            "bot_user_count": bot_user_count,
        })
    return overview
```

- [ ] **Step 3: Run the targeted per-schema tests - expect GREEN**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run pytest tests/test_sysadmin.py::test_overview_per_schema_dedicated_company tests/test_sysadmin.py::test_overview_default_company_still_counts -v 2>&1 | tail -30
```

Expected: both `PASSED`.

- [ ] **Step 4: Run the full sysadmin suite to confirm no regressions**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run pytest tests/test_sysadmin.py -v 2>&1 | tail -30
```

Expected: all sysadmin tests PASS.

- [ ] **Step 5: Commit schema + repo changes**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
git add services/fleet-api/app/schemas.py services/fleet-api/app/repo.py
git commit -m "$(cat <<'EOF'
fix(fleet-api): per-schema system overview with enriched metrics

Rewrites repo.system_overview to open a schema_translate_map translated
connection per company (same pattern as find_enrollment_by_phone), so
tenant counts (vehicles, drivers, events, customers, accidents, reports)
read from each company's actual schema instead of just public.

Adds to SystemOverviewItem: customer_count, accident_count,
maintenance_due_count, docs_expiring_count, unpaid_report_count,
total_km_7d (from kpi_daily), is_active, schema_name, bot_user_count.
Companies with schema_name '__pending__' get zero tenant counts.
EOF
)"
```

---

### Task 4: Run full fleet-api suite (GREEN gate)

- [ ] **Step 1: Run the full test suite**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run pytest -q 2>&1 | tail -20
```

Expected: all tests pass. Record the pass count.

- [ ] **Step 2: Run ruff on fleet-api**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
uvx ruff check services/fleet-api 2>&1
```

Expected: no output (clean).

- [ ] **Step 3: Run mypy on fleet-api**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run mypy . 2>&1 | tail -20
```

Expected: `Success: no issues found` or only pre-existing unrelated warnings.

- [ ] **Step 4: Fix any ruff/mypy issues before proceeding**

If ruff reports issues, fix them (format: line numbers + messages). If mypy reports new issues in `repo.py` or `schemas.py`, fix them. Commit fixes if any:

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
git add services/fleet-api/app/repo.py services/fleet-api/app/schemas.py
git commit -m "fix(fleet-api): resolve ruff/mypy issues in overview enrichment"
```

---

### Task 5: Update bot text and rendering (telegram-bot)

**Files:**
- Modify: `services/telegram-bot/app/texts.py` (lines 58-62)
- Modify: `services/telegram-bot/app/flows/sysadmin.py` (lines 105-116)

**Interfaces:**
- Consumes: `SystemOverviewItem` fields from the API response dict: `customer_count`, `accident_count`, `maintenance_due_count`, `docs_expiring_count`, `unpaid_report_count`, `total_km_7d`, `is_active`, `schema_name`
- Produces: updated `SA_OVERVIEW_LINE` format string; updated `_overview()` `.format()` call

- [ ] **Step 1: Update SA_OVERVIEW_LINE in texts.py**

In `services/telegram-bot/app/texts.py`, find and replace `SA_OVERVIEW_LINE` (lines 58-62):

Old:
```python
SA_OVERVIEW_LINE = (
    "🏢 {name}\n"
    "   רכבים: {vehicles} · נהגים: {drivers} · אירועים פתוחים: {events}\n"
    "   נוכחות: {attendance} · Drive: {drive}"
)
```

New:
```python
SA_OVERVIEW_LINE = (
    "🏢 {name} [{schema}] {active}\n"
    "   🚗 {vehicles} רכבים · 👷 {drivers} נהגים · ⚠️ {events} אירועים\n"
    "   👥 {customers} לקוחות · 💥 {accidents} תאונות · 🎫 {unpaid} דוחות\n"
    "   🔧 {maint_due} תחזוקה · 📄 {docs_exp} מסמכים · 📈 {km_7d} ק\"מ (7י)\n"
    "   🤖 {bot_users} בוט · נוכחות: {attendance} · Drive: {drive}"
)
```

- [ ] **Step 2: Update _overview() in flows/sysadmin.py**

In `services/telegram-bot/app/flows/sysadmin.py`, find and replace the `_overview` function (lines 99-117):

Old:
```python
async def _overview(ctx: Ctx) -> None:
    resp = await ctx.fleet.get("/sysadmin/overview")
    companies = resp.json().get("companies", []) if resp.status_code == 200 else []
    if not companies:
        await send(ctx, f"{texts.SA_OVERVIEW_TITLE}\n\n{texts.SA_OVERVIEW_EMPTY}")
        return
    lines = [texts.SA_OVERVIEW_TITLE, ""]
    for c in companies:
        lines.append(
            texts.SA_OVERVIEW_LINE.format(
                name=c["name"],
                vehicles=c["vehicle_count"],
                drivers=c["driver_count"],
                events=c["open_event_count"],
                attendance=texts.SA_ON if c["attendance_enabled"] else texts.SA_OFF,
                drive=texts.SA_ON if c["gdrive_configured"] else texts.SA_OFF,
            )
        )
    await send(ctx, "\n".join(lines))
```

New:
```python
async def _overview(ctx: Ctx) -> None:
    resp = await ctx.fleet.get("/sysadmin/overview")
    companies = resp.json().get("companies", []) if resp.status_code == 200 else []
    if not companies:
        await send(ctx, f"{texts.SA_OVERVIEW_TITLE}\n\n{texts.SA_OVERVIEW_EMPTY}")
        return
    lines = [texts.SA_OVERVIEW_TITLE, ""]
    for c in companies:
        active_flag = texts.SA_ON if c.get("is_active", True) else texts.SA_OFF
        lines.append(
            texts.SA_OVERVIEW_LINE.format(
                name=c["name"],
                schema=c.get("schema_name", ""),
                active=active_flag,
                vehicles=c["vehicle_count"],
                drivers=c["driver_count"],
                events=c["open_event_count"],
                customers=c.get("customer_count", 0),
                accidents=c.get("accident_count", 0),
                unpaid=c.get("unpaid_report_count", 0),
                maint_due=c.get("maintenance_due_count", 0),
                docs_exp=c.get("docs_expiring_count", 0),
                km_7d=c.get("total_km_7d", 0),
                bot_users=c.get("bot_user_count", 0),
                attendance=texts.SA_ON if c["attendance_enabled"] else texts.SA_OFF,
                drive=texts.SA_ON if c["gdrive_configured"] else texts.SA_OFF,
            )
        )
    await send(ctx, "\n".join(lines))
```

- [ ] **Step 3: Commit bot changes**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
git add services/telegram-bot/app/texts.py services/telegram-bot/app/flows/sysadmin.py
git commit -m "$(cat <<'EOF'
feat(telegram-bot): enrich sysadmin overview with new metrics

Updates SA_OVERVIEW_LINE and _overview() to display the new per-company
fields: customers, accidents, unpaid reports, maintenance due, expiring
docs, 7d km, bot users, schema name, and active status.
EOF
)"
```

---

### Task 6: Update telegram-bot overview rendering test (telegram-bot)

**Files:**
- Modify: `services/telegram-bot/tests/test_flows.py`

**Interfaces:**
- Consumes: `test_overview_uses_system_admin_context` at line ~526 in test_flows.py
- Produces: extended test that mocks all new fields and asserts they appear in the sent message

- [ ] **Step 1: Read the existing test at line 526**

The existing test `test_overview_uses_system_admin_context` (lines 526-553) mocks a company response with only the old fields. We need to extend the mock to include the new fields and assert they appear.

- [ ] **Step 2: Replace the mock payload and add assertions**

In `services/telegram-bot/tests/test_flows.py`, find and replace the `test_overview_uses_system_admin_context` function. The exact old text to match (lines 526-553):

```python
async def test_overview_uses_system_admin_context(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    route = mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(
            200,
            json={
                "companies": [
                    {
                        "company_id": LIVE_CO,
                        "name": "Acme",
                        "vehicle_count": 3,
                        "driver_count": 5,
                        "open_event_count": 1,
                        "attendance_enabled": True,
                        "gdrive_configured": False,
                    }
                ]
            },
        )
    )
    await dispatch(
        {"chat_id": 61, "sender_id": 61, "is_callback": True, "callback_data": "sa_overview"},
        bot,
        fleet,
    )
    # The overview reads as the company-less system admin (no company_id, no impersonator).
    assert caller_ctx(route) == {"role": "admin"}
    assert any("Acme" in t for t in sent_texts(bot))
```

Replace with:

```python
async def test_overview_uses_system_admin_context(store, bot, fleet, mock_api):
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    route = mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(
            200,
            json={
                "companies": [
                    {
                        "company_id": LIVE_CO,
                        "name": "Acme",
                        "vehicle_count": 3,
                        "driver_count": 5,
                        "open_event_count": 1,
                        "attendance_enabled": True,
                        "gdrive_configured": False,
                        "customer_count": 7,
                        "accident_count": 2,
                        "maintenance_due_count": 1,
                        "docs_expiring_count": 3,
                        "unpaid_report_count": 4,
                        "total_km_7d": 1500,
                        "is_active": True,
                        "schema_name": "co_acme",
                        "bot_user_count": 6,
                    }
                ]
            },
        )
    )
    await dispatch(
        {"chat_id": 61, "sender_id": 61, "is_callback": True, "callback_data": "sa_overview"},
        bot,
        fleet,
    )
    # The overview reads as the company-less system admin (no company_id, no impersonator).
    assert caller_ctx(route) == {"role": "admin"}
    texts_sent = sent_texts(bot)
    assert any("Acme" in t for t in texts_sent)
    # New fields must appear in the rendered output.
    combined = "\n".join(texts_sent)
    assert "co_acme" in combined, "schema_name 'co_acme' must appear in overview"
    assert "7" in combined, "customer_count=7 must appear"
    assert "1500" in combined, "total_km_7d=1500 must appear"
    assert "4" in combined, "unpaid_report_count=4 must appear"
```

- [ ] **Step 3: Run the bot overview test - expect it to fail first (before Task 5 changes)**

If you're applying tasks in order, Task 5 was already committed. Run:

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/telegram-bot
poetry run pytest tests/test_flows.py::test_overview_uses_system_admin_context -v 2>&1 | tail -20
```

Expected: `PASSED` (Task 5 already updated the format; the new fields are rendered).

- [ ] **Step 4: Run the full bot suite**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/telegram-bot
poetry run pytest -q 2>&1 | tail -20
```

Expected: all tests pass. Record count.

- [ ] **Step 5: Run ruff and mypy on telegram-bot**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course-FinalProject/Shepherd
uvx ruff check services/telegram-bot 2>&1
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/telegram-bot
poetry run mypy . 2>&1 | tail -10
```

Expected: clean.

- [ ] **Step 6: Commit bot test update**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
git add services/telegram-bot/tests/test_flows.py
git commit -m "$(cat <<'EOF'
test(telegram-bot): extend overview test with new metric fields

Updates test_overview_uses_system_admin_context to mock all new
SystemOverviewItem fields and assert they appear in the rendered
Telegram message (schema_name, customer_count, total_km_7d,
unpaid_report_count).
EOF
)"
```

---

### Task 7: Write the report and final verification

**Files:**
- Create: `/Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/.superpowers/sdd/task-overview-report.md`

- [ ] **Step 1: Run all verification commands and collect output**

```bash
# fleet-api sysadmin/overview focused
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run pytest tests/ -k "overview or sysadmin" -q 2>&1 | tail -20

# fleet-api full suite
poetry run pytest -q 2>&1 | tail -5

# telegram-bot full suite
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/telegram-bot
poetry run pytest -q 2>&1 | tail -5

# ruff
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
uvx ruff check services/fleet-api services/telegram-bot 2>&1

# mypy fleet-api
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/fleet-api
poetry run mypy . 2>&1 | tail -5

# mypy telegram-bot
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd/services/telegram-bot
poetry run mypy . 2>&1 | tail -5
```

- [ ] **Step 2: Write the report**

Write the report to `.superpowers/sdd/task-overview-report.md` covering:
- Per-schema approach (how `engine.connect()` + `schema_translate_map` was used)
- New fields added (list with descriptions)
- RED/GREEN evidence (copy the FAILED/PASSED lines from Step 1 of Task 1 and Step 3 of Task 3)
- All suite counts
- ruff status
- mypy status
- Commit SHAs

- [ ] **Step 3: Commit the report**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
git add .superpowers/sdd/task-overview-report.md
git commit -m "docs: add sysadmin overview enrichment task report"
```

---

## Self-Review

**Spec coverage check:**

- [x] `customer_count` - computed per-schema in repo, added to schema, rendered in bot
- [x] `accident_count` - computed per-schema in repo, added to schema, rendered in bot
- [x] `maintenance_due_count` - condition `current_km >= next_maintenance_km`, per-schema, rendered
- [x] `docs_expiring_count` - `insurance_valid_to <= today+30 OR license_valid_to <= today+30`, per-schema
- [x] `unpaid_report_count` - `status == 'unpaid'`, per-schema, rendered in bot
- [x] `total_km_7d` - latest `kpi_daily.total_km_7d` on main session (public), rendered
- [x] `is_active` - from `companies.is_active`, rendered in bot
- [x] `schema_name` - from `company_settings.schema_name` (fallback: shared), rendered in bot
- [x] `bot_user_count` - count `users` where `company_id=c.company_id` on main session (public)
- [x] Per-schema fix for existing fields (vehicle_count, driver_count, open_event_count)
- [x] `__pending__` sentinel handled (all tenant counts = 0)
- [x] Exclude internal companies - kept via existing `Company.is_internal.is_(False)` filter
- [x] RED failing test added before implementation
- [x] Bot rendering updated (texts.py + flows/sysadmin.py)
- [x] Bot rendering test extended
- [x] Verification commands specified

**Placeholder scan:** No TBD, TODO, or vague steps. All code blocks are complete.

**Type consistency:** `SystemOverviewItem` fields match the dict keys in `repo.system_overview`. Bot format keys (`{schema}`, `{active}`, `{customers}`, `{accidents}`, `{unpaid}`, `{maint_due}`, `{docs_exp}`, `{km_7d}`, `{bot_users}`) match the `.format()` kwargs in `_overview()`.

**One note on the `Session(bind=tconn)` pattern:** In SQLAlchemy 2.x, the `bind` kwarg on `Session.__init__` is removed in favor of `Session(bind=...)` being legacy. However, the existing codebase uses this pattern successfully in `find_enrollment_by_phone` (line 733: `with Session(bind=tconn) as s:`), so we follow the same established pattern.
