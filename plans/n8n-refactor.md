# n8n Workflow Refactor - Sub-workflows + Sticky Notes

## Goal

Turn the single 146-node `shepherd-telegram-bot.json` into a **thin router
workflow that dispatches each feature to its own sub-workflow**, and document
every workflow with **sticky notes** (style inspired by
`plans/Telegram Bot Inline.json`).

Why:
- One giant canvas is hard to read, diff, and reason about.
- Each feature becomes independently viewable, testable, and editable.
- Sticky notes make the intent of every step explicit for the next maintainer.

Non-goals: changing behaviour. This is a structural refactor only. The data-access
policy stays as-is (only `bot_sessions` is touched directly; everything else via
the Fleet API).

---

## Target architecture

```
shepherd-telegram-bot (ROUTER)
  Telegram Trigger
    -> Code: Normalize Update
    -> HTTP: GET /whoami
    -> Code: Merge whoami
    -> Postgres: Read Session            (bot_sessions - the only direct DB read here)
    -> Code: Route Decision              (computes {feature, route} for ALL cases)
    -> Switch: Feature                   (one output per sub-workflow)
        -> Execute Workflow: <feature>   (passes the ctx item to the sub)
  + kept inline (too small to split): driver menu, admin menu, access-denied

sub-<feature> (one per case)
  Execute Workflow Trigger ("On Parent Call")  (receives ctx as $json)
    -> [single chain]              for one-shot features, OR
    -> Switch: Step (on ctx.route) -> handler chains   for multi-step features
```

### Routing model (key decision)

The **parent** owns all routing. `Code: Route Decision` is extended to merge what
today is split between `Route Decision` and `Active Flow Router`, producing two
fields on `ctx`:

- `feature` - which sub-workflow to call (e.g. `accident`, `clock`, `broadcast`).
- `route` - the fine-grained step (e.g. `accident_video`, `cmd_clock_in`,
  `update_details_value`), exactly the values used today.

`Switch: Feature` dispatches on `feature`. Inside a multi-step sub-workflow,
`Switch: Step` dispatches on `route`. One-shot sub-workflows need no inner switch.

This keeps every existing handler chain **byte-for-byte identical** - it is only
relocated. The active-flow resume case is just: when `sessionState.flow` is set,
`Route Decision` sets `feature = flowToFeature[flow]` and `route =` the active step.

### Context passing

The Execute Workflow node passes the current item (the full `ctx`) to the sub.
The sub's `Execute Workflow Trigger` emits that object as `$json`. Therefore:

- The two global anchors used throughout the current nodes,
  `$('Switch: Main Router')` and `$('Code: Active Flow Router')`, are rewritten in
  every relocated node to `$('On Parent Call')`.
- `.item.json` references become `.first().json` (the trigger emits a single item).
- Intra-flow anchors (e.g. `$('Code: Handle Accident Video')`,
  `$('Code: UpdateDetails Validate')`) are unchanged - those nodes move together
  with the flow.
- `$env.*` and `process.env.*` work unchanged (same n8n instance).

`ctx` shape passed to every sub: `{ chatId, isCallback, callbackData, text, video,
photo, messageId, whoami, sessionState, route }`.

---

## Decomposition

Sub-workflows (one file each, fixed IDs `sub-<feature>` so `executeWorkflow`
references resolve regardless of import order):

| # | Sub-workflow | Routes it owns | Steps |
|---|---|---|---|
| 1 | `sub-clock` | cmd_clock_in, cmd_clock_out | 2 one-shot |
| 2 | `sub-accident` | cmd_accident + accident_safe/video/road_clear/insurance_photo/driver_license/car_license/complete | 8-step machine |
| 3 | `sub-attendance-csv` | cmd_attendance_csv | one-shot |
| 4 | `sub-my-vehicle` | cmd_my_vehicle | one-shot |
| 5 | `sub-vehicle-issue` | cmd_vehicle_issue, vehicle_issue_text | 2-step |
| 6 | `sub-update-details` | cmd_update_details, update_details_field, update_details_value | 3-step |
| 7 | `sub-broadcast` | cmd_admin_broadcast, broadcast_message/confirm/cancel | multi-step |
| 8 | `sub-attendance-admin` | cmd_admin_attendance | one-shot |
| 9 | `sub-fleet-summary` | cmd_admin_summary | one-shot |
| 10 | `sub-maintenance` | cmd_admin_maintenance, cmd_maint_overdue, cmd_maint_log, maint_log_vehicle/type/km | menu + overdue + 3-step log |
| 11 | `sub-update-driver` | cmd_admin_update_driver, update_driver_pick/field/value | 3-step |
| 12 | `sub-invite-claim` | unknown_with_token | claim + welcome/invalid |

