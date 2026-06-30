# Bot RTL Formatter + Drill-Down Overview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Shepherd Telegram bot's data presentation to be RTL-clean and professional: a shared `fmt.py` helper for LTR-isolation, and a drill-down overview (compact list -> company detail card).

**Architecture:** A new pure helper `app/fmt.py` wraps LTR content in Unicode LRI/PDI isolates and provides `kv`, `section`, `card`, `bool_chip` builders; `sysadmin._overview` splits into list + detail views connected by inline-keyboard drill-down; `router.route_decision` catches the dynamic `sa_ov_<uuid>` prefix; three existing screens (`attendance_admin`, `fleet_summary`, `my_vehicle`) adopt `fmt.val()`/`fmt.kv()` to fix number rendering. All flow logic is preserved; only presentation changes.

**Tech Stack:** Python 3.12, aiogram 3.x, pytest-asyncio, respx, mypy, ruff. No new dependencies.

## Global Constraints

- Service scope: `services/telegram-bot/` only. No changes to fleet-api or webui.
- `send()` uses `parse_mode="HTML"`. Telegram supports only `b/i/u/s/code/pre/a` tags - no `div`, no `dir` attribute.
- No new dependencies (no additions to `pyproject.toml`).
- TDD: write the failing test first, then the minimum implementation.
- Test runner: `cd services/telegram-bot && poetry run pytest -q` (must stay all green).
- Linter: `uvx ruff check services/telegram-bot` (zero errors).
- Type check: `cd services/telegram-bot && poetry run mypy .` (no new errors beyond baseline).
- `sa_ov_` (with trailing underscore) is the dynamic prefix. It does NOT match `sa_overview` (no underscore after `sa_ov`). Verify with `"sa_overview".startswith("sa_ov_")` == False.
- Do NOT run docker or restart anything. Do NOT change `attendance_csv.py`.
- Commit format: lowercase imperative subject <=72 chars, blank line, body wrapped 72 chars, NO `Co-Authored-By`.
- Pre-commit: update related docs in the same commit (check plans/ and README for impact).

---

## File Map

| Status | File | Role |
|--------|------|------|
| Create | `app/fmt.py` | Shared RTL-safe formatter (pure, no I/O) |
| Create | `tests/test_fmt.py` | Unit tests for fmt.py |
| Modify | `app/texts.py` | Add `SA_OVERVIEW_NOT_FOUND`, `SA_BACK_BTN`; remove dead `SA_OVERVIEW_CARD`, `SA_OVERVIEW_DEDICATED`, `SA_STATUS_*`, `SA_ATT_*`, `SA_DRIVE_*` |
| Modify | `app/keyboards.py` | Add `sa_back()` and `sa_overview_list()` builders |
| Modify | `app/flows/sysadmin.py` | Split `_overview` into list + detail; add `overview_detail` dispatch |
| Modify | `app/router.py` | Add `sa_ov_` prefix route before the `("menu", None)` fallback |
| Modify | `app/flows/attendance_admin.py` | Wrap times with `fmt.val()` |
| Modify | `app/flows/fleet_summary.py` | Replace local `val()` with `fmt.kv()` |
| Modify | `app/flows/my_vehicle.py` | Replace f-strings with `fmt.kv()` |
| Modify | `tests/test_flows.py` | Replace/extend sysadmin overview tests |

---

## Task 1: Create `app/fmt.py` with unit tests

**Files:**
- Create: `services/telegram-bot/app/fmt.py`
- Create: `services/telegram-bot/tests/test_fmt.py`

**Interfaces:**
- Produces:
  - `fmt.val(x: object) -> str` - wraps value in Unicode LRI/PDI
  - `fmt.kv(label: str, value: object) -> str` - `"label: ⁦value⁩"`
  - `fmt.section(title: str, lines: list[str]) -> str` - `"▸ title\n   line1\n   line2"`
  - `fmt.card(title: str, body: str) -> str` - `"<b>escaped_title</b>\nbody"`
  - `fmt.bool_chip(ok: bool, on: str, off: str) -> str` - `"✅ on"` or `"⛔️ off"`

- [ ] **Step 1: Write the failing tests**

