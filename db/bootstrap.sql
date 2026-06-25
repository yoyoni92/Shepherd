-- Non-model SQL applied by db-init after create_schema.py.
-- Holds the pg_cron functions + schedules that SQLAlchemy models can't express.
-- pg_cron bits are guarded on extension availability so this runs unchanged on a
-- plain Postgres image (e.g. the test container) that lacks pg_cron.

-- Daily KPI rollup (formerly migration 0003). The dashboard reads the latest
-- kpi_daily rows in O(1); this recomputes today's snapshot.
CREATE OR REPLACE FUNCTION refresh_kpi_daily() RETURNS void AS $fn$
DECLARE
  v_window_start timestamptz := (current_date - interval '7 days');
  v_license_days int := COALESCE(
    (SELECT (config_value #>> '{}')::int FROM system_config WHERE config_key = 'license_expiring_days'), 30);
  v_insurance_days int := COALESCE(
    (SELECT (config_value #>> '{}')::int FROM system_config WHERE config_key = 'insurance_expiring_days'), 30);
BEGIN
  INSERT INTO kpi_daily (
    snapshot_date, total_km_7d, avg_km_per_driver_7d, avg_days_between_maintenance,
    maintenance_due_count, docs_expiring_count, top_customer_id, top_customer_km,
    top_customer_vehicle_count, computed_ts
  )
  WITH vkm AS (
    SELECT v.vehicle_id, v.customer_id,
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
  totals AS (SELECT COALESCE(SUM(km_7d), 0)::int AS total_km FROM vkm),
  drv AS (SELECT COUNT(*)::int AS n FROM drivers),
  gaps AS (
    SELECT AVG(gap) AS avg_gap FROM (
      SELECT (service_date - LAG(service_date)
              OVER (PARTITION BY vehicle_id ORDER BY service_date)) AS gap
      FROM vehicle_care
    ) g WHERE gap IS NOT NULL
  ),
  maint AS (
    SELECT COUNT(*)::int AS n FROM vehicles
    WHERE current_km IS NOT NULL AND next_maintenance_km IS NOT NULL
      AND current_km >= next_maintenance_km
  ),
  docs AS (
    SELECT COUNT(*)::int AS n FROM vehicles
    WHERE (insurance_valid_to IS NOT NULL AND insurance_valid_to <= current_date + v_insurance_days)
       OR (license_valid_to IS NOT NULL AND license_valid_to <= current_date + v_license_days)
  ),
  topc AS (
    SELECT customer_id, SUM(km_7d)::int AS km
    FROM vkm WHERE customer_id IS NOT NULL
    GROUP BY customer_id ORDER BY SUM(km_7d) DESC NULLS LAST LIMIT 1
  )
  SELECT current_date,
         totals.total_km,
         totals.total_km::numeric / NULLIF(drv.n, 0),
         gaps.avg_gap,
         maint.n,
         docs.n,
         topc.customer_id,
         topc.km,
         (SELECT COUNT(*)::int FROM vehicles vv WHERE vv.customer_id = topc.customer_id),
         now()
  FROM totals
  CROSS JOIN drv CROSS JOIN gaps CROSS JOIN maint CROSS JOIN docs
  LEFT JOIN topc ON true
  ON CONFLICT (snapshot_date) DO UPDATE SET
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
