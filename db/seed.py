#!/usr/bin/env python3
"""Synthetic fleet seed - deterministic, idempotent, run via: python seed.py"""
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import create_engine, text

from shepherd_db.logic import next_maintenance
from shepherd_db.security import hash_password

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://shepherd:shepherd@localhost:5432/shepherd",
)

SEED_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# Default Company - fixed id shared with the test suite (conftest.DEFAULT_COMPANY_ID)
# so seed + tests are deterministic. Every seeded domain row belongs to it.
DEFAULT_COMPANY_ID = uuid.UUID("00000000-0000-0000-0000-0000000000c0")

# Playground - the built-in, non-customer sandbox for system-admin Debug mode.
# is_internal=true keeps it out of customer lists + the system overview.
PLAYGROUND_COMPANY_ID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


def stable_uuid(namespace: str, key) -> uuid.UUID:
    return uuid.uuid5(SEED_NS, f"{namespace}:{key}")


CONFIG = [
    ("license_expiring_days", 30, "Days before license expiry to trigger alert"),
    ("insurance_expiring_days", 30, "Days before insurance expiry to trigger alert"),
    ("maintenance_km_buffer", 500, "km before next_maintenance_km to fire maintenance_due"),
    ("extractor_provider", "bedrock", "Document extraction provider"),
    ("image_confidence_min", 0.60, "Minimum Bedrock confidence score"),
]

ATTACHMENT_CATEGORIES = [
    "another_driver_insurance",
    "photo_our_vehicle",
    "photo_other_vehicle",
]

EVENT_TYPES = [
    "maintenance_due",
    "license_expiring",
    "insurance_expiring",
    "ticket_received",
    "accident_logged",
]

EVENT_SEVERITIES = ["info", "warning", "critical"]
EVENT_SOURCES = ["km_updates", "scheduler", "accidents", "reports"]
TICKET_TYPES = ["traffic", "parking"]
MAINTENANCE_TYPES = [
    {
        "name": "קטן ואז גדול",
        "description": "טיפול קטן ולאחריו טיפול גדול, לסירוגין",
        "interval_km": 10000,
        "steps": ["קטן", "גדול"],
    },
    {
        "name": "שניים קטנים ואז גדול",
        "description": "שני טיפולים קטנים ולאחריהם טיפול גדול",
        "interval_km": 10000,
        "steps": ["קטן א׳", "קטן ב׳", "גדול"],
    },
]
VENDORS = ["Toyota", "Ford", "Hyundai", "Kia", "Volkswagen"]
MODELS = ["Corolla", "Transit", "Tucson", "Sportage", "Caddy"]


def _seed_companies(conn):
    conn.execute(
        text("""
            INSERT INTO companies (company_id, name)
            VALUES (:id, 'Default Company')
            ON CONFLICT (company_id) DO NOTHING
        """),
        {"id": DEFAULT_COMPANY_ID},
    )


def _seed_drivers(conn):
    for i in range(1, 26):
        conn.execute(
            text("""
                INSERT INTO drivers (driver_id, company_id, full_name, phone_number, license_number, status)
                VALUES (:id, :company_id, :name, :phone, :lic, 'active')
                ON CONFLICT (driver_id) DO NOTHING
            """),
            {
                "id": stable_uuid("driver", i),
                "company_id": DEFAULT_COMPANY_ID,
                "name": f"Driver {i}",
                "phone": f"+9725{i:08d}",
                "lic": f"IL-DRV-{i:05d}",
            },
        )


def _seed_customers(conn):
    for i in range(1, 26):
        conn.execute(
            text("""
                INSERT INTO customers (customer_id, company_id, full_name, phone_number, email, status)
                VALUES (:id, :company_id, :name, :phone, :email, 'active')
                ON CONFLICT (customer_id) DO NOTHING
            """),
            {
                "id": stable_uuid("customer", i),
                "company_id": DEFAULT_COMPANY_ID,
                "name": f"Customer {i}",
                "phone": f"+9726{i:08d}",
                "email": f"customer{i}@example.com",
            },
        )