```python
# services/telegram-bot/tests/test_fmt.py
"""Unit tests for app.fmt (RTL-safe formatter)."""

from __future__ import annotations

from app import fmt


def test_val_wraps_with_lri_pdi():
    result = fmt.val(5)
    assert result == "⁦5⁩"


def test_val_wraps_string():
    assert fmt.val("hello") == "⁦hello⁩"


def test_val_wraps_zero():
    assert fmt.val(0) == "⁦0⁩"


def test_kv_builds_label_colon_val():
    assert fmt.kv("count", 3) == "count: ⁦3⁩"


def test_kv_uses_val_for_value():
    result = fmt.kv("label", "text")
    assert result.startswith("label: ")
    assert "⁦text⁩" in result


def test_section_title_and_indented_lines():
    s = fmt.section("צי", ["line1", "line2"])
    assert s == "▸ צי\n   line1\n   line2"


def test_section_single_line():
    assert fmt.section("h", ["only"]) == "▸ h\n   only"


def test_card_bold_title_html_escaped():
    assert fmt.card("A & B", "body") == "<b>A &amp; B</b>\nbody"


def test_card_plain_title():
    assert fmt.card("Acme", "some body") == "<b>Acme</b>\nsome body"


def test_bool_chip_true():
    assert fmt.bool_chip(True, "on", "off") == "✅ on"


def test_bool_chip_false():
    assert fmt.bool_chip(False, "on", "off") == "⛔️ off"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd services/telegram-bot && poetry run pytest tests/test_fmt.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.fmt'` (or similar import error).

- [ ] **Step 3: Create `app/fmt.py`**

```python
# services/telegram-bot/app/fmt.py
"""RTL-safe Telegram message formatter (pure, no I/O).

Hebrew (RTL) text mixed with Latin/numbers causes Telegram to jumble the
order. Wrapping LTR content in Unicode LRI/PDI isolates (U+2066/U+2069)
fixes the rendering inside RTL text.

Telegram HTML accepts only b/i/u/s/code/pre/a - no div, no dir attribute.
"""

from __future__ import annotations

import html as _html

# Unicode LRI (Left-to-Right Isolate) U+2066 and PDI (Pop Directional Isolate) U+2069
_LRI = "⁦"
_PDI = "⁩"


def val(x: object) -> str:
    """Wrap a value in a Unicode LTR isolate so it renders correctly in RTL text."""
    return f"{_LRI}{x}{_PDI}"


def kv(label: str, value: object) -> str:
    """One metric line: 'label: ⁦value⁩'."""
    return f"{label}: {val(value)}"


def section(title: str, lines: list[str]) -> str:
    """A labeled block: '▸ title' then each line indented 3 spaces."""
    body = "\n".join(f"   {line}" for line in lines)
    return f"▸ {title}\n{body}"


def card(title: str, body: str) -> str:
    """Bold HTML title (html-escaped) followed by body."""
    return f"<b>{_html.escape(title)}</b>\n{body}"


def bool_chip(ok: bool, on: str, off: str) -> str:
    """'✅ on' if ok else '⛔️ off'."""
    return f"✅ {on}" if ok else f"⛔️ {off}"
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd services/telegram-bot && poetry run pytest tests/test_fmt.py -v
```
Expected: 11 tests pass.

- [ ] **Step 5: Commit**

```bash
cd services/telegram-bot
git add app/fmt.py tests/test_fmt.py
git commit -m "add RTL-safe fmt helper with LRI/PDI isolation

val() wraps any LTR value in Unicode LRI/PDI so numbers and Latin
text render correctly inside Hebrew (RTL) Telegram messages.
kv, section, card, bool_chip build common message constructs.
Pure module; no I/O. 11 unit tests."
```

---

## Task 2: Update `texts.py` and `keyboards.py` for new SA constants

**Files:**
- Modify: `services/telegram-bot/app/texts.py`
- Modify: `services/telegram-bot/app/keyboards.py`

**Interfaces:**
- Consumes: `fmt.py` from Task 1 (keyboards.py does NOT import fmt; only texts is touched here)
- Produces:
  - `texts.SA_OVERVIEW_NOT_FOUND` - shown when `sa_ov_<id>` points to unknown company
  - `texts.SA_BACK_BTN` - "⬅️ חזרה" button label
  - `keyboards.sa_back() -> InlineKeyboardMarkup` - single-button back keyboard
  - `keyboards.sa_overview_list(companies: list[dict]) -> InlineKeyboardMarkup` - one `🏢 Name` button per company

- [ ] **Step 1: Update `app/texts.py`**

