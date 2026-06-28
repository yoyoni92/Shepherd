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
