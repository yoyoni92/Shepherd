# Architecture Review: Multi-Tenancy + Company-Admin Authorization

Reviewed: `plans/epics/multi-tenancy-and-company-admin.md`
Against spec: `docs/superpowers/specs/2026-06-26-multi-tenancy-and-company-admin-design.md`
Codebase verified at repo root.

## Verdict

PASS WITH CONCERNS

The decomposition is fundamentally sound: foundation-first sequencing is correct, the
service seams (fleet-api/db vs telegram-bot vs webui) are natural, and the
channel-agnostic auth boundary is well-drawn. But two seam issues are real enough to
fix before the features are planned (one is an internal contradiction in Feature 1's
own scope boundaries; the other is a hidden blast-radius the epic context omits), plus
a NAV co-design gap and several factual inaccuracies against the schema. None are fatal
to the structure; all are cheap to fix in the epic before feature planning starts.

---

## Critical Findings

### Finding: Feature 1 cannot make the bot tables' `company_id` NOT NULL while excluding the enrollment/authorization writers (assigned to Feature 3)

- **Affects**: `plans/epics/multi-tenancy-and-company-admin.md` Feature 1 (lines
  144-153) and Feature 3 (lines 219-244)
- **Problem**: This is an internal contradiction in the epic's own boundaries.
  Feature 1's "Includes" says `company_id` columns + FKs **NOT NULL** on all domain
  tables "(incl. bot tables)" (line 145-146), and the epic Requirements say
  "`company_id` (NOT NULL) on every domain table, including ... the bot tables"
  (lines 26-27). Feature 1's "Excludes" then hands "authorization/enrollment sets it"
  to Feature 3 (lines 152-153, 238-244). These cannot both hold.

  Verified against code: `services/fleet-api/app/repo.py::enroll_bot_user`
  (lines 577-596) constructs `BotUser(...)` with no `company_id`, and
  `create_bot_authorization` (lines 599-612) constructs `BotAuthorization(...)` with
  no `company_id`. The enrollment endpoint `POST /bot-enroll`
  (`services/fleet-api/app/routers/bot.py` lines 46-55) takes **X-Internal-Token only,
  no caller context** - so company cannot be derived from a caller; it can only come
  from the matched driver. The moment Feature 1 flips these columns to NOT NULL,
  `enroll_bot_user` and `create_bot_authorization` raise `IntegrityError` on every
  insert, breaking the bot enroll/authorize paths and their tests - work the plan
  explicitly defers to Feature 3.

  Note also the two writers have *different* company sources, which the plan treats as
  one:
  - `users` (the BotUser table; note it is named `users`, not `bot_users` -
    `db/shepherd_db/models.py` line 657) - company is derivable at enrollment from the
    matched **driver's** `company_id`, which Feature 1 already adds. Feature 1 *can*
    satisfy NOT NULL here on its own.
  - `bot_authorizations` - company has **no** driver to derive from for an admin grant;
    it must come from the inviting caller's `company_id`, i.e. the caller-context +
    permission work that is genuinely Feature 3. Feature 1 *cannot* satisfy NOT NULL
    here without pulling Feature 3 forward.
- **Recommendation**: Pick one and state it explicitly in the epic:
  - **(Preferred)** Feature 1 adds the bot tables' `company_id` columns as **nullable**
    (+ FK + index); Feature 3 backfills the writers (enrollment derives from driver,
    authorization derives from caller) and flips them to NOT NULL once writers set them.
    Update the epic Requirements line 26-27 to carve out the bot tables as
    "nullable in F1, NOT NULL in F3."
  - **(Alternative)** Feature 1 keeps NOT NULL but also updates `enroll_bot_user` to set
    `company_id = matched_driver.company_id` and `create_bot_authorization` to accept a
    `company_id` arg - i.e. move that slice of "enrollment sets company" into Feature 1.
    Then Feature 1's "Excludes" (lines 152-153) must be reworded; it currently claims the
    opposite.

### Finding: Feature 1's per-company `kpi_daily` and `system_config` changes require rewriting non-model SQL and break single-key repo lookups - none of this is in Feature 1's context or risks

- **Affects**: `plans/epics/multi-tenancy-and-company-admin.md` Feature 1 Context
  (lines 122-142), Cross-Cutting "No DB migrations" (lines 96-98)
