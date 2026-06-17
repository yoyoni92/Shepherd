FROM python:3.12-slim
WORKDIR /db
RUN pip install --quiet poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only main --no-root
COPY . .
