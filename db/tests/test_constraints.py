import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DataError, IntegrityError


def test_vehicle_uuid_pk_default(conn, company_id):
    result = conn.execute(
        text(
            "INSERT INTO vehicles (company_id, licensing_plate)"
            " VALUES (:co, 'TEST-001') RETURNING vehicle_id"
        ),
        {"co": company_id},
    )
    vid = result.scalar()
    assert vid is not None
    uuid.UUID(str(vid))


def test_licensing_plate_unique(conn, company_id):
    conn.execute(
        text("INSERT INTO vehicles (company_id, licensing_plate) VALUES (:co, 'DUPE-PLATE')"),
        {"co": company_id},
    )
    with pytest.raises(IntegrityError):
        conn.execute(
            text("INSERT INTO vehicles (company_id, licensing_plate) VALUES (:co, 'DUPE-PLATE')"),
            {"co": company_id},
        )


def test_fk_orphan_vehicle_driver_rejects(conn, company_id):
    fake_id = uuid.uuid4()
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO vehicles (company_id, licensing_plate, driver_id)"
                " VALUES (:co, :plate, :driver_id)"
            ),
            {"co": company_id, "plate": "FK-TEST-001", "driver_id": fake_id},
        )


def test_enum_column_rejects_invalid_value(conn, company_id):
    # ponytail: enum rejection is DataError, not IntegrityError in PostgreSQL
    with pytest.raises((IntegrityError, DataError)):
        conn.execute(
            text(
                "INSERT INTO vehicles (company_id, licensing_plate, vehicle_type)"
                " VALUES (:co, :plate, :vt)"
            ),
            {"co": company_id, "plate": "ENUM-TEST-001", "vt": "nope"},
        )


def test_driver_phone_unique(conn, company_id):
    conn.execute(
        text(
            "INSERT INTO drivers (company_id, full_name, phone_number)"
            " VALUES (:co, :name, :phone)"
        ),
        {"co": company_id, "name": "Driver One", "phone": "+972501234567"},
    )
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO drivers (company_id, full_name, phone_number)"
                " VALUES (:co, :name, :phone)"
            ),
            {"co": company_id, "name": "Driver Two", "phone": "+972501234567"},
        )


def test_channel_identities_composite_unique(conn, company_id):
    conn.execute(
        text(
            "INSERT INTO channel_identities (company_id, channel, external_id, phone_number)"
            " VALUES (:co, :ch, :ext, :phone)"
        ),
        {"co": company_id, "ch": "telegram", "ext": "12345", "phone": "+972501111111"},
    )
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO channel_identities (company_id, channel, external_id, phone_number)"
                " VALUES (:co, :ch, :ext, :phone)"
            ),
            {"co": company_id, "ch": "telegram", "ext": "12345", "phone": "+972502222222"},
        )


def test_vehicle_care_driver_id_nullable(conn, company_id):
    result = conn.execute(
        text(
            "INSERT INTO vehicles (company_id, licensing_plate)"
            " VALUES (:co, :plate) RETURNING vehicle_id"
        ),
        {"co": company_id, "plate": "CARE-TEST-001"},
    )
    vehicle_id = result.scalar()

    # NULL driver_id must succeed
    conn.execute(
        text(
            "INSERT INTO vehicle_care"
            " (company_id, vehicle_id, service_date, maintenance_type, km_at_service)"
            " VALUES (:co, :vid, '2024-01-01', 'small', 10000)"
        ),
        {"co": company_id, "vid": vehicle_id},
    )

    # Non-existent driver_id must raise
    fake_driver = uuid.uuid4()
    with pytest.raises(IntegrityError):
        conn.execute(
            text(
                "INSERT INTO vehicle_care"
                " (company_id, vehicle_id, service_date,"
                "  maintenance_type, km_at_service, driver_id)"
                " VALUES (:co, :vid, '2024-01-01', 'small', 10000, :did)"
            ),
            {"co": company_id, "vid": vehicle_id, "did": fake_driver},
        )
