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
