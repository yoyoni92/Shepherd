# Build context must be repo root (path dep: ../../db).
FROM python:3.12-slim

# llama-cpp-python requires gcc/g++/cmake to compile from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ cmake build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

COPY db /db
COPY services/rag /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