Kept inline in the router (1-node sends, not worth a sub-workflow):
`unknown_no_token` (access denied), `driver_main`, `admin_main` menus.

Total: 1 router + 12 sub-workflows = **13 files** in `services/n8n/workflows/`.

---

## Sticky notes (documentation)

Apply the reference style: large group notes + per-step notes.

- **Router**: one title note (overview + quick-start + credential list), one note
  over the backbone explaining the pipeline, one note over `Switch: Feature`
  listing the dispatch table.
- **Each sub-workflow**: one title note (what this case does, the Hebrew UX, which
  tables/endpoints it touches), and a short note over each logical step
  (e.g. "download from Telegram", "upload to S3", "advance session step").
- Colours follow the reference convention (title = colour 7, API = default,
  DB/session = colour 4, branching = colour 3/6).

Markdown content in notes uses `##` headers + emoji + bullet lists, matching
`plans/Telegram Bot Inline.json`.

---

## n8n plumbing details (to confirm during build)

- **Execute Workflow node** (`n8n-nodes-base.executeWorkflow`): `source = database`,
  `workflowId` referencing the sub's fixed ID. Confirm the exact `workflowId`
  shape for the running n8n version (string vs resource-locator object) via
  `mcp__n8n__get_node` before generating.
- **Trigger** (`n8n-nodes-base.executeWorkflowTrigger`): receives parent input;
  emits it as `$json`. Confirm input mode ("passthrough").
- **Fixed IDs**: every workflow JSON gets a stable top-level `id` (the monolith
  already needed this for Postgres-backed CLI import). The router's Execute
  Workflow nodes reference sub IDs; runtime resolution by ID means import order is
  irrelevant once all are imported.
- **Import**: `docker-compose` already runs `n8n import:workflow --input=/workflows/*.json`,
  so all 13 files auto-import on container start. No compose change needed.
- **Credentials**: unchanged (`Shepherd Telegram Bot`, `Shepherd DB`,
  `Shepherd AWS`) - referenced by the same IDs inside the sub-workflows that use
  them.

---

## Risks / limitations

- **No live E2E test**: behaviour can be validated structurally (JSON valid,
  references resolve, JS syntax, `validate_workflow`, successful import + workflow
  list) but a full Telegram round-trip needs a real bot token + chat. The relocation
  is mechanical and the Fleet API paths are already verified, so risk is mostly in
  the plumbing (trigger I/O, executeWorkflow IDs), which the validators cover.
- **Sub-workflow fan-out items**: features that emit multiple items (broadcast
  fan-out, accident admin notify) must keep their `Split`/per-item sends inside the
  sub - already self-contained, so no special handling.
- **Old single workflow**: replaced. Keep a copy at
  `plans/shepherd-telegram-bot.monolith.json` for reference/rollback.

---

## Execution steps

1. Confirm `executeWorkflow` / `executeWorkflowTrigger` schema for the running
   n8n version (MCP `get_node`).
2. Back up the monolith to `plans/`.
3. Write a generator that: extracts each feature's node cluster, builds each
   sub-workflow (trigger + nodes + inner switch + sticky notes + fixed id),
   rewrites anchors, and builds the router (backbone + merged Route Decision +
   Switch: Feature + Execute Workflow nodes + sticky notes).
4. Validate every file: JSON parse, unique ids/names, no dangling refs, JS
   `node --check`, and `mcp__n8n__validate_workflow`.
5. Import all into the running n8n; confirm `n8n list:workflow` shows 13 and the
   Execute Workflow references resolve.
6. Update `services/n8n/workflows/README.md` to document the new multi-workflow
   layout (router + per-feature subs).
7. Smoke-test whatever is possible without live Telegram (manual trigger with a
   pinned sample update per sub-workflow, if feasible).

---

## Status: IMPLEMENTED (2026-06-22)

Done and validated. Router + 12 sub-workflows generated, all 13 import cleanly
(`n8n import:workflow --separate`), the router's 12 Execute references resolve to
the imported sub ids, structural checks pass (0 errors), and all Code nodes are
JS-valid. Monolith backed up at `plans/shepherd-telegram-bot.monolith.json`.
docker-compose entrypoint switched to `--separate --input=/workflows`.

Resolved questions:
- One-shot features → kept as their own sub-workflows (per "each case").
- access-denied + both menus → inline in the router (single-node sends).
- n8n plumbing → `executeWorkflow` **v1.1** (resource-locator `workflowId`,
  auto-forwards input) + `executeWorkflowTrigger` **v1.2** (`inputSource:
  passthrough`).

Remaining (manual / not scriptable here):
- Activate the router workflow in the n8n UI (import deactivates it).
- Full Telegram E2E round-trip needs a live bot token + chat (not set yet).
