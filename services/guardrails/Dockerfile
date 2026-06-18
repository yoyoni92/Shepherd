# Build context must be repo root (consistent with other services).
FROM python:3.12-slim

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

COPY db /db
COPY services/guardrails /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

# Install Guardrails AI hub validators (require GUARDRAILS_API_KEY at build time if not cached)
RUN guardrails hub install hub://guardrails/restrict_to_topic \
    hub://guardrails/toxic_language \
    hub://guardrails/provenance_v1 || true

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
