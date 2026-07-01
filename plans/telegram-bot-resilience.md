# Plan: Telegram bot resilience (provider-failure handling)

**Status:** T1 + accident-STT shipped (TDD). Rest deferred - see "Shipped" below.
**Owner:** (unassigned)
**Related:** QA finding #6 (`docs/qa/e2e-test-plan.md` ERR-1/ERR-2, gap G6);
ROADMAP "Free-Text Guardrails" (separate, not this plan).

## Problem

The bot awaits Fleet API writes, Whisper, Gemini, and Google Drive uploads with
**no exception handling**, and there is no top-level catch in the dispatch path
(`main.on_message`/`on_callback` -> `router.dispatch` -> `FEATURES[feature]` at
`app/router.py:267`). If a provider is down, times out, or 5xxs:

- `FleetClient._request` (`app/fleet.py:66`) raises `httpx` errors on connect
  failure / timeout (30s); several flows also call `.json()` on non-200.
- `stt.transcribe`, `vision.extract`, `storage.upload` propagate any exception.

The exception unwinds out of `dispatch` into aiogram, which logs it and sends the
user **nothing**. The driver is left staring at a dead chat. The worst case is
**mid-accident**: after completing "I'm safe", location share, and description, a
Drive timeout on a photo upload (`app/flows/accident.py:26`) or the final
`POST /accidents` (`:142`) aborts silently, losing the report.

### Blast radius (await-without-try sites)

| Provider | Call sites | User-facing effect today |
| --- | --- | --- |
| Fleet write | `clock.py:16`, `km_update.py`, `accident.py:142`, `update_details.py`, `update_driver.py`, `vehicle_care` (`maintenance.py`), `broadcast.py` | silent dead chat on 5xx / network error |
| Whisper (STT) | `accident.py:87` | accident wizard dies after description step |
| Gemini (vision) | `doc_scan.py:126`, `update_driver.py:75` | doc-scan dies (empty extraction already handled; exceptions are not) |
| Drive upload | `accident.py:26`, `accident.py:130`, `doc_scan.py:125` | accident/doc upload dies mid-flow |

Note: `vehicle_issue.py` already does this correctly (checks non-2xx ->
`VEHICLE_ISSUE_FAILED`). It is the template for the targeted handling below.

## Goals

1. **No silent failures.** Every provider failure produces a Hebrew message that
   tells the user what happened and that they can retry.
2. **Preserve multi-step state.** A failure mid-flow must not clear the session,
   so the user re-sends only the failed step (re-tap, re-send the photo, retype)
   rather than restarting the whole accident wizard.
3. **Never report false success.** A failed write must not send the success text
   or the dice flourish (the BUG-1 class of defect).
4. **Give ops a trail.** Log the failure with `chat_id`, feature, route, and the
   exception, so an outage is diagnosable.

## Non-goals

- Automatic ret/queueing of failed writes, offline buffering, or a circuit
  breaker. Out of scope; a single inline retry for transient network errors is a
  stretch item only.
- Free-text input validation / guardrails (separate ROADMAP item).
- Changing Fleet API behavior. This plan is bot-side only.

## Design

Two layers: a **global safety net** so nothing is ever silent, plus **targeted
handling** where a specific message or state care is needed.

### Layer 1 - global safety net (catches everything)

Wrap the flow invocation in `dispatch` (`app/router.py:267`) in try/except:

- On any unhandled exception: log it with context, then
  `ctx.bot.send_message(ctx.chat_id, texts.GENERIC_ERROR)`.
- **Do not** clear `bot_sessions` state - a multi-step flow keeps its `step`, so
  the user can retry the same input. (Single-shot flows have no step to lose.)

This single change removes the "dead chat" failure mode for all paths at once and
is the highest-value, lowest-risk piece. It ships first.

### Layer 2 - typed transport error + targeted messages

1. **Typed Fleet transport error.** In `FleetClient._request`, wrap `httpx`
   transport exceptions (`httpx.TransportError`: connect, read timeout) in a new
   `FleetUnavailable(Exception)`. Flows (and Layer 1) can then distinguish "Fleet
   is unreachable" from an HTTP status they already inspect. `_request` still
   returns the response for status-based branching as today; only raised
   transport errors are wrapped.

