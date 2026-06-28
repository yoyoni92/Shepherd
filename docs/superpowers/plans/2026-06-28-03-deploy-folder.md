# Deploy Folder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a self-contained `deploy/` folder so a destination host that has **only Docker + this folder** (no git clone, no source tree, no build toolchain) can run the full Shepherd stack from **pre-built images pulled from Docker Hub**.

**Architecture:** `deploy/docker-compose.prod.yml` is a faithful copy of the repo-root `docker-compose.yml` with every `build:` swapped for `image: ${REGISTRY}/shepherd-<svc>:${TAG}`. Five images are pulled: `shepherd-postgres` (Postgres 16 + pg_cron, with `db/roles.sql` baked in), `shepherd-db-init` (runs schema + seed via the existing `entrypoint.sh`), `shepherd-fleet-api`, `shepherd-telegram-bot`, `shepherd-webui`. The filled `config.toml` is mounted into the two Python services at `/etc/shepherd/config.toml` (`SHEPHERD_CONFIG`); the webui stays on env only. Secret **values** live in exactly one place, `deploy/.env`, injected via `env_file:`; `config.toml` references them as `${VAR}`. `deploy.sh` is a short bash script: `docker compose pull` then `up -d`, waiting for Postgres to go healthy (the `depends_on` chain then runs `db-init` and gates the app services). Images are produced and pushed by CI (plan 04).

**Tech Stack:** Docker, docker compose, bash.

## Global Constraints
- mirror docker-compose.yml; pull images, never build on host
- no git clone / no source on the destination host
- single source of secret values: deploy/.env ; config.toml interpolates ${VAR}
- reuse the existing db `entrypoint.sh` for schema/seed (baked into the `shepherd-db-init` image); do NOT reimplement provisioning here
- webui keeps env-only config (no config.toml mount), exactly as in the dev compose
- do NOT redesign services, ports, volumes, healthchecks, or `depends_on` — copy them from `docker-compose.yml` and only swap `build:` for `image:`
- infra has no unit tests: every task ends with a concrete VERIFICATION command + its expected output, then a commit
- mark every deliberate simplification with a `# ponytail:` comment

### Shared interface contract (must match plans 01 and 04)
- Images: `${REGISTRY}/shepherd-<svc>:${TAG}` for `svc` in `{postgres, db-init, fleet-api, telegram-bot, webui}`. `${REGISTRY}` is an env var (e.g. `docker.io/yourorg`); domain/placeholder emails use `shepherd.ai`.
- Plan 04's image builds MUST bake host-independent assets into the images: `shepherd-postgres` copies `db/roles.sql` into `/docker-entrypoint-initdb.d/`; `shepherd-db-init` copies the whole `db/` tree (so `sh entrypoint.sh` works with no host mount). This plan assumes those bakes exist.
- `config.toml` schema (from `shepherd_config`, plan 01):
  - `[database]` `url="${DATABASE_URL}"` `shared_schema="public"`
  - `[services]` `fleet_api_url="${FLEET_API_URL}"`
  - `[[company]]` `slug="default"` `schema="co_default"` (repeatable; `schema` may be shared across companies)
- Python services read `SHEPHERD_CONFIG=/etc/shepherd/config.toml`.

---

### Task 1: `deploy/.env.example` (single source of secret values) + `deploy/.gitignore`

**Files:**
- `deploy/.env.example` (new)
- `deploy/.gitignore` (new)

`deploy/.env` and `deploy/config.toml` are the operator's filled, secret-bearing copies — they must never be committed. The `.gitignore` guards that. Only the `*.example` templates are tracked.

Steps:

- [x] 1. Create `deploy/.env.example` with the exact contents below. Every value an operator must supply lives here once; `config.toml` and the compose interpolation both read from it.

