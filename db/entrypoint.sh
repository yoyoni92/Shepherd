#!/bin/sh
set -e
alembic upgrade head
python seed.py
python - <<'EOF'
from sqlalchemy import create_engine, text
import os
engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO rag_readonly"))
    conn.execute(text("GRANT USAGE ON SCHEMA public TO rag_readonly"))
    conn.commit()
EOF
echo "DB init complete."
