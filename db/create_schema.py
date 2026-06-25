#!/usr/bin/env python3
"""Build the schema straight from the models (no migrations - pre-prod, DB is disposable).

create_all is idempotent (checkfirst), so re-running on an existing DB is a no-op.
bootstrap.sql holds the non-model SQL (pg_cron functions + schedules); it's applied
right after, and is a no-op on a Postgres image without pg_cron.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from shepherd_db.models import Base

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://shepherd:shepherd@localhost:5432/shepherd"
)
_BOOTSTRAP = os.path.join(os.path.dirname(__file__), "bootstrap.sql")


def build(engine: Engine) -> None:
    """create_all + apply bootstrap.sql. Used by db-init and the test schema fixture."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(open(_BOOTSTRAP).read())


def main() -> None:
    build(create_engine(DATABASE_URL))
    print("Schema created from models.")


if __name__ == "__main__":
    main()