```bash
# deploy/.env.example
# Single source of secret VALUES. Copy to .env and fill in.
#   cp .env.example .env
# config.toml references ${VAR} from this file; docker compose interpolates
# ${REGISTRY}/${TAG} from it too (deploy.sh passes --env-file .env).

# --- Image registry (pre-built images pushed by CI, plan 04) ---
# <org> placeholder. e.g. docker.io/yourorg  or  ghcr.io/yourorg
REGISTRY=docker.io/yourorg
TAG=latest

# --- Postgres (compose `command` + container init read these) ---
POSTGRES_USER=shepherd
POSTGRES_PASSWORD=change-me
POSTGRES_DB=shepherd
# Points at the `postgres` service on the compose network (host = service name).
DATABASE_URL=postgresql+psycopg://shepherd:change-me@postgres:5432/shepherd

# --- Internal service auth (shared by fleet-api, webui proxy, telegram-bot) ---
INTERNAL_SERVICE_TOKEN=change-me
# Fleet API signs the app-user JWT (POST /auth/login) with this. Keep it stable
# across restarts or existing sessions break.
AUTH_JWT_SECRET=change-me-jwt-secret

# --- Telegram bot (aiogram long-polling) ---
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=ShepherdBot

# --- External LLMs ---
GEMINI_API_KEY=
OPENAI_API_KEY=

# --- WebUI admin console (Next.js / NextAuth) ---
NEXTAUTH_SECRET=change-me
# Public base URL the browser hits (set to your real domain in prod).
NEXTAUTH_URL=http://localhost:3000
ADMIN_EMAIL=admin@shepherd.ai
ADMIN_PASSWORD=change-me

# --- Google Drive storage (Fleet API owns uploads) ---
# Host path to the service-account JSON key, mounted read-only into fleet-api.
GDRIVE_SA_KEY_PATH=./secrets/gdrive-sa.json
GDRIVE_FOLDER_ID=

# --- Inter-service URL ---
# config.toml interpolates this; the webui proxy reads it directly.
FLEET_API_URL=http://fleet-api:8000
```

- [x] 2. Create `deploy/.gitignore` with the exact contents below.

```gitignore
# deploy/.gitignore
# Filled, secret-bearing copies. Never commit. Track only the *.example templates.
.env
config.toml
secrets/
```

- [x] 3. VERIFICATION — confirm both files exist and the template parses as a valid env file (no shell-special breakage):

```bash
test -f deploy/.env.example && test -f deploy/.gitignore && \
  env -i sh -c 'set -a; . deploy/.env.example; echo "REGISTRY=$REGISTRY TAG=$TAG"'
```

Expected output (exactly):

```
REGISTRY=docker.io/yourorg TAG=latest
```

- [x] 4. COMMIT.

```bash
git add deploy/.env.example deploy/.gitignore
```

Commit subject: `add deploy env template and gitignore`

Commit body (wrapped at 72):
```
Introduce deploy/.env.example as the single source of secret values for
the pull-only deploy folder, plus a .gitignore that keeps the filled
.env, config.toml, and secrets out of version control.
```

---

### Task 2: `deploy/config.example.toml` (central config template)

**Files:**
- `deploy/config.example.toml` (new)

Matches the `shepherd_config` schema from plan 01. Non-secret structure only; secret values are `${VAR}` references resolved from `deploy/.env` at load time.

Steps:

- [x] 1. Create `deploy/config.example.toml` with the exact contents below.

```toml
# deploy/config.example.toml
# Central config template. Copy to config.toml and edit the [[company]] map.
#   cp config.example.toml config.toml
# Secret values stay as ${VAR} and are read from deploy/.env at load time.
# Mounted into the Python services at /etc/shepherd/config.toml (SHEPHERD_CONFIG).

[database]
url = "${DATABASE_URL}"        # postgresql+psycopg://... (from .env)
shared_schema = "public"       # control-plane tables live here

[services]
fleet_api_url = "${FLEET_API_URL}"

# Seeded companies. The schema name is DATA, never derived from the slug in code.
# The map is many-to-one: two companies may point at the SAME schema (subcompanies),
# in which case company_id row scoping is the only thing separating them.
[[company]]
slug = "default"
schema = "co_default"

# Example of a second tenant (uncomment and edit to add one):
# [[company]]
# slug = "acme"
# schema = "co_acme"

# Example of a shared schema (subcompanies a + b colocated in one schema):
# [[company]]
# slug = "bigcorp-a"
# schema = "co_bigcorp"
# [[company]]
# slug = "bigcorp-b"
# schema = "co_bigcorp"
```

- [x] 2. VERIFICATION — confirm the template is valid TOML (`${VAR}` placeholders are ordinary strings to a TOML parser):