Remove the block of SA overview constants that are only used by the old `_overview` wall-of-text, and add the two new ones. The removed constants are: `SA_OVERVIEW_CARD`, `SA_OVERVIEW_DEDICATED`, `SA_STATUS_ACTIVE`, `SA_STATUS_INACTIVE`, `SA_ATT_ON`, `SA_ATT_OFF`, `SA_DRIVE_ON`, `SA_DRIVE_OFF`.

Find the relevant block in `texts.py` (lines 56-75 approximately):

```python
# SA_OVERVIEW_TITLE and SA_OVERVIEW_EMPTY stay as-is.
# Remove everything from "# Status chips" down through SA_OVERVIEW_CARD.
# Add new constants after SA_OVERVIEW_EMPTY:
SA_OVERVIEW_NOT_FOUND = "❌ החברה לא נמצאה."
SA_BACK_BTN = "⬅️ חזרה"
```

The full updated SA overview section in `texts.py` (replace the block from `# Status chips` through the end of `SA_OVERVIEW_CARD`):

Old block to remove (lines after `SA_OVERVIEW_EMPTY`):
```python
# Status chips (joined with ' · ' on the card's status line).
SA_STATUS_ACTIVE = "✅ פעיל"
SA_STATUS_INACTIVE = "⛔️ לא פעיל"
SA_ATT_ON = "נוכחות מופעלת"
SA_ATT_OFF = "נוכחות כבויה"
SA_DRIVE_ON = "Drive מוגדר"
SA_DRIVE_OFF = "Drive לא מוגדר"
# Shown only for a dedicated tenant (the shared "public" schema is the default - hidden).
SA_OVERVIEW_DEDICATED = "🔒 מתחם ייעודי: {schema}\n"
SA_OVERVIEW_CARD = (
    "🏢 <b>{name}</b>\n"
    "{status}\n"
    "{schema}"
    "🚗 רכבים {vehicles}   ·   👷 נהגים {drivers}   ·   👥 לקוחות {customers}\n"
    "⚠️ אירועים פתוחים {events}   ·   💥 תאונות {accidents}\n"
    "🎫 דוחות לא שולמו {unpaid}   ·   🔧 טיפולים נדרשים {maint_due}\n"
    "📄 מסמכים לחידוש {docs_exp}   ·   📈 ק\"מ השבוע {km_7d}   ·   🤖 משתמשי בוט {bot_users}"
)
```

New lines to insert in their place (after `SA_OVERVIEW_EMPTY`):
```python
# Drill-down detail view
SA_OVERVIEW_NOT_FOUND = "❌ החברה לא נמצאה."
SA_BACK_BTN = "⬅️ חזרה"
```

- [ ] **Step 2: Update `app/keyboards.py`**

Add two new functions at the bottom of the SA keyboard section (after `sa_live_role_pick`):

```python
def sa_back() -> InlineKeyboardMarkup:
    """Single '⬅️ חזרה' button returning to the overview list."""
    return _inline([[(texts.SA_BACK_BTN, "sa_overview")]])


def sa_overview_list(companies: list[dict]) -> InlineKeyboardMarkup:
    """One '🏢 Name' button per company for the overview drill-down."""
    return _inline([
        [(f"🏢 {c['name']}", f"sa_ov_{c['company_id']}")] for c in companies
    ])
```

Insert these between `sa_live_role_pick` and `sa_exit` (or after `sa_exit`). The exact placement does not matter; after `sa_exit` is fine.

- [ ] **Step 3: Run the existing test suite to confirm nothing broke**

```bash
cd services/telegram-bot && poetry run pytest -q
```
Expected: all existing tests pass. If any test references the removed `texts.SA_OVERVIEW_CARD` or `texts.SA_OVERVIEW_DEDICATED`, it will fail - note those and handle them in Task 4.

- [ ] **Step 4: Commit**

```bash
git add app/texts.py app/keyboards.py
git commit -m "add SA overview drill-down texts and keyboard builders

Remove dead SA_OVERVIEW_CARD/DEDICATED/status-chip constants
(replaced in Task 3 by fmt-based rendering). Add
SA_OVERVIEW_NOT_FOUND, SA_BACK_BTN, keyboards.sa_back(),
and keyboards.sa_overview_list()."
```

---

## Task 3: Rework sysadmin overview + wire router (TDD)

**Files:**
- Modify: `services/telegram-bot/app/flows/sysadmin.py`
- Modify: `services/telegram-bot/app/router.py`
- Modify: `services/telegram-bot/tests/test_flows.py`

