# Telegram Bot - Implementation Plan

## Overview

A Hebrew-language interactive Telegram bot for Shepherd fleet management.
Drivers and admins interact via inline-keyboard menus. All text is in Hebrew.

**Architecture decision:** a dedicated `services/telegram-bot` (aiogram 3,
long-polling) owns Telegram directly - no public HTTPS / tunnel needed. Fleet
API is its only tool layer; multi-step flow state lives in `bot_sessions`. The
existing Channel Gateway continues serving the webapp channel and cron
notifications; it is not extended for this feature.

> History: this was first built as an n8n workflow (`services/n8n`), then
> rewritten 1:1 as the native aiogram service. The flow specs, Hebrew copy, DB
> schema, and Fleet API contracts below are unchanged; only Phases 3 and 6
> (delivery + env) describe the aiogram service rather than n8n.

---

## What Already Exists (do not rebuild)

| Thing | Location |
|---|---|
| `accidents` table | `db/shepherd_db/models.py:321` |
| `accident_attachments` table + category enum | `db/shepherd_db/models.py:350` |
| `attendance_records` table with `clock_in`/`clock_out` (Text "HH:MM") | `db/shepherd_db/models.py:555` |
| `channel_identities` table (Telegram `external_id` -> `phone_number`) | `db/shepherd_db/models.py:584` |
| `drivers`, `vehicles`, `maintenance_records`, `maintenance_types` | same file |

---

## Phase 1 - DB Migrations

### 1.1 - New `bot_invite_tokens` table

Access to the bot is invite-only. When a driver is registered (or their
phone number changes), a one-time token is generated and shown in the WebUI
as a Telegram deep link. The admin copies the link and shares it with the
driver (via SMS, WhatsApp, etc.). Without a valid token, `/start` is rejected.

```sql
CREATE TABLE bot_invite_tokens (
    token       TEXT PRIMARY KEY,          -- random UUID, URL-safe
    driver_id   UUID NOT NULL REFERENCES drivers(driver_id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT now() + INTERVAL '7 days',
    used_at     TIMESTAMPTZ             -- NULL = not yet claimed
);
```

**Token lifecycle:**
- Created: when a driver is first registered, or when their phone number is
  updated (old token is invalidated by setting `expires_at = now()`).
- Consumed: on `/start <token>` - bot validates token, creates `users` row,
  sets `used_at = now()`. Token cannot be reused.
- Expired: tokens older than 7 days are rejected. Admin can regenerate from
  WebUI.

**Why phone-change triggers a new token:** a phone change often means a new
device and a new Telegram account (new `chat_id`). The new token lets the
driver re-link their new `chat_id` to their existing `driver_id`. The old
`users` row (old `chat_id`) is deleted when the new token is claimed.

### 1.2 - New `users` table

Auth/permissions layer. A row is created only after a valid invite token is
claimed via `/start <token>`. Admins are users with `role = 'admin'`.

