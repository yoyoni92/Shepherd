import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# All 11 tables
TABLES = [
    "vehicles", "drivers", "customers", "accidents", "accident_attachments",
    "km_updates", "vehicle_care", "reports", "events", "system_config",
    "channel_identities",
]


@pytest.fixture(scope="module")
def readonly_engine(pg_engine):
    """Create rag_readonly role and return an engine connected as that role."""
    with pg_engine.connect() as conn:
        conn.execute(text("DROP ROLE IF EXISTS rag_readonly"))
        conn.execute(text("CREATE ROLE rag_readonly LOGIN PASSWORD 'readonly123'"))
        conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO rag_readonly"))
        conn.commit()

    # Build a URL for the readonly role
    url = pg_engine.url.set(
        username="rag_readonly",
        password="readonly123",
    )
    ro_engine = create_engine(url)
    yield ro_engine
    ro_engine.dispose()
    # Cleanup: revoke grants before dropping the role
    with pg_engine.connect() as conn:
        conn.execute(text("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM rag_readonly"))
        conn.execute(text("REVOKE USAGE ON SCHEMA public FROM rag_readonly"))
        conn.execute(text("DROP ROLE IF EXISTS rag_readonly"))
        conn.commit()


def test_readonly_can_select(readonly_engine):
    for table in TABLES:
        with readonly_engine.connect() as conn:
            conn.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))  # noqa: S608


def test_readonly_cannot_insert(readonly_engine):
    with pytest.raises((ProgrammingError, Exception)) as exc_info:
        with readonly_engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO drivers (full_name, phone_number) VALUES ('Hacker', '+000')"
            ))
            conn.commit()
    # Verify it's an insufficient privilege error
    assert "permission denied" in str(exc_info.value).lower() or \
           "insufficient" in str(exc_info.value).lower() or \
           exc_info.type.__name__ in ("ProgrammingError", "InsufficientPrivilege")


def test_readonly_cannot_update(readonly_engine):
    with pytest.raises(Exception) as exc_info:
        with readonly_engine.connect() as conn:
            conn.execute(text("UPDATE drivers SET full_name = 'Hacker' WHERE 1=0"))
            conn.commit()
    assert "permission denied" in str(exc_info.value).lower() or \
           exc_info.type.__name__ in ("ProgrammingError",)