**Interfaces:**
- Consumes: `fmt.py` (Task 1), `texts.SA_BACK_BTN`/`SA_OVERVIEW_NOT_FOUND` (Task 2), `keyboards.sa_back()`/`sa_overview_list()` (Task 2)
- Produces:
  - `sysadmin(ctx, route="overview")` - compact list view with inline keyboard
  - `sysadmin(ctx, route="overview_detail")` - sectioned detail card with back button
  - `route_decision` returns `("sysadmin", "overview_detail")` when `callback_data.startswith("sa_ov_")`

Important: `"sa_overview".startswith("sa_ov_")` is False (no underscore after `sa_ov` in `sa_overview`) - verified in Python: the 7th character of `sa_overview` is `e`, not `_`. So checking `startswith("sa_ov_")` safely distinguishes `sa_ov_<uuid>` from `sa_overview`.

The company data shape used in overview tests (add as module-level constants in the test module):
```python
GLOBEX_CO = "00000000-0000-0000-0000-0000000000c0"  # = COMPANY_ID from conftest

ACME_DATA = {
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

GLOBEX_DATA = {
    "company_id": GLOBEX_CO,
    "name": "Globex",
    "vehicle_count": 2,
    "driver_count": 2,
    "open_event_count": 0,
    "attendance_enabled": False,
    "gdrive_configured": True,
    "customer_count": 1,
    "accident_count": 0,
    "maintenance_due_count": 0,
    "docs_expiring_count": 0,
    "unpaid_report_count": 0,
    "total_km_7d": 0,
    "is_active": True,
    "schema_name": "public",
    "bot_user_count": 0,
}
```

- [ ] **Step 1: Write the failing tests (replace/extend existing overview test)**

Replace `test_overview_uses_system_admin_context` in `tests/test_flows.py` with the following four tests. Also add `GLOBEX_CO`, `ACME_DATA`, `GLOBEX_DATA` constants near the top of the `# Feature 6` section (below the `OPERATOR_ID`/`LIVE_CO`/`PLAYGROUND` constants).

```python
GLOBEX_CO = "00000000-0000-0000-0000-0000000000c0"

ACME_DATA: dict = {
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

GLOBEX_DATA: dict = {
    "company_id": GLOBEX_CO,
    "name": "Globex",
    "vehicle_count": 2,
    "driver_count": 2,
    "open_event_count": 0,
    "attendance_enabled": False,
    "gdrive_configured": True,
    "customer_count": 1,
    "accident_count": 0,
    "maintenance_due_count": 0,
    "docs_expiring_count": 0,
    "unpaid_report_count": 0,
    "total_km_7d": 0,
    "is_active": True,
    "schema_name": "public",
    "bot_user_count": 0,
}


async def test_overview_uses_system_admin_context(store, bot, fleet, mock_api):
    """List view: caller-context is company-less admin; bold names; keyboard per company."""
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    route = mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(200, json={"companies": [ACME_DATA, GLOBEX_DATA]})
    )
    await dispatch(
        {"chat_id": 61, "sender_id": 61, "is_callback": True, "callback_data": "sa_overview"},
        bot, fleet,
    )
    # API is called with company-less system-admin context
    assert caller_ctx(route) == {"role": "admin"}

    combined = "\n".join(sent_texts(bot))
    # Both company names appear bold in the list view
    assert "<b>Acme</b>" in combined
    assert "<b>Globex</b>" in combined

    # Inline keyboard has one sa_ov_<id> button per company
    cbs = menu_callbacks(bot)
    assert f"sa_ov_{LIVE_CO}" in cbs
    assert f"sa_ov_{GLOBEX_CO}" in cbs


async def test_overview_detail_card(store, bot, fleet, mock_api):
    """Detail view: tapping sa_ov_<id> sends sectioned card with all metrics + back btn."""
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(200, json={"companies": [ACME_DATA, GLOBEX_DATA]})
    )
    await dispatch(
        {"chat_id": 62, "sender_id": 62, "is_callback": True,
         "callback_data": f"sa_ov_{LIVE_CO}"},
        bot, fleet,
    )
    combined = "\n".join(sent_texts(bot))

    # Company name in title
    assert "Acme" in combined

    # All key metrics present
    assert "7" in combined    # customer_count
    assert "1500" in combined  # total_km_7d
    assert "4" in combined    # unpaid_report_count

    # Section headers
    assert "צי" in combined
    assert "סיכונים" in combined
    assert "תחזוקה" in combined
    assert "פלטפורמה" in combined

    # Hebrew labels
    assert "לקוחות" in combined
    assert "דוחות לא שולמו" in combined
    assert "טיפולים נדרשים" in combined
    assert "מסמכים לחידוש" in combined

    # Back button returns to overview list
    cbs = menu_callbacks(bot)
    assert "sa_overview" in cbs


async def test_overview_detail_dedicated_schema_shown(store, bot, fleet, mock_api):
    """Detail view: dedicated-tenant schema is shown for Acme (co_acme)."""
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(200, json={"companies": [ACME_DATA]})
    )
    await dispatch(
        {"chat_id": 63, "sender_id": 63, "is_callback": True,
         "callback_data": f"sa_ov_{LIVE_CO}"},
        bot, fleet,
    )
    combined = "\n".join(sent_texts(bot))
    assert "מתחם ייעודי" in combined
    assert "co_acme" in combined


async def test_overview_detail_public_schema_hidden(store, bot, fleet, mock_api):
    """Detail view: 'public' schema company does not show dedicated-schema line."""
    mock_api.get(f"{FLEET}/whoami").mock(return_value=sysadmin_whoami())
    mock_api.get(f"{FLEET}/sysadmin/overview").mock(
        return_value=httpx.Response(200, json={"companies": [GLOBEX_DATA]})
    )
    await dispatch(
        {"chat_id": 64, "sender_id": 64, "is_callback": True,
         "callback_data": f"sa_ov_{GLOBEX_CO}"},
        bot, fleet,
    )
    combined = "\n".join(sent_texts(bot))
    assert "מתחם ייעודי" not in combined
    assert "public" not in combined
```