- **Problem**: The plan asserts "schema is rebuilt from `models.py`
  (`db/create_schema.py`) and re-seeded" and lists only `models.py`, `create_schema.py`,
  and `seed.py` as the schema surface. But making `kpi rollups` and `config`
  per-company (Requirements line 27; spec section 3 line 68) reaches code the models
  cannot express:
  - `db/bootstrap.sql` `refresh_kpi_daily()` (lines 8-84) inserts into `kpi_daily`
    keyed on `ON CONFLICT (snapshot_date)`. `KpiDaily`'s PK is `snapshot_date` alone
    (`models.py` line 551). Per-company KPI means PK `(snapshot_date, company_id)`, a
    rewritten aggregate that GROUPs BY company, and a changed `ON CONFLICT` target.
    `bootstrap.sql` is applied by `create_schema.py::build` (lines 24-25) but is **not
    mentioned anywhere in the epic**, and "rebuild from models" does not cover it.
  - `system_config` PK is `config_key` alone (`models.py` line 534). Per-company config
    makes it composite `(config_key, company_id)`, which breaks the single-key lookups
    `repo.get_config_key` / `repo.set_config` (`repo.py` lines 372-373, 636-647) and
    `repo.get_maintenance_buffer` (`session.get(SystemConfig, "maintenance_km_buffer")`,
    line 169) - the last of which is on the bot km-update path (`update_km`, line 192),
    so per-company config ripples into a bot flow.
- **Recommendation**: Add `db/bootstrap.sql` to Feature 1's Context and its
  Scope-Includes ("rewrite `refresh_kpi_daily()` for per-company rollups; update the
  `kpi_daily` PK / ON CONFLICT"). Explicitly call out that `kpi_daily` and
  `system_config` move to composite PKs and that `get_config_key`/`set_config`/
  `get_maintenance_buffer` must take a `company_id`. Add a risk row: "config/KPI
  per-company changes touch non-model SQL and composite keys, not just column adds."
  (Or, if per-company config/KPI is more than the epic wants right now, decide
  explicitly to keep those two global and update Requirements line 27 / spec line 68 to
  match.)

---

## Concerns

### Concern: Feature 1's scoping helper must key on `company_id` presence, not on the `company_admin` role value (which only exists in Feature 2)

- **Affects**: Feature 1 (lines 130-138, 152-153), Feature 2 (lines 195-199),
  Sequencing (lines 284-289)
- **Problem**: The user's ordering question is real. `Role` today is
  `admin|driver|customer` (`libs/shepherd_contracts/auth.py` lines 9-12); `company_admin`
  is added in **Feature 2** (plan line 152, 196). Feature 1 builds the repo scoping
  helper. If that helper is written to branch on `Role.company_admin`, Feature 1 has a
  hidden compile/runtime dependency on Feature 2 and cannot be tested in isolation -
  contradicting "Dependencies: None" (line 111). The spec describes scoping by role
  ("`company_admin`: always filtered; `admin`: selected-or-all", spec lines 117-119),
  which invites exactly this mistake.

  The ordering *does* hold, but only if Feature 1 implements scoping role-agnostically:
  "if `caller.company_id` is set, filter to it; an `admin` with no `company_id` and an
  explicit overview flag reads unfiltered." That expresses both the company_admin
  ("always has company_id") and admin-with-switcher ("selected company_id") cases
  without naming `Role.company_admin`. Feature 2 then only adds the enum value + matrix
  rows and the `CallerContext` validator rule "company_admin requires company_id"; the
  scoping helper is untouched.
- **Recommendation**: State in Feature 1 that the scoping predicate keys on
  `CallerContext.company_id` presence (+ an explicit cross-company override), **not** on
  the `company_admin` enum. State in Feature 2 that adding `company_admin` requires no
  change to Feature 1's scoping helper - only the matrix rows (all operational actions
  `admin: False`-equivalent for `company_admin`) and the `CallerContext` validator. This
  makes the F1->F2 dependency one-directional and keeps F1 independently testable
  (its tests use `admin` callers with/without `company_id`).

### Concern: The NAV "nesting" (Feature 4) and "allowedRoles" (Feature 2) are a structural co-design, not a "slot-in" - sequencing alone does not prevent rework

- **Affects**: Cross-Cutting (lines 86-90), Feature 2 (lines 188-193), Feature 4
  (lines 259-278), Sequencing (lines 290-297)
