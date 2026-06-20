# Postgres 16 + pg_cron, for the kpi_daily nightly rollup (migration 0003).
# Must be paired with: shared_preload_libraries=pg_cron and cron.database_name=<db>
# (set via the compose `command`). The 0003 migration creates the extension and
# schedules refresh_kpi_daily(); it no-ops the schedule on images without pg_cron.
FROM postgres:16
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-cron \
    && rm -rf /var/lib/apt/lists/*
