"""T3 - GuardrailProvider Protocol conformance (swap seam)."""
from app.base import GuardrailProvider
from app.guardrails_ai import BedrockGuardrailsStub, GuardrailsAIProvider


def test_guardrails_ai_conforms_to_protocol():
    assert isinstance(GuardrailsAIProvider(), GuardrailProvider)


def test_bedrock_stub_conforms_to_protocol():
    assert isinstance(BedrockGuardrailsStub(), GuardrailProvider)


def test_protocol_requires_both_methods():
    class Incomplete:
        def check_input(self, text, context): ...
        # missing check_output

    assert not isinstance(Incomplete(), GuardrailProvider)


def test_bedrock_stub_raises_on_check_input():
    import pytest

    stub = BedrockGuardrailsStub()
    with pytest.raises(NotImplementedError):
        stub.check_input("text", {})


def test_bedrock_stub_raises_on_check_output():
    import pytest

    stub = BedrockGuardrailsStub()
    with pytest.raises(NotImplementedError):
        stub.check_output("text", [])
