# Sysadmin Overview Enrichment - Task Report

## Per-Schema Approach

The original `repo.system_overview` ran all tenant-table counts on the
request session. For a System Admin (company_id=None), `get_db` resolves
the schema to `shared` ("public"), so every count hit `public.*` - any
company on a dedicated schema returned 0.

The fix (commit `94e94ea`) mirrors `find_enrollment_by_phone` and
`refresh_kpi_daily`:

1. For each non-internal company, read `company_settings.schema_name`
   (public table, main session).
2. Skip tenant counts if `schema_name == '__pending__'` (sentinel for
   unprovisioned schemas).
3. Otherwise, open `engine.connect()` (obtained via `session.bind.engine`)
   and set `execution_options(schema_translate_map={"tenant": schema_name,
   None: shared})` on the new connection.
4. Open a `Session(bind=tconn)` and run all tenant-table counts there.
5. Public-table reads (BotUser count, kpi_daily) remain on the main session.

## New Fields Added to SystemOverviewItem

| Field | Source | Default |
|---|---|---|
| `customer_count` | tenant.customers WHERE company_id=c | 0 |
| `accident_count` | tenant.accidents WHERE company_id=c | 0 |
| `maintenance_due_count` | tenant.vehicles WHERE current_km >= next_maintenance_km | 0 |
| `docs_expiring_count` | tenant.vehicles WHERE insurance_valid_to<=today+30 OR license_valid_to<=today+30 | 0 |
| `unpaid_report_count` | tenant.reports WHERE status='unpaid' | 0 |
| `total_km_7d` | public.kpi_daily latest row (main session) | 0 |
| `is_active` | public.companies.is_active | True |
| `schema_name` | public.company_settings.schema_name | "" |
| `bot_user_count` | public.users WHERE company_id=c (main session) | 0 |

Existing fields (vehicle_count, driver_count, open_event_count) were also
moved into the per-schema block to read from the correct schema.

## RED/GREEN Evidence

**RED (commit `1bf5b4c` - before implementation):**
```
FAILED tests/test_sysadmin.py::test_overview_per_schema_dedicated_company
  AssertionError: schema_name field missing from SystemOverviewItem
  assert 'schema_name' in {'attendance_enabled': False, 'company_id': '...', 
  'driver_count': 0, 'gdrive_configured': False, ...}
```

**GREEN (commit `94e94ea` - after implementation):**
```
tests/test_sysadmin.py::test_overview_per_schema_dedicated_company PASSED
tests/test_sysadmin.py::test_overview_default_company_still_counts PASSED
2 passed in 1.85s
```

## Suite Results

**fleet-api sysadmin/overview focused:**
```
11 passed, 171 deselected in 2.10s
```

**fleet-api full suite:**
```
182 passed in 4.40s
```

**telegram-bot full suite:**
```
75 passed in 1.49s
```

## Ruff

```
services/fleet-api: All checks passed!
services/telegram-bot: All checks passed!
```

(Two issues were found and fixed: import ordering in repo.py, UP017
`datetime.UTC` alias in test_sysadmin.py.)

## Mypy

```
fleet-api: Success: no issues found in 58 source files
telegram-bot: Success: no issues found in 37 source files
```

## Commit SHAs

| SHA | Description |
|---|---|
| `1bf5b4c` | test(fleet-api): add RED per-schema overview test |
| `94e94ea` | fix(fleet-api): per-schema system overview with enriched metrics |
| `bf4dd3c` | fix(fleet-api): resolve ruff import-sort and UP017 issues |
| `ee4982c` | feat(telegram-bot): enrich sysadmin overview with new metrics |
| `e8849c7` | test(telegram-bot): extend overview test with new metric fields |
