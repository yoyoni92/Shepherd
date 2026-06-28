# Maintenance dual-interval: "every X km or every Y months"

A maintenance type can be due by **distance**, by **time**, or **whichever comes
first**. Today it's km-only. Decisions were settled in a grilling session; this is
the build plan.

## Decisions (locked)

- **Semantics:** whichever-comes-first (OR). `interval_km` and `interval_months`
  both optional, **at least one** required.
- **Storage:** time interval as `interval_months` (integer). "1 year" = 12; the
  Years/Months choice is UI sugar (Years ×12).
- **Next-due:** add `Vehicle.next_maintenance_date` next to existing
  `next_maintenance_km`. Anchored on the service date. No anchor → not time-due.
- **Trigger:** km path stays inline (`repo.update_km`). Time path = new daily
  pg_cron sweep `emit_time_maintenance_due()`, mirroring the existing cron jobs.
- **Dedup:** one open `maintenance_due` event per vehicle per cycle. Guard both
  insert sites (`update_km`, cron) with `NOT EXISTS (open maintenance_due for
  vehicle)`. `create_care` resolves the open event when the cycle resets.
  `payload_json` records which dimension tripped (`km` / `time`).
- **Threshold:** new dynamic `maintenance_time_buffer_days` system_config key,
  surfaced in the הגדרות page like `maintenance_km_buffer`. Default 30.
- **KPI:** remove `maintenance_due_count` entirely.
- **Notifications:** event-feed parity only (no push). Tracked on ROADMAP under
  Event Alert Pipeline.

## Tasks

### 1. DB model (`db/shepherd_db/models.py`)
- `MaintenanceType.interval_km` → nullable; add `interval_months` (Integer, nullable).
- Add `__table_args__` CHECK: `interval_km IS NOT NULL OR interval_months IS NOT NULL`.
- `Vehicle.next_maintenance_date` (Date, nullable).
- Remove `kpi_daily.maintenance_due_count` column.

### 2. Cycle logic (`db/shepherd_db/logic.py`)
- `next_maintenance(...)` gains `last_date` + `interval_months` params; returns
  `next_date` (`last_date + interval_months`, or None). Keep km behavior.
- Test: date math + None handling (`db/tests/test_logic.py`).

### 3. bootstrap.sql (`db/bootstrap.sql`)
- New `emit_time_maintenance_due()`: insert `maintenance_due` event for vehicles
  where `next_maintenance_date IS NOT NULL AND current_date >= next_maintenance_date
  - <buffer days>` AND no open maintenance_due event exists; `payload_json` = `{"trigger":"time"}`.
- Schedule it daily (alongside `kpi-daily`).
- Remove the `due` CTE + `maintenance_due_count` from `refresh_kpi_daily`.

### 4. fleet-api
- `schemas.py`: `MaintenanceType{Create,Update,Read}` km optional + `interval_months`;
  validator "≥1 set". Vehicle read gains `next_maintenance_date`. Drop
  `maintenance_due_count` from KPI schema.
- `repo.py`: `create_care` writes `next_maintenance_date` (pass type's
  `interval_months` + service date to `next_maintenance`) and resolves the open
  event. `update_km` dedup guard + `payload_json` trigger reason. Add
  `get_maintenance_time_buffer_days` getter (default 30).
- `routers/maintenance_types.py`: `_to_read` includes `interval_months`.
- `routers/vehicles.py`: include `next_maintenance_date`.
- `routers/kpi.py`: drop `maintenance_due_count`.
- Tests: schema validation, care date write, dedup.

### 5. webui
- `lib/api/schemas.ts` + `lib/adapters.ts`: `interval_months`, `next_maintenance_date`,
  drop `maintenance_due_count`.
- `MaintenanceTypeForm.tsx`: km optional; months input + Years/Months selector;
  validate ≥1 set.
- `MaintenanceTypeCard.tsx`: subtitle shows km and/or time joined by "או" (years when ÷12).
- `config/page.tsx`: add `maintenance_time_buffer_days` field.
- `dashboard/page.tsx` + `lib/kpis.ts`: drop `maintDue` card.
- Tests: msw handlers, kpis.test.ts.

### 6. telegram-bot
- `flows/fleet_summary.py`: drop the `maintenance_due_count` line.
- Test: `test_e2e.py` fleet-summary expectation.

### 7. Docs (pre-commit rule)
- This plan, `.env.example` if a new seed key, READMEs if commands/config changed.

## Definition of done
- ≥1-interval validation enforced (schema + DB CHECK).
- Logging a service sets both next km and next date per the type's intervals.
- A vehicle overdue only by date gets exactly one `maintenance_due` event from the
  daily sweep; no duplicate from repeated sweeps or km reports.
- `maintenance_time_buffer_days` editable in הגדרות and honored by the sweep.
- `maintenance_due_count` gone from every layer; all suites green.