- [ ] **Step 2: Run tests to confirm the new tests fail**

```bash
cd services/telegram-bot && poetry run pytest tests/test_flows.py::test_overview_detail_card -v
```
Expected: FAIL (route_decision falls through to `("menu", None)` for `sa_ov_<uuid>`).

- [ ] **Step 3: Update `app/router.py` - add the `sa_ov_` prefix route**

In `route_decision`, add the prefix check AFTER the `CALLBACK_MAP` lookup and BEFORE the `("menu", None)` fallback:

```python
    if ctx.is_callback and ctx.callback_data in CALLBACK_MAP:
        return CALLBACK_MAP[ctx.callback_data]

    # Dynamic prefix: sa_ov_<company_id> -> sysadmin overview_detail.
    # "sa_overview".startswith("sa_ov_") is False (e vs _), so no collision.
    if ctx.is_callback and ctx.callback_data and ctx.callback_data.startswith("sa_ov_"):
        return ("sysadmin", "overview_detail")

    return ("menu", None)
```

The full updated `route_decision` tail (only the last 8 lines change):

```python
    if ctx.is_callback and ctx.callback_data in CALLBACK_MAP:
        return CALLBACK_MAP[ctx.callback_data]

    # Dynamic prefix: sa_ov_<company_id> -> sysadmin overview_detail.
    # Note: "sa_overview".startswith("sa_ov_") is False, so the CALLBACK_MAP
    # entry above handles sa_overview correctly before we reach this branch.
    if ctx.is_callback and ctx.callback_data and ctx.callback_data.startswith("sa_ov_"):
        return ("sysadmin", "overview_detail")

    return ("menu", None)
```

- [ ] **Step 4: Update `app/flows/sysadmin.py` - rework `_overview` and add `_overview_detail`**

Add import for `fmt` at the top of the imports block:

```python
from app import commands, fmt, keyboards, sessions, texts
```

Replace the entire `_overview` function and add `_overview_detail`:

