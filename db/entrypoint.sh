#!/bin/sh
set -e
# Schema comes straight from the models (no migrations); create_schema also applies
# bootstrap.sql (pg_cron functions + schedules). Then seed, grants, and KPI backfill.
python create_schema.py
python seed.py
python - <<'EOF'
import os
from sqlalchemy import create_engine, text
engine = create_engine(os.environ["DATABASE_URL"])
with engine.begin() as conn:
    conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly"))
    conn.execute(text("GRANT USAGE ON SCHEMA public TO rag_readonly"))
    conn.execute(text("SELECT refresh_kpi_daily()"))
EOF
echo "DB init complete."
