# Build context MUST be the repo root so path deps (libs, testkit) are available.
# In docker-compose:
#   build: { context: ., dockerfile: services/__NAME__/Dockerfile }
FROM python:3.12-slim

RUN pip install --no-cache-dir poetry==2.4.0
WORKDIR /app

# path deps land where pyproject expects them (../../libs from /app/svc -> /libs)
COPY libs /libs
COPY testkit /testkit
COPY services/__NAME__ /app/svc

WORKDIR /app/svc
RUN poetry config virtualenvs.create false \
 && poetry install --only main --no-root

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
