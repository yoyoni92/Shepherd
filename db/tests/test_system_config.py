import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from seed import seed

EXPECTED_CONFIG = [
    ("license_expiring_days",   30,           int),
    ("insurance_expiring_days", 30,           int),
    ("maintenance_km_buffer",   500,          int),
    ("extractor_provider",      "bedrock",    str),
    ("image_confidence_min",    0.60,         float),
]


def test_system_config_values(pg_engine):
    seed(pg_engine)
    with pg_engine.connect() as conn:
        for key, expected_value, expected_type in EXPECTED_CONFIG:
            row = conn.execute(
                text("SELECT config_value FROM system_config WHERE config_key = :k"),
                {"k": key},
            ).fetchone()
            assert row is not None, f"Missing config key: {key}"
            value = row[0]  # psycopg3 returns JSONB already parsed as Python objects
            assert isinstance(value, expected_type), (
                f"{key}: expected {expected_type.__name__}, got {type(value).__name__}"
            )
            assert value == expected_value, f"{key}: expected {expected_value!r}, got {value!r}"
