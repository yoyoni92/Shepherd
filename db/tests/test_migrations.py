from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

EXPECTED_TABLES = [
    "vehicles",
    "drivers",
    "customers",
    "accidents",
    "accident_attachments",
    "km_updates",
    "vehicle_care",
    "reports",
    "events",
    "system_config",
    "channel_identities",
]


def _make_cfg(pg_engine) -> Config:
    alembic_cfg = Config("alembic.ini")
    # Use render_as_string so the password is not masked as '***'
    url = pg_engine.url.render_as_string(hide_password=False)
    alembic_cfg.set_main_option("sqlalchemy.url", url)
    return alembic_cfg


def test_migration_cycle(pg_engine):
    cfg = _make_cfg(pg_engine)

    # First upgrade
    command.upgrade(cfg, "head")
    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    for t in EXPECTED_TABLES:
        assert t in tables, f"Missing table after upgrade: {t}"

    # Downgrade
    command.downgrade(cfg, "base")
    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    assert "vehicles" not in tables

    # Re-upgrade (idempotency)
    command.upgrade(cfg, "head")
    inspector = inspect(pg_engine)
    tables = inspector.get_table_names()
    for t in EXPECTED_TABLES:
        assert t in tables, f"Missing table after re-upgrade: {t}"
