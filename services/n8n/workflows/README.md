# Shepherd Telegram Bot - Workflow Reference

The bot is Hebrew-only, invite-only, and n8n owns Telegram directly (no Channel
Gateway in the path). It is split into a **thin router workflow + one
sub-workflow per feature** (n8n Execute Sub-workflow). This document explains the
architecture and each flow.

- **Router:** `shepherd-telegram-bot.json` (id `shepherdtelegrambot01`) - the only
  workflow with the Telegram Trigger; it must be **activated** in the n8n UI.
- **Sub-workflows:** `sub-*.json` (12 files) - one per case, each starting with an
  Execute Workflow Trigger.
- **Trigger:** Telegram webhook (on the router only).

## Architecture

```
ROUTER  (shepherd-telegram-bot)
  Telegram Trigger → Normalize → GET /whoami → Merge → Read Session (bot_sessions)
    → Code: Route Decision  (computes {feature, route})
    → Switch: Feature
        menu_driver / menu_admin / access_denied  → inline send (1 node)
        every other feature                       → Execute Sub-workflow (passes ctx)

SUB  (sub-<feature>)
  On Parent Call (Execute Workflow Trigger, passthrough → emits ctx as $json)
    → [single chain]                 (one-shot features), or
    → Switch: Step (on ctx.route)    → step handler chains   (multi-step features)
```

- The **parent owns all routing**: `Route Decision` merges the old Route Decision +
  Active Flow Router into one node, producing `feature` (which sub) and `route`
  (which step). Active-flow resume maps `sessionState.flow → feature`.
- The sub receives the full `ctx` (`chatId, whoami, callbackData, text, video,
  photo, sessionState, route`) on `$json` from its trigger. Inside a sub, the
  cross-node anchor is `$('On Parent Call').first().json` (see Pattern E).

### Sub-workflow map

| Feature (`feature`) | Workflow | Routes | File |
|---|---|---|---|
| clock | Shepherd · Clock In/Out | cmd_clock_in, cmd_clock_out | `sub-clock.json` |
| accident | Shepherd · Accident Protocol | cmd_accident + 7 steps | `sub-accident.json` |
| attendance_csv | Shepherd · Monthly Attendance CSV | cmd_attendance_csv | `sub-attendance-csv.json` |
| my_vehicle | Shepherd · My Vehicle | cmd_my_vehicle | `sub-my-vehicle.json` |
| vehicle_issue | Shepherd · Report Vehicle Issue | cmd_vehicle_issue, vehicle_issue_text | `sub-vehicle-issue.json` |
| update_details | Shepherd · Update My Details | cmd_update_details + 2 steps | `sub-update-details.json` |
| broadcast | Shepherd · Broadcast | cmd_admin_broadcast + 3 | `sub-broadcast.json` |
| attendance_admin | Shepherd · Today's Attendance | cmd_admin_attendance | `sub-attendance-admin.json` |
| fleet_summary | Shepherd · Fleet Summary | cmd_admin_summary | `sub-fleet-summary.json` |
| maintenance | Shepherd · Maintenance | cmd_admin_maintenance, overdue, log+3 | `sub-maintenance.json` |
| update_driver | Shepherd · Update Driver | cmd_admin_update_driver + 3 | `sub-update-driver.json` |
| invite_claim | Shepherd · Invite Claim | unknown_with_token | `sub-invite-claim.json` |

`menu_driver`, `menu_admin`, `access_denied` are single-node sends kept inline in
the router. All 13 files auto-import via the container entrypoint
(`n8n import:workflow --separate --input=/workflows`).
- **Credentials required (create in n8n UI):**
  - `Shepherd Telegram Bot` (Telegram API) - referenced as credential id `1`
  - `Shepherd DB` (Postgres) - referenced as credential id `2`
  - `Shepherd AWS` (AWS) - referenced as credential id `3`; used by the accident
    `S3 Upload *` nodes to sign the PUT with SigV4. Without it the uploads 403.
- **Environment variables (set on the n8n container):**
  `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`, `FLEET_API_URL`,
  `INTERNAL_SERVICE_TOKEN`, `S3_BUCKET`, `AWS_ACCESS_KEY_ID`,
  `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`.

---

## Conventions (how nodes are configured)

The workflow uses a small set of node patterns repeatedly. Understanding these
five patterns explains ~90% of the nodes.

