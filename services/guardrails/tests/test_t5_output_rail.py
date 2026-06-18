"""T5 - Output grounding rail: grounded passes, fabricated claims fail with safe_text."""
from unittest.mock import MagicMock

from app.guardrails_ai import GuardrailsAIProvider


def _make_provider(mocker, passed: bool, error: str | None = None, validated_output: str | None = None):
    outcome = MagicMock(validation_passed=passed, error=error, validated_output=validated_output)
    mock_guard = MagicMock()
    mock_guard.validate.return_value = outcome
    mocker.patch("app.guardrails_ai._get_output_guard", return_value=mock_guard)
    return GuardrailsAIProvider()


def test_grounded_output_passes(mocker):
    provider = _make_provider(mocker, passed=True)
    result = provider.check_output(
        'הרכב עבר 50,000 ק"מ',
        ['mileage: 50000 km'],
    )
    assert result["pass"] is True
    assert result.get("safe_text") is None


def test_invented_price_fails_with_safe_text(mocker):
    redacted = "הרכב יצא לטיפול"
    provider = _make_provider(
        mocker,
        passed=False,
        error="Unsupported claim: fine amount not in sources",
        validated_output=redacted,
    )
    result = provider.check_output(
        "הרכב יקבל קנס של 500 שקל על פי תקנה 5",
        ["no financial data here"],
    )
    assert result["pass"] is False
    assert result["safe_text"] == redacted


def test_invented_legal_claim_fails(mocker):
    provider = _make_provider(
        mocker,
        passed=False,
        error="Unsupported legal claim",
        validated_output="",
    )
    result = provider.check_output(
        "על פי חוק התעבורה סעיף 99 יש לשלם 1000 שקל",
        ["no legal reference"],
    )
    assert result["pass"] is False
    assert "safe_text" in result


def test_safe_text_returned_when_redaction_applies(mocker):
    provider = _make_provider(
        mocker,
        passed=False,
        error="grounding failed",
        validated_output="[REDACTED]",
    )
    result = provider.check_output("fabricated claim", [])
    assert result["safe_text"] == "[REDACTED]"
