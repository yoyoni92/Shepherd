-- Non-model SQL applied by db-init after create_schema.py.
-- Holds the pg_cron functions + schedules that SQLAlchemy models can't express.
-- pg_cron bits are guarded on extension availability so this runs unchanged on a
-- plain Postgres image (e.g. the test container) that lacks pg_cron.

-- Daily KPI rollup, per company. Tenant tables live in per-company schemas
-- (company_settings.schema_name); read each company's schema with dynamic SQL and
-- write the snapshot into public.kpi_daily. company_id row-scoping keeps shared-schema
-- subcompanies apart.
-- # ponytail: one company at a time with format()/EXECUTE (%%I quotes the schema
-- identifier, %%L literalises the company id and window; file uses %%%% so psycopg
-- passes a literal %% to Postgres). Schemas shared by sibling companies are visited
-- once per company and kept apart by WHERE company_id, so the snapshot stays
-- per-company-correct.
CREATE OR REPLACE FUNCTION refresh_kpi_daily() RETURNS void AS $fn$
DECLARE
  v_window_start timestamptz := (current_date - interval '7 days');
  c record;
  v_schema text;
BEGIN
  FOR c IN SELECT company_id FROM companies LOOP
    SELECT COALESCE(s.schema_name, 'public') INTO v_schema
      FROM company_settings s WHERE s.company_id = c.company_id;
    IF v_schema IS NULL THEN
      v_schema := 'public';
    END IF;
    -- Skip companies whose schema has not been provisioned yet.
    IF v_schema = '__pending__' THEN
      CONTINUE;
    END IF;

    EXECUTE format($q$
      INSERT INTO kpi_daily (
        snapshot_date, company_id, total_km_7d, avg_km_per_driver_7d,
        avg_days_between_maintenance, docs_expiring_count,
        top_customer_id, top_customer_km, top_customer_vehicle_count, computed_ts
      )
      WITH cfg AS (
        SELECT
          COALESCE((SELECT (config_value #>> '{}')::int FROM system_config s
                    WHERE s.company_id = %%1$L AND s.config_key = 'license_expiring_days'), 30) AS license_days,
          COALESCE((SELECT (config_value #>> '{}')::int FROM system_config s
                    WHERE s.company_id = %%1$L AND s.config_key = 'insurance_expiring_days'), 30) AS insurance_days
      ),
      vkm AS (
        SELECT v.vehicle_id, v.customer_id,
          GREATEST(
            COALESCE((SELECT max(k.km) FROM %%2$I.km_updates k
                      WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts >= %%3$L), 0)
            - COALESCE(
                (SELECT k.km FROM %%2$I.km_updates k
                 WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts < %%3$L
                 ORDER BY k.recorded_ts DESC LIMIT 1),
                (SELECT max(k.km) FROM %%2$I.km_updates k
                 WHERE k.vehicle_id = v.vehicle_id AND k.recorded_ts >= %%3$L),
                0),
            0) AS km_7d
        FROM %%2$I.vehicles v WHERE v.company_id = %%1$L
      ),
      totals AS (SELECT COALESCE(SUM(km_7d), 0)::int AS total_km FROM vkm),
      drv AS (SELECT COUNT(*)::int AS n FROM %%2$I.drivers WHERE company_id = %%1$L),
      gaps AS (
        SELECT AVG(gap) AS avg_gap FROM (
          SELECT (service_date - LAG(service_date)
                  OVER (PARTITION BY vehicle_id ORDER BY service_date)) AS gap
          FROM %%2$I.vehicle_care WHERE company_id = %%1$L
        ) g WHERE gap IS NOT NULL
      ),
      docs AS (
        SELECT COUNT(*)::int AS n FROM %%2$I.vehicles v, cfg
        WHERE v.company_id = %%1$L
          AND ((v.insurance_valid_to IS NOT NULL AND v.insurance_valid_to <= current_date + cfg.insurance_days)
            OR (v.license_valid_to IS NOT NULL AND v.license_valid_to <= current_date + cfg.license_days))
      ),
      topc AS (
        SELECT customer_id, SUM(km_7d)::int AS km FROM vkm WHERE customer_id IS NOT NULL
        GROUP BY customer_id ORDER BY SUM(km_7d) DESC NULLS LAST LIMIT 1
      )
      SELECT current_date, %%1$L,
             COALESCE(totals.total_km, 0),
             COALESCE(totals.total_km, 0)::numeric / NULLIF(drv.n, 0),
             gaps.avg_gap,
             COALESCE(docs.n, 0),
             topc.customer_id, topc.km,
             (SELECT COUNT(*)::int FROM %%2$I.vehicles vv
              WHERE vv.customer_id = topc.customer_id AND vv.company_id = %%1$L),
             now()
      FROM totals, drv, gaps, docs
      LEFT JOIN topc ON true
      ON CONFLICT (snapshot_date, company_id) DO UPDATE SET
        total_km_7d = EXCLUDED.total_km_7d,
        avg_km_per_driver_7d = EXCLUDED.avg_km_per_driver_7d,
        avg_days_between_maintenance = EXCLUDED.avg_days_between_maintenance,
        docs_expiring_count = EXCLUDED.docs_expiring_count,
        top_customer_id = EXCLUDED.top_customer_id,
        top_customer_km = EXCLUDED.top_customer_km,
        top_customer_vehicle_count = EXCLUDED.top_customer_vehicle_count,
        computed_ts = EXCLUDED.computed_ts;
    $q$, c.company_id, v_schema, v_window_start);
  END LOOP;
END;
$fn$ LANGUAGE plpgsql;

-- Revoke expired temporary bot access (authorizations + enrolled users).
CREATE OR REPLACE FUNCTION cleanup_expired_bot_access() RETURNS void AS $fn$
BEGIN
  DELETE FROM bot_authorizations WHERE expires_at IS NOT NULL AND expires_at < now();
  DELETE FROM users WHERE expires_at IS NOT NULL AND expires_at < now();
END;
$fn$ LANGUAGE plpgsql;

-- Time-based maintenance trigger. The KM path emits maintenance_due inline on a km
-- report; the clock has no such trigger, so this daily sweep emits one for vehicles
-- whose next_maintenance_date has arrived (within the per-company warning buffer,
-- default 30 days), unless an open maintenance_due event already exists for the
-- vehicle (one open event per cycle - create_care resolves it on the next service).
CREATE OR REPLACE FUNCTION emit_time_maintenance_due() RETURNS void AS $fn$
BEGIN
  INSERT INTO events (vehicle_id, company_id, event_type, severity, message,
                      source_type, status, payload_json)
  SELECT v.vehicle_id, v.company_id, 'maintenance_due', 'warning', 'Maintenance due soon',
         'scheduler', 'open', '{"trigger": "time"}'::jsonb
  FROM vehicles v
  WHERE v.next_maintenance_date IS NOT NULL
    AND current_date >= v.next_maintenance_date - COALESCE(
      (SELECT (config_value #>> '{}')::int FROM system_config s
       WHERE s.company_id = v.company_id AND s.config_key = 'maintenance_time_buffer_days'), 30)
    AND NOT EXISTS (
      SELECT 1 FROM events e
      WHERE e.vehicle_id = v.vehicle_id
        AND e.event_type = 'maintenance_due'
        AND e.status = 'open');
END;
$fn$ LANGUAGE plpgsql;

DO $do$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
    PERFORM cron.schedule('kpi-daily', '0 3 * * *', 'SELECT refresh_kpi_daily()');
    PERFORM cron.schedule('maintenance-time-due', '30 3 * * *', 'SELECT emit_time_maintenance_due()');
    PERFORM cron.schedule('bot-access-cleanup', '*/5 * * * *', 'SELECT cleanup_expired_bot_access()');
  END IF;
END
$do$;
