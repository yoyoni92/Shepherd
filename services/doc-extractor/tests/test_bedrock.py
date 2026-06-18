"""T3 - Bedrock extractor (mocked)."""
import json
import pytest
from unittest.mock import MagicMock, patch

from shepherd_contracts import DocType
from app.base import ExtractionError
from app.bedrock import BedrockExtractor


def _mock_client(response_text: str) -> MagicMock:
    body_bytes = json.dumps({"content": [{"text": response_text}]}).encode()
    mock_body = MagicMock()
    mock_body.read.return_value = body_bytes
    mock_response = {"body": mock_body}
    client = MagicMock()
    client.invoke_model.return_value = mock_response
    return client


GOLDEN_INSURANCE = json.dumps({
    "fields": {
        "insurer": "Harel",
        "policy_number": "P-001",
        "plate_number": "12-345-67",
        "coverage_type": "comprehensive",
        "valid_from": "2024-01-01",
        "valid_to": "2025-01-01",
    },
    "confidence": 0.97,
    "raw": "Harel | P-001 | 12-345-67",
})


def test_extract_insurance_returns_parsed_fields():
    client = _mock_client(GOLDEN_INSURANCE)
    extractor = BedrockExtractor(client=client)
    with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
        result = extractor.extract("docs/insurance.pdf", DocType.insurance_cert)
    assert result.doc_type == DocType.insurance_cert
    assert result.fields["plate_number"] == "12-345-67"
    assert result.confidence == 0.97
    assert result.raw == "Harel | P-001 | 12-345-67"


def test_extract_filters_to_known_keys():
    golden = json.dumps({
        "fields": {"insurer": "X", "plate_number": "1", "unknown_extra": "bad"},
        "confidence": 0.9,
    })
    client = _mock_client(golden)
    extractor = BedrockExtractor(client=client)
    with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
        result = extractor.extract("docs/ins.pdf", DocType.insurance_cert)
    assert "unknown_extra" not in result.fields


def test_malformed_json_raises_extraction_error():
    client = _mock_client("not json at all {{{")
    extractor = BedrockExtractor(client=client)
    with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
        with pytest.raises(ExtractionError) as exc:
            extractor.extract("docs/ins.pdf", DocType.insurance_cert)
    assert exc.value.reason == "parse_error"


def test_missing_required_keys_raises_extraction_error():
    client = _mock_client(json.dumps({"only_fields": {}}))
    extractor = BedrockExtractor(client=client)
    with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
        with pytest.raises(ExtractionError) as exc:
            extractor.extract("docs/ins.pdf", DocType.insurance_cert)
    assert exc.value.reason == "schema_error"


def test_image_file_uses_image_block():
    client = _mock_client(GOLDEN_INSURANCE)
    extractor = BedrockExtractor(client=client)
    with patch("app.bedrock._s3_download", return_value=(b"fake", "image/png")):
        extractor.extract("docs/ins.png", DocType.insurance_cert)
    call_body = json.loads(client.invoke_model.call_args.kwargs["body"])
    content = call_body["messages"][0]["content"]
    assert content[0]["type"] == "image"


def test_pdf_file_uses_document_block():
    client = _mock_client(GOLDEN_INSURANCE)
    extractor = BedrockExtractor(client=client)
    with patch("app.bedrock._s3_download", return_value=(b"fake", "application/pdf")):
        extractor.extract("docs/ins.pdf", DocType.insurance_cert)
    call_body = json.loads(client.invoke_model.call_args.kwargs["body"])
    content = call_body["messages"][0]["content"]
    assert content[0]["type"] == "document"