```python
async def _overview(ctx: Ctx) -> None:
    resp = await ctx.fleet.get("/sysadmin/overview")
    companies = resp.json().get("companies", []) if resp.status_code == 200 else []
    if not companies:
        await send(ctx, f"{texts.SA_OVERVIEW_TITLE}\n\n{texts.SA_OVERVIEW_EMPTY}")
        return
    blocks = []
    for c in companies:
        status_chip = fmt.bool_chip(c.get("is_active", True), "פעיל", "לא פעיל")
        headline = (
            f"⚠️ {fmt.val(c['open_event_count'])} פתוחים · "
            f"🚗 {fmt.val(c['vehicle_count'])}"
        )
        blocks.append(fmt.card(c["name"], f"{status_chip}\n{headline}"))
    text = f"{texts.SA_OVERVIEW_TITLE}\n\n" + "\n\n".join(blocks)
    await send(ctx, text, reply_markup=keyboards.sa_overview_list(companies))


async def _overview_detail(ctx: Ctx) -> None:
    assert ctx.callback_data is not None
    company_id = ctx.callback_data[len("sa_ov_"):]
    resp = await ctx.fleet.get("/sysadmin/overview")
    companies = resp.json().get("companies", []) if resp.status_code == 200 else []
    company = next((c for c in companies if c["company_id"] == company_id), None)
    if company is None:
        await send(ctx, texts.SA_OVERVIEW_NOT_FOUND, reply_markup=keyboards.sa_back())
        return
    c = company
    status_line = "  ·  ".join([
        fmt.bool_chip(c.get("is_active", True), "פעיל", "לא פעיל"),
        fmt.bool_chip(c["attendance_enabled"], "נוכחות", "נוכחות כבויה"),
        fmt.bool_chip(c["gdrive_configured"], "Drive", "ללא Drive"),
    ])
    fleet_section = fmt.section("צי", [
        fmt.kv("🚗 רכבים", c["vehicle_count"]),
        fmt.kv("👷 נהגים", c["driver_count"]),
        fmt.kv("👥 לקוחות", c.get("customer_count", 0)),
    ])
    risk_section = fmt.section("סיכונים", [
        fmt.kv("⚠️ אירועים פתוחים", c["open_event_count"]),
        fmt.kv("💥 תאונות", c.get("accident_count", 0)),
        fmt.kv("🎫 דוחות לא שולמו", c.get("unpaid_report_count", 0)),
    ])
    maint_section = fmt.section("תחזוקה ומסמכים", [
        fmt.kv("🔧 טיפולים נדרשים", c.get("maintenance_due_count", 0)),
        fmt.kv("📄 מסמכים לחידוש", c.get("docs_expiring_count", 0)),
        fmt.kv('📈 ק"מ השבוע', c.get("total_km_7d", 0)),
    ])
    platform_lines = [fmt.kv("🤖 משתמשי בוט", c.get("bot_user_count", 0))]
    schema_name = c.get("schema_name") or ""
    if schema_name and schema_name != "public":
        platform_lines.append(fmt.kv("🔒 מתחם ייעודי", html.escape(schema_name)))
    platform_section = fmt.section("פלטפורמה", platform_lines)
    body = "\n\n".join([status_line, fleet_section, risk_section, maint_section, platform_section])
    await send(ctx, fmt.card(f"🏢 {c['name']}", body), reply_markup=keyboards.sa_back())
```

Update the `sysadmin` dispatcher to handle `overview_detail`:

```python
async def sysadmin(ctx: Ctx, route: str | None) -> None:
    if route == "exit":
        await _exit(ctx)
        return
    if not ctx.is_system_admin:
        await send(ctx, texts.ACCESS_DENIED)
        return

    if route == "overview":
        await _overview(ctx)
    elif route == "overview_detail":
        await _overview_detail(ctx)
    elif route == "debug_menu":
        await send(ctx, texts.SA_DEBUG_PICK, reply_markup=keyboards.sa_debug_pick())
    elif route == "debug_driver":
        await _debug_driver(ctx)
    elif route == "debug_admin":
        await _debug_admin(ctx)
    elif route == "live_start":
        await _live_start(ctx)
    elif route == "live_pick_company":
        await _live_pick_company(ctx)
    elif route == "live_pick_role":
        await _live_pick_role(ctx)
    elif route == "live_pick_driver":
        await _live_pick_driver(ctx)
    elif route == "live_pick_admin":
        await _live_pick_admin(ctx)
```

- [ ] **Step 5: Run all tests**

```bash
cd services/telegram-bot && poetry run pytest -q
```
Expected: all green. Count should increase by 3 (the 3 new tests added). The replaced test (`test_overview_uses_system_admin_context`) is updated in place, so the count net change is +3.

- [ ] **Step 6: Run ruff and mypy**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
uvx ruff check services/telegram-bot
cd services/telegram-bot && poetry run mypy .
```
Expected: zero ruff errors, mypy clean (no new errors).

- [ ] **Step 7: Commit**

```bash
git add app/flows/sysadmin.py app/router.py tests/test_flows.py
git commit -m "drill-down overview: list -> company detail card

