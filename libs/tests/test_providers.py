
import pytest
from shepherd_contracts import (
    ChannelProvider,
    DocType,
    DocumentExtractor,
    ExtractionResult,
    GuardrailProvider,
)


def test_abstract_cannot_instantiate():
    with pytest.raises(TypeError):
        ChannelProvider()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        DocumentExtractor()  # type: ignore[abstract]
    with pytest.raises(TypeError):
        GuardrailProvider()  # type: ignore[abstract]


class FakeExtractor(DocumentExtractor):
    def extract(self, s3_key: str, doc_type: DocType) -> ExtractionResult:
        return ExtractionResult(doc_type=doc_type, fields={}, confidence=1.0)


def test_concrete_extractor_conforms():
    r = FakeExtractor().extract("k", DocType.other)
    assert isinstance(r, ExtractionResult)


class FakeGuardrail(GuardrailProvider):
    def check_input(self, text, context):
        return {"pass": True, "reason": ""}

    def check_output(self, text, sources):
        return {"pass": True, "reason": "", "safe_text": text}


def test_concrete_guardrail_conforms():
    g = FakeGuardrail()
    assert g.check_input("hi", None)["pass"] is True
    assert g.check_output("brief", [])["safe_text"] == "brief"
