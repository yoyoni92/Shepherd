#!/usr/bin/env python3
"""Build the schema straight from the models (no migrations - pre-prod, DB is disposable).

Public (control-plane + identity) tables are created in public; each distinct schema named
in config is provisioned with the tenant tables. bootstrap.sql holds the non-model SQL.
"""
import os

import shepherd_config as _sc
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from shepherd_db.models import Base

from provisioning import TENANT_TABLES, provision_company

_BOOTSTRAP = os.path.join(os.path.dirname(__file__), "bootstrap.sql")
_TENANT = {t.name for t in TENANT_TABLES}
PUBLIC_TABLES = [t for t in Base.metadata.sorted_tables if t.name not in _TENANT]


def build(engine: Engine) -> None:
    """create public tables + bootstrap.sql, then provision each config schema."""
    Base.metadata.create_all(engine, tables=PUBLIC_TABLES)
    with engine.begin() as conn:
        conn.exec_driver_sql(open(_BOOTSTRAP).read())
    # ponytail: tests without config get public-only; production (db-init) always has
    # SHEPHERD_CONFIG so provisioning runs.
    try:
        cfg = _sc.get_config()
    except FileNotFoundError:
        return
    for schema in {c.schema_name for c in cfg.companies}:
        provision_company(engine, schema, shared_schema=cfg.database.shared_schema)


def main() -> None:
    build(create_engine(_sc.get_config().database.url))
    print("Schema created from models.")


if __name__ == "__main__":
    main()