### Pattern A - Send a Telegram message (`httpRequest`)
Direct call to the Bot API because the built-in Telegram node cannot send
`reply_markup` (inline keyboards).
- **method:** `POST`
- **url:** `https://api.telegram.org/bot{{ $env.TELEGRAM_BOT_TOKEN }}/sendMessage`
- **header:** `Content-Type: application/json`
- **body:** `={{ JSON.stringify({ chat_id, text, parse_mode:'HTML', reply_markup }) }}`
- **options:** `neverError: true` so a Telegram 4xx doesn't abort the run.

### Pattern B - Call the Fleet API, GET (`httpRequest`)
- **method:** `GET`, **url:** `{{ $env.FLEET_API_URL }}/<path>`
- **headers:** `X-Internal-Token: {{ $env.INTERNAL_SERVICE_TOKEN }}` and
  `X-Caller-Context: {"role":"admin"}` (admin context = full read access).
- **options:** `neverError: true`, `responseFormat: json`.

### Pattern C - Call the Fleet API, POST (`httpRequest`)
Same headers as B plus `Content-Type: application/json`, `sendBody: true`,
`contentType: json`, and a `body` expression building the JSON payload.

### Data-access policy (important)
The workflow reaches the database **directly for one table only: `bot_sessions`**
(its own conversation/orchestration state). Every other read or write goes
through the Fleet API so auth, validation, and business rules are enforced in one
place. That includes clock-in/out (`POST /attendance/clock-in|clock-out`, which
enforce the reporting window server-side), driver edits (`PATCH /drivers/{id}`),
attendance reads (`GET /attendance/today`, `GET /attendance/{month}?driver_id=`),
overdue maintenance (`GET /vehicles`, filtered in a Code node), and config.

### Pattern D - Session read/write (`postgres`, cred `Shepherd DB`)
The **only** direct-DB pattern. Multi-step flows persist state in `bot_sessions`
keyed by `chat_id`.
- **Create/replace session:**
  `INSERT INTO bot_sessions (chat_id, state, updated_at) VALUES ($1,$2::jsonb,NOW())
   ON CONFLICT (chat_id) DO UPDATE SET state=$2::jsonb, updated_at=NOW()`
- **Patch one field:** `UPDATE bot_sessions SET state = jsonb_set(state,'{step}','"..."') WHERE chat_id=$1`
- **Merge:** `UPDATE bot_sessions SET state = state || $2::jsonb WHERE chat_id=$1`
- **Clear:** `DELETE FROM bot_sessions WHERE chat_id=$1`
- **params:** passed via `additionalFields.queryParams` as a JSON-stringified array.

### Pattern E - Cross-node data access (`code`)
Because Postgres/HTTP nodes overwrite `$json`, downstream nodes re-read the
originating node by name: `$('Node Name').first().json`. **Inside a sub-workflow**
the context anchor is `$('On Parent Call').first().json` (the Execute Workflow
Trigger that emits the `ctx` passed by the router). In the router itself, context
comes from `$('Code: Merge whoami')` / `$('Code: Route Decision')`.

### `chat_id` shape
`telegram_chat_id` is a Postgres `BIGINT`; Telegram chat ids exceed 32-bit.

---

## Router backbone (every update flows through these)

Lives in `shepherd-telegram-bot.json`.

| Node | Type | What it does |
|---|---|---|
| **Telegram Trigger** | telegramTrigger | Fires on every incoming update (message / callback_query). |
| **Code: Normalize Update** | code | Flattens the update into `{chatId, isCallback, callbackData, text, video, photo, messageId, startToken, isStart}`. Extracts `startToken` from `/start <token>`. Reduces a photo array to its largest size. |
| **HTTP: GET whoami** | httpRequest (B) | `GET /whoami?chat_id=` - resolves the chat to a bot user. `neverError` so a 404 (unknown user) doesn't abort. |
| **Code: Merge whoami** | code | Merges the normalized fields with the whoami result. `whoami=null` when status≠200, marking an unknown user. |
| **Postgres: Read Session** | postgres (D) | Reads `bot_sessions.state` for this chat (drives active-flow routing). |
| **Code: Route Decision** | code | Computes `{feature, route}`: unknown→`invite_claim`/`access_denied`; active session→`flowToFeature[flow]` + the resumed step; callback→feature+`cmd_*` via lookup; default→`menu_driver`/`menu_admin`. |
| **Switch: Feature** | switch (15 outputs) | Routes on `feature`. Inline sends for `menu_driver`/`menu_admin`/`access_denied`; every other feature → an **Execute Sub-workflow** node (see the Sub-workflow map above). |

