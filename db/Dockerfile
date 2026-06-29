# Build context is repo root (compose: context: ., dockerfile: db/Dockerfile).
# db/pyproject.toml path-deps ../libs/shepherd_config, so libs/shepherd_config must be
# present in the image (it resolves to /libs/shepherd_config from WORKDIR /db).
FROM python:3.12-slim
RUN pip install --quiet poetry
WORKDIR /db
COPY libs/shepherd_config /libs/shepherd_config
COPY db/pyproject.toml db/poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root
COPY db /db
