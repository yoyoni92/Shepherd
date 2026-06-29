# Build context is repo root (compose: context: ., dockerfile: services/telegram-bot/Dockerfile).
FROM python:3.12-slim

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

# Path dep: services/telegram-bot/pyproject.toml -> ../../libs/shepherd_config, which
# resolves to /libs/shepherd_config from /app/svc. Copy it so poetry install can find it.
COPY libs/shepherd_config /libs/shepherd_config
COPY services/telegram-bot /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

# Long-polling worker: no port to expose.
CMD ["python", "-m", "app.main"]