```sql
CREATE TYPE user_role_enum AS ENUM ('admin', 'driver');

CREATE TABLE users (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_chat_id BIGINT UNIQUE NOT NULL,
    role             user_role_enum NOT NULL DEFAULT 'driver',
    driver_id        UUID REFERENCES drivers(driver_id) ON DELETE SET NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Admin users need not be drivers - their `driver_id` may be NULL. They are
created either by claiming an admin invite token or by an existing admin
promoting them in the WebUI (see Phase 7).

### 1.3 - New `bot_sessions` table

Holds in-progress multi-step flow state per chat. TTL-expired rows can be
cleaned by a pg_cron job or simply left (they are overwritten on next use).

```sql
CREATE TABLE bot_sessions (
    chat_id     BIGINT PRIMARY KEY,
    state       JSONB NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`state` shape example (accident flow, step 3):
```json
{ "flow": "accident", "step": "awaiting_vehicle_clear", "accident_id": "uuid" }
```

### 1.4 - Extend `accident_attachment_category_enum`

Two categories are missing for the bot flow:

```sql
ALTER TYPE accident_attachment_category_enum
    ADD VALUE IF NOT EXISTS 'another_driver_license';
ALTER TYPE accident_attachment_category_enum
    ADD VALUE IF NOT EXISTS 'accident_video';
```

> **Note:** `ADD VALUE` on a PG enum cannot be rolled back inside a
> transaction. The Alembic migration must use `op.execute()` directly, not
> `op.alter_column()`, and must set `transaction_per_migration = False` or
> use a non-transactional block.

---

## Phase 2 - Fleet API Changes

**Service:** `services/fleet-api` (FastAPI)

### 2.1 - `GET /whoami`

```
GET /whoami?chat_id=<telegram_chat_id>
```

**Response 200:**
```json
{ "role": "driver", "driver_id": "uuid", "user_id": "uuid" }
```
or
```json
{ "role": "admin", "driver_id": null, "user_id": "uuid" }
```

**Response 404:** `{ "detail": "unknown" }`

Logic: look up `users` by `telegram_chat_id`. Return role + driver_id or 404.

The bot calls this on every incoming Telegram update before routing any flow.

### 2.2 - `POST /bot-invite` (generate invite token)

Called by the WebUI when a driver is registered or their phone changes.

```
POST /bot-invite
Body: { "driver_id": "uuid" }
```

**Response 201:**
```json
{
  "token": "a1b2c3d4-...",
  "deep_link": "https://t.me/<BOT_USERNAME>?start=a1b2c3d4",
  "expires_at": "2026-06-28T00:00:00Z"
}
```

Logic:
1. Invalidate any existing unused token for this `driver_id` (set
   `expires_at = now()`).
2. Generate a new UUID token.
3. Insert into `bot_invite_tokens`.
4. Return the deep link for the admin to share.

### 2.3 - `POST /bot-invite/claim` (called by the bot)

When a driver sends `/start <token>`:

```
POST /bot-invite/claim
Body: { "token": "a1b2c3d4", "telegram_chat_id": 123456789 }
```

**Response 200:** `{ "driver_id": "uuid", "role": "driver" }`
**Response 400:** token invalid, expired, or already used.
**Response 409:** `telegram_chat_id` already has a `users` row (phone
change re-link case) - the API deletes the old `users` row and proceeds.

Logic:
1. Look up token - reject if not found, expired, or `used_at` set.
2. Set `used_at = now()`.
3. Upsert `users (telegram_chat_id, role='driver', driver_id)`.
4. Return driver info.

### 2.4 - `PATCH /users/:user_id/role` (WebUI admin only)

```
PATCH /users/<user_id>/role
Body: { "role": "admin" | "driver" }
```

**Response 200:** updated user object.

Guards: caller must be authenticated as an admin (WebUI session). An admin
cannot demote themselves.

---

## Phase 3 - Bot Service (aiogram)

A single long-polling worker (`services/telegram-bot`, `python -m app.main`).
Every update is flattened to a `Ctx`, then routed by pure functions.

### Entry point

```
update -> normalize -> GET /whoami?chat_id=<chat.id> -> read bot_sessions
       -> route_decision(ctx) -> (feature, route) -> FEATURES[feature](ctx, route)
```

`route_decision` precedence: unknown user -> invite-claim / access-denied; a
slash command (the ☰ menu) preempts an in-progress flow; an active session
resumes its step via `active_route`; a menu callback starts a feature;
otherwise show the role menu. `app/router.py` holds this logic; `app/flows/*`
holds one handler per feature. Role is gated in the bot (`FEATURE_ROLES`) and
re-enforced by Fleet API.

### Unknown user (no `users` row)

Two sub-cases:

**A - `/start <token>` message:** token is present in the text. The bot asks the
driver to share their Telegram contact (phone), then claims with the phone for
identity verification.
```
bot -> request contact share -> POST /bot-invite/claim {token, chat_id, phone_number}
  -> 200: users row created, send welcome message
  -> 403: phone mismatch    -> rejection
  -> 400: invalid/expired   -> rejection
```

Welcome message (200):
```
ברוך הבא למערכת Shepard! 👋
הגישה שלך אושרה.
```
Then immediately show the driver main menu.

Rejection message (400):
```
❌ הקישור אינו תקף או שפג תוקפו.
פנה/י למנהל לקבלת קישור חדש.
```

**B - Any other message (no token):** user is not registered and has no
invite link.
```
הגישה למערכת מוגבלת. 🔒
לקבלת גישה פנה/י למנהל שלך.
```
No further action. No contact-share prompt.

### State routing (for multi-step flows)

Before role-switch, read `bot_sessions` for the chat_id. If `state.flow` is
set, route to the active flow handler regardless of message type (photo,
video, text, callback_query). This is how mid-flow media uploads are caught.

---

## Phase 4 - Driver Menu and Flows

Main menu (sent on `/start` or `🏠 תפריט ראשי`):

```
🚗 ניהול נהג - Shepard
━━━━━━━━━━━━━━━━
[⏱ כניסה לעבודה]   [🚪 יציאה מעבודה]
[🔧 דיווח תקלה]    [🚨 דיווח תאונה]
[✏️ עדכון פרטים]   [📊 דוח נוכחות]
[🚗 הרכב שלי]
```

### Flow 4.1 - Clock In / Clock Out

**Clock in:**
1. Check `attendance_records` for `(driver_id, today)`.
2. If row exists and `clock_in` already set: reply `כבר נרשמת כניסה היום בשעה <time>.`
3. Otherwise: `INSERT ... clock_in = HH:MM` (or `UPDATE` if row exists without clock_in).
4. Reply: `✅ כניסה נרשמה בהצלחה בשעה <time>.`

**Clock out:**
1. Find today's row with `clock_in` set and `clock_out` null.
2. If not found: `לא נמצאה כניסה פתוחה להיום.`
3. Otherwise: `UPDATE ... clock_out = HH:MM`.
4. Reply: `✅ יציאה נרשמה. סה"כ: <hours> שעות.`

### Flow 4.2 - Report Vehicle Issue

1. Fetch driver's coupled vehicle from `drivers.vehicle_id`.
2. Fetch maintenance types from `maintenance_types` catalog.
3. Show inline keyboard of types.
4. On selection: prompt for free-text notes.
5. Insert `maintenance_records` row.
6. Reply: `✅ התקלה נרשמה.`

### Flow 4.3 - Accident Report (multi-step)

State machine stored in `bot_sessions`. Steps:

| Step key | Bot message | Wait for |
|---|---|---|
| `start` | הודעת רגיעה (see below) | button: `✅ אני במקום בטוח ועצרתי` |
| `awaiting_video` | בקשת סרטון (see below) | video upload -> S3 |
| `awaiting_vehicle_clear` | פינוי רכב (see below) | button: `✅ הכביש פנוי` |
| `awaiting_insurance_photo` | `📸 צלם את מסמך הביטוח של הצד השני` | photo -> S3 |
| `awaiting_driver_license_photo` | `📸 צלם את רישיון הנהיגה של הצד השני` | photo -> S3 |
| `awaiting_car_license_photo` | `📸 צלם את רישיון הרכב של הצד השני` | photo -> S3 |
| `awaiting_manager_call` | הוראות התקשרות עם מנהל (see below) | button: `✅ דיברתי עם המנהל` |
| `done` | סיכום + התראה לאדמינים | - |

**Full Hebrew messages:**

Step `start`:
```
🚨 דיווח תאונה

קודם כל - תירגע/י. 🫁
שתה/י מים, נשום/י עמוק.

📍 עצור/י במקום בטוח בצד הדרך.
🚫 אל תזיז/י את הרכב עדיין!

כשאת/ה במקום בטוח ועצרת, לחץ/י להמשך:
[✅ אני במקום בטוח ועצרתי]
```

Step `awaiting_video`:
```
📹 כעת צלם/י סרטון של האירוע.

בסרטון:
- הסבר/י מה קרה בתאונה
- הראה/י את אזור התאונה
- הראה/י את כל הרכבים המעורבים
- הראה/י את הנזק לרכב שלך

שלח/י את הסרטון כאן:
```

Step `awaiting_vehicle_clear`:
```
✅ הסרטון התקבל.

🚗 כעת פנה/י את הכביש בצורה בטוחה
   והזז/י את הרכב לצד.

כשהכביש פנוי:
[✅ הכביש פנוי]
```

Step `awaiting_manager_call`:
```
📞 צור/י קשר עם המנהל שלך עכשיו
   ופעל/י לפי הנחיותיו.

כשסיימת לדבר:
[✅ דיברתי עם המנהל]
```

Step `done` (to driver):
```
✅ דיווח התאונה הושלם.
המנהלים קיבלו עדכון.
מספר דיווח: #<accident_id_short>
```

Admin DM (sent to ALL rows in `users` where `role = 'admin'`):
```
🚨 דיווח תאונה חדש

נהג: <driver_name>
רכב: <plate> - <make> <model>
זמן: <datetime>
מזהה: #<accident_id_short>

קבצים: סרטון + 3 תמונות מסמכים
```

**DB writes during accident flow:**
- On `start`: `INSERT INTO accidents (vehicle_id, driver_id, datetime)` -> get `accident_id`, save to session.
- On video received: upload to S3 -> `INSERT INTO accident_attachments (accident_id, category='accident_video', file_url)`.
- On each doc photo: `INSERT INTO accident_attachments` with matching category.

### Flow 4.4 - Update Personal Details

Inline keyboard:
```
[📅 עדכון תוקף רישיון]
[🪪 עדכון מספר רישיון/ת.ז.]
[📱 עדכון טלפון]
```

Each sub-flow: prompt for new value, validate, `UPDATE drivers SET ... WHERE driver_id = ?`.

Phone update also updates `channel_identities.phone_number` AND triggers a
new invite token via `POST /bot-invite` - the WebUI shows the admin a fresh
deep link to share with the driver so they can re-link their new device.

License expiry: expect `DD/MM/YYYY` format, store as `Date`.

### Flow 4.5 - Monthly Attendance CSV

1. Show month picker (inline keyboard: `ינואר` `פברואר` ... `דצמבר` + year).
2. Query `attendance_records` for `(driver_id, work_date BETWEEN first..last)`.
3. Build CSV:
   ```
   תאריך,כניסה,יציאה,שעות
   01/06/2026,08:03,17:12,9.15
   ```
4. Send as file: `נוכחות_<driver_name>_<month>_<year>.csv`

### Flow 4.6 - View My Vehicle

Query `vehicles JOIN drivers` on `drivers.vehicle_id`.
Reply with:
```
🚗 הרכב שלך

יצרן: <make>
דגם: <model>
לוחית: <plate>
סוג: <type>
ק"מ אחרון: <last_km>
```

---

## Phase 5 - Admin Menu and Flows

Main menu:

```
⚙️ פאנל ניהול - Shepard
━━━━━━━━━━━━━━━━
[👥 נוכחות היום]    [📢 שידור הודעה]
[🚗 סיכום צי]       [✏️ עדכון נהג]
[🔧 תחזוקה]
```

### Flow 5.1 - Today's Attendance

Query `attendance_records` where `work_date = today`.
Join with `drivers`.

```
👥 נוכחות - <today_date>

✅ במקום (X):
- יוסי כהן  08:03 -> בעבודה
- דנה לוי   07:55 -> בעבודה

⏳ לא נכנסו עדיין (Y):
- משה אברהם
- רחל דוד
```

### Flow 5.2 - Broadcast Message

1. Prompt: `הקלד/י את ההודעה לשליחה לכל הנהגים:`
2. Admin types message.
3. Confirm: `שולח לX נהגים - אישור?` `[✅ שלח] [❌ ביטול]`
4. On confirm: fetch all `users` where `role = 'driver'`, send DM to each.

### Flow 5.3 - Fleet Status Summary

Query aggregations:

```
🚗 סיכום צי

רכבים פעילים: X
נהגים מחוברים היום: Y
תקלות פתוחות: Z
תחזוקות באיחור: W
```

### Flow 5.4 - Update Driver Data

1. Show list of drivers (paginated inline keyboard if >10).
2. On selection: show fields to update (same as Flow 4.4 but for any driver).
3. Update `drivers` row.

### Flow 5.5 - Maintenance

Sub-menu:
```
[📋 תחזוקות באיחור]
[➕ רשום אירוע תחזוקה]
```

**View overdue:**
Query `maintenance_records` for records where next-due date < today.
List by vehicle, sorted by most overdue.

**Log new event:**
1. Pick vehicle (inline keyboard).
2. Pick type from `maintenance_types` catalog.
3. Enter date (default: today).
4. Enter notes (optional, skip button).
5. `INSERT INTO maintenance_records`.
6. Reply: `✅ אירוע התחזוקה נרשם.`

---

## Phase 6 - Bot Environment Variables

```env
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_BOT_USERNAME=ShepherdBot
FLEET_API_URL=http://fleet-api:8000
INTERNAL_SERVICE_TOKEN=change-me
DATABASE_URL=postgresql+psycopg://shepherd:shepherd@postgres:5432/shepherd
S3_BUCKET_ACCIDENTS=shepherd-accidents
S3_BUCKET_DOCS=shepherd-docs
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1
OPENAI_API_KEY=...   # Whisper STT (accident voice description)
GEMINI_API_KEY=...   # Gemini vision (admin document scan)
```

---

## Phase 7 - WebUI: Bot User Management

**Location:** new section in the existing Next.js admin console
(`services/webui`). Add a "ניהול בוט" (Bot Management) tab.

### 7.1 - Driver invite panel (in existing Drivers section)

When an admin creates or edits a driver, a "Telegram" card is shown:

```
חיבור טלגרם
━━━━━━━━━━━━━━━━
סטטוס: לא מחובר / מחובר (chat_id)

[🔗 צור קישור הזמנה]
```

Clicking "צור קישור הזמנה" calls `POST /bot-invite` and shows the deep
link in a copyable text field with a "העתק" button. Admin shares it with
the driver via any channel.

When phone number is saved (PATCH driver), the WebUI automatically calls
`POST /bot-invite` for that driver and surfaces the new link inline.

### 7.2 - Bot users table (new "ניהול בוט" section)

Lists all rows from `users`. Columns:

| שם | תפקיד | Telegram ID | מזוהה מאז | פעולות |
|---|---|---|---|---|
| יוסי כהן | נהג | 123456789 | 01/06/2026 | [שנה תפקיד] |
| דנה לוי | אדמין | 987654321 | 15/05/2026 | [שנה תפקיד] |

"שנה תפקיד" button: opens a confirm dialog, calls
`PATCH /users/:user_id/role`. An admin cannot change their own role.

### 7.3 - Pending invites table

Lists `bot_invite_tokens` where `used_at IS NULL AND expires_at > now()`.

| שם נהג | קישור | יפוג בתאריך | פעולות |
|---|---|---|---|
| משה אברהם | [העתק] | 28/06/2026 | [בטל] [חדש] |

"בטל" sets `expires_at = now()`. "חדש" calls `POST /bot-invite` for that
driver and replaces the row.

---

## Implementation Order

1. **Alembic migrations** (Phase 1) - `bot_invite_tokens`, `users`,
   `bot_sessions`, enum extension.
2. **Fleet API** (Phase 2) - `/whoami`, `/bot-invite`, `/bot-invite/claim`,
   `PATCH /users/:id/role`.
3. **Bot routing core** - normalize -> whoami -> route_decision -> role menu;
   phone-verified token claim on `/start`; locked message for unknown users.
4. **Driver flows** in order: clock-in/out, view vehicle, update details,
   monthly CSV, vehicle issue, accident.
5. **Admin flows** in order: attendance, fleet summary, broadcast, update
   driver, maintenance.
6. **WebUI** (Phase 7) - invite panel on driver card, bot users table,
   pending invites table.

---

## Open Questions

- [x] Which `drivers` column links a driver to their vehicle? - The bot doesn't
  read a column; `fleet.driver_vehicle()` calls `GET /vehicles` with a driver
  caller-context and Fleet API's ownership filter returns the coupled vehicle.
- [x] Is there a dedicated S3 bucket for accidents? - Yes: `shepherd-accidents`
  (`S3_BUCKET_ACCIDENTS`) for accident media; scanned documents go to
  `shepherd-docs` (`S3_BUCKET_DOCS`).
- [x] Pagination strategy for large driver lists in admin flows (>10 drivers)?
  - `keyboards.pick_list` caps at 50 entries, one per row, **no pagination**.
  Upgrade to paged keyboards if a fleet exceeds that.
- [x] Should clock-in be blocked if the driver has no coupled vehicle? -
  No; attendance is independent of vehicle assignment. The reporting window is
  enforced server-side (`result: "blocked"`).
- [x] How are admin users first created? - Via the WebUI directly. The
  bot users table (Phase 7.2) allows promoting any registered driver to
  admin without requiring DB access.