The fine-grained `route` (e.g. `cmd_clock_in`, `accident_video`,
`update_details_value`) is passed into the sub-workflow, whose inner
`Switch: Step` dispatches to the matching step handler.

---

## Access control

### Invite claim (`/start <token>`)
| Node | Type | Detail |
|---|---|---|
| HTTP: Claim Invite Token | httpRequest (C) | `POST /bot-invite/claim {token, telegram_chat_id}`. 200 creates a `users` row; 400 = invalid/expired. |
| Code: Check Claim Result | code | Reads the status into a boolean. |
| Switch: Claim OK? | switch | Branch on success. |
| HTTP: Send Driver Menu After Claim | httpRequest (A) | Welcome + driver menu. |
| HTTP: Send Invalid Token Msg | httpRequest (A) | `❌ הקישור אינו תקף או שפג תוקפו.` |

### Locked / access denied
| Node | Type | Detail |
|---|---|---|
| HTTP: Send Access Denied | httpRequest (A) | `הגישה למערכת מוגבלת. 🔒` - any non-`/start` message from an unknown user. |

### Menus
| Node | Type | Detail |
|---|---|---|
| HTTP: Send Driver Main Menu | httpRequest (A) | Inline keyboard: clock_in, clock_out, vehicle_issue, accident_start, update_details, attendance_csv, my_vehicle. |
| HTTP: Send Admin Main Menu | httpRequest (A) | Inline keyboard: admin_attendance, admin_broadcast, admin_summary, admin_update_driver, admin_maintenance. |

---

## Active-flow dispatcher (multi-step resume)

When a session exists, the backbone routes to:

| Node | Type | Detail |
|---|---|---|
| **Code: Active Flow Router** | code | Reads `sessionState.{flow,step}` plus the current input type (callback / text / photo / video) and emits an `activeRoute`. Handles flows: `accident`, `broadcast`, `vehicle_issue`, `update_details`, `update_driver`, `maint_log`. A non-matching step yields `<flow>_wait` (dropped). |
| **Switch: Active Flow Routes** | switch (19 outputs) | Routes on `activeRoute`. |

### Switch: Active Flow Routes outputs
0 accident_safe · 1 accident_video · 2 accident_road_clear ·
3 accident_insurance_photo · 4 accident_driver_license · 5 accident_car_license ·
6 accident_complete · 7 broadcast_message · 8 broadcast_confirm ·
9 broadcast_cancel · 10 vehicle_issue_text · 11 update_details_field ·
12 update_details_value · 13 update_driver_pick · 14 update_driver_field ·
15 update_driver_value · 16 maint_log_vehicle · 17 maint_log_type ·
18 maint_log_km

---

## Flow 4.1 - Clock In / Clock Out

Goes through the Fleet API; the **attendance reporting window** (feature flag,
default off = any time allowed) is enforced **server-side** in the endpoint, not in
n8n. Config keys (`system_config`, editable on the WebUI config page):
`attendance_window_enabled`, `attendance_window_start`, `attendance_window_end`.

**Clock in** (`cmd_clock_in`):
| Node | Type | Detail |
|---|---|---|
| HTTP: POST Clock In | httpRequest (C) | `POST /attendance/clock-in {driver_id}`. Returns `{result, time, window_start, window_end}`; `result` ∈ `ok`/`already_in`/`blocked`. Idempotent + window check are in the API. |
| Code: Format Clock In | code | Maps `result` → Hebrew (`✅ כניסה נרשמה...` / `כבר נרשמת...` / `⛔ דיווח נוכחות אפשרי רק בין ...`). |
| HTTP: Send Clock In Result | httpRequest (A) | Sends the message. |

**Clock out** (`cmd_clock_out`): `HTTP: POST Clock Out` (`result` ∈ `ok`/`no_open`/`blocked`, plus `hours`) → `Code: Format Clock Out` → `HTTP: Send Clock Out Result`.

---

## Flow 4.3 - Accident Report (8-step state machine)

