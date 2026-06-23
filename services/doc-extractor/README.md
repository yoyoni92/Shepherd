# doc-extractor

Turns S3 documents (insurance cert, annual license, traffic ticket) into typed fields
via a vision LLM, then reconciles by plate against Fleet API.

## Setup

```bash
poetry install
```

## Required env vars

| Var | Description |
|-----|-------------|
| `BEDROCK_MODEL_ID` | Claude model ID in Bedrock (e.g. `anthropic.claude-3-5-sonnet-20241022-v2:0`) |
| `BEDROCK_REGION` | AWS region (default: `us-east-1`) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS credentials |
| `S3_BUCKET` | S3 bucket containing documents (default: `shepherd-docs`) |
| `FLEET_API_URL` | Internal Fleet API URL (default: `http://fleet-api:8000`) |
| `INTERNAL_SERVICE_TOKEN` | Auth token for Fleet API |
| `EXTRACTOR_PROVIDER` | `bedrock` (default) or `gemini` |
| `GEMINI_API_KEY` | Required when `EXTRACTOR_PROVIDER=gemini` |

## Run

```bash
uvicorn app.service:app --port 8002
```

## Test

```bash
poetry run pytest tests/ -m "not live"
```

## Eval harness (prompt quality)

```bash
poetry run python -m eval.run
```

Results are appended to `eval/prompt_log.md`. Threshold: 70% pass rate.

## Endpoints

- `POST /extract` - extract doc from S3 and reconcile to Fleet API
- `GET /health`