2. **Fleet write flows.** For each write, on `FleetUnavailable` or a 5xx status,
   send a Hebrew retry message and stop (no success text, no dice). Reuse the
   `vehicle_issue.py` pattern. Flows that already map 4xx (`km_update` 422,
   `update_*` validation) keep that; we add only the transport/5xx branch.

3. **Whisper (accident description).** Wrap `stt.transcribe` (`accident.py:87`).
   On failure: send `ACCIDENT_STT_FAILED` ("could not process the voice note -
   send it again or type the description"), stay on `awaiting_description`. The
   already-captured safe/location state is untouched.

4. **Gemini (doc scan + update-driver license).** Wrap `vision.extract`
   (`doc_scan.py:126`, `update_driver.py:75`). On exception: reuse the existing
   `DOC_SCAN_FAILED` and stay on the file step to retry (matches how an empty
   extraction is already handled).

5. **Drive upload (accident photos/videos, doc files).** Wrap `storage.upload`
   (`accident.py:26`/`:130`, `doc_scan.py:125`). On failure: send
   `UPLOAD_FAILED` ("upload failed, send the photo/video again") and stay on the
   current photo/video step so only that item is re-sent - the wizard does not
   advance and prior uploads are kept.

### New Hebrew text keys (`app/texts.py`)

Following the existing retry-oriented convention (`"נסה/י שוב"`):

- `GENERIC_ERROR = "⚠️ אירעה תקלה זמנית. נסה/י שוב מאוחר יותר."`
- `SERVICE_UNAVAILABLE = "⚠️ השירות אינו זמין כרגע. נסה/י שוב בעוד רגע."`
  (Fleet transport/5xx on writes)
- `ACCIDENT_STT_FAILED = "⚠️ לא הצלחתי לעבד את ההודעה הקולית. שלח/י שוב או כתוב/י את התיאור."`
- `UPLOAD_FAILED = "⚠️ העלאת הקובץ נכשלה. שלח/י את הקובץ שוב."`
  (`DOC_SCAN_FAILED` already exists and is reused for vision failures.)

### Optional helper (DRY)

Add `Ctx.reply(text, **kw)` wrapping `self.bot.send_message(self.chat_id, text)`.
Error sends and existing sends can adopt it. Optional; not required for the fix.

## Shipped (ponytail scope)

Implemented via TDD, `services/telegram-bot/tests/test_resilience.py`:

- **T1 - global safety net** (`app/router.py`): try/except around the flow call;
  logs with context and sends `GENERIC_ERROR`; state left intact so multi-step
  flows retry from their current step. This alone removes the silent-dead-chat
  failure mode for **every** path - Fleet writes, Gemini, Drive uploads, doc-scan.
- **Accident STT** (`app/flows/accident.py`): the one spot where the generic
  message is insufficient - a Whisper failure now sends `ACCIDENT_STT_FAILED`
  ("send again or type"), keeping `awaiting_description` so the driver can type
  instead of re-recording. The already-captured safe/location state is preserved.

**Deliberately deferred** (T1 already prevents silent failure for these; only a
more specific message would be added): typed `FleetUnavailable` + per-write
`SERVICE_UNAVAILABLE` (T2/T3), doc-scan/upload-specific messages (T5), inline
retry (T6). Add when a nicer per-provider message is wanted; not needed to close
the severity. The 5xx-with-JSON-body edge on `clock`/writes (misleading
"already clocked in" instead of an error) is the one correctness gap left - small,
tracked here.

## Tasks (sequenced, tracer-bullet order)

Each task is independently shippable and testable. Ship T1 first - it alone
closes the "silent dead chat" severity.

### T1 - Global safety net in dispatch
- Wrap `FEATURES[feature](ctx, route)` in try/except in `app/router.py`.
- Log (`logging.exception`) with `chat_id`, `feature`, `route`.
- Send `GENERIC_ERROR`; do not clear state.
- Add `GENERIC_ERROR` to `texts.py`.
- **DoD:** an exception raised by any flow results in exactly one Hebrew message
  to the user and a logged error; session state is preserved.
- **Tests:** unit test that monkeypatches a feature to raise and asserts one
  `GENERIC_ERROR` send + state unchanged.

### T2 - Typed Fleet transport error
- Add `FleetUnavailable` and wrap `httpx.TransportError` in `_request`.
- **DoD:** a simulated connect error / timeout raises `FleetUnavailable`, not a
  raw `httpx` error.
- **Tests:** `respx` mocked connect error / timeout -> `FleetUnavailable`.

### T3 - Fleet write flows surface transport/5xx
- clock, km_update, accident `POST /accidents`, update_details, update_driver,
  maintenance `vehicle_care`, broadcast.
- On `FleetUnavailable`/5xx: send `SERVICE_UNAVAILABLE`, no success text, no dice.
- **DoD:** each write flow, on 5xx and on `FleetUnavailable`, sends the retry
  message and never the success/dice.
- **Tests:** per flow, `respx` returns 500 and raises transport error; assert the
  Hebrew message and absence of dice/success.

### T4 - Accident STT + Drive resilience (the mid-accident case)
- Wrap `stt.transcribe` and the two `storage.upload` calls in `accident.py`.
- Failures keep the step; send `ACCIDENT_STT_FAILED` / `UPLOAD_FAILED`.
- **DoD:** STT failure keeps `awaiting_description`; a photo/video upload failure
  keeps the current photo/video step; the already-captured accident state is
  never lost.
- **Tests:** monkeypatch `stt.transcribe` and `storage.upload` to raise; assert
  the message, the preserved `step`, and that no `POST /accidents` fires.

### T5 - Doc-scan / update-driver vision + Drive resilience
- Wrap `vision.extract` (`doc_scan.py`, `update_driver.py`) and
  `storage.upload` (`doc_scan.py`).
- Vision exception -> `DOC_SCAN_FAILED`, stay on file step; upload exception ->
  `UPLOAD_FAILED`, stay on file step.
- **DoD:** a raised vision/upload error is handled identically to the existing
  empty-extraction path (retry, no crash).
- **Tests:** monkeypatch `vision.extract` / `storage.upload` to raise; assert
  message + preserved step.

### T6 (stretch) - single inline retry for transient Fleet reads
- One retry with short backoff on `FleetUnavailable` for idempotent GETs only.
- **DoD:** a single transient GET failure is retried once before surfacing.
- Skip unless there is evidence of flaky transient reads; keep YAGNI.

## Testing strategy

The existing bot suites mock every provider (`respx` for Fleet; monkeypatched
`stt`/`vision`/`storage`), so failure injection is straightforward and needs no
new infrastructure. Add a **negative-path test per provider per flow** (currently
absent - see QA gap). Verify:

1. exactly one Hebrew error message is sent,
2. no success text and no dice on a failed write,
3. multi-step `step` is preserved (no state loss),
4. no downstream write fires after an upstream failure (e.g. no
   `POST /accidents` when a photo upload failed).

Run `make test SVC=services/telegram-bot`, then the cross-system suite
(`make up && make e2e`) to confirm the happy paths still pass.

## Verification / rollout

- Land T1 first and confirm via a forced-failure manual check (point
  `FLEET_API_URL` at a dead port, drive a flow, see the Hebrew error).
- After T3-T5, do a manual outage drill on staging: stop fleet-api mid-flow;
  stop/deny Drive and use a bad Gemini/OpenAI key; confirm every flow degrades to
  a Hebrew retry message and no state is lost.
- Feeds QA exit criteria ERR-1/ERR-2 in `docs/qa/e2e-test-plan.md`.

## Risks

- **Over-broad catch masking bugs.** The global net logs full stack traces, so
  real bugs remain visible in logs; it only changes the user-facing outcome.
- **Retry preserving a bad step.** Preserving state on failure is correct for
  transient outages; if a step is genuinely un-retryable the user can still
  re-open the menu (a command already takes precedence over an active step in
  `route_decision`), so they are never stuck.
- **Double side effects.** Targeted handling must place the try/except so a
  partial success (e.g. Drive upload succeeded but `POST /accidents` failed) does
  not double-upload on retry. Accident uploads are keyed per item, so re-sending
  one photo overwrites rather than duplicates.

## Effort

Small-to-medium. T1 is ~30 min and removes the worst symptom. T2-T5 are
mechanical, one flow at a time, each with its negative-path test. T6 optional.
