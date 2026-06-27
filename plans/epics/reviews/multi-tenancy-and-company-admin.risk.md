# Risk Review: Multi-Tenancy + Company-Admin Authorization

Reviewed plan: `plans/epics/multi-tenancy-and-company-admin.md`
Source spec: `docs/superpowers/specs/2026-06-26-multi-tenancy-and-company-admin-design.md`
Scope of review: technical risk and feasibility only (not decomposition/architecture).

## Verdict

NEEDS REVISION

The epic's strategy is directionally sound, but it under-scopes its single most
important risk and leaves three concrete data-layer couplings unaddressed: the
`bootstrap.sql` KPI rollup, per-company `system_config`, and `NOT NULL company_id`
on derived/system writes that have no caller. The headline mitigation
("centralize scoping in one repo-layer helper") does not fit the actual repo
architecture, where 18 of the highest-risk access paths use `session.get()` by
primary key and cannot be filtered by a shared helper. These need to be resolved
in Feature 1's plan before execution.

---

## Critical Findings

### Finding: "One repo-layer helper" does not fit the repo; 18 by-PK paths bypass any filter
- **Affects**: `plans/.../multi-tenancy-and-company-admin.md` (Feature 1; Risks table row 1), spec section 4 "Tenant scoping"
- **Risk**: `services/fleet-api/app/repo.py` is ~40 free functions, not a class with a
  single query chokepoint. 18 call sites use `session.get(Model, pk)`
  (`get_vehicle_by_id`, `update_vehicle`, `delete_vehicle`, `get_driver`,
  `update_driver`, `delete_driver`, `update_customer`, `delete_customer`,
  `get_maintenance_type`, `update_maintenance_type`, `delete_maintenance_type`,
  `update_bot_user_role`, `delete_bot_authorization`, `get_config_key`,
  `get_maintenance_buffer`, the `Vehicle` lookups inside `update_km`/`create_care`).
  `session.get()` fetches by PK and **cannot carry a `WHERE company_id` clause**, so a
  centralized "add a filter" helper cannot cover them. Today a `company_admin` who
  passes another company's UUID to `PATCH /vehicles/{id}`, `DELETE /drivers/{id}`,
  etc. would succeed.
- **Likelihood**: high (this is the default path for every detail/update/delete route)
- **Impact**: cross-tenant read and write - the epic's stated top risk, fully realized.
- **Recommendation**: Feature 1's plan must explicitly enumerate the by-PK paths and
  specify the pattern (convert to filtered `select(...).where(pk, company_id)` or a
  mandatory post-fetch `assert row.company_id == caller.company_id`). The "one helper"
  framing in the Risks table should be replaced with a per-function checklist; the
  list-style functions and the by-PK functions need two different scoping mechanisms.

### Finding: `bootstrap.sql` KPI rollup is non-model SQL untouched by "rebuild from models"
- **Affects**: Feature 1 (kpi rollups gaining `company_id`); spec sections 3 and 6
- **Risk**: `db/bootstrap.sql` `refresh_kpi_daily()` (lines 8-84) is plpgsql applied
  *after* `create_schema.py` and is **not** regenerated from `models.py`. It (a)
  aggregates globally across all `vehicles`/`drivers`/`km_updates`/`vehicle_care`
  with no company partition, (b) writes one row keyed on `snapshot_date` alone
  (`ON CONFLICT (snapshot_date)`), and (c) reads `system_config WHERE config_key =
  'license_expiring_days'` assuming a single global row. If `kpi_daily` gains
  `company_id` (composite PK) and config becomes per-company, this function is broken
  on every axis and must be rewritten to loop per company. The plan never mentions
  `bootstrap.sql`; Feature 1's "schema is rebuilt from models" gives false comfort
  that the rebuild covers it.
- **Likelihood**: high (the nightly `cron.schedule('kpi-daily', ...)` will run the
  unmodified function against the new schema)
- **Impact**: KPI dashboard either errors, double-counts across tenants, or silently
  produces one global row that leaks aggregate cross-company data into every tenant's
  dashboard.
