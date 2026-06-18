# Build context must be repo root (consistent with other services).
FROM python:3.12-slim

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

COPY prompts /prompts
COPY services/ollama-assistant /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
