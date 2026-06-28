"""The tenant domain tables carry the symbolic 'tenant' schema token; control-plane
and identity tables stay in public (schema None); no public->tenant FK survives."""
from shepherd_db.models import Base


TENANT = {
    "drivers", "customers", "maintenance_types", "vehicles", "accidents",
    "accident_attachments", "km_updates", "vehicle_care", "reports", "events",
    "attendance_records",
}
PUBLIC = {
    "companies", "company_settings", "app_users", "impersonation_audit", "kpi_daily",
    "system_config", "channel_identities", "users", "bot_authorizations", "bot_sessions",
}


def _table(name):
    return Base.metadata.tables[name] if name in Base.metadata.tables else \
        next(t for t in Base.metadata.tables.values() if t.name == name)


def test_tenant_tables_use_symbolic_schema():
    for name in TENANT:
        assert _table(name).schema == "tenant", name


def test_public_tables_have_no_schema():
    for name in PUBLIC:
        assert _table(name).schema is None, name


def test_no_public_to_tenant_foreign_keys():
    # kpi_daily.top_customer_id, users.driver_id, bot_authorizations.driver_id were FKs
    # to tenant tables; they must now be plain columns (no FK across the public/tenant line).
    for tname, col in [
        ("kpi_daily", "top_customer_id"),
        ("users", "driver_id"),
        ("bot_authorizations", "driver_id"),
    ]:
        assert not _table(tname).c[col].foreign_keys, f"{tname}.{col} still has a FK"
