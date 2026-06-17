import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DataError


def test_vehicle_uuid_pk_default(conn):
    result = conn.execute(
        text("INSERT INTO vehicles (licensing_plate) VALUES ('TEST-001') RETURNING vehicle_id")
    )
    vid = result.scalar()
    assert vid is not None
    uuid.UUID(str(vid))


def test_licensing_plate_unique(conn):
    conn.execute(text("INSERT INTO vehicles (licensing_plate) VALUES ('DUPE-PLATE')"))
    with pytest.raises(IntegrityError):
        conn.execute(text("INSERT INTO vehicles (licensing_plate) VALUES ('DUPE-PLATE')"))


def test_fk_orphan_vehicle_driver_rejects(conn):
    fake_id = uuid.uuid4()
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO vehicles (licensing_plate, driver_id)"
                " VALUES (:plate, :driver_id)"
            ),
            {"plate": "FK-TEST-001", "driver_id": fake_id},
        )


def test_enum_column_rejects_invalid_value(conn):
    # ponytail: enum rejection is DataError, not IntegrityError in PostgreSQL
    with pytest.raises((IntegrityError, DataError)):
        conn.execute(
            text(
                "INSERT INTO vehicles (licensing_plate, maintenance_type)"
                " VALUES (:plate, :mt)"
            ),
            {"plate": "ENUM-TEST-001", "mt": "nope"},
        )


def test_driver_phone_unique(conn):
    conn.execute(
        text("INSERT INTO drivers (full_name, phone_number) VALUES (:name, :phone)"),
        {"name": "Driver One", "phone": "+972501234567"},
    )
    with pytest.raises(IntegrityError):
        conn.execute(
            text("INSERT INTO drivers (full_name, phone_number) VALUES (:name, :phone)"),
            {"name": "Driver Two", "phone": "+972501234567"},
        )


def test_channel_identities_composite_unique(conn):
    conn.execute(
        text(
            "INSERT INTO channel_identities (channel, external_id, phone_number)"
            " VALUES (:ch, :ext, :phone)"
        ),
        {"ch": "telegram", "ext": "12345", "phone": "+972501111111"},
    )
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO channel_identities (channel, external_id, phone_number)"
                " VALUES (:ch, :ext, :phone)"
            ),
            {"ch": "telegram", "ext": "12345", "phone": "+972502222222"},
        )


def test_vehicle_care_driver_id_nullable(conn):
    result = conn.execute(
        text(
            "INSERT INTO vehicles (licensing_plate) VALUES (:plate) RETURNING vehicle_id"
        ),
        {"plate": "CARE-TEST-001"},
    )
    vehicle_id = result.scalar()

    # NULL driver_id must succeed
    conn.execute(
        text(
            "INSERT INTO vehicle_care"
            " (vehicle_id, service_date, maintenance_type, km_at_service)"
            " VALUES (:vid, '2024-01-01', 'small', 10000)"
        ),
        {"vid": vehicle_id},
    )

    # Non-existent driver_id must raise
    fake_driver = uuid.uuid4()
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO vehicle_care"
                " (vehicle_id, service_date, maintenance_type, km_at_service, driver_id)"
                " VALUES (:vid, '2024-01-01', 'small', 10000, :did)"
            ),
            {"vid": vehicle_id, "did": fake_driver},
        )