- **Recommendation**: Add an explicit Feature 1 task to rewrite `refresh_kpi_daily()`
  (and re-verify `cleanup_expired_bot_access()`) for per-company semantics, and call
  out `bootstrap.sql` as in-scope non-model SQL. Decide whether `kpi_daily` is truly
  per-company or stays global (the spec says per-company; if so the PK and the
  function both change).

### Finding: Per-company `system_config` breaks single-key PK and every global config reader
- **Affects**: Feature 1 (config gaining `company_id`); spec section 3
- **Risk**: `SystemConfig.config_key` is the sole PK (`models.py` line 534). Making
  config per-company forces a composite PK `(company_id, config_key)`, which breaks
  every reader that keys by `config_key` alone: `repo.get_config_key`,
  `repo.get_all_config`, `repo.set_config`, `repo.get_maintenance_buffer`
  (all `session.get(SystemConfig, key)` / single-column selects), the attendance
  `_window()` helper (`routers/attendance.py` lines 33-43), and `refresh_kpi_daily()`.
  Worse, the code paths that read config have **no caller company**:
  `attendance.clock_in/clock_out` carry only `driver_id` and run under
  `verify_internal_token` with no `X-Caller-Context`; `update_km` -> `get_maintenance_buffer`
  has only a vehicle. Each must now resolve a company (from the driver/vehicle) before
  it can read the right config row.
- **Likelihood**: high
- **Impact**: maintenance-trigger threshold and attendance window read the wrong (or no)
  row; clock-in/out and km-update either error or fall back to defaults silently.
- **Recommendation**: Treat "config becomes per-company" as a cross-cutting subtask, not
  a column add. Specify the composite-PK migration of all config readers and how the
  caller-less endpoints (attendance clock, km update) derive `company_id` from the
  driver/vehicle. Consider whether some keys (e.g. extractor settings) should stay
  global to avoid this entirely.

### Finding: `NOT NULL company_id` on derived/system writes with no caller, incl. an orphan-event path
- **Affects**: Feature 1 (NOT NULL on events/reports); spec sections 3, 4
- **Risk**: Several writes create rows with no caller-supplied company:
  `repo.process_extracted_doc` creates an `Event` with **no vehicle** when the plate is
  not in any fleet (`repo.py` lines 280-289) - there is no company to attach, so a
  `NOT NULL company_id` insert fails and the "review_required" path dies.
  `update_km` and `create_accident` create `Event`s derived from a vehicle, and doc
  extraction creates `Report` + `Event` from a vehicle - all can inherit
  `vehicle.company_id`, but only if explicitly wired. The plan addresses none of these
  derived-write company-inheritance cases.
- **Likelihood**: high (the orphan-event path is exercised whenever an extracted doc's
  plate is unknown - a designed-for case, per the docstring)
- **Impact**: insert failures on real flows (doc extraction, km updates, accident
  logging) once the column is NOT NULL; or, if patched hastily, mis-attributed events.
