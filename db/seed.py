#!/usr/bin/env python3
"""Synthetic fleet seed - deterministic, idempotent, run via: python seed.py"""
import json
import os
import sys
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import create_engine, text

from shepherd_db.logic import next_maintenance

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://shepherd:shepherd@localhost:5432/shepherd",
)

SEED_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def stable_uuid(namespace: str, key) -> uuid.UUID:
    return uuid.uuid5(SEED_NS, f"{namespace}:{key}")


CONFIG = [
    ("license_expiring_days", 30, "Days before license expiry to trigger alert"),
    ("insurance_expiring_days", 30, "Days before insurance expiry to trigger alert"),
    ("maintenance_km_buffer", 500, "km before next_maintenance_km to fire maintenance_due"),
    ("allowed_languages", ["he", "en"], "Accepted languages for guardrails"),
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
MAINTENANCE_CYCLES = ["1_small_then_1_big", "2_small_then_1_big"]
VENDORS = ["Toyota", "Ford", "Hyundai", "Kia", "Volkswagen"]
MODELS = ["Corolla", "Transit", "Tucson", "Sportage", "Caddy"]


def _seed_drivers(conn):
    for i in range(1, 26):
        conn.execute(
            text("""
                INSERT INTO drivers (driver_id, full_name, phone_number, license_number, status)
                VALUES (:id, :name, :phone, :lic, 'active')
                ON CONFLICT (driver_id) DO NOTHING
            """),
            {
                "id": stable_uuid("driver", i),
                "name": f"Driver {i}",
                "phone": f"+9725{i:08d}",
                "lic": f"IL-DRV-{i:05d}",
            },
        )


def _seed_customers(conn):
    for i in range(1, 26):
        conn.execute(
            text("""
                INSERT INTO customers (customer_id, full_name, phone_number, email, status)
                VALUES (:id, :name, :phone, :email, 'active')
                ON CONFLICT (customer_id) DO NOTHING
            """),
            {
                "id": stable_uuid("customer", i),
                "name": f"Customer {i}",
                "phone": f"+9726{i:08d}",
                "email": f"customer{i}@example.com",
            },
        )


def _seed_vehicles(conn):
    for i in range(1, 26):
        cycle = MAINTENANCE_CYCLES[i % 2]
        last_km = 10000 * i
        # Use cycle-appropriate last_type values
        if cycle == "2_small_then_1_big":
            last_type = ["small_1", "small_2", "big"][i % 3]
        else:
            last_type = "small" if i % 2 == 0 else "big"
        nm = next_maintenance(last_type, cycle, last_km=last_km)
        conn.execute(
            text("""
                INSERT INTO vehicles (
                    vehicle_id, licensing_plate, nickname, inseration_ts,
                    insurance_valid_to, license_valid_to,
                    allowed_driver, vendor, model,
                    last_maintenance_date, last_maintenance_type,
                    last_maintenance_km, next_maintenance_km, next_maintenance_type,
                    current_km, driver_id, maintenance_type, customer_id
                ) VALUES (
                    :id, :plate, :nick, :ins_ts,
                    :insurance_valid_to, :license_valid_to,
                    'all_drivers', :vendor, :model,
                    :last_maint_date, :last_maint_type,
                    :last_maint_km, :next_maint_km, :next_maint_type,
                    :current_km, :driver_id, :maint_cycle, :customer_id
                )
                ON CONFLICT (vehicle_id) DO NOTHING
            """),
            {
                "id": stable_uuid("vehicle", i),
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
                "maint_cycle": cycle,
                "customer_id": stable_uuid("customer", (i % 5) + 1),
            },
        )


def _seed_accidents(conn):
    for i in range(1, 11):
        conn.execute(
            text("""
                INSERT INTO accidents (
                    accident_id, vehicle_id, driver_id, datetime,
                    location, description,
                    another_driver_licensing_plate, another_driver_phone_number
                ) VALUES (
                    :id, :vehicle_id, :driver_id, :dt,
                    :location, :desc,
                    :other_plate, :other_phone
                )
                ON CONFLICT (accident_id) DO NOTHING
            """),
            {
                "id": stable_uuid("accident", i),
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
                        attachment_id, accident_id, category, file_url, uploaded_ts
                    ) VALUES (
                        :id, :accident_id, :category, :file_url, :uploaded_ts
                    )
                    ON CONFLICT (attachment_id) DO NOTHING
                """),
                {
                    "id": stable_uuid("attachment", attach_i),
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
                        km_update_id, vehicle_id, km, recorded_ts, driver_id, source
                    ) VALUES (
                        :id, :vehicle_id, :km, :recorded_ts, :driver_id, :source
                    )
                    ON CONFLICT (km_update_id) DO NOTHING
                """),
                {
                    "id": stable_uuid("km_update", update_i),
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
        cycle = MAINTENANCE_CYCLES[i % 2]
        if cycle == "2_small_then_1_big":
            last_type = ["small_1", "small_2", "big"][i % 3]
        else:
            last_type = "small" if i % 2 == 0 else "big"
        nm = next_maintenance(last_type, cycle, last_km=last_km)
        invoice_url = None
        if i % 3 == 0:
            invoice_url = f"vehicles/{vehicle_id}/care/{care_id}/invoice.pdf"
        driver_id = stable_uuid("driver", i) if i % 4 == 0 else None
        conn.execute(
            text("""
                INSERT INTO vehicle_care (
                    care_id, vehicle_id, service_date, maintenance_type,
                    km_at_service, description, cost, garage,
                    invoice_file_url, next_maintenance_km, driver_id
                ) VALUES (
                    :id, :vehicle_id, :service_date, :maint_type,
                    :km_at_service, :desc, :cost, :garage,
                    :invoice_url, :next_maint_km, :driver_id
                )
                ON CONFLICT (care_id) DO NOTHING
            """),
            {
                "id": care_id,
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
                    report_id, vehicle_id, driver_id, ticket_type,
                    violation_desc, amount, issued_ts, due_date,
                    status, location, authority
                ) VALUES (
                    :id, :vehicle_id, :driver_id, :ticket_type,
                    :desc, :amount, :issued_ts, :due_date,
                    'unpaid', :location, :authority
                )
                ON CONFLICT (report_id) DO NOTHING
            """),
            {
                "id": stable_uuid("report", i),
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
                    event_id, vehicle_id, event_type, severity,
                    message, payload_json, source_type, source_id,
                    status, notified
                ) VALUES (
                    :id, :vehicle_id, :event_type, :severity,
                    :message, :payload, :source_type, :source_id,
                    'open', false
                )
                ON CONFLICT (event_id) DO NOTHING
            """),
            {
                "id": stable_uuid("event", i),
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
                INSERT INTO system_config (config_key, config_value, description)
                VALUES (:key, :value, :desc)
                ON CONFLICT (config_key) DO NOTHING
            """),
            {
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
                    identity_id, channel, external_id, phone_number, status
                ) VALUES (
                    :id, 'telegram', :external_id, :phone, 'linked'
                )
                ON CONFLICT (channel, external_id) DO NOTHING
            """),
            {
                "id": stable_uuid("channel_identity", i),
                "external_id": f"tg_user_{i:06d}",
                "phone": f"+9725{i:08d}",
            },
        )


def seed(engine):
    with engine.connect() as conn:
        _seed_drivers(conn)
        _seed_customers(conn)
        _seed_vehicles(conn)
        _seed_accidents(conn)
        _seed_accident_attachments(conn)
        _seed_km_updates(conn)
        _seed_vehicle_care(conn)
        _seed_reports(conn)
        _seed_events(conn)
        _seed_system_config(conn)
        _seed_channel_identities(conn)
        conn.commit()


if __name__ == "__main__":
    engine = create_engine(DATABASE_URL)
    seed(engine)
    print("Seed complete.")
