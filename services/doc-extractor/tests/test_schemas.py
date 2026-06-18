"""T2 - Per-doc-type output schemas."""
import pytest
from shepherd_contracts import DocType, InsuranceFields, LicenseFields, TicketFields, ExtractionResult


def test_insurance_fields_optional_all_null():
    f = InsuranceFields()
    assert f.insurer is None
    assert f.policy_number is None
    assert f.plate_number is None


def test_insurance_fields_populated():
    f = InsuranceFields(insurer="Harel", policy_number="P-001", plate_number="12-345-67",
                        coverage_type="comprehensive", valid_from="2024-01-01", valid_to="2025-01-01")
    assert f.insurer == "Harel"
    assert f.plate_number == "12-345-67"


def test_license_fields_optional_all_null():
    f = LicenseFields()
    assert f.plate_number is None
    assert f.owner_name is None
    assert f.year is None


def test_license_fields_populated():
    f = LicenseFields(plate_number="12-345-67", owner_name="Moshe", vendor="Toyota",
                      model="Corolla", year=2020, valid_to="2025-06-30")
    assert f.year == 2020


def test_ticket_fields_optional_all_null():
    f = TicketFields()
    assert f.amount is None
    assert f.authority is None


def test_ticket_fields_ignores_extra_fields():
    # Pydantic models allow extra fields by default - unknown keys are silently dropped
    f = TicketFields.model_validate({"plate_number": "x", "nonexistent_field": "bad"})
    assert f.plate_number == "x"
    assert not hasattr(f, "nonexistent_field")


def test_extraction_result_structure():
    r = ExtractionResult(
        doc_type=DocType.insurance_cert,
        fields={"plate_number": "12-345-67"},
        confidence=0.95,
    )
    assert r.doc_type == DocType.insurance_cert
    assert r.confidence == 0.95
    assert r.raw is None