def _seed_maintenance_types(conn):
    for idx, mt in enumerate(MAINTENANCE_TYPES):
        conn.execute(
            text("""
                INSERT INTO maintenance_types (id, company_id, name, description, interval_km, steps)
                VALUES (:id, :company_id, :name, :desc, :interval, :steps)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": stable_uuid("maintenance_type", idx),
                "company_id": DEFAULT_COMPANY_ID,
                "name": mt["name"],
                "desc": mt["description"],
                "interval": mt["interval_km"],
                "steps": json.dumps(mt["steps"]),
            },
        )


def _seed_vehicles(conn):
    for i in range(1, 26):
        idx = i % 2
        mt = MAINTENANCE_TYPES[idx]
        steps = mt["steps"]
        last_km = 10000 * i
        last_type = steps[i % len(steps)]
        nm = next_maintenance(last_type, steps, last_km=last_km, interval_km=mt["interval_km"])
        conn.execute(
            text("""
                INSERT INTO vehicles (
                    vehicle_id, company_id, licensing_plate, nickname, inseration_ts,
                    insurance_valid_to, license_valid_to,
                    allowed_driver, vendor, model,
                    last_maintenance_date, last_maintenance_type,
                    last_maintenance_km, next_maintenance_km, next_maintenance_type,
                    current_km, driver_id, maintenance_type_id, customer_id
                ) VALUES (
                    :id, :company_id, :plate, :nick, :ins_ts,
                    :insurance_valid_to, :license_valid_to,
                    'all_drivers', :vendor, :model,
                    :last_maint_date, :last_maint_type,
                    :last_maint_km, :next_maint_km, :next_maint_type,
                    :current_km, :driver_id, :maint_type_id, :customer_id
                )
                ON CONFLICT (vehicle_id) DO NOTHING
            """),
            {
                "id": stable_uuid("vehicle", i),
                "company_id": DEFAULT_COMPANY_ID,
                "plate": f"TLV-{i:04d}",
                "nick": f"Fleet-{i}",
                "ins_ts": datetime(2024, 1, i % 28 + 1, tzinfo=timezone.utc),
                "insurance_valid_to": date(2026, (i % 12) + 1, 15),
                "license_valid_to": date(2026, (i % 12) + 1, 28),
                "vendor": VENDORS[i % len(VENDORS)],
                "model": MODELS[i % len(MODELS)],
                "last_maint_date": date(2025, (i % 12) + 1, 10),
                "last_maint_type": last_type,
                "last_maint_km": last_km,
                "next_maint_km": nm["next_km"],
                "next_maint_type": nm["next_type"],
                "current_km": last_km + 2000,
                "driver_id": stable_uuid("driver", i),
                "maint_type_id": stable_uuid("maintenance_type", idx),
                "customer_id": stable_uuid("customer", (i % 5) + 1),
            },
        )


def _seed_accidents(conn):
    for i in range(1, 11):
        conn.execute(
            text("""
                INSERT INTO accidents (
                    accident_id, company_id, vehicle_id, driver_id, datetime,
                    location, description,
                    another_driver_licensing_plate, another_driver_phone_number
                ) VALUES (
                    :id, :company_id, :vehicle_id, :driver_id, :dt,
                    :location, :desc,
                    :other_plate, :other_phone
                )
                ON CONFLICT (accident_id) DO NOTHING
            """),
            {
                "id": stable_uuid("accident", i),
                "company_id": DEFAULT_COMPANY_ID,
                "vehicle_id": stable_uuid("vehicle", i),
                "driver_id": stable_uuid("driver", i),
                "dt": datetime(2025, (i % 12) + 1, i % 28 + 1, tzinfo=timezone.utc),
                "location": f"Street {i}, Tel Aviv",
                "desc": f"Accident description {i}",
                "other_plate": f"BER-{i:04d}",
                "other_phone": f"+9729{i:08d}",
            },
        )


def _seed_accident_attachments(conn):
    attach_i = 1
    for acc_i in range(1, 11):
        num_attachments = 1 + (acc_i % 3)
        for j in range(num_attachments):
            category = ATTACHMENT_CATEGORIES[j % len(ATTACHMENT_CATEGORIES)]
            acc_id = stable_uuid("accident", acc_i)
            conn.execute(
                text("""
                    INSERT INTO accident_attachments (
                        attachment_id, company_id, accident_id, category, file_url, uploaded_ts
                    ) VALUES (
                        :id, :company_id, :accident_id, :category, :file_url, :uploaded_ts
                    )
                    ON CONFLICT (attachment_id) DO NOTHING
                """),
                {
                    "id": stable_uuid("attachment", attach_i),
                    "company_id": DEFAULT_COMPANY_ID,
                    "accident_id": acc_id,
                    "category": category,
                    "file_url": f"accidents/{acc_id}/attachments/{attach_i}.jpg",
                    "uploaded_ts": datetime(2025, (acc_i % 12) + 1, acc_i % 28 + 1, tzinfo=timezone.utc),
                },
            )
            attach_i += 1


def _seed_km_updates(conn):
    update_i = 1
    for v_i in range(1, 11):
        base_km = 10000 * v_i
        for j in range(1, 4):
            km = base_km + j * 1500
            conn.execute(
                text("""
                    INSERT INTO km_updates (
                        km_update_id, company_id, vehicle_id, km, recorded_ts, driver_id, source
                    ) VALUES (
                        :id, :company_id, :vehicle_id, :km, :recorded_ts, :driver_id, :source
                    )
                    ON CONFLICT (km_update_id) DO NOTHING
                """),
                {
                    "id": stable_uuid("km_update", update_i),
                    "company_id": DEFAULT_COMPANY_ID,
                    "vehicle_id": stable_uuid("vehicle", v_i),
                    "km": km,
                    "recorded_ts": datetime(2025, (j % 12) + 1, j * 5, tzinfo=timezone.utc),
                    "driver_id": stable_uuid("driver", v_i),
                    "source": "telegram" if j % 2 == 0 else "admin_ui",
                },
            )
            update_i += 1


def _seed_vehicle_care(conn):
    for i in range(1, 21):
        vehicle_id = stable_uuid("vehicle", i)
        care_id = stable_uuid("care", i)
        last_km = 10000 * i
        mt = MAINTENANCE_TYPES[i % 2]
        steps = mt["steps"]
        last_type = steps[i % len(steps)]
        nm = next_maintenance(last_type, steps, last_km=last_km, interval_km=mt["interval_km"])
        invoice_url = None
        if i % 3 == 0:
            invoice_url = f"vehicles/{vehicle_id}/care/{care_id}/invoice.pdf"
        driver_id = stable_uuid("driver", i) if i % 4 == 0 else None
        conn.execute(
            text("""
                INSERT INTO vehicle_care (
                    care_id, company_id, vehicle_id, service_date, maintenance_type,
                    km_at_service, description, cost, garage,
                    invoice_file_url, next_maintenance_km, driver_id
                ) VALUES (
                    :id, :company_id, :vehicle_id, :service_date, :maint_type,
                    :km_at_service, :desc, :cost, :garage,
                    :invoice_url, :next_maint_km, :driver_id
                )
                ON CONFLICT (care_id) DO NOTHING
            """),
            {
                "id": care_id,
                "company_id": DEFAULT_COMPANY_ID,
                "vehicle_id": vehicle_id,
                "service_date": date(2025, (i % 12) + 1, 10),
                "maint_type": last_type,
                "km_at_service": last_km,
                "desc": f"Service for vehicle {i}",
                "cost": 150 + i * 10,
                "garage": f"Garage {(i % 5) + 1}",
                "invoice_url": invoice_url,
                "next_maint_km": nm["next_km"],
                "driver_id": driver_id,
            },
        )


def _seed_reports(conn):
    for i in range(1, 11):
        conn.execute(
            text("""
                INSERT INTO reports (
                    report_id, company_id, vehicle_id, driver_id, ticket_type,
                    violation_desc, amount, issued_ts, due_date,
                    status, location, authority
                ) VALUES (
                    :id, :company_id, :vehicle_id, :driver_id, :ticket_type,
                    :desc, :amount, :issued_ts, :due_date,
                    'unpaid', :location, :authority
                )
                ON CONFLICT (report_id) DO NOTHING
            """),
            {
                "id": stable_uuid("report", i),
                "company_id": DEFAULT_COMPANY_ID,
                "vehicle_id": stable_uuid("vehicle", i),
                "driver_id": stable_uuid("driver", i),
                "ticket_type": TICKET_TYPES[i % 2],
                "desc": f"Violation {i}",
                "amount": 250 + i * 50,
                "issued_ts": datetime(2025, (i % 12) + 1, i % 28 + 1, tzinfo=timezone.utc),
                "due_date": date(2025, (i % 12) + 1, 28),
                "location": f"Location {i}",
                "authority": "Police" if i % 2 == 0 else "Municipality",
            },
        )


def _seed_events(conn):
    for i in range(1, 16):
        event_type = EVENT_TYPES[i % len(EVENT_TYPES)]
        severity = EVENT_SEVERITIES[i % len(EVENT_SEVERITIES)]
        source = EVENT_SOURCES[i % len(EVENT_SOURCES)]
        conn.execute(
            text("""
                INSERT INTO events (
                    event_id, company_id, vehicle_id, event_type, severity,
                    message, payload_json, source_type, source_id,
                    status, notified
                ) VALUES (
                    :id, :company_id, :vehicle_id, :event_type, :severity,
                    :message, :payload, :source_type, :source_id,
                    'open', false
                )
                ON CONFLICT (event_id) DO NOTHING
            """),
            {
                "id": stable_uuid("event", i),
                "company_id": DEFAULT_COMPANY_ID,
                "vehicle_id": stable_uuid("vehicle", (i % 25) + 1),
                "event_type": event_type,
                "severity": severity,
                "message": f"Event {i}: {event_type} for vehicle {(i % 25) + 1}",
                "payload": json.dumps({"event_index": i}),
                "source_type": source,
                "source_id": stable_uuid("source", i),
            },
        )


def _seed_system_config(conn):
    for key, value, description in CONFIG:
        conn.execute(
            text("""
                INSERT INTO system_config (company_id, config_key, config_value, description)
                VALUES (:company_id, :key, :value, :desc)
                ON CONFLICT (company_id, config_key) DO NOTHING
            """),
            {
                "company_id": DEFAULT_COMPANY_ID,
                "key": key,
                "value": json.dumps(value),
                "desc": description,
            },
        )


def _seed_channel_identities(conn):
    for i in range(1, 11):
        conn.execute(
            text("""
                INSERT INTO channel_identities (
                    identity_id, company_id, channel, external_id, phone_number, status
                ) VALUES (
                    :id, :company_id, 'telegram', :external_id, :phone, 'linked'
                )
                ON CONFLICT (channel, external_id) DO NOTHING
            """),
            {
                "id": stable_uuid("channel_identity", i),
                "company_id": DEFAULT_COMPANY_ID,
                "external_id": f"tg_user_{i:06d}",
                "phone": f"+9725{i:08d}",
            },
        )


def _seed_company_settings(conn):
    # The Default Company starts with attendance OFF (empty feature_flags) and Drive
    # unconfigured (null folder + credentials). System admin configures these per company.
    conn.execute(
        text("""
            INSERT INTO company_settings (company_id, feature_flags)
            VALUES (:id, '{}'::jsonb)
            ON CONFLICT (company_id) DO NOTHING
        """),
        {"id": DEFAULT_COMPANY_ID},
    )


def _seed_app_users(conn):
    # System admin (no company) - credentials default to the webui .env.example values.
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@fleetops.io")
    admin_password = os.environ.get("ADMIN_PASSWORD", "shepherd")
    admin_phone = os.environ.get("ADMIN_PHONE", "+972500000000")
    conn.execute(
        text("""
            INSERT INTO app_users (
                id, email, password_hash, role, company_id, name,
                is_system_admin, phone_number
            )
            VALUES (:id, :email, :hash, 'admin', NULL, 'System Admin', true, :phone)
            ON CONFLICT (email) DO NOTHING
        """),
        {
            "id": stable_uuid("app_user", admin_email),
            "email": admin_email,
            "hash": hash_password(admin_password),
            "phone": admin_phone,
        },
    )
    # Demo company_admin bound to the Default Company.
    conn.execute(
        text("""
            INSERT INTO app_users (id, email, password_hash, role, company_id, name)
            VALUES (:id, :email, :hash, 'company_admin', :company_id, 'Demo Company Admin')
            ON CONFLICT (email) DO NOTHING
        """),
        {
            "id": stable_uuid("app_user", "company@fleetops.io"),
            "email": "company@fleetops.io",
            "hash": hash_password("shepherd"),
            "company_id": DEFAULT_COMPANY_ID,
        },
    )


def _seed_playground(conn):
    """Built-in sandbox company (is_internal) with attendance ON + mock drivers/vehicles.

    Drive stays unconfigured. Idempotent via fixed ids / ON CONFLICT.
    """
    conn.execute(
        text("""
            INSERT INTO companies (company_id, name, is_internal)
            VALUES (:id, 'Playground', true)
            ON CONFLICT (company_id) DO NOTHING
        """),
        {"id": PLAYGROUND_COMPANY_ID},
    )
    # Attendance ON so the sandbox surfaces every flow; Drive left empty.
    conn.execute(
        text("""
            INSERT INTO company_settings (company_id, feature_flags)
            VALUES (:id, '{"attendance": true}'::jsonb)
            ON CONFLICT (company_id) DO NOTHING
        """),
        {"id": PLAYGROUND_COMPANY_ID},
    )
    for i in range(1, 4):
        conn.execute(
            text("""
                INSERT INTO drivers (
                    driver_id, company_id, full_name, phone_number, license_number, status
                )
                VALUES (:id, :company_id, :name, :phone, :lic, 'active')
                ON CONFLICT (driver_id) DO NOTHING
            """),
            {
                "id": stable_uuid("pg_driver", i),
                "company_id": PLAYGROUND_COMPANY_ID,
                "name": f"Playground Driver {i}",
                "phone": f"+9725900000{i:02d}",
                "lic": f"PG-DRV-{i:05d}",
            },
        )
    for i in range(1, 4):
        conn.execute(
            text("""
                INSERT INTO vehicles (
                    vehicle_id, company_id, licensing_plate, nickname,
                    allowed_driver, vendor, model, current_km, driver_id
                ) VALUES (
                    :id, :company_id, :plate, :nick,
                    'all_drivers', :vendor, :model, :current_km, :driver_id
                )
                ON CONFLICT (vehicle_id) DO NOTHING
            """),
            {
                "id": stable_uuid("pg_vehicle", i),
                "company_id": PLAYGROUND_COMPANY_ID,
                "plate": f"PG-{i:04d}",
                "nick": f"Playground-{i}",
                "vendor": VENDORS[i % len(VENDORS)],
                "model": MODELS[i % len(MODELS)],
                "current_km": 10000 * i,
                "driver_id": stable_uuid("pg_driver", i),
            },
        )


def seed(engine):
    with engine.connect() as conn:
        _seed_companies(conn)
        _seed_company_settings(conn)
        _seed_playground(conn)
        _seed_drivers(conn)
        _seed_customers(conn)
        _seed_maintenance_types(conn)
        _seed_vehicles(conn)
        _seed_accidents(conn)
        _seed_accident_attachments(conn)
        _seed_km_updates(conn)
        _seed_vehicle_care(conn)
        _seed_reports(conn)
        _seed_events(conn)
        _seed_system_config(conn)
        _seed_channel_identities(conn)
        _seed_app_users(conn)
        conn.commit()


if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    seed(engine)
    print("Seed complete.")
