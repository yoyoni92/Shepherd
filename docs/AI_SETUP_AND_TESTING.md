# Shepherd - AI Areas: Setup & Manual Testing Recap

Source-of-truth: the **code under `services/`**, not the plan docs. Where the
one-pager / `plans/*.md` describe something the code no longer does, this file
follows the code and flags the drift.

This is a recap to verify every AI surface is correctly provisioned. It covers,
per area: what it is, what you must set up (AWS / keys / models), the exact env
vars, and a copy-pasteable manual test.

---

## 0. The AI inventory at a glance

| # | Area | Provider / model (actual) | Needs | Port | In compose? | Live caller in repo? |
|---|------|---------------------------|-------|------|-------------|----------------------|
| 1 | **doc-extractor** | AWS Bedrock Claude **or** Gemini `gemini-2.0-flash` | S3 + (Bedrock **or** Gemini key) | 8002 | yes | **no** (tests/eval only) |
| 2 | **image-analyser** | PyTorch ResNet-50 (local, 5-class) | S3 + `model.pth` | - | **no** | **no** (tests/eval only) |
| 3 | **rag** | Embeddings: local `sentence-transformers`; Generation: **Anthropic** `claude-sonnet-4-6` | Anthropic key + DB | 8004 | yes | webui `/rag`, agent `rag_tool` |
| 4 | **langgraph-agent** | **Anthropic** `claude-sonnet-4-6` | Anthropic key | 8003 | yes | webui `/agent` |
| 5 | **guardrails** | Deterministic (DB + langdetect) + **guardrails-ai** hub; rail LLM `openai/gpt-4o-mini` | OpenAI key + Guardrails Hub key | 8005 | yes | **no** (tests only) |
| 6 | **ollama** | Local `llama3` (baked into image) | nothing (pulls at build) | 11434 | yes | ollama-assistant |
| 7 | **ollama-assistant** | Calls ollama `/api/chat` | reachable ollama | 8006 | yes | webui `/assistant` |
| - | **n8n + channel-gateway** | not AI, but **write images to S3** for the above | S3 + AWS creds | 5678 / 8001 | yes | Telegram / webapp |

### Important drift / gaps (read first)

1. **doc-extractor, image-analyser, guardrails have no live caller in the repo.**
   They expose `/extract`, `/analyse`, `/check/input|output` and are exercised by
   their own tests/eval harnesses, but no n8n flow, gateway, or webui route calls
   them. If the demo is supposed to run extraction/classification/guardrails
   end-to-end, that wiring is missing (it would live in n8n).
2. **image-analyser is not in `docker-compose.yml` at all** and has no Dockerfile.
   It only runs locally via `uvicorn`. To demo it, add a compose service.
3. **RAG runtime uses Anthropic, not Llama.cpp.** `services/rag/app/main.py` uses
   `langchain_anthropic.ChatAnthropic` (needs an **Anthropic** key). Llama.cpp /
   `LLAMA_MODEL_PATH` survives only in the offline `eval/run.py --live` path. The
   RAG `README.md` has been corrected; some `plans/*.md` still say Llama.cpp.
4. **Guardrails uses `guardrails-ai`, not NeMo** (one-pager says NeMo). The rail
   LLM is OpenAI `gpt-4o-mini`, and the hub validators need a Guardrails Hub key.
5. **S3 bucket names (now standardized).** The docs/extraction bucket is
   `shepherd-docs` everywhere (`.env.example`, compose, gateway, doc-extractor,
   image-analyser fallbacks all aligned); n8n accident photos use
   `shepherd-accidents`. Create both buckets.

---

## 1. Cross-cutting setup (do this once)

Everything below is consumed through the root `.env` (copy `.env.example`).

### 1.1 AWS account, IAM, region

Used by: doc-extractor (Bedrock + S3), image-analyser (S3), channel-gateway (S3),
n8n (S3).

