# telegram-bot

Phone-enrolled Hebrew Telegram bot for Shepherd. Replaces the former n8n workflow.
Built on **aiogram 3** with **long-polling** (no public HTTPS / tunnel). Fleet API is
the only tool layer (sole DB writer + permission enforcer); the bot touches the DB
directly only for its own `bot_sessions` conversation state.

## Access (no invites)

There are no invite tokens. An unknown user opens the bot, shares their contact once,
and Fleet API's `POST /bot-enroll` matches the phone: an **active driver** is granted
the driver role automatically, otherwise a non-expired **bot authorization** (admins +
temporary grants) decides the role. On success the bot sends a Hebrew welcome listing
that role's commands. Temporary roles carry an `expires_at`; an expired role (or a
deactivated driver) loses access - `whoami` denies immediately, and a pg_cron job
sweeps the rows.

## Architecture

```
update -> normalize -> GET /whoami -> read bot_sessions -> route_decision(feature, route)
  unknown            -> share contact -> POST /bot-enroll (phone match) / not authorized
  active session     -> resume the flow's next step
  menu callback      -> start a feature
  otherwise          -> role menu (driver / admin)
```

- `app/router.py` - ports the n8n Route Decision + Active Flow Router.
- `app/flows/*.py` - one module per feature (12 ported + `doc_scan`).
- `app/fleet.py` - async Fleet API client (`X-Internal-Token` + `X-Caller-Context`).
- `app/sessions.py` - `bot_sessions` read/write (psycopg).
- `app/keyboards.py`, `app/texts.py` - inline keyboards + Hebrew strings (n8n callbacks 1:1).

## Flows

Driver: clock in/out · vehicle issue · accident · update details · attendance CSV · my vehicle.
Admin: today's attendance · broadcast · fleet summary · update driver · maintenance
(overdue + log) · **document scan**.

Every action is reachable two ways: the inline-keyboard menu, and the Telegram **command
menu** (the ☰ button). `app/commands.py` sets a per-role command list per chat once the user
is authorized (on claim + whenever the menu is shown); a tapped command (e.g. `/clock_in`)
routes to the same feature as the matching button.

On a successful completion (clock-in/out, issue logged, details/driver updated, maintenance
logged, broadcast sent, document applied) the bot sends an **animated-emoji flourish** via
`sendDice` (🎯) - `tg.send_dice`. The accident flow is deliberately excluded.

## LLM touches

- **Accident description** (`app/stt.py`) - the driver describes the event by voice or
  text; a voice note is transcribed by **OpenAI Whisper** into `accidents.description`.
- **Document scan** (`app/vision.py`) - admin picks a type (vehicle license / insurance /
  driver license), uploads a file, **Gemini** extracts the fields, the bot shows them for
  confirmation, then applies via `POST /documents/extracted` (vehicle docs, plate-matched)
  or `PATCH /drivers/{id}` (driver license).

Accident photos/videos are uploaded through Fleet API (`POST /files` -> Google Drive) and
stored as attachments; they are **not** run through an LLM.

## Dev

```
poetry env use python3.12 && poetry install
poetry run pytest
```

Two test layers (both mock Fleet API with respx and stub storage / Whisper / Gemini):

- `tests/test_flows.py` - unit tests that call `router.dispatch()` directly with a faked bot.
- `tests/test_e2e.py` + `tests/sim.py` - black-box e2e: real aiogram `Update`s (one user per
  role) fed through the real dispatcher with the **Telegram Bot API mocked at the session
  boundary**, so the suite acts like Telegram itself and covers every bot activity.

Config (see repo `.env.example`): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`,
`FLEET_API_URL`, `INTERNAL_SERVICE_TOKEN`, `DATABASE_URL`, `OPENAI_API_KEY`,
`GEMINI_API_KEY`. Media is uploaded via Fleet API, so the bot needs no storage creds.

Runs as a long-polling worker (`python -m app.main`); no port is exposed.