```bash
python3 -c "import tomllib; d=tomllib.load(open('deploy/config.example.toml','rb')); print(d['database']['shared_schema'], d['company'][0]['slug'])"
```

Expected output (exactly):

```
public default
```

- [x] 3. COMMIT.

```bash
git add deploy/config.example.toml
```

Commit subject: `add deploy config.toml template`

Commit body (wrapped at 72):
```
Add the central config template for the deploy folder. It carries the
non-secret structure (database, services, per-company schema map) and
references secrets as ${VAR} resolved from deploy/.env at load time.
```

---

### Task 3: `deploy/docker-compose.prod.yml` (mirror dev compose, pull images)

**Files:**
- `deploy/docker-compose.prod.yml` (new)
- `db/postgres.Dockerfile` (modify - bake `roles.sql` into the image)

A faithful copy of `docker-compose.yml`: same services, ports, volumes, healthchecks, `depends_on`. Only changes: `build:` becomes `image: ${REGISTRY}/shepherd-<svc>:${TAG}`; secrets come from `env_file: .env`; `config.toml` is mounted into the Python services; the dev `roles.sql` host mount is dropped. Because the prod host has no source tree to mount, `roles.sql` must be **baked into the postgres image** - the dev compose mounts `./db/roles.sql` into `/docker-entrypoint-initdb.d/`, so this task adds that `COPY` to `db/postgres.Dockerfile` (harmless for dev: initdb scripts only run on a fresh data volume). The `db-init` image already bakes the whole `db/` tree (`db/Dockerfile` does `COPY . .`), so no change is needed there.

Steps:

- [x] 1. Create `deploy/docker-compose.prod.yml` with the exact contents below.

```yaml
# deploy/docker-compose.prod.yml
# ponytail: this is docker-compose.yml with `build:` swapped for `image:` and a
# single env_file for secrets — services, ports, volumes, healthchecks, and
# depends_on are copied verbatim from the dev compose. Do not redesign them.
# Run via deploy.sh (docker compose -f docker-compose.prod.yml --env-file .env ...).
name: shepherd
services:
  postgres:
    image: ${REGISTRY}/shepherd-postgres:${TAG}
    # pg_cron must be preloaded and pointed at the app DB for the kpi_daily schedule.
    command: postgres -c shared_preload_libraries=pg_cron -c cron.database_name=${POSTGRES_DB:-shepherd}
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-shepherd}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-shepherd}
      POSTGRES_DB: ${POSTGRES_DB:-shepherd}
    ports:
      - "5432:5432"
    # ponytail: no ./db/roles.sql host mount — the prebuilt shepherd-postgres
    # image bakes roles.sql into /docker-entrypoint-initdb.d/ (see step 2 below).
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-shepherd}"]
      interval: 5s
      timeout: 3s
      retries: 10

  db-init:
    image: ${REGISTRY}/shepherd-db-init:${TAG}
    # Reuses the existing db entrypoint (create_schema + seed + grants + KPI backfill),
    # baked into the image at /db. Runs once, then exits.
    command: sh entrypoint.sh
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
    restart: "no"

  fleet-api:
    image: ${REGISTRY}/shepherd-fleet-api:${TAG}
    env_file:
      - .env
    environment:
      # Pinned, non-secret container wiring (overrides anything from .env).
      SHEPHERD_CONFIG: /etc/shepherd/config.toml
      GOOGLE_APPLICATION_CREDENTIALS: /run/secrets/gdrive-sa.json
    volumes:
      - ./config.toml:/etc/shepherd/config.toml:ro
      - ${GDRIVE_SA_KEY_PATH:-./secrets/gdrive-sa.json}:/run/secrets/gdrive-sa.json:ro
    ports:
      - "8000:8000"
    depends_on:
      db-init:
        condition: service_completed_successfully
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\""]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  webui:
    image: ${REGISTRY}/shepherd-webui:${TAG}
    env_file:
      - .env
    environment:
      # ponytail: webui stays env-only (no config.toml). Pinned non-secret wiring:
      # Docker auto-sets HOSTNAME to the container id; Next's standalone server would
      # bind to it and refuse localhost (breaking the healthcheck). Pin to all ifaces.
      HOSTNAME: 0.0.0.0
      PORT: 3000
      # Public: rendered as the plain t.me/<bot> link. NEXT_PUBLIC_* is inlined at
      # build time, so a non-default bot name needs a rebuilt image.
      NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: ${TELEGRAM_BOT_USERNAME:-ShepherdBot}
    ports:
      - "3000:3000"
    depends_on:
      db-init:
        condition: service_completed_successfully
    healthcheck:
      # 127.0.0.1, not localhost: inside the container localhost resolves to ::1 (IPv6),
      # but the standalone server binds IPv4 0.0.0.0 — the probe must hit 127.0.0.1.
      test: ["CMD-SHELL", "wget -q -O- http://127.0.0.1:3000/api/auth/session || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 5
      start_period: 30s

  # Invite-only Hebrew Telegram bot. aiogram long-polling, so no public HTTPS / tunnel.
  telegram-bot:
    image: ${REGISTRY}/shepherd-telegram-bot:${TAG}
    env_file:
      - .env
    environment:
      SHEPHERD_CONFIG: /etc/shepherd/config.toml
    volumes:
      - ./config.toml:/etc/shepherd/config.toml:ro
    depends_on:
      fleet-api:
        condition: service_healthy

volumes:
  pgdata:
```

