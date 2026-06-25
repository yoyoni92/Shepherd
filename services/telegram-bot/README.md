# telegram-bot

Invite-only Hebrew Telegram bot for Shepherd. Replaces the former n8n workflow.
Built on **aiogram 3** with **long-polling** (no public HTTPS / tunnel). Fleet API is
the only tool layer (sole DB writer + permission enforcer); the bot touches the DB
directly only for its own `bot_sessions` conversation state.

## Architecture

```
update -> normalize -> GET /whoami -> read bot_sessions -> route_decision(feature, route)
  unknown            -> invite-claim (phone-verified) / access denied
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

Accident photos/videos are stored as S3 attachments and are **not** run through an LLM.

## Dev

```
poetry env use python3.12 && poetry install
poetry run pytest
```

Config (see repo `.env.example`): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_BOT_USERNAME`,
`FLEET_API_URL`, `INTERNAL_SERVICE_TOKEN`, `DATABASE_URL`, `S3_BUCKET_ACCIDENTS`,
`S3_BUCKET_DOCS`, `AWS_*`, `OPENAI_API_KEY`, `GEMINI_API_KEY`.

Runs as a long-polling worker (`python -m app.main`); no port is exposed.
