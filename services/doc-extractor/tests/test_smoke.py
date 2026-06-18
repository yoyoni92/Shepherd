"""T7 - Live smoke tests (gated on real creds)."""
import os
import pytest

from shepherd_contracts import DocType

_NO_AWS = not (
    os.environ.get("AWS_ACCESS_KEY_ID")
    and os.environ.get("AWS_SECRET_ACCESS_KEY")
    and os.environ.get("BEDROCK_MODEL_ID")
    and os.environ.get("S3_BUCKET")
)

_NO_GEMINI = not (
    os.environ.get("GEMINI_API_KEY")
    and os.environ.get("S3_BUCKET")
)


@pytest.mark.live
@pytest.mark.skipif(_NO_AWS, reason="requires AWS creds, BEDROCK_MODEL_ID, and S3_BUCKET")
def test_bedrock_live_smoke():
    """One real Bedrock call on a fixture object. Confirms region/model wiring."""
    from app.bedrock import BedrockExtractor
    extractor = BedrockExtractor()
    s3_key = os.environ.get("SMOKE_TEST_S3_KEY", "fixtures/clean_insurance.pdf")
    result = extractor.extract(s3_key, DocType.insurance_cert)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.fields, dict)


@pytest.mark.live
@pytest.mark.skipif(_NO_GEMINI, reason="requires GEMINI_API_KEY and S3_BUCKET")
def test_gemini_live_smoke():
    """One real Gemini call on a fixture object. Confirms API key and model wiring."""
    from app.gemini import GeminiExtractor
    extractor = GeminiExtractor()
    s3_key = os.environ.get("SMOKE_TEST_S3_KEY", "fixtures/clean_insurance.pdf")
    result = extractor.extract(s3_key, DocType.insurance_cert)
    assert 0.0 <= result.confidence <= 1.0
    assert isinstance(result.fields, dict)
