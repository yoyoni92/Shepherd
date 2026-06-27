-- Non-model SQL applied by db-init after create_schema.py.
-- Holds the pg_cron functions + schedules that SQLAlchemy models can't express.
-- pg_cron bits are guarded on extension availability so this runs unchanged on a
-- plain Postgres image (e.g. the test container) that lacks pg_cron.

-- Daily KPI rollup (formerly migration 0003). The dashboard reads the latest
-- kpi_daily rows in O(1); this recomputes today's snapshot.
CREATE OR REPLACE FUNCTION refresh_kpi_daily() RETURNS void AS $fn$
DECLARE
  v_window_start timestamptz := (current_date - interval '7 days');
BEGIN
  INSERT INTO kpi_daily (
    snapshot_date, company_id, total_km_7d, avg_km_per_driver_7d, avg_days_between_maintenance,
    maintenance_due_count, docs_expiring_count, top_customer_id, top_customer_km,
    top_customer_vehicle_count, computed_ts
  )
  WITH cfg AS (
    -- Per-company alert thresholds (fall back to 30 days when a company has no override).
    SELECT c.company_id,
      COALESCE((SELECT (config_value #>> '{}')::int FROM system_config s
                WHERE s.company_id = c.company_id AND s.config_key = 'license_expiring_days'), 30) AS license_days,
      COALESCE((SELECT (config_value #>> '{}')::int FROM system_config s
                WHERE s.company_id = c.company_id AND s.config_key = 'insurance_expiring_days'), 30) AS insurance_days
    FROM companies c
  ),
  vkm AS (
    SELECT v.company_id, v.vehicle_id, v.customer_id,
      GREATEST(
        COALESCE((SELECT max(k.km) FROM km_updates k
                  WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts >= v_window_start), 0)
        - COALESCE(
            (SELECT k.km FROM km_updates k
             WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts < v_window_start
             ORDER BY k.recorded_ts DESC LIMIT 1),
            (SELECT max(k.km) FROM km_updates k
             WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts >= v_window_start),
            0),
        0) AS km_7d
    FROM vehicles v
  ),
  totals AS (SELECT company_id, COALESCE(SUM(km_7d), 0)::int AS total_km FROM vkm GROUP BY company_id),
  drv AS (SELECT company_id, COUNT(*)::int AS n FROM drivers GROUP BY company_id),
  gaps AS (
    SELECT company_id, AVG(gap) AS avg_gap FROM (
      SELECT company_id, (service_date - LAG(service_date)
              OVER (PARTITION BY vehicle_id ORDER BY service_date)) AS gap
      FROM vehicle_care
    ) g WHERE gap IS NOT NULL GROUP BY company_id
  ),
  maint AS (
    SELECT company_id, COUNT(*)::int AS n FROM vehicles
    WHERE current_km IS NOT NULL AND next_maintenance_km IS NOT NULL
      AND current_km >= next_maintenance_km
    GROUP BY company_id
  ),
  docs AS (
    SELECT v.company_id, COUNT(*)::int AS n FROM vehicles v
    JOIN cfg ON cfg.company_id = v.company_id
    WHERE (v.insurance_valid_to IS NOT NULL AND v.insurance_valid_to <= current_date + cfg.insurance_days)
       OR (v.license_valid_to IS NOT NULL AND v.license_valid_to <= current_date + cfg.license_days)
    GROUP BY v.company_id
  ),
  topc AS (
    SELECT DISTINCT ON (company_id) company_id, customer_id, SUM(km_7d)::int AS km
    FROM vkm WHERE customer_id IS NOT NULL
    GROUP BY company_id, customer_id
    ORDER BY company_id, SUM(km_7d) DESC NULLS LAST
  )
  SELECT current_date,
         c.company_id,
         COALESCE(totals.total_km, 0),
         COALESCE(totals.total_km, 0)::numeric / NULLIF(drv.n, 0),
         gaps.avg_gap,
         COALESCE(maint.n, 0),
         COALESCE(docs.n, 0),
         topc.customer_id,
         topc.km,
         (SELECT COUNT(*)::int FROM vehicles vv
          WHERE vv.customer_id = topc.customer_id AND vv.company_id = c.company_id),
         now()
  FROM companies c
  LEFT JOIN totals ON totals.company_id = c.company_id
  LEFT JOIN drv ON drv.company_id = c.company_id
  LEFT JOIN gaps ON gaps.company_id = c.company_id
  LEFT JOIN maint ON maint.company_id = c.company_id
  LEFT JOIN docs ON docs.company_id = c.company_id
  LEFT JOIN topc ON topc.company_id = c.company_id
  ON CONFLICT (snapshot_date, company_id) DO UPDATE SET
    total_km_7d = EXCLUDED.total_km_7d,
    avg_km_per_driver_7d = EXCLUDED.avg_km_per_driver_7d,
    avg_days_between_maintenance = EXCLUDED.avg_days_between_maintenance,
    maintenance_due_count = EXCLUDED.maintenance_due_count,
    docs_expiring_count = EXCLUDED.docs_expiring_count,
    top_customer_id = EXCLUDED.top_customer_id,
    top_customer_km = EXCLUDED.top_customer_km,
    top_customer_vehicle_count = EXCLUDED.top_customer_vehicle_count,
    computed_ts = EXCLUDED.computed_ts;
END;
$fn$ LANGUAGE plpgsql;

-- Revoke expired temporary bot access (authorizations + enrolled users).
CREATE OR REPLACE FUNCTION cleanup_expired_bot_access() RETURNS void AS $fn$
BEGIN
  DELETE FROM bot_authorizations WHERE expires_at IS NOT NULL AND expires_at < now();
  DELETE FROM users WHERE expires_at IS NOT NULL AND expires_at < now();
END;
$fn$ LANGUAGE plpgsql;

DO $do$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
    PERFORM cron.schedule('kpi-daily', '0 3 * * *', 'SELECT refresh_kpi_daily()');
    PERFORM cron.schedule('bot-access-cleanup', '*/5 * * * *', 'SELECT cleanup_expired_bot_access()');
  END IF;
END
$do$;