1. **Pick a region with Bedrock Claude**: `us-east-1` (matches all defaults).
2. **Create an IAM user** (or instance role on EC2) with programmatic access. For
   a quick demo, the simplest least-effort policy is S3 + Bedrock invoke:
   - `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on the project buckets.
   - `bedrock:InvokeModel` on the Claude model ARN(s).
3. Put the access key id / secret in `.env` (`AWS_ACCESS_KEY_ID`,
   `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION=us-east-1`).
   - On EC2 prefer an **instance role** over static keys (boto3 picks it up with
     no env vars).

**Verify:**
```bash
aws sts get-caller-identity            # confirms creds resolve
```

### 1.2 S3 buckets

Code reads/writes these keys:
- channel-gateway writes inbound media to `inbox/telegram/...` / `inbox/webapp/...`
  in `S3_BUCKET`.
- doc-extractor & image-analyser read the `s3_key` they're handed from `S3_BUCKET`.
- n8n writes accident photos to `S3_BUCKET_ACCIDENTS`.

1. Create two buckets in your region, e.g. `shepherd-docs` and `shepherd-accidents`.
2. Set `S3_BUCKET=shepherd-docs` and `S3_BUCKET_ACCIDENTS=shepherd-accidents` in
   `.env`. (Resolve the `shepherd-fleet` vs `shepherd-docs` mismatch by choosing
   one value here; compose passes this var to every service that needs it.)

**Verify:**
```bash
aws s3 ls s3://shepherd-docs
echo "hello" | aws s3 cp - s3://shepherd-docs/inbox/test.txt
aws s3 rm s3://shepherd-docs/inbox/test.txt
```

### 1.3 AWS Bedrock model access

Used by: doc-extractor (when `EXTRACTOR_PROVIDER=bedrock`, the default).

1. In the AWS console -> **Bedrock -> Model access**, request/enable access to a
   Claude model in your region (e.g. *Claude 3.5 Sonnet*).
2. Copy its **model id** into `.env`:
   `BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0` (use whatever id
   your account shows) and `BEDROCK_REGION=us-east-1`.

**Verify:**
```bash
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?contains(modelId,'claude')].modelId" --output table
```

### 1.4 API keys (managed LLMs)

| Key | Used by | How to get it |
|-----|---------|---------------|
| `ANTHROPIC_API_KEY` | rag, langgraph-agent | console.anthropic.com |
| `GEMINI_API_KEY` | doc-extractor (only if `EXTRACTOR_PROVIDER=gemini`) | aistudio.google.com |
| `OPENAI_API_KEY` | guardrails rail LLM (`gpt-4o-mini`) | platform.openai.com |
| `GUARDRAILS_API_KEY` | guardrails - installs hub validators at image build | hub.guardrailsai.com |

Set `ANTHROPIC_MODEL=claude-sonnet-4-6` and `GUARDRAILS_LLM=openai/gpt-4o-mini`
(both already defaults).

### 1.5 Ollama (local, no key)

`services/ollama/Dockerfile` bakes `llama3` (~4.7 GB) into the image at build
time. No account needed, but the build pulls weights and the runtime needs RAM.

**Verify after `docker compose up ollama`:**
```bash
docker compose exec ollama ollama list      # llama3 present
```

### 1.6 Bring the stack up

```bash
cp .env.example .env        # then fill the blanks from 1.1-1.4
docker compose up -d postgres db-init
docker compose up -d        # builds + starts everything
docker compose ps           # all healthy
```

---

## 2. Per-area setup & manual test

All HTTP tests assume the compose port mappings above and run from the host.

### 2.1 doc-extractor (Bedrock / Gemini vision extraction)

**What:** downloads a document from S3, asks a vision LLM for typed fields +
confidence, then POSTs the result to fleet-api `/documents/extracted` (reconcile
by plate). Provider chosen by `EXTRACTOR_PROVIDER` (`bedrock` default, `gemini`
fallback).

**Setup:** §1.1 (AWS+S3) + §1.3 (Bedrock model) for the default path, or
`EXTRACTOR_PROVIDER=gemini` + `GEMINI_API_KEY` (§1.4) for the fallback. Plus
`FLEET_API_URL` and `INTERNAL_SERVICE_TOKEN` (already set by compose).

Env: `BEDROCK_MODEL_ID`, `BEDROCK_REGION`, `AWS_ACCESS_KEY_ID/SECRET`, `S3_BUCKET`,
`EXTRACTOR_PROVIDER`, `GEMINI_API_KEY`, `FLEET_API_URL`, `INTERNAL_SERVICE_TOKEN`.

**Manual test (offline - no AWS, proves the service & prompt logic):**
```bash
cd services/doc-extractor
poetry install
poetry run pytest -m "not live"          # bedrock/gemini mocked
poetry run python -m eval.run            # prompt eval, appends eval/prompt_log.md (>=70% pass)
```

**Manual test (live, real Bedrock):**
```bash
# 1. put a sample doc in S3
aws s3 cp sample_license.pdf s3://shepherd-docs/inbox/test/license.pdf
# 2. call the running service
curl -s localhost:8002/health
curl -s -X POST localhost:8002/extract -H 'content-type: application/json' -d '{
  "s3_key": "inbox/test/license.pdf",
  "doc_type": "annual_license",
  "confidence_min": 0.7
}' | jq
```
Expect JSON `{status, doc_type, confidence, fleet_response}`. Failure modes to
check: missing `BEDROCK_MODEL_ID` -> 500 "BEDROCK_MODEL_ID env var is required";
non-JSON model output -> 422 parse_error; wrong plate -> reconcile mismatch in
`fleet_response`.

### 2.2 image-analyser (PyTorch ResNet-50 doc classifier)

**What:** ResNet-50 (ImageNet weights, frozen backbone, 5-way head) classifies an
image fetched from S3 into one of 5 doc types via `POST /analyse`. Falls back to
an **untrained** head if `artifacts/model.pth` is absent (so confidence is
meaningless until you train).

**Setup:**
- §1.1 (AWS+S3). Env: `S3_BUCKET`, `IMAGE_CONFIDENCE_MIN` (default 0.6), AWS creds.
- **Train / supply a checkpoint** so it's not random:
  ```bash
  cd services/image-analyser
  poetry install
  python data/generate.py     # or supply real labeled data
  python train.py             # writes artifacts/model.pth
  python eval.py              # report accuracy (target >75%)
  ```
- **Not in compose** - run standalone: `uvicorn app.main:app --port 8007`
  (or add a compose service if it must be part of the demo).

**Manual test (offline):**
```bash
cd services/image-analyser
poetry run pytest          # S3 mocked via moto; covers app/infer/model/train
```

**Manual test (live):**
```bash
aws s3 cp sample_plate.jpg s3://shepherd-docs/inbox/test/plate.jpg
curl -s -X POST localhost:8007/analyse -H 'content-type: application/json' \
  -d '{"s3_key":"inbox/test/plate.jpg"}' | jq