- **Problem**: The epic treats the shared-webui coupling as "Feature 2 establishes the
  structure; Features 3 and 4 slot in" (lines 86-90, 306). For Feature 3 (add
  `allowedRoles: [admin, company_admin]` to the existing `/bot` item) that is true.
  For Feature 4 it is not: today `NAV` is a **flat** array of leaf items
  (`services/webui/components/Sidebar.tsx` lines 32-44). Feature 4 introduces
  **nested sections** - maintenance-types under Vehicles, accidents under Events
  (plan lines 263-265). That is a change to the `NavItem` *type* (children/sub-sections),
  not a value added to an existing shape. If Feature 2 designs `NavItem` as
  `{...; allowedRoles}` flat leaves and lands first, Feature 4 must then retrofit
  nesting into both the type and the render loop (lines 83-127) - the exact "conflicting
  `Sidebar.tsx` rewrite" the risk row tries to avoid. Sequencing F4 after F2 does not
  fix it; it just decides who eats the rework.
- **Recommendation**: Have Feature 2 own the **full** `NavItem` shape up front -
  `allowedRoles` **and** an optional `children`/section affordance - even though
  Feature 2 itself adds no nested items. Feature 4 then only populates children and
  deletes the Chat entry. Alternatively, make Feature 4 a hard predecessor that defines
  the nested shape and Feature 2 layers `allowedRoles` on top. Either way, name the
  `NavItem` type (allowedRoles + children) as a single owned contract in one feature, and
  say so in the Cross-Cutting section rather than implying nesting is a free "slot-in."

### Concern: Feature 1's "every domain table" enumeration is inaccurate against the actual schema (missing tables, a non-existent one, a wrong table name)

- **Affects**: Feature 1 Context (lines 122-129), Requirements (lines 26-27), spec
  section 3 (lines 64-68)
- **Problem**: The enumerated list is "drivers, customers, vehicles, maintenance_types,
  accidents, events, attendance, reports/tickets, documents, config, kpi rollups,
  bot_users, bot_authorizations." Checked against `db/shepherd_db/models.py`:
  - **Omitted tenant-bearing tables**: `km_updates` (line 391), `vehicle_care`
    (line 421), `accident_attachments` (line 367), `channel_identities` (line 601).
    These hold tenant data (scoped today only transitively via vehicle/accident FKs).
    Whether each gets its own `company_id` (denormalize for direct repo filtering) or is
    scoped purely by joining its parent is a real Feature-1 design decision the plan does
    not surface. `repo.list_accidents` (line 232) loads attachments via `selectinload`,
    so attachment scoping rides on the accident filter today - fine, but it must be a
    *conscious* choice, and `_seed_*` for all four still needs the parent's company.
  - **`documents`** (listed line 128, spec line 66) **does not exist** as a table. There
    is a `documents` router but file/doc data lives in `reports`, `accident_attachments`,
    and `*_file_url` columns. The reference is ambiguous.
  - **`bot_users`** is the table named **`users`** in the ORM (`BotUser.__tablename__ =
    "users"`, line 657); the new identity table is `app_users`. Calling the bot table
    "bot_users" throughout the plan/spec will mislead the executor, especially next to
    the new `app_users`.
- **Recommendation**: Replace the prose enumeration with the actual table list and an
  explicit decision per child table (own `company_id` vs parent-scoped). Drop or rename
  the non-existent `documents` entry. Refer to the bot user table as `users`
  (`BotUser`) to avoid confusion with `app_users`.

### Concern: Repo-layer scoping blast radius is larger than "apply a helper" - many list functions have no scoping parameter at all today

- **Affects**: Feature 1 Scope (lines 144-149), Risk row 1 (line 303)
- **Problem**: The mitigation "centralize scoping in one repo-layer helper" understates
  the change. Numerous read functions in `repo.py` take **no** ownership/scope argument
  and select whole tables: `list_drivers` (92), `list_customers` (128), `list_accidents`
  (232), `list_reports` (333), `list_events` (349), `list_maintenance_types` (380),
  `list_attendance_month`/`list_attendance_day` (426, 440), `list_bot_users` (527),
  `list_bot_authorizations` (615), `list_kpi_daily` (512). Every one needs a new
  `company_id` parameter **and** every caller across the 16 routers
  (`services/fleet-api/app/routers/*.py`) must thread the caller's company through. A
  single helper does not retrofit those signatures; this is broad, mechanical, and
  exactly where a missed filter leaks. The work is correctly inside Feature 1, but the
  risk row should reflect "every list/read signature + every router call site," not just
  "one helper."