- [x] 2. Bake `roles.sql` into the postgres image so the prod host needs no source mount. Edit `db/postgres.Dockerfile`, appending a `COPY` after the `RUN` block (build context for this image is `./db`, so `roles.sql` is at the context root):

```dockerfile
# Bake role/grant bootstrap into initdb so no host mount is needed in prod
# (dev compose used a ./db/roles.sql volume; baking is a no-op on an existing
# data volume since initdb scripts run only on first cluster init).
COPY roles.sql /docker-entrypoint-initdb.d/roles.sql
```

VERIFICATION — confirm the file is in the build context and the Dockerfile references it:

```bash
test -f db/roles.sql && grep -q "COPY roles.sql /docker-entrypoint-initdb.d/" db/postgres.Dockerfile && echo OK
```

Expected output: `OK`

- [x] 3. VERIFICATION — render and validate the compose file with full var interpolation. `config` requires `.env` and `config.toml` to exist, so create them from the templates first (they are gitignored, so they will not be committed):

```bash
cp deploy/.env.example deploy/.env
cp deploy/config.example.toml deploy/config.toml
docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env config | grep -E 'image:'
```

Expected output (exactly, order may vary by service):

```
    image: docker.io/yourorg/shepherd-postgres:latest
    image: docker.io/yourorg/shepherd-db-init:latest
    image: docker.io/yourorg/shepherd-fleet-api:latest
    image: docker.io/yourorg/shepherd-webui:latest
    image: docker.io/yourorg/shepherd-telegram-bot:latest
```

A clean `config` exit code (`echo $?` -> `0`) confirms the YAML parses and every `${VAR}` resolved. If `config` warns about an unset variable, that variable is missing from `.env.example` — fix it there.

- [x] 4. CLEANUP the local secret copies so they are never staged:

```bash
rm -f deploy/.env deploy/config.toml
```

- [x] 5. COMMIT.

```bash
git add deploy/docker-compose.prod.yml db/postgres.Dockerfile
```

Commit subject: `add pull-only prod compose for the deploy folder`

Commit body (wrapped at 72):
```
Mirror the dev docker-compose.yml as docker-compose.prod.yml: every
service pulls ${REGISTRY}/shepherd-<svc>:${TAG} instead of building, the
Python services mount the filled config.toml at /etc/shepherd, and all
secrets come from a single env_file. Ports, volumes, healthchecks, and
depends_on are copied verbatim from the dev compose.

Bake roles.sql into the postgres image (COPY into initdb) so the prod
host needs no source mount; the dev compose used a host volume.
```

---

### Task 4: `deploy/deploy.sh` (pull + up, idempotent)

**Files:**
- `deploy/deploy.sh` (new)

A short bash script: validate inputs, `docker compose pull`, `up -d`, wait for Postgres healthy, print status. The `depends_on` chain runs `db-init` (schema + seed, idempotent) and gates the app services, so the script needs no orchestration logic. Re-running it is safe.

Steps:

- [x] 1. Create `deploy/deploy.sh` with the exact contents below.

