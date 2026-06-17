import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import text
from seed import seed


def test_seed_counts(pg_engine):
    seed(pg_engine)
    with pg_engine.connect() as conn:
        for table, min_count in [
            ("vehicles", 20),
            ("drivers", 20),
            ("customers", 20),
            ("km_updates", 1),
            ("accidents", 1),
            ("vehicle_care", 1),
            ("reports", 1),
            ("events", 1),
            ("system_config", 6),
            ("channel_identities", 1),
        ]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count >= min_count, f"{table}: expected >={min_count}, got {count}"


def test_seed_idempotent(pg_engine):
    seed(pg_engine)
    seed(pg_engine)
    with pg_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM vehicles")).scalar()
        assert count <= 30


def test_seed_vehicle_care_has_invoices(pg_engine):
    seed(pg_engine)
    with pg_engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM vehicle_care WHERE invoice_file_url IS NOT NULL")
        ).scalar()
        assert count >= 1


def test_seed_vehicle_care_has_drivers(pg_engine):
    seed(pg_engine)
    with pg_engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM vehicle_care WHERE driver_id IS NOT NULL")
        ).scalar()
        assert count >= 1
