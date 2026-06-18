import os
import pytest

@pytest.fixture(autouse=True)
def bedrock_model_env(monkeypatch):
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    monkeypatch.setenv("EXTRACTOR_PROVIDER", "bedrock")
    monkeypatch.setenv("S3_BUCKET", "test-bucket")
