# Build context must be repo root (path dep: ../../libs).
FROM python:3.12-slim

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

COPY libs /libs
COPY services/doc-extractor /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

EXPOSE 8002
CMD ["uvicorn", "app.service:app", "--host", "0.0.0.0", "--port", "8002"]