State lives in `bot_sessions.state = {flow:'accident', step, vehicleId, accidentDatetime, attachments[]}`.

**Start** (`cmd_accident`):
| Node | Type | Detail |
|---|---|---|
| HTTP: GET Driver Vehicle | httpRequest (B) | `GET /vehicles?driver_id=` - the vehicle in the accident. |
| Code: Start Accident Flow | code | Builds the initial state (step `awaiting_safe`) and Israel-time datetime. |
| Postgres: Save Accident Session | postgres (D) | Writes the session. |
| HTTP: Send Accident Step 1 | httpRequest (A) | Calming message + button `✅ אני במקום בטוח ועצרתי`. |

**Steps** (each resumes via the active dispatcher):
| activeRoute | Nodes | Purpose |
|---|---|---|
| accident_safe | Postgres: Accident Safe - Update Step → HTTP: Send Awaiting Video | Ask for a video. |
| accident_video | Code: Handle Accident Video → HTTP: TG GetFile Video → Code: Build S3 Key Video → HTTP: Download TG File Video → HTTP: S3 Upload Video → Postgres: Save Video Attachment → HTTP: Send Awaiting Road Clear | Download from Telegram, PUT to S3, record key in `state.attachments`. |
| accident_road_clear | Postgres: Accident Road Clear Step → HTTP: Send Awaiting Insurance Photo | Confirm road cleared, ask for the insurance photo. |
| accident_insurance_photo | Handle/GetFile/BuildKey/Download/Upload/Save Insurance → HTTP: Send Awaiting Driver License | Other side's insurance doc. |
| accident_driver_license | …Driver License… → HTTP: Send Awaiting Car License | Other side's driving licence. |
| accident_car_license | …Car License… → Postgres: Save Car License and Submit Accident → Code: Prepare Accident POST → HTTP: POST Create Accident → HTTP: Send Awaiting Manager Call | Last photo; **create the accident** (`POST /accidents`) with all attachments; ask the driver to phone the manager. |
| accident_complete | Postgres: Clear Accident Session → HTTP: Send Accident Complete to Driver → HTTP: GET Admins for Accident Notify → Code: Notify Admins Accident → HTTP: Send Accident Notify to Each Admin | Close out; DM every admin. |

Each media step shares the same 6-node S3 sub-pattern: `Handle*` (extract
`file_id`) → `TG GetFile*` (Bot API `getFile`) → `Build S3 Key*` (compose bucket
+ key) → `Download TG File*` (fetch bytes) → `S3 Upload*` (PUT, virtual-host
URL `https://{bucket}.s3.{region}.amazonaws.com/{key}`) → `Save*Attachment`
(append to `state.attachments`, advance `step`).

---

## Flow 5.2 - Broadcast (admin)

State: `{flow:'broadcast', step, message, drivers[]}`.
| activeRoute / entry | Nodes | Purpose |
|---|---|---|
| entry (`cmd_admin_broadcast`) | Postgres: Set Broadcast Session → HTTP: Send Broadcast Prompt | Ask for the message text. |
| broadcast_message | HTTP: GET Drivers for Broadcast → Code: Prepare Broadcast Confirm → Postgres: Save Broadcast State → HTTP: Send Broadcast Confirm Prompt | Count recipients, ask to confirm. |
| broadcast_confirm | Code: Prepare Broadcast Send → HTTP: Send Broadcast Message to Each Driver → Postgres: Clear Broadcast Session → HTTP: Send Broadcast Sent Confirm | Fan out one message per driver (`recipientChatId`). |
| broadcast_cancel | Postgres: Clear Broadcast Cancel Session → HTTP: Send Broadcast Cancelled | Abort. |

---

## Flow 5.1 / 5.3 - Attendance & Fleet Summary (admin, single-shot)

| Flow | Nodes |
|---|---|
| Attendance (`cmd_admin_attendance`) | Postgres: Get Attendance Today → Code: Format Attendance → HTTP: Send Attendance Report |
| Fleet summary (`cmd_admin_summary`) | HTTP: GET Fleet KPI (`GET /kpi/latest`) → Code: Format Fleet Summary → HTTP: Send Fleet Summary |

---

## Flow 4.6 - My Vehicle (driver, single-shot)