```bash
#!/usr/bin/env bash
# deploy/deploy.sh
# Pull pre-built images and bring the Shepherd stack up. Idempotent / re-runnable.
# ponytail: just `docker compose pull` + `up -d` — no orchestration tooling. The
# compose depends_on chain runs db-init (schema+seed) and gates the app services.
set -euo pipefail
cd "$(dirname "$0")"

[ -f .env ] || { echo "ERROR: .env not found. Run: cp .env.example .env  then fill it." >&2; exit 1; }
[ -f config.toml ] || { echo "ERROR: config.toml not found. Run: cp config.example.toml config.toml  then edit it." >&2; exit 1; }

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env)

echo ">> Pulling images..."
"${COMPOSE[@]}" pull

echo ">> Starting stack..."
"${COMPOSE[@]}" up -d

echo ">> Waiting for postgres to become healthy..."
for _ in $(seq 1 30); do
  status="$("${COMPOSE[@]}" ps postgres --format '{{.Health}}' 2>/dev/null || true)"
  [ "$status" = "healthy" ] && { echo ">> postgres healthy."; break; }
  sleep 2
done

echo ">> Stack status:"
"${COMPOSE[@]}" ps

echo ">> Done. db-init ran schema + seed (idempotent); app services are gated on it."
```

- [x] 2. Make it executable:

```bash
chmod +x deploy/deploy.sh
```

- [x] 3. VERIFICATION (a) — bash syntax check (no run, no Docker needed):

```bash
bash -n deploy/deploy.sh && echo "syntax OK"
```

Expected output (exactly):

```
syntax OK
```

- [x] 4. VERIFICATION (b) — confirm the guard rails fire when inputs are missing (run from a temp dir so no real `.env` is present):

```bash
( cd "$(mktemp -d)" && cp "$OLDPWD/deploy/deploy.sh" . && ./deploy.sh; echo "exit=$?" )
```

Expected output (exactly):

```
ERROR: .env not found. Run: cp .env.example .env  then fill it.
exit=1
```

- [x] 5. VERIFICATION (c) — DOCUMENTED MANUAL SMOKE (requires plan 04 images to exist on Docker Hub; do NOT run in CI). On a host with Docker and a filled `deploy/.env` + `deploy/config.toml`:

```bash
cd deploy && ./deploy.sh
# wait for fleet-api to report healthy, then:
curl -fsS http://localhost:8000/health
```

Expected: `deploy.sh` ends with `>> postgres healthy.` and a `docker compose ps` table where `db-init` shows `Exited (0)` and `fleet-api`/`webui` show `healthy`; the `curl` prints fleet-api's health JSON (HTTP 200). Re-running `./deploy.sh` produces the same end state (idempotent).

- [x] 6. COMMIT.

```bash
git add deploy/deploy.sh
```

Commit subject: `add idempotent deploy.sh for the deploy folder`

Commit body (wrapped at 72):
```
Add deploy.sh: validate the filled .env and config.toml, pull the
pre-built images, bring the stack up, and wait for Postgres to go
healthy. The compose depends_on chain runs db-init and gates the app
services, so the script stays a short pull-and-up wrapper that is safe
to re-run.
```

---

### Task 5: `deploy/README.md` (operator runbook)

**Files:**
- `deploy/README.md` (new)

Exact, copy-pasteable steps for an operator on a fresh host. Documents that images come from CI (plan 04) pushing to Docker Hub.

Steps:

- [x] 1. Create `deploy/README.md` with the exact contents below.