- **Recommendation**: Feature 1 must specify company inheritance for every derived write
  and decide where the orphan "plate not found" event lands (e.g. a system/inbox company,
  or make that event's `company_id` nullable as an explicit exception). Add a test for
  the unknown-plate path under NOT NULL.

### Finding: Bot caller context is company-blind; `admin_ctx()` defaults to unfiltered (cross-company)
- **Affects**: Feature 3; spec section 4 "Bot tenancy"; Risks table row 3
- **Risk**: The bot's only context helpers are `admin_ctx() = {"role":"admin"}` and
  `driver_ctx(driver_id)` (`telegram-bot/app/fleet.py` 18-23), and **every** generic
  `get/post/patch` defaults to `admin_ctx()` (lines 69-79). `whoami` does not return a
  company today (`routers/bot.py` 38-43; `context.py` exposes only role/driver_id).
  Under the new "admin unfiltered unless a company is supplied" rule, all admin-side bot
  flows (`fleet_summary`, `broadcast`, `attendance_admin`, `update_driver`,
  `update_details`, `maintenance`, `doc_scan`) would operate across *all* companies.
  This is ~73 fleet calls across 13 flow files, validated by 52 bot tests - the
  default-admin context is the leak vector, and the plan's mitigation ("Feature 3 is
  isolated; rely on the existing pytest suite") understates it.
- **Likelihood**: high (the default is the leak)
- **Impact**: a company-bound bot admin broadcasts to / reads / edits every company's
  drivers and vehicles; driver flows that route through `admin_ctx()` writes land
  unscoped.
- **Recommendation**: Feature 3 must (a) return `company_id` from `whoami`/`enroll`,
  (b) replace `admin_ctx()` with a company-scoped context derived from the enrolled
  user, (c) for the caller-less endpoints (`attendance` clock, km), derive company
  server-side from the driver, and (d) add per-flow cross-company-denial tests, not
  just rely on the existing suite. Treat the `admin_ctx()` default as a code-level
  landmine to remove.

---

## Concerns

### Concern: Global unique constraints become cross-tenant collisions and a phone-enrollment leak
- **Affects**: Feature 1 (schema), Feature 3 (enrollment); `models.py`, `repo.py`
- **Risk**: `Driver.phone_number` (unique, line 239), `Vehicle.licensing_plate`
  (unique, 297), `MaintenanceType.name` (unique, 278), and `BotUser.telegram_chat_id`
  (unique) are globally unique. Two companies cannot reuse a plate, phone, or
  maintenance-type name. Critically, `find_enrollment_by_phone` (`repo.py` 552-574)
  scans **all active drivers across all companies** by normalized phone; combined with
  the recent "auto-enroll bot users by phone" commit, a phone match silently enrolls
  against whichever company owns that driver. The plan does not decide whether these
  uniques become per-company composite constraints. If they do, phone-based enrollment
  becomes ambiguous (same phone in two companies); if they do not, tenants can't reuse
  identifiers.
- **Likelihood**: medium
- **Impact**: either onboarding friction (can't reuse plate/phone) or a cross-tenant
  enrollment where a user is bound to the wrong company.
- **Recommendation**: Make an explicit decision per constraint (global vs per-company)
  and, for enrollment, scope/disambiguate the phone match by company (e.g. authorization
  carries the company; driver match must be unambiguous within the target company).

### Concern: Seeding is a rewrite of every INSERT, not a "backfill"; enumeration is incomplete
- **Affects**: Feature 1 seeding; spec section 6; `db/seed.py`
- **Risk**: All 12 `_seed_*` functions have explicit column lists with no `company_id`
  (`seed.py` 68-386). "Backfill existing seed rows" is misleading in a rebuild-from-zero
  model - there is no existing data; every INSERT statement must be edited to add
  `company_id`, and a new `_seed_companies` must run first in `seed()` (line 389). The
  ordering itself is simple, but the surface is all 12 functions, plus `_seed_app_users`
  (Feature 2). The `ON CONFLICT DO NOTHING` + `stable_uuid` pattern keeps it idempotent.
- **Likelihood**: medium
- **Impact**: a missed function leaves a NOT NULL insert failing the whole seed; partial
  edits are easy to overlook across 12 functions.
- **Recommendation**: Reframe the task as "add `company_id` to every seed INSERT + seed
  companies first," and treat the seed as the canonical end-to-end test that the NOT NULL
  schema is internally consistent.

### Concern: Domain-table enumeration omits real tables; "documents" table does not exist
- **Affects**: Feature 1 requirements / spec section 3 "company_id on all domain tables"
- **Risk**: The enumerated list omits actual tables that carry tenant data:
  `km_updates`, `vehicle_care`, `accident_attachments`, `channel_identities`,
  `bot_sessions`. If "NOT NULL company_id on every domain table" is literal, these need
  columns + seed + scoping; if they are scoped only via parent FK, that contradicts the
  stated rule and leaves `km_updates`/`vehicle_care` reads unfiltered. Separately,
  "documents" is listed as a domain table but there is **no documents table** in
  `models.py` - documents are S3 objects referenced by `file_url` columns
  (insurance/registration/invoice/ticket). The requirement is ambiguous.
- **Likelihood**: medium
- **Impact**: tables silently left unscoped (leak surface) or wasted effort chasing a
  non-existent table.
- **Recommendation**: Reconcile the enumeration against `models.py`. Decide explicitly,
  per table, "own `company_id` column" vs "scoped via parent FK," and drop or redefine
  "documents."

### Concern: "No migrations" + idempotent `create_all` means existing DBs silently miss the new columns
- **Affects**: Cross-cutting "No DB migrations"; `db/create_schema.py`
- **Risk**: `Base.metadata.create_all` is `checkfirst` (idempotent) - it creates missing
  tables but does **not** alter existing ones. On any environment with an existing volume,
  the new `company_id` columns will not appear and the re-seed will fail. "Rebuild from
  models" only holds on a freshly dropped database; there is no in-place path.
- **Likelihood**: medium (depends on dev/staging volume reuse)
- **Impact**: confusing partial-schema failures; every environment must be dropped and
  recreated.
- **Recommendation**: State explicitly in Feature 1 that all environments must
  drop-and-recreate, and that this is irreversible (acceptable pre-prod, but should be
  called out, including any persisted volumes in compose/CI).

### Concern: Cross-feature gap - `company_admin` cannot be exercised until Feature 2
- **Affects**: Feature 1 vs Feature 2 split; `libs/shepherd_contracts/auth.py`
- **Risk**: The plan puts `CallerContext.company_id` and repo scoping in Feature 1 but
  the `company_admin` **role value** and its matrix rows in Feature 2. So Feature 1's
  scoping tests can only exercise `admin` + selected-company; the "company_admin forced
  to its company" path - the highest-risk behavior - is untestable end-to-end until
  Feature 2. The `CallerContext` validator (`auth.py` 20-26) also needs "company_admin
  requires company_id" logic that logically belongs with the role value.
- **Likelihood**: medium
- **Impact**: the riskiest scoping path ships in Feature 1 unverified and is only
  validated a feature later.
- **Recommendation**: Either pull the `company_admin` role value into Feature 1 (so its
  scoping tests are real), or have Feature 1 test the forced-company path via a stand-in,
  and explicitly note the deferred validation.

## Observations

- The system-admin "active company vs all companies" semantics touch ~15 list functions
  (`list_vehicles`, `list_drivers`, `list_customers`, `list_events`, `list_reports`,
  `list_accidents`, `list_maintenance_types`, `list_attendance_*`, `list_bot_users`,
  `list_bot_authorizations`) plus their routers, each gaining an optional company filter
  threaded from the caller. Mechanical but broad - larger than "one helper" implies.

- `middleware.ts` currently gates by token presence only and its matcher omits most
  routes (`/health`, `/bot`, `/events`, `/customers`, `/accidents`, `/maintenance-types`,
  and the new `/companies`, `/access`). Feature 2 must enumerate every route in both the
  matcher and the `route -> allowedRoles` map; a forgotten route falls through to no
  client gating (backend 403 still backstops data, so this is a UX/redirect gap, not a
  leak). The spec already acknowledges the backend backstop.

- Feature 4 says "remove the Chat/Assistant tab," but the current `Sidebar.tsx` `NAV`
  has no `/chat` or `/assistant` entry (a `ChatSurface.tsx` component and `Topbar`
  references exist). Verify what is actually wired before planning the deletion, and
  confirm the `agent.ts` cross-tenant leak this is said to "moot" is currently reachable.

- The `Sidebar` calls `useHealth()` (and vehicles/drivers/customers/events/accidents
  hooks) unconditionally for badge counts; for a `company_admin`, `useHealth` will hit a
  forbidden endpoint. Ensure these hook calls degrade gracefully under role gating.

- JWT-issued-but-unused (Risks table row 5) is correctly identified and has a reasonable
  mitigation (issuance/claims unit test). No additional concern beyond keeping the claim
  set (`sub`, `role`, `company_id`, `exp`) frozen as the documented mobile contract.

- The `Customer` vs `Company` distinction (Risks table row 6) is handled correctly in
  the design: `customers.company_id` is additive and `Vehicle.customer_id` is untouched.
  No risk there; flagged only to confirm it was verified against `models.py`.
