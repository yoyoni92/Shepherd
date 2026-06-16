from datetime import date

from shepherd_contracts import (
    DocType,
    ExtractionResult,
    InsuranceFields,
    LicenseFields,
    TicketFields,
)


def test_doctype_members():
    assert {d.value for d in DocType} == {
        "insurance_cert",
        "annual_license",
        "traffic_ticket",
        "vehicle_photo",
        "other",
    }


def test_partial_fields_allowed():
    f = InsuranceFields(plate_number="12-345-67", valid_to=date(2026, 9, 1))
    assert f.insurer is None
    assert f.plate_number == "12-345-67"


def test_license_and_ticket_fields():
    lic = LicenseFields(plate_number="88-221-30", year=2020)
    tic = TicketFields(plate_number="45-902-11", amount=250.0, ticket_type="parking")
    assert lic.year == 2020
    assert tic.amount == 250.0


def test_extraction_result():
    r = ExtractionResult(
        doc_type=DocType.insurance_cert,
        fields={"plate_number": "12-345-67"},
        confidence=0.97,
    )
    assert r.doc_type is DocType.insurance_cert
    assert 0 <= r.confidence <= 1
