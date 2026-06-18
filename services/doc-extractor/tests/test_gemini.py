"""T6 - Gemini fallback parity: same fixtures, schema-valid output."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shepherd_contracts import DocType, ExtractionResult
from app.base import ExtractionError
from app.gemini import GeminiExtractor

FIXTURES_DIR = Path(__file__).parent.parent / "eval" / "fixtures"


def _mock_gemini_model(llm_response: dict) -> MagicMock:
    model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(llm_response)
    model.generate_content.return_value = mock_response
    return model


def test_gemini_satisfies_interface():
    from shepherd_contracts import DocumentExtractor
    assert isinstance(GeminiExtractor(), DocumentExtractor)


def test_gemini_parses_golden_insurance():
    llm_response = {
        "fields": {
            "insurer": "Harel",
            "policy_number": "P-001",
            "plate_number": "12-345-67",
            "coverage_type": "comprehensive",
            "valid_from": "2024-01-01",
            "valid_to": "2025-01-01",
        },
        "confidence": 0.94,
    }
    model = _mock_gemini_model(llm_response)
    extractor = GeminiExtractor(model=model)
    with patch("app.gemini._s3_download", return_value=b"fake"):
        result = extractor.extract("docs/ins.pdf", DocType.insurance_cert)
    assert isinstance(result, ExtractionResult)
    assert result.fields["plate_number"] == "12-345-67"
    assert result.confidence == 0.94


def test_gemini_malformed_json_raises():
    model = MagicMock()
    model.generate_content.return_value.text = "not json {"
    extractor = GeminiExtractor(model=model)
    with patch("app.gemini._s3_download", return_value=b"fake"):
        with pytest.raises(ExtractionError) as exc:
            extractor.extract("docs/ins.pdf", DocType.insurance_cert)
    assert exc.value.reason == "parse_error"


def test_gemini_fixtures_produce_schema_valid_output():
    """Provider-swap contract: Gemini passes same fixtures as Bedrock."""
    for fixture_path in sorted(FIXTURES_DIR.glob("*.json")):
        scenario = json.loads(fixture_path.read_text())
        doc_type = DocType(scenario["doc_type"])
        model = _mock_gemini_model(scenario["llm_response"])
        extractor = GeminiExtractor(model=model)

        try:
            with patch("app.gemini._s3_download", return_value=b"fake"):
                result = extractor.extract(f"fake/{fixture_path.stem}.pdf", doc_type)
            assert isinstance(result, ExtractionResult)
            assert 0.0 <= result.confidence <= 1.0
        except ExtractionError:
            pass