_overview shows a compact bold-name + status-chip card per company
with an inline keyboard (sa_ov_<uuid> per company). Tapping drills
into _overview_detail: a sectioned card (צי/סיכונים/תחזוקה/פלטפורמה)
with a back button. router.route_decision catches sa_ov_ prefix
before the menu fallback. Tests: list keyboard, detail metrics,
schema visibility."
```

---

## Task 4: Reformat `attendance_admin`, `fleet_summary`, `my_vehicle` with `fmt`

**Files:**
- Modify: `services/telegram-bot/app/flows/attendance_admin.py`
- Modify: `services/telegram-bot/app/flows/fleet_summary.py`
- Modify: `services/telegram-bot/app/flows/my_vehicle.py`

**Interfaces:**
- Consumes: `fmt.val()`, `fmt.kv()` from Task 1

The existing e2e tests already verify the data appears (`"1200" in summary`, `"Toyota" in card`, etc.). Since `"1200"` is a substring of `"⁦1200⁩"`, these tests remain green without changes.

- [ ] **Step 1: Update `app/flows/attendance_admin.py`**

Add `from app import fmt` import. Replace the `lines.append(...)` in the loop:

Old:
```python
lines.append(f"• {name}: {clock_in} - {clock_out} ({status})")
```

New:
```python
lines.append(
    f"• {name}: {fmt.val(clock_in)} - {fmt.val(clock_out)} ({status})"
)
```

The full updated file:

```python
"""Flow 5.1 - Today's attendance (admin, single-shot)."""

from __future__ import annotations

from app import fmt, texts
from app.context import Ctx
from app.tg import send

_STATUS_HE = {"present": "נוכח", "late": "איחור", "leave": "חופשה", "absent": "נעדר"}


async def attendance_admin(ctx: Ctx, route: str | None) -> None:
    resp = await ctx.fleet.get("/attendance/today")
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        await send(ctx, texts.ATTENDANCE_EMPTY)
        return
    lines = [texts.ATTENDANCE_TODAY_TITLE, ""]
    for r in rows:
        name = r.get("driver_name") or str(r.get("driver_id"))
        clock_in = r.get("clock_in") or "-"
        clock_out = r.get("clock_out") or "-"
        status = _STATUS_HE.get(r.get("status"), r.get("status") or "")
        lines.append(
            f"• {name}: {fmt.val(clock_in)} - {fmt.val(clock_out)} ({status})"
        )
    await send(ctx, "\n".join(lines))
```

- [ ] **Step 2: Update `app/flows/fleet_summary.py`**

Add `from app import fmt` import. Replace the local `def val(key)` helper and the f-string lines with `fmt.kv()`:

```python
"""Flow 5.3 - Fleet summary (admin, single-shot) from the latest KPI snapshot."""

from __future__ import annotations

from app import fmt, texts
from app.context import Ctx
from app.tg import send


async def fleet_summary(ctx: Ctx, route: str | None) -> None:
    resp = await ctx.fleet.get("/kpi/daily", params={"limit": 1})
    rows = resp.json() if resp.status_code == 200 else []
    if not rows:
        await send(ctx, f"{texts.FLEET_SUMMARY_TITLE}\n\nאין נתונים זמינים.")
        return
    k = rows[0]

    def _v(key: str) -> object:
        v = k.get(key)
        return "-" if v is None else v

    lines = [
        texts.FLEET_SUMMARY_TITLE,
        "",
        fmt.kv('ק"מ ב-7 ימים', _v("total_km_7d")),
        fmt.kv('ממוצע ק"מ לנהג', _v("avg_km_per_driver_7d")),
        fmt.kv("מסמכים שעומדים לפוג", _v("docs_expiring_count")),
    ]
    await send(ctx, "\n".join(lines))
```

- [ ] **Step 3: Update `app/flows/my_vehicle.py`**

Add `from app import fmt` import. Replace the f-string lines with `fmt.kv()`:

```python
"""Flow 4.6 - My Vehicle (single-shot card)."""

from __future__ import annotations

from app import fmt, texts
from app.context import Ctx
from app.tg import send


