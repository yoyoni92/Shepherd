"""Cross-system integration harness.

Drives the *real* telegram-bot code in-process (the real aiogram dispatcher in
`app.main`, the real `app.sessions` Postgres pool, the real `app.fleet` HTTP client)
against the **live compose stack** - Fleet API on :8000 and Postgres on :5432. Only the
genuinely-external boundaries are mocked: Telegram itself (at the aiogram session layer,
via `tests/sim.Recorder`) and the third-party LLM/Drive calls. Everything the bot does to
Fleet API and Postgres is real, and the tests assert the real rows that result.

Requires the stack to be up (`make up`); if Fleet API isn't reachable the whole suite is
skipped with a clear reason.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import psycopg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_DIR = REPO_ROOT / "services" / "telegram-bot"

FLEET_URL = "http://localhost:8000"


def _load_dotenv() -> dict[str, str]:
    env: dict[str, str] = {}
    path = REPO_ROOT / ".env"
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env


_ENV = _load_dotenv()
PG_USER = _ENV.get("POSTGRES_USER", "shepherd")
PG_PASSWORD = _ENV.get("POSTGRES_PASSWORD", "shepherd")
PG_DB = _ENV.get("POSTGRES_DB", "shepherd")
INTERNAL_TOKEN = _ENV.get("INTERNAL_SERVICE_TOKEN", "change-me")
PG_DSN = f"postgresql://{PG_USER}:{PG_PASSWORD}@localhost:5432/{PG_DB}"
# The seeded Default Company's schema (config.example.toml maps default -> co_default).
# The harness's direct tenant-table queries route here; control-plane tables (bot_sessions,
# users, bot_authorizations) fall back to public.
DEFAULT_SCHEMA = "co_default"

# Point the bot's settings at the live stack BEFORE importing any app.* module
# (pydantic reads the environment at import time).
os.environ["FLEET_API_URL"] = FLEET_URL
os.environ["INTERNAL_SERVICE_TOKEN"] = INTERNAL_TOKEN
os.environ["DATABASE_URL"] = f"postgresql+psycopg://{PG_USER}:{PG_PASSWORD}@localhost:5432/{PG_DB}"
os.environ.setdefault("TELEGRAM_BOT_TOKEN", _ENV.get("TELEGRAM_BOT_TOKEN", "123456:dummy"))

# The bot package + its test-only Telegram simulator (single source of truth).
sys.path.insert(0, str(BOT_DIR))
sys.path.insert(0, str(BOT_DIR / "tests"))

from aiogram import Bot  # noqa: E402
from app import main, sessions, storage, stt, vision  # noqa: E402
from app.fleet import FleetClient  # noqa: E402
from identities import (  # noqa: E402
    ADMIN_CHAT,
    ADMIN_CONTACT,
    ADMIN_PHONE,
    AUTHORIZATION_ID,
    COMPANY_ID,
    CUSTOMER_ID,
    DRIVER_CHAT,
    DRIVER_CONTACT,
    DRIVER_ID,
    DRIVER_PHONE,
    MAINTENANCE_TYPE_ID,
    MAINTENANCE_TYPE_NAME,
    PLATE,
    SEED_CURRENT_KM,
    SEED_NEXT_MAINTENANCE_KM,
    UNKNOWN_CHAT,
    VEHICLE_ID,
)
from sim import TOKEN as TG_TOKEN  # noqa: E402
from sim import Recorder, TelegramSim  # noqa: E402

_TEST_CHATS = (DRIVER_CHAT, ADMIN_CHAT, UNKNOWN_CHAT)


# --------------------------------------------------------------------------- stack gate


_STACK_UP: bool | None = None


def _stack_up() -> bool:
    global _STACK_UP
    if _STACK_UP is None:
        try:
            _STACK_UP = httpx.get(f"{FLEET_URL}/health", timeout=3).status_code == 200
        except Exception:
            _STACK_UP = False
    return _STACK_UP


@pytest.fixture(autouse=True)
def require_stack():
    if not _stack_up():
        pytest.skip("compose stack not reachable on :8000 - run `make up` first")


# --------------------------------------------------------------------------- seeding


def _connect() -> psycopg.Connection:
    conn = psycopg.connect(PG_DSN, autocommit=True)
    # Schema-per-tenant: tenant tables live in DEFAULT_SCHEMA, public holds control-plane.
    conn.execute(f'SET search_path TO "{DEFAULT_SCHEMA}", public')
    return conn


def _delete_derived(cur) -> None:
    """Remove everything the bot could have written for the seeded driver/vehicle/chats."""
    cur.execute("DELETE FROM bot_sessions WHERE chat_id = ANY(%s)", (list(_TEST_CHATS),))
    cur.execute("DELETE FROM users WHERE telegram_chat_id = ANY(%s)", (list(_TEST_CHATS),))
    cur.execute("DELETE FROM attendance_records WHERE driver_id = %s", (DRIVER_ID,))
    cur.execute("DELETE FROM events WHERE vehicle_id = %s", (VEHICLE_ID,))
    cur.execute(
        "DELETE FROM accident_attachments WHERE accident_id IN "
        "(SELECT accident_id FROM accidents WHERE vehicle_id = %s)",
        (VEHICLE_ID,),
    )
    cur.execute("DELETE FROM accidents WHERE vehicle_id = %s", (VEHICLE_ID,))
    cur.execute("DELETE FROM vehicle_care WHERE vehicle_id = %s", (VEHICLE_ID,))


@pytest.fixture(scope="session", autouse=True)
def seed_fleet():
    """Insert a self-contained fleet graph for the suite; tear it down at the end."""
    if not _stack_up():
        yield
        return
    conn = _connect()
    cur = conn.cursor()
    _delete_derived(cur)
    cur.execute("DELETE FROM vehicles WHERE vehicle_id = %s", (VEHICLE_ID,))
    cur.execute("DELETE FROM drivers WHERE driver_id = %s", (DRIVER_ID,))
    cur.execute("DELETE FROM customers WHERE customer_id = %s", (CUSTOMER_ID,))
    cur.execute("DELETE FROM maintenance_types WHERE id = %s", (MAINTENANCE_TYPE_ID,))
    cur.execute("DELETE FROM bot_authorizations WHERE id = %s", (AUTHORIZATION_ID,))

    cur.execute(
        "INSERT INTO customers (customer_id, company_id, full_name) VALUES (%s, %s, %s)",
        (CUSTOMER_ID, COMPANY_ID, "E2E Customer"),
    )
    cur.execute(
        "INSERT INTO drivers (driver_id, company_id, full_name, phone_number, status) "
        "VALUES (%s, %s, %s, %s, 'active')",
        (DRIVER_ID, COMPANY_ID, "E2E Driver", DRIVER_PHONE),
    )
    cur.execute(
        "INSERT INTO maintenance_types (id, company_id, name, interval_km, steps) "
        "VALUES (%s, %s, %s, %s, %s)",
        (MAINTENANCE_TYPE_ID, COMPANY_ID, MAINTENANCE_TYPE_NAME, 10000, '["A", "B"]'),
    )
    cur.execute(
        "INSERT INTO vehicles (vehicle_id, company_id, licensing_plate, driver_id, customer_id, "
        "current_km, next_maintenance_km, vendor, model, vehicle_type) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'car')",
        (
            VEHICLE_ID,
            COMPANY_ID,
            PLATE,
            DRIVER_ID,
            CUSTOMER_ID,
            SEED_CURRENT_KM,
            SEED_NEXT_MAINTENANCE_KM,
            "Toyota",
            "Corolla",
        ),
    )
    cur.execute(
        "INSERT INTO bot_authorizations (id, company_id, phone_number, role) "
        "VALUES (%s, %s, %s, 'admin')",
        (AUTHORIZATION_ID, COMPANY_ID, ADMIN_PHONE),
    )
    # The suite exercises the attendance flows, so turn the feature on for its company
    # (the seeded Default Company ships with it off). company_settings is a public table.
    cur.execute(
        "UPDATE company_settings SET feature_flags = feature_flags || '{\"attendance\": true}'::jsonb "
        "WHERE company_id = %s",
        (COMPANY_ID,),
    )
    conn.close()

    yield

    conn = _connect()
    cur = conn.cursor()
    _delete_derived(cur)
    cur.execute("DELETE FROM vehicles WHERE vehicle_id = %s", (VEHICLE_ID,))
    cur.execute("DELETE FROM drivers WHERE driver_id = %s", (DRIVER_ID,))
    cur.execute("DELETE FROM customers WHERE customer_id = %s", (CUSTOMER_ID,))
    cur.execute("DELETE FROM maintenance_types WHERE id = %s", (MAINTENANCE_TYPE_ID,))
    cur.execute("DELETE FROM bot_authorizations WHERE id = %s", (AUTHORIZATION_ID,))
    conn.close()


@pytest.fixture(autouse=True)
def reset_state(require_stack, seed_fleet):
    """Per-test clean slate: drop derived rows and restore the seeded driver/vehicle."""
    conn = _connect()
    cur = conn.cursor()
    _delete_derived(cur)
    cur.execute(
        "UPDATE drivers SET phone_number = %s, license_number = NULL, "
        "license_valid_to = NULL, status = 'active' WHERE driver_id = %s",
        (DRIVER_PHONE, DRIVER_ID),
    )
    cur.execute(
        "UPDATE vehicles SET insurance_valid_to = NULL, license_valid_to = NULL, "
        "current_km = %s, next_maintenance_km = %s WHERE vehicle_id = %s",
        (SEED_CURRENT_KM, SEED_NEXT_MAINTENANCE_KM, VEHICLE_ID),
    )
    conn.close()
    yield


# --------------------------------------------------------------------------- bot wiring


@pytest.fixture
def db():
    conn = _connect()
    yield conn
    conn.close()


@pytest.fixture
def rec() -> Recorder:
    return Recorder()


@pytest.fixture
async def bot_pool():
    await sessions.open_pool()
    yield
    await sessions.close_pool()


@pytest.fixture
def stub_external(monkeypatch):
    """Stub only the third-party boundaries: Drive upload, Whisper STT, Gemini vision."""
    from unittest.mock import AsyncMock

    monkeypatch.setattr(storage, "upload", AsyncMock(return_value="https://drive.example/e2e/object"))
    monkeypatch.setattr(stt, "transcribe", AsyncMock(return_value="תיאור תאונה קולי"))

    async def fake_extract(doc_type, image, mime="image/jpeg"):
        if doc_type == "driver_license":
            return {"license_number": "E2E-LIC-77", "valid_to": "2031-03-03"}
        return {"plate_number": PLATE, "valid_to": "2030-02-02"}

    monkeypatch.setattr(vision, "extract", fake_extract)


@pytest.fixture
def sim(reset_state, bot_pool, stub_external, rec, monkeypatch) -> TelegramSim:
    monkeypatch.setattr(main, "_fleet", FleetClient(base_url=FLEET_URL, token=INTERNAL_TOKEN))
    bot = Bot(TG_TOKEN, session=rec)
    return TelegramSim(bot, rec, main.dp)


@pytest.fixture
async def driver_user(sim) -> int:
    """An enrolled driver (real POST /bot-enroll, real users row)."""
    await sim.share_contact(DRIVER_CHAT, DRIVER_CONTACT)
    sim.rec.reset()  # drop the welcome so a test asserts only its own actions
    return DRIVER_CHAT


@pytest.fixture
async def admin_user(sim) -> int:
    """An enrolled admin (matched to the seeded bot_authorization)."""
    await sim.share_contact(ADMIN_CHAT, ADMIN_CONTACT)
    sim.rec.reset()
    return ADMIN_CHAT