```
Expect `{doc_type, confidence}`. Check the S3-miss path: a bad key returns 400
"S3 key not found".

### 2.3 rag (DB-grounded Q&A)

**What:** embeds vehicle-profile docs with a **local** multilingual
sentence-transformer into an **ephemeral** ChromaDB, retrieves, and generates the
answer with **Anthropic** `claude-sonnet-4-6`. Cites the source plate; says "No
record found." when nothing matches.

**Setup:** §1.4 `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-sonnet-4-6`.
`DATABASE_URL` uses the read-only `rag_readonly` role (compose sets it). First
embedding call downloads the `paraphrase-multilingual-MiniLM-L12-v2` model (needs
internet at runtime/build). Index is **ephemeral** - data must be synced on
startup (`app.sync.bulk`); a fresh container starts empty.

> Runtime generation is Anthropic; `LLAMA_MODEL_PATH` applies only to `eval.run --live`.

**Manual test (offline):**
```bash
cd services/rag
poetry install
poetry run pytest -m "not live"     # LLM + chroma stubbed
poetry run python -m eval.run        # mock LLM, prompt eval (V5: 12/12)
```

**Manual test (live):**
```bash
curl -s localhost:8004/health
curl -s -X POST localhost:8004/query -H 'content-type: application/json' -d '{
  "question": "What is the insurance status of plate 12-345-67?",
  "caller_context": {"role": "admin"}
}' | jq
```
Expect `{answer, citations[]}`. With an empty index you should get
`"No record found."` and `citations: []` - if so, run a sync to populate, then
re-query and confirm a real plate appears in `citations`.

### 2.4 langgraph-agent (planner -> tools -> synthesiser)

**What:** LangGraph state machine. Planner (`claude-sonnet-4-6`) emits JSON tool
calls (`rag`, `fleet_api`, or `clarify`); tool_exec runs them; synthesiser
(`claude-sonnet-4-6`) writes the final answer and collects RAG citations.

**Setup:** §1.4 `ANTHROPIC_API_KEY`; `FLEET_API_URL`, `RAG_URL`,
`INTERNAL_SERVICE_TOKEN` (compose-set). Depends on fleet-api + rag being healthy.

**Manual test (offline):**
```bash
cd services/langgraph-agent
poetry install
poetry run pytest -m "not live"      # graph/tools/prompts with stubbed LLM
```

**Manual test (live):**
```bash
curl -s localhost:8003/health
curl -s -X POST localhost:8003/agent/run -H 'content-type: application/json' -d '{
  "query": "List active vehicles and their insurance status",
  "caller_context": {"role": "admin", "phone": "+972500000000"}
}' | jq
```
Expect `{answer, tools_used, reasoning_steps, citations}`. Verify: `tools_used`
contains `rag`/`fleet_api`; a vague query triggers the `clarify` path (answer is a
clarifying question, no tools used); a 403 from fleet-api surfaces as a refusal
inside `tool_results`, not a crash.

### 2.5 guardrails (input/output rails)

**What:** `POST /check/input` runs **deterministic** auth (phone lookup in
`channel_identities` / `drivers`) then **langdetect** language gate (allowed set
from `system_config`, default `["he","en"]`), then **guardrails-ai**
`RestrictToTopic` + `ToxicLanguage`. `POST /check/output` runs `ProvenanceV1`
(grounding). Topic + provenance call the rail LLM `openai/gpt-4o-mini`.

**Setup:**
- §1.4 `OPENAI_API_KEY`, `GUARDRAILS_LLM=openai/gpt-4o-mini`.
- `GUARDRAILS_API_KEY` (Guardrails Hub) - the **Dockerfile installs the hub
  validators at build time** (`guardrails hub install ...`), which needs this key
  unless cached. If the build's `|| true` swallowed a failure, validators are
  missing at runtime; rebuild after setting the key.
- `DATABASE_URL` for the auth lookups (compose-set).
- ToxicLanguage downloads a local classifier model on first use.

**Manual test (offline):**
```bash
cd services/guardrails
poetry install
poetry run pytest         # t1 auth .. t7 endpoints; hub validators mocked
```

**Manual test (live):**
```bash
# input rail - unregistered phone is rejected before any LLM call
curl -s -X POST localhost:8005/check/input -H 'content-type: application/json' -d '{
  "phone":"+972500000000","text":"מתי מסתיים הביטוח של הרכב?","context":{}
}' | jq      # expect {"pass":false,"reason":"not registered"}  (for an unknown phone)