async def my_vehicle(ctx: Ctx, route: str | None) -> None:
    vehicle = await ctx.fleet.driver_vehicle(ctx.driver_id)
    if vehicle is None:
        await send(ctx, texts.NO_VEHICLE)
        return
    km = vehicle.get("current_km")
    km = "-" if km is None else km
    lines = [
        texts.MY_VEHICLE_TITLE,
        fmt.kv("יצרן", vehicle.get("vendor") or "-"),
        fmt.kv("דגם", vehicle.get("model") or "-"),
        fmt.kv("לוחית", vehicle.get("licensing_plate") or "-"),
        fmt.kv("סוג", vehicle.get("vehicle_type") or "-"),
        fmt.kv('ק"מ נוכחי', km),
    ]
    await send(ctx, "\n".join(lines))
```

- [ ] **Step 4: Run all tests**

```bash
cd services/telegram-bot && poetry run pytest -q
```
Expected: all green. The e2e tests `test_admin_fleet_summary` checks `"1200" in summary` - this passes because `"1200"` is a substring of `"⁦1200⁩"`. `test_driver_my_vehicle_card` checks `"Toyota" in card` and `"42000" in card` - both pass.

- [ ] **Step 5: Run ruff and mypy**

```bash
cd /Users/yehonatandahan/Documents/Projects/AI-Course/FinalProject/Shepherd
uvx ruff check services/telegram-bot
cd services/telegram-bot && poetry run mypy .
```
Expected: zero ruff errors, mypy clean.

- [ ] **Step 6: Commit**

```bash
git add app/flows/attendance_admin.py app/flows/fleet_summary.py app/flows/my_vehicle.py
git commit -m "apply fmt LTR-isolation to attendance, fleet-summary, my-vehicle

Clock times, km values, and Latin vehicle data (vendor, plate, model)
are now wrapped with fmt.val()/fmt.kv() so they render correctly
inside Hebrew RTL text in Telegram."
```

---

## Task 5: Write the final report

**Files:**
- Create: `.superpowers/sdd/task-botui-report.md`

- [ ] **Step 1: Write the report**

Write a report to `.superpowers/sdd/task-botui-report.md` covering:
- The `fmt.py` API (all 5 functions with their signatures and purpose)
- The drill-down flow (list view -> detail card) and router wiring
- Screens reformatted (attendance_admin, fleet_summary, my_vehicle) and what changed
- Test count, ruff status, mypy status
- A sample of the rendered detail card text for Acme

- [ ] **Step 2: Commit the report**

```bash
git add .superpowers/sdd/task-botui-report.md
git commit -m "add botui redesign report to .superpowers/sdd"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| `fmt.val()` wraps in LRI/PDI | Task 1 |
| `fmt.kv()`, `fmt.section()`, `fmt.card()`, `fmt.bool_chip()` | Task 1 |
| Unit tests for all fmt functions | Task 1 |
| List view: compact card per company with inline keyboard | Task 3 |
| Detail view: sectioned card with back button | Task 3 |
| `sa_ov_` prefix route in router | Task 3 |
| `sa_overview` still maps via CALLBACK_MAP (no collision) | Task 3 |
| Reformat `attendance_admin.py` | Task 4 |
| Reformat `fleet_summary.py` | Task 4 |
| Reformat `my_vehicle.py` | Task 4 |
| Tests: list view keyboard, detail card metrics, schema visibility | Task 3 |
| All existing tests green | Task 3, 4 |
| Ruff + mypy clean | Task 3, 4 |
| Final report at `.superpowers/sdd/task-botui-report.md` | Task 5 |
| No changes to `attendance_csv.py` | (verified - not in file map) |
| No docker/deploy | (constraint) |

### Placeholder check

No "TBD", "TODO", or vague steps - all code is provided in full.

### Type consistency check

- `fmt.val(x: object) -> str` used as `fmt.val(clock_in)`, `fmt.val(5)` etc. - consistent.
- `fmt.kv(label: str, value: object) -> str` used as `fmt.kv("יצרן", vehicle.get("vendor") or "-")` - consistent.
- `fmt.section(title: str, lines: list[str]) -> str` called with list of `fmt.kv(...)` results - consistent.
- `fmt.card(title: str, body: str) -> str` called in `_overview_detail` and list view - consistent.
- `keyboards.sa_back()` returns `InlineKeyboardMarkup` - consistent with `send(ctx, text, reply_markup=keyboards.sa_back())`.
- `keyboards.sa_overview_list(companies: list[dict])` - `companies` is `list[dict]`, which matches `resp.json().get("companies", [])` - consistent.
- `sysadmin(ctx, route="overview_detail")` dispatched by `route_decision` returning `("sysadmin", "overview_detail")` - consistent with `FEATURES["sysadmin"]` in `flows/__init__.py`.