```markdown
# Shepherd - Deploy Folder

Run the full Shepherd stack on a fresh host from **pre-built Docker images**.
The host needs only **Docker** (with the Compose plugin) and **this folder** -
no git clone, no source tree, no build toolchain.

The images (`shepherd-postgres`, `shepherd-db-init`, `shepherd-fleet-api`,
`shepherd-telegram-bot`, `shepherd-webui`) are built and pushed to Docker Hub by
CI (see plan 04) as `${REGISTRY}/shepherd-<svc>:${TAG}`.

## Contents

| File                       | Purpose                                                  |
| -------------------------- | -------------------------------------------------------- |
| `docker-compose.prod.yml`  | Pull-only stack (images, not builds).                    |
| `config.example.toml`      | Central config template -> copy to `config.toml`.        |
| `.env.example`             | All secret values + `REGISTRY`/`TAG` -> copy to `.env`.  |
| `deploy.sh`                | `docker compose pull` + `up -d`; idempotent.             |

## Prerequisites

- A Linux host with Docker Engine and the Compose plugin:

  ```bash
  curl -fsSL https://get.docker.com | sh
  docker compose version   # must succeed
  ```

- Login to the registry if the images are private:

  ```bash
  docker login docker.io   # use your Docker Hub user + access token
  ```

## Steps

1. **Get this folder onto the host** (only `deploy/` is needed - no clone):

   ```bash
   # from your workstation
   tar czf deploy.tgz -C /path/to/Shepherd deploy
   scp deploy.tgz user@host:~
   # on the host
   tar xzf deploy.tgz && cd deploy
   ```

2. **Create the secret file** and fill every value (registry, DB password,
   tokens, LLM keys, NextAuth, admin login, Google Drive):

   ```bash
   cp .env.example .env
   ${EDITOR:-vi} .env
   ```

   Set `REGISTRY` and `TAG` to the images CI pushed (e.g. `docker.io/yourorg`
   and a git SHA or `latest`). Set `DATABASE_URL` to point at the `postgres`
   service host (`@postgres:5432`).

3. **Create the config file** and edit the company -> schema map:

   ```bash
   cp config.example.toml config.toml
   ${EDITOR:-vi} config.toml
   ```

   Leave the `${VAR}` references as-is - they resolve from `.env` at load time.

4. **(If using Google Drive uploads)** place the service-account JSON key at the
   path named by `GDRIVE_SA_KEY_PATH` (default `./secrets/gdrive-sa.json`):

   ```bash
   mkdir -p secrets && cp /path/to/sa.json secrets/gdrive-sa.json
   ```

5. **Deploy:**

   ```bash
   ./deploy.sh
   ```

   This pulls the images, starts the stack, runs `db-init` (schema + seed,
   idempotent), and waits for Postgres to go healthy. Re-running `./deploy.sh`
   is safe.

## Verify

```bash
docker compose -f docker-compose.prod.yml --env-file .env ps
curl -fsS http://localhost:8000/health     # fleet-api
curl -fsS http://localhost:3000/api/auth/session   # webui
```

`db-init` should show `Exited (0)`; `fleet-api` and `webui` should be `healthy`.

## Operate

```bash
# tail logs
docker compose -f docker-compose.prod.yml --env-file .env logs -f

# stop (keeps the pgdata volume)
docker compose -f docker-compose.prod.yml --env-file .env down

# upgrade to a new image tag: edit TAG in .env, then
./deploy.sh
```

## Notes

- `.env`, `config.toml`, and `secrets/` are git-ignored and must never be
  committed - they hold secret values.
- The stack publishes Postgres `5432`, fleet-api `8000`, and webui `3000`. Put a
  reverse proxy / firewall in front of `3000` (and `8000` if exposed) in prod.
```

- [x] 2. VERIFICATION — confirm the README exists and references the four deliverables it documents:

```bash
test -f deploy/README.md && \
  grep -c -E 'docker-compose.prod.yml|config.example.toml|\.env.example|deploy.sh' deploy/README.md
```

Expected output (a count of 4 or greater):

```
<a number >= 4>
```

- [x] 3. COMMIT.

```bash
git add deploy/README.md
```

Commit subject: `add operator runbook for the deploy folder`

Commit body (wrapped at 72):
```
Document the fresh-host deploy flow: install Docker, copy the deploy
folder, fill .env and config.toml, drop in the Google Drive key, and run
deploy.sh. Notes that images come from CI pushing to Docker Hub and that
the filled secret files stay out of version control.
```

---

## Done criteria

- `deploy/` contains: `.env.example`, `.gitignore`, `config.example.toml`, `docker-compose.prod.yml`, `deploy.sh` (executable), `README.md`.
- `docker compose -f deploy/docker-compose.prod.yml --env-file deploy/.env config` exits 0 with all five `image:` lines resolved to `${REGISTRY}/shepherd-<svc>:${TAG}` and no unset-variable warnings.
- `bash -n deploy/deploy.sh` passes; the missing-input guard exits 1 with the expected message.
- No secret-bearing file (`deploy/.env`, `deploy/config.toml`, `deploy/secrets/`) is tracked by git.
- The documented manual smoke (Task 4 step 5) is runnable once plan 04 has pushed images.
```
