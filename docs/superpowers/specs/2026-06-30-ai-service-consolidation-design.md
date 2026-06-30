# AI Service Consolidation + Accident-Description Sanity Check

Date: 2026-06-30
Status: Approved (design)

## Summary

Introduce a dedicated `ai-service` that owns every AI/LLM interaction in Shepherd,
and add a new accident-description sanity check as its first new capability.

Today the Telegram bot makes LLM calls directly from two thin modules:

- `services/telegram-bot/app/stt.py` - OpenAI Whisper (`whisper-1`) for the accident
  voice description.
- `services/telegram-bot/app/vision.py` - Google Gemini (`gemini-2.0-flash`) for the
  admin document scan.

This spec moves both into a new FastAPI `ai-service`, adds a third capability (the
accident-description classifier), and has the bot call all three over HTTP - the same
pattern the bot already uses for Fleet API. After this change the bot holds no LLM
provider keys.

## Motivation

- The user wants a single service that "covers our AI", since more AI capabilities are
  coming (a Drive-files RAG is on the roadmap, plus document-type classification).
- The originating request was narrower: after the accident description is resolved
  (voice transcribed, or typed), sanity-check that it actually reads like an accident
  description; if not, re-prompt for a proper explanation.

### Prior-decision note (on the record)

`ROADMAP.md` "Phase 2 - AI Services (removed)" records that an earlier AI stack
(`channel-gateway`, `doc-extractor`, `rag`, `langgraph-agent`, `guardrails`,
`ollama-assistant`) was built and deliberately removed; the project was pruned to three
services (fleet-api, telegram-bot, webui). This spec re-introduces an AI service tier.
This was an explicit user decision made with that history in view.

## Decisions

- **Scope:** consolidate all AI now - move STT and doc-vision into the service and add
  the new classifier. All LLM keys move to the service.
- **Name:** `ai-service`.
- **Sanity-check loop guard:** up to 2 re-prompts, then accept whatever the driver sent
  (never trap a stressed driver mid-accident-report).
- **Sanity-check strictness:** lenient - reject only clearly-unrelated input (empty,
  gibberish, greeting, off-topic); accept any plausible accident account.
- **Classifier provider/model:** Gemini `gemini-2.5-flash-lite` with native
  structured output (current cheap model per research).
- **Migrated code keeps its current model IDs** (`whisper-1`, `gemini-2.0-flash`). This
  is a relocation, not a behavior change. Upgrading vision to
  `gemini-2.5-flash-lite` + structured output is a separate, optional follow-up.

## Architecture

### New service: `services/ai-service/`

Scaffolded from `templates/python-service/` and following `services/fleet-api/`
conventions:

- FastAPI app, `/health` endpoint.
- Guarded by `X-Internal-Token` against `INTERNAL_SERVICE_TOKEN` (same shared secret as
  fleet-api), via a `deps.verify_internal_token` dependency.
- Config via `pydantic-settings` + `shepherd_config` overlay (mirrors
  `fleet-api`/bot `config.py`).
- Sole holder of `OPENAI_API_KEY`, `GEMINI_API_KEY` (and `ANTHROPIC_API_KEY` is
  available for future use).
- Port `8001` (fleet-api owns 8000, webui 3000).

```
services/ai-service/
  app/
    __init__.py
    main.py            # FastAPI app + /health + routers
    config.py          # settings (keys) + shepherd_config overlay
    deps.py            # verify_internal_token
    stt.py             # Whisper impl, moved verbatim from bot
    vision.py          # Gemini doc-extract impl, moved verbatim from bot
    classify.py        # NEW Gemini classifier
    routers/
      __init__.py
      stt.py
      vision.py
      classify.py
  tests/
    test_health.py
    test_stt.py
    test_vision.py
    test_classify.py
  Dockerfile
  pyproject.toml       # fastapi, uvicorn, openai, google-genai, shepherd_config, shepherd_contracts
  README.md
```

### Endpoints

| Method/Path | Input | Output | Notes |
|---|---|---|---|
| `GET /health` | - | `{status}` | From template. |
| `POST /stt/transcribe` | multipart: audio file + `language` (default `he`) | `{text}` | Wraps moved `stt.py` (`whisper-1`). |
| `POST /vision/extract` | multipart: image file + `doc_type`, `mime` | flat field dict | Wraps moved `vision.py` (`gemini-2.0-flash`). |
| `POST /classify/accident-description` | JSON `{text}` | `{is_accident: bool}` | NEW. Lenient prompt, native structured output, fails open. |

Multipart for binary payloads matches Fleet API's `POST /files`. Request/response
Pydantic models live in `libs/shepherd_contracts` (new `ai.py`), imported by both the
service and the bot client so the contract is shared and type-checked.

### Classifier behavior (`classify.py`)