| Node | Type | Detail |
|---|---|---|
| HTTP: GET My Vehicle | httpRequest (B) | `GET /vehicles?driver_id={{ $json.whoami.driver_id }}`. |
| Code: Format My Vehicle | code | Reads chat from `$('Switch: Main Router')`; formats vendor/model/plate/type/km, or a "no vehicle" message. |
| HTTP: Send My Vehicle | httpRequest (A) | Sends the formatted card. |

---

## Flow 4.5 - Monthly Attendance CSV (driver, single-shot)

Sends the **current month** as a CSV document. *(No month picker - simplification.)*
| Node | Type | Detail |
|---|---|---|
| Postgres: Get My Attendance Month | postgres | Rows for `driver_id` where `date_trunc('month',work_date)=date_trunc('month',CURRENT_DATE)`. `alwaysOutputData` so an empty month still flows. |
| Code: Build Attendance CSV | code | Builds `תאריך,כניסה,יציאה,שעות`, computes worked hours, prepends a UTF-8 BOM (Excel Hebrew), returns the file as **binary** (`binary.data`, base64). |
| HTTP: Send Attendance CSV | httpRequest | `POST /sendDocument`, `multipart-form-data`: `chat_id` + `document` from `inputDataFieldName: data`. |

---

## Flow 4.2 - Report Vehicle Issue (driver)

Free-text fault report written to the `events` table. *(The maintenance-type
keyboard from the original plan is omitted; a fault is free text - the type
catalog is used by the maintenance-log flow 5.5.)*

**Entry** (`cmd_vehicle_issue`):
| Node | Type | Detail |
|---|---|---|
| Postgres: Set VehicleIssue Session | postgres (D) | `{flow:'vehicle_issue', step:'awaiting_description'}`. |
| HTTP: Send VehicleIssue Prompt | httpRequest (A) | `🔧 תאר/י את התקלה ברכב`. |

**Resume** (`vehicle_issue_text`):
| Node | Type | Detail |
|---|---|---|
| HTTP: GET Issue Vehicle | httpRequest (B) | Find the driver's vehicle. |
| Code: Prepare Issue Event | code | `{chatId, vehicleId, message}`. |
| HTTP: POST Issue Event | httpRequest (C) | `POST /events {event_type:'warning', severity:'warning', message:'תקלה מהנהג: …', source_type:'telegram', vehicle_id}`. |
| Postgres: Clear VehicleIssue Session | postgres (D) | Clear session. |
| HTTP: Send Issue Confirm | httpRequest (A) | `✅ התקלה נרשמה.` |

---

## Flow 4.4 - Update My Details (driver)

State: `{flow:'update_details', step, field}`. Editable fields: licence expiry,
licence number, phone.

**Entry** (`cmd_update_details`): `Postgres: Set UpdateDetails Session` (step
`awaiting_field`) → `HTTP: Send UpdateDetails Menu` (keyboard:
`ud_license_valid`, `ud_license_number`, `ud_phone`).

**Pick field** (`update_details_field`):
| Node | Detail |
|---|---|
| Code: UpdateDetails SetField | Stores chosen field, builds the value prompt, sets step `awaiting_value`. |
| Postgres: Save UpdateDetails Field | Persist session. |
| HTTP: Send UpdateDetails ValuePrompt | Ask for the new value. |

**Enter value** (`update_details_value`):
| Node | Detail |
|---|---|
| Code: UpdateDetails Validate | Validates by field - date `DD/MM/YYYY`→`YYYY-MM-DD`; phone `^0\d{8,9}$`; licence non-empty. Sets `{valid, column, value, driverId}`. |
| IF: UpdateDetails Valid | Branch on `valid`. |
| Postgres: Update Driver Field *(true)* | One static `UPDATE drivers` using `CASE WHEN $2=<col>` so only the chosen column changes (no dynamic SQL). |
| Postgres: Clear UpdateDetails Session *(true)* | Clear session. |
| HTTP: Send UpdateDetails Confirm *(true)* | `✅ הפרטים עודכנו…` |
| HTTP: Send UpdateDetails Invalid *(false)* | Re-prompts with the error; session kept so the driver can retry. |

