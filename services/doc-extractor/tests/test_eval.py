"""T4 - Prompt eval harness: >=10 fixtures, pass rate >= threshold."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "eval" / "fixtures"
PASS_RATE_THRESHOLD = 0.70


def _make_mock_client(llm_response: dict):
    body_bytes = json.dumps({"content": [{"text": json.dumps(llm_response)}]}).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = body_bytes
    client = MagicMock()
    client.invoke_model.return_value = {"body": mock_body}
    return client


def test_fixture_count():
    fixtures = list(FIXTURES_DIR.glob("*.json"))
    assert len(fixtures) >= 10, f"Need >=10 fixtures, found {len(fixtures)}"


def test_eval_pass_rate():
    from shepherd_contracts import DocType
    from app.base import ExtractionError
    from app.bedrock import BedrockExtractor
    from app.prompt import FIELD_KEYS

    fixtures = sorted(FIXTURES_DIR.glob("*.json"))
    passed = 0
    total = len(fixtures)

    required_per_type = {
        "insurance_cert": ["plate_number"],
        "annual_license": ["plate_number"],
        "traffic_ticket": ["plate_number", "amount"],
    }

    for fixture_path in fixtures:
        scenario = json.loads(fixture_path.read_text())
        doc_type = DocType(scenario["doc_type"])
        llm_response = scenario["llm_response"]
        client = _make_mock_client(llm_response)
        extractor = BedrockExtractor(client=client)

        try:
            with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
                result = extractor.extract(f"fake/{fixture_path.stem}.pdf", doc_type)
            required = required_per_type.get(scenario["doc_type"], [])
            if all(result.fields.get(k) is not None for k in required):
                passed += 1
        except ExtractionError:
            pass

    rate = passed / total if total else 0.0
    assert rate >= PASS_RATE_THRESHOLD, (
        f"Eval pass rate {rate:.0%} below threshold {PASS_RATE_THRESHOLD:.0%} "
        f"({passed}/{total} passed)"
    )


def test_all_fixtures_produce_valid_schema():
    """Every fixture that doesn't error must return a schema-valid ExtractionResult."""
    from shepherd_contracts import DocType, ExtractionResult
    from app.base import ExtractionError
    from app.bedrock import BedrockExtractor

    for fixture_path in sorted(FIXTURES_DIR.glob("*.json")):
        scenario = json.loads(fixture_path.read_text())
        doc_type = DocType(scenario["doc_type"])
        client = _make_mock_client(scenario["llm_response"])
        extractor = BedrockExtractor(client=client)

        try:
            with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
                result = extractor.extract(f"fake/{fixture_path.stem}.pdf", doc_type)
            assert isinstance(result, ExtractionResult)
            assert 0.0 <= result.confidence <= 1.0
        except ExtractionError:
            pass  # low-confidence or error scenarios are acceptable