- Model `gemini-2.5-flash-lite`, lazy `genai.Client` (same shape as the existing
  `vision.py`).
- One lenient prompt: does this text describe a vehicle accident/incident? Reject only
  if empty, gibberish, a greeting, or clearly off-topic.
- Native structured output: `responseMimeType="application/json"` + a `{is_accident:
  bool}` response schema. No markdown-fence stripping.
- **Fails open:** on any provider/parse error, return `is_accident = true`, so an AI
  outage can never block an accident report.

## Bot changes (`services/telegram-bot/`)

- Delete `app/stt.py` and `app/vision.py`.
- Add `app/ai.py` - a thin HTTP client mirroring `app/fleet.py` (httpx, base URL
  `ai_service_url`, `X-Internal-Token`): `transcribe(audio, ...)`,
  `extract(doc_type, image, mime)`, `is_accident_description(text) -> bool`. The client
  fails open for `is_accident_description` (returns `True`) when the service is
  unreachable, matching the service-side fail-open.
- Repoint callers:
  - `app/flows/accident.py:87` - `stt.transcribe` -> `ai.transcribe`.
  - `app/flows/doc_scan.py:126` - `vision.extract` -> `ai.extract`.
  - `app/flows/update_driver.py:75` - `vision.extract` -> `ai.extract`.
- `app/config.py`: remove `openai_api_key` / `gemini_api_key`; add `ai_service_url`
  (overlaid from `shepherd_config` `[services]`).
- `pyproject.toml`: drop `openai` and `google-genai` deps (AI is now httpx-only).

### Accident-description sanity check (`accident.py`, `accident_description`, lines 83-96)

1. Resolve `description` (voice -> `ai.transcribe`, else `ctx.text`) - unchanged.
2. Call `ai.is_accident_description(description)`.
3. **Pass** -> store `description`, advance to `awaiting_road_clear` (current behavior).
4. **Fail** -> read `ctx.state["desc_rejects"]` (default 0):
   - If `< 2`: increment `desc_rejects`, stay in `awaiting_description`, send
     `texts.ACCIDENT_DESCRIPTION_RETRY`.
   - If `>= 2`: accept anyway - store `description`, advance.
   - Net effect: up to 2 re-prompts, then accept.

The router already re-fires `accident_description` on text or voice while in
`awaiting_description` (`router.py:83-84`); **no router change needed**.

New Hebrew string `texts.ACCIDENT_DESCRIPTION_RETRY` explaining what a proper
description should include (what happened, where, other vehicles involved).

## Wiring

- `docker-compose.yml`:
  - Add `ai-service` (repo-root build context, `services/ai-service/Dockerfile`, port
    `8001`, env `OPENAI_API_KEY`/`GEMINI_API_KEY`/`INTERNAL_SERVICE_TOKEN`/
    `SHEPHERD_CONFIG`, `/health` healthcheck).
  - `telegram-bot`: `depends_on` ai-service (healthy); remove `OPENAI_API_KEY` /
    `GEMINI_API_KEY`; add `AI_SERVICE_URL: http://ai-service:8001`.
- `config.toml` + `config.example.toml`: add `ai_service_url = "http://ai-service:8001"`
  under `[services]`.
- `.env.example`: keys documented as owned by ai-service.

## Testing

- **ai-service** (`tests/`): provider SDKs stubbed.
  - `test_health.py` (from template).
  - `test_stt.py`, `test_vision.py`: endpoint contract with the provider call mocked.
  - `test_classify.py`: pass/fail cases + fail-open returns `is_accident = true` on
    provider error.
- **telegram-bot** (`tests/`): re-stub the new `ai` HTTP client instead of
  `stt`/`vision` (respx against `ai_service_url`, or monkeypatch `ai.*`).
  - Update existing accident / doc_scan / update_driver tests.
  - New accident sanity-check tests: pass -> advance; fail -> stays + retry message +
    `desc_rejects` increments; third failing submission -> accepted + advances; voice
    path (bad transcription -> re-prompt); fail-open (classifier errors -> treated as
    accident, advances).

## Docs to update (same commit as code, per repo pre-commit rule)

- `ROADMAP.md` - Phase 2: AI service re-introduced (update the "removed" note).
- root `README.md` - service list; LLM touches now live in ai-service.
- `services/telegram-bot/README.md` - LLM touches now via ai-service over HTTP.
- `services/ai-service/README.md` - new.
- `.env.example`, `config.example.toml`.

## Out of scope

- Upgrading the migrated vision model to `gemini-2.5-flash-lite` + structured output.
- Switching STT off Whisper to a Google model (no evidence it improves Hebrew; needs an
  empirical A/B test first).
- The planned Drive-files RAG.

## Open questions

None blocking. Provider model IDs/pricing move fast; re-verify `gemini-2.5-flash-lite`
availability on the API key before relying on it.
