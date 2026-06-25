# Build context is repo root (compose: context: ., dockerfile: services/telegram-bot/Dockerfile).
FROM python:3.12-slim

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

COPY services/telegram-bot /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

# Long-polling worker: no port to expose.
CMD ["python", "-m", "app.main"]