# off-topic (registered phone, allowed language, non-fleet topic) -> topic rail blocks
curl -s -X POST localhost:8005/check/input -H 'content-type: application/json' -d '{
  "phone":"<registered-phone>","text":"What is the capital of France?","context":{}
}' | jq

# output rail - claim not supported by sources should fail grounding
curl -s -X POST localhost:8005/check/output -H 'content-type: application/json' -d '{
  "text":"The fine is exactly 750 NIS.","sources":["Vehicle 12-345-67 insurance valid to 2026."]
}' | jq      # expect pass:false + safe_text
```
Verify the layering: bad phone never reaches the LLM (auth first); wrong language
(e.g. French text) fails on `language ... not allowed`; only registered + allowed
+ on-topic input reaches the topic/toxicity rails.

### 2.6 ollama + 2.7 ollama-assistant (local chat)

**What:** `ollama` serves local `llama3`. `ollama-assistant` is a DB-blind helper:
loads a system prompt from `/prompts/ollama_system.txt` and calls ollama
`/api/chat` via `POST /chat`.

**Setup:** none beyond compose. Env: `OLLAMA_URL`, `OLLAMA_MODEL=llama3`,
`SYSTEM_PROMPT_PATH`, `OLLAMA_TIMEOUT` (default 60s). First `docker compose build
ollama` pulls the weights.

**Manual test:**
```bash
docker compose exec ollama ollama list                 # llama3 present
curl -s localhost:8006/health
curl -s -X POST localhost:8006/chat -H 'content-type: application/json' \
  -d '{"message":"How do I report a vehicle accident?"}' | jq