- **Recommendation**: In Feature 1, note that scoping is applied at *both* a shared
  helper and at each `list_*`/read signature + router call site, and make the
  cross-tenant test assertion (Risk row 1) per-resource, not generic. This is sizing
  guidance for the feature plan, not a structural change.

### Concern: Ownership of the `/bot` route's `allowedRoles` straddles Feature 2 and Feature 3

- **Affects**: Feature 2 (lines 188-193, 196-199), Feature 3 (lines 230-233), spec
  route enforcement (lines 172-185)
- **Problem**: Feature 2 "OWNS the nav/middleware role-gating mechanism" and builds the
  central `route -> allowedRoles` map. The spec says `/bot` is allowed for both roles
  (lines 177-178, 184). But Feature 3 is what makes the Bot tab visible/scoped for
  `company_admin` (lines 230-233, 240-241). If Feature 2 seeds `/bot` as admin-only and
  Feature 3 edits the map to add `company_admin`, that is a second editor of
  `middleware.ts`/`Sidebar.tsx` - the coupling the epic is trying to minimize. If
  Feature 2 seeds `/bot` as both-roles up front, Feature 3 only needs backend scoping +
  page behavior and touches neither shared file.
- **Recommendation**: Have Feature 2 seed `/bot -> [admin, company_admin]` in the
  middleware map and nav `allowedRoles` when it establishes the structure, so Feature 3's
  webui slice is backend/behavior only and does not re-edit the gating files. State this
  in Feature 3's "uses Feature 2's gating" note.

---

## Observations

- **Seed rewrite is non-trivial and correctly inside Feature 1.** `db/seed.py` uses raw
  `INSERT` statements with explicit column lists (e.g. `_seed_vehicles` lines 128-146,
  `_seed_drivers` lines 71-82). Backfill is not an `UPDATE` pass - every `INSERT` must
  gain a `company_id` value (the default company), and a `companies` insert must run
  first. `_seed_channel_identities` (lines 370-386) is also a raw insert that will need a
  company if `channel_identities` gets the column. The plan's "backfill existing seed
  rows" phrasing (line 142) slightly misdescribes this as backfill rather than
  per-insert column additions; worth a one-line clarification in Feature 1.

- **`middleware.ts` matcher is stale and thin** (`services/webui/middleware.ts` lines
  6-13): it lists `/missions/:path*` (no such route - the events tab routes to
  `/events`) and omits `/events`, `/accidents`, `/customers`, `/bot`, `/health`,
  `/maintenance-types`. Feature 2's "bring everything under the gate" is correct and the
  spec calls this out (lines 178); just confirm the stale `/missions` entry is removed.

- **`AUTH_JWT_SECRET` is not yet in either `.env.example`** (root or
  `services/webui/.env.example`); Feature 2 correctly owns adding it (plan line 180). The
  webui `lib/auth.ts` (lines 11-18) plaintext env check and the proxy's hardcoded
  `{role:'admin'}` (`app/api/fleet/[...path]/route.ts` line 10) match the plan's
  description exactly - Feature 2's webui scope is accurately targeted.

- **`CallerContext` validator placement** (`libs/shepherd_contracts/auth.py` lines
  20-26): Feature 1 adds the optional `company_id` field; the rule "`company_admin`
  requires `company_id`" must wait for Feature 2 (when the role exists). The plan implies
  this (lines 132-133) but does not say the validator rule itself is Feature 2 work -
  worth making explicit so Feature 1 does not add a rule referencing a non-existent role.

- **Sidebar count hooks vs tenant scoping**: `Sidebar.tsx` (lines 51-63) calls
  `useVehicles`/`useDrivers`/`useCustomers`/`useEvents`/`useAccidents`/`useHealth` for
  badge counts. Once these go through the company-scoped proxy, a `company_admin`'s
  badges become company-scoped automatically (good), but `useHealth` feeds the
  system-only Health tab's status dot - confirm the health call degrades gracefully for
  `company_admin` (who is denied Health) rather than 403-ing in the sidebar. Minor, but a
  candidate cross-feature integration check between Features 2 and 4.

- **Bot table FK target**: when adding `company_id` to `users`/`bot_authorizations`,
  note `cleanup_expired_bot_access()` (`bootstrap.sql` lines 87-92) deletes by
  `expires_at` only and needs no change - good, no hidden dependency there.
