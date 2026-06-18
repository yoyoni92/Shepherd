"""T1 - Interface + provider selection."""
import pytest
from shepherd_contracts import DocumentExtractor

from app.base import get_extractor
from app.bedrock import BedrockExtractor
from app.gemini import GeminiExtractor


def test_default_returns_bedrock():
    extractor = get_extractor("bedrock")
    assert isinstance(extractor, BedrockExtractor)


def test_gemini_returned_when_configured():
    extractor = get_extractor("gemini")
    assert isinstance(extractor, GeminiExtractor)


def test_bedrock_satisfies_interface():
    assert isinstance(get_extractor("bedrock"), DocumentExtractor)


def test_gemini_satisfies_interface():
    assert isinstance(get_extractor("gemini"), DocumentExtractor)


def test_missing_model_id_raises_on_extract(monkeypatch):
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    extractor = BedrockExtractor()
    from unittest.mock import patch
    with patch("app.bedrock._s3_download", return_value=(b"x", "application/pdf")):
        with pytest.raises(RuntimeError, match="BEDROCK_MODEL_ID"):
            from shepherd_contracts import DocType
            extractor.extract("any/key.pdf", DocType.insurance_cert)