> Phone change does **not** auto-issue a new invite here (re-link requires the
> new device; that's an admin action from the WebUI driver card).

---

## Flow 5.4 - Update Driver (admin)

State: `{flow:'update_driver', step, targetDriverId, field}`. Three steps: pick
driver → pick field → enter value (same validation as 4.4).

**Entry** (`cmd_admin_update_driver`):
| Node | Detail |
|---|---|
| HTTP: GET Drivers List | `GET /drivers`. |
| Code: Build Drivers Keyboard | Inline keyboard, callback `ud2_driver_<driver_id>` (capped 50). |
| Postgres: Set UpdateDriver Session | step `awaiting_driver`. |
| HTTP: Send Drivers Keyboard | `בחר/י נהג לעדכון`. |

**Pick driver** (`update_driver_pick`): `Code: UpdateDriver SetDriver` (store
`targetDriverId`, step `awaiting_field`) → `Postgres: Save UpdateDriver Driver` →
`HTTP: Send UpdateDriver FieldMenu` (callbacks `ud2_field_*`).

**Pick field** (`update_driver_field`): `Code: UpdateDriver SetField` (map to the
shared field keys, step `awaiting_value`) → `Postgres: Save UpdateDriver Field` →
`HTTP: Send UpdateDriver ValuePrompt`.

**Enter value** (`update_driver_value`): `Code: UpdateDriver Validate` (driverId =
`targetDriverId`) → `IF: UpdateDriver Valid` → *true:* `Postgres: Update Target
Driver` → `Postgres: Clear UpdateDriver Session` → `HTTP: Send UpdateDriver
Confirm`; *false:* `HTTP: Send UpdateDriver Invalid`.

> No pagination: up to 50 drivers are listed in one keyboard.

---

## Flow 5.5 - Maintenance (admin)

**Menu** (`cmd_admin_maintenance`): `HTTP: Send Maintenance Menu` - two buttons:
`maint_overdue`, `maint_log`. Both are plain callbacks (no session yet), mapped
by Route Decision to `cmd_maint_overdue` / `cmd_maint_log`.

**View overdue** (`cmd_maint_overdue`):
| Node | Detail |
|---|---|
| Postgres: Get Overdue Maintenance | `vehicles` where `current_km >= next_maintenance_km`, ordered by how far past due. `alwaysOutputData`. *(km-based, not date-based.)* |
| Code: Format Overdue | Build the report or `✅ אין תחזוקות באיחור`. |
| HTTP: Send Overdue | Send it. |

**Log event** (`cmd_maint_log`) - state `{flow:'maint_log', step, vehicleId, maintType}`:
| Step | Nodes |
|---|---|
| entry | HTTP: GET Vehicles For Maint → Code: Build Maint Vehicle Keyboard (callbacks `ml_veh_<vehicle_id>`) → Postgres: Set MaintLog Session → HTTP: Send Maint Vehicle Keyboard |
| maint_log_vehicle | Code: MaintLog SetVehicle → HTTP: GET Maint Types (`/maintenance-types`) → Code: Build Maint Type Keyboard (callbacks `ml_type_<name>`, capped 64 bytes) → Postgres: Save MaintLog Vehicle → HTTP: Send Maint Type Keyboard |
| maint_log_type | Code: MaintLog SetType → Postgres: Save MaintLog Type → HTTP: Send Maint KM Prompt |
| maint_log_km | Code: MaintLog Validate KM → IF: MaintLog KM Valid → *true:* HTTP: POST Vehicle Care (`POST /vehicle_care {vehicle_id, service_date=today, maintenance_type, km_at_service}`) → Postgres: Clear MaintLog Session → HTTP: Send Maint Logged Confirm; *false:* HTTP: Send Maint KM Invalid |

> `ml_type_<name>` callback data is capped at 64 bytes (Telegram limit). Very
> long maintenance-type names would truncate - keep names short, or switch to an
> index-based key if that becomes a problem.

---

## Known simplifications

- **Attendance CSV:** current month only (no month/year picker).
- **Vehicle issue:** free text → `events`; no maintenance-type selection.
- **Update driver / maint log:** lists are capped at 50 entries, no pagination.
- **Overdue maintenance:** km-based threshold only.
- **Phone update (driver):** updates `drivers.phone_number`; re-issuing the bot
  invite for the new device is done from the WebUI driver card.

## Editing the workflow

The flows and routing were generated/repaired programmatically. If you change
the Main Router or Active Flow Routes outputs, keep the `rules` array and the
`connections` array index-aligned (the original off-by-one bug came from editing
one without the other). After importing into n8n, re-attach the two credentials.