```
Expect `{content: "..."}`. Check the timeout path: a cold model can exceed
`OLLAMA_TIMEOUT` and return HTTP 504 - bump the env if so. The assistant must
**refuse off-topic / not invent fleet data** (that behavior lives in the system
prompt; compare `prompts/ollama_system.txt` vs the `_v5` it should match).

### 2.8 channel-gateway + n8n S3 writes (feeders, not models)

**What:** not AI, but they produce the S3 objects the AI services read.
channel-gateway `put_object`s inbound Telegram/webapp media to `S3_BUCKET`; the
n8n accident flow uploads photos to `S3_BUCKET_ACCIDENTS` (presigned URL) and
reads Telegram files.

**Setup:** §1.1 + §1.2; n8n also needs `TELEGRAM_BOT_TOKEN` and the localtunnel
sidecar for the Telegram webhook (dev).

**Manual test:**
```bash
# gateway writes to S3 on inbound media
curl -s localhost:8001/health
# (drive a real inbound via Telegram, then:)
aws s3 ls s3://shepherd-docs/inbox/telegram/ --recursive | tail
```

---

## 3. Final verification checklist

Run top to bottom; each line is independently checkable.

- [ ] `aws sts get-caller-identity` resolves (creds OK)
- [ ] both S3 buckets exist and a put/get round-trips (§1.2)
- [ ] Bedrock Claude model is access-enabled and `BEDROCK_MODEL_ID` is set (§1.3)
- [ ] `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GUARDRAILS_API_KEY` set; `GEMINI_API_KEY` only if using gemini
- [ ] `docker compose ps` - all services healthy
- [ ] `docker compose exec ollama ollama list` shows `llama3`
- [ ] rag `/query` returns answer+citations (after a sync); empty index returns "No record found."
- [ ] agent `/agent/run` returns answer with `tools_used`
- [ ] assistant `/chat` returns content (raise `OLLAMA_TIMEOUT` if 504)
- [ ] guardrails `/check/input` rejects unknown phone before any LLM call
- [ ] doc-extractor `/extract` returns fields from a real S3 doc (live Bedrock)
- [ ] image-analyser trained (`artifacts/model.pth` exists) and `/analyse` returns a class
- [ ] **decide:** wire extractor / analyser / guardrails into n8n (or document them as standalone), and add image-analyser to compose if it must demo

---

## 4. Quick env-var reference

| Var | Area(s) | Default | Required for |
|-----|---------|---------|--------------|
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | extractor, image, gateway, n8n | - | all S3/Bedrock (skip if EC2 role) |
| `AWS_DEFAULT_REGION` / `BEDROCK_REGION` | extractor, n8n | us-east-1 | S3 / Bedrock |
| `S3_BUCKET` | extractor, image, gateway | shepherd-docs | reading/writing docs |
| `S3_BUCKET_ACCIDENTS` | n8n | shepherd-accidents | accident photos |
| `BEDROCK_MODEL_ID` | doc-extractor | - | bedrock extraction |
| `EXTRACTOR_PROVIDER` | doc-extractor | bedrock | choose bedrock/gemini |
| `GEMINI_API_KEY` | doc-extractor | - | gemini extraction |
| `ANTHROPIC_API_KEY` | rag, agent | - | generation/planning |
| `ANTHROPIC_MODEL` | rag | claude-sonnet-4-6 | model select |
| `OPENAI_API_KEY` | guardrails | - | topic/provenance rails |
| `GUARDRAILS_API_KEY` | guardrails | - | install hub validators (build) |
| `GUARDRAILS_LLM` | guardrails | openai/gpt-4o-mini | rail LLM |
| `IMAGE_CONFIDENCE_MIN` | image-analyser | 0.6 | classify threshold |
| `OLLAMA_MODEL` | ollama, assistant | llama3 | local model |
| `OLLAMA_TIMEOUT` | ollama-assistant | 60 | slow-model guard |
| `DATABASE_URL` | rag, guardrails | compose-set | DB reads |
| `INTERNAL_SERVICE_TOKEN` | extractor, agent | change-me | fleet-api auth |
</content>
</invoke>
