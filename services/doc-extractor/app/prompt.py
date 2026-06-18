"""Extraction prompt templates. This is prompt-engineering surface #1."""
from __future__ import annotations

from shepherd_contracts import DocType

PROMPT_VERSION = "V5"  # current active version

FIELD_KEYS: dict[DocType, list[str]] = {
    DocType.insurance_cert: ["insurer", "policy_number", "plate_number", "coverage_type", "valid_from", "valid_to"],
    DocType.annual_license: ["plate_number", "owner_name", "vendor", "model", "year", "valid_to"],
    DocType.traffic_ticket: ["plate_number", "ticket_type", "violation_desc", "amount", "issued_ts", "due_date", "authority"],
}

_FIELD_DESCRIPTIONS: dict[DocType, str] = {
    DocType.insurance_cert: (
        "- insurer: insurance company name\n"
        "- policy_number: policy/certificate number\n"
        "- plate_number: vehicle license plate\n"
        "- coverage_type: type of coverage (e.g. comprehensive, third-party)\n"
        "- valid_from: coverage start date (ISO YYYY-MM-DD)\n"
        "- valid_to: coverage expiry date (ISO YYYY-MM-DD)"
    ),
    DocType.annual_license: (
        "- plate_number: vehicle license plate\n"
        "- owner_name: registered owner full name\n"
        "- vendor: vehicle manufacturer/brand\n"
        "- model: vehicle model name\n"
        "- year: vehicle manufacturing year (integer)\n"
        "- valid_to: license expiry date (ISO YYYY-MM-DD)"
    ),
    DocType.traffic_ticket: (
        "- plate_number: vehicle license plate\n"
        "- ticket_type: type of violation (e.g. speeding, parking)\n"
        "- violation_desc: description of the violation\n"
        "- amount: fine amount as a number (no currency symbols; convert ILS/NIS to number)\n"
        "- issued_ts: date and time of violation (ISO YYYY-MM-DDTHH:MM:SS)\n"
        "- due_date: payment due date (ISO YYYY-MM-DD)\n"
        "- authority: issuing authority name"
    ),
}

# V1: baseline - JSON-only output, null for missing, confidence float
_V1 = """\
You are a document extraction assistant for a vehicle fleet management system.

Extract the following fields from the document. The document is of type: {doc_type}.

Fields to extract:
{field_descriptions}

Rules:
- Return ONLY valid JSON, no prose, no markdown fences
- Use null for any field that is unreadable, absent, or unclear
- Dates: ISO format YYYY-MM-DD; datetimes: YYYY-MM-DDTHH:MM:SS
- Amount: numeric value only, no currency symbols
- Plate numbers: uppercase, strip spaces
- "confidence": float 0.0-1.0 representing your overall confidence in the extraction

JSON format:
{{
  "fields": {{field_template}},
  "confidence": 0.95,
  "raw": "optional: verbatim text you read from the document"
}}
"""

# V2: adds Hebrew/RTL handling and Israeli date format normalization
_V2 = """\
You are a document extraction assistant for an Israeli vehicle fleet management system.

Extract the following fields from the document. The document is of type: {doc_type}.
The document may be in Hebrew (RTL) or English. Keep value text in its original language.

Fields to extract:
{field_descriptions}

Rules:
- Return ONLY valid JSON, no prose, no markdown fences
- Use null for any field that is unreadable, absent, or unclear
- Dates: convert any format (DD/MM/YYYY, MM/YYYY, Hebrew) to ISO YYYY-MM-DD
- Datetimes: ISO YYYY-MM-DDTHH:MM:SS
- Amount: numeric only; strip currency symbols (ILS, NIS)
- Plate numbers: uppercase, strip spaces
- "confidence": float 0.0-1.0

JSON format:
{{
  "fields": {{field_template}},
  "confidence": 0.95,
  "raw": "optional: verbatim text you read from the document"
}}
"""

# V3: adds chain-of-thought step before emitting JSON
_V3 = """\
You are a document extraction assistant for an Israeli vehicle fleet management system.

The document is of type: {doc_type}. It may be in Hebrew or English.

Step 1 - Read the document and identify each visible field.
Step 2 - Normalize values (dates to ISO, amounts to numbers, plates to uppercase).
Step 3 - Emit ONLY the JSON below. No other text before or after.

Fields to extract:
{field_descriptions}

Normalization rules:
- Dates: any format -> ISO YYYY-MM-DD; datetimes -> YYYY-MM-DDTHH:MM:SS
- Amounts: strip currency symbols, return float
- Plates: uppercase
- null for unreadable/absent fields
- "confidence": 0.0-1.0

JSON format:
{{
  "fields": {{field_template}},
  "confidence": 0.95,
  "raw": "verbatim text extracted from document"
}}
"""

# V4: adds per-field confidence scores (better signal for partial extractions)
_V4 = """\
You are a document extraction assistant for an Israeli vehicle fleet management system.

The document is of type: {doc_type}. It may be in Hebrew or English.

Extract these fields:
{field_descriptions}

Normalization rules:
- Dates: any format -> ISO YYYY-MM-DD; datetimes -> YYYY-MM-DDTHH:MM:SS
- Amounts: strip currency symbols, return numeric only
- Plates: uppercase
- null for unreadable/absent fields

Return ONLY valid JSON (no prose, no markdown fences):
{{
  "fields": {{field_template}},
  "field_confidence": {{field_confidence_template}},
  "confidence": 0.95,
  "raw": "verbatim text extracted"
}}

field_confidence mirrors the fields keys with per-field 0.0-1.0 scores.
Overall "confidence" = average of non-null field confidence values.
"""

# V5: adds document-type mismatch detection to handle wrong-doc uploads
_V5 = """\
You are a document extraction assistant for an Israeli vehicle fleet management system.

Expected document type: {doc_type}. The document may be in Hebrew or English.

First verify the document matches the expected type. If it clearly does NOT match
(e.g. expected insurance_cert but the document is an invoice or receipt),
set confidence to 0.05, all fields to null, and raw to "document_type_mismatch".

Fields to extract:
{field_descriptions}

Normalization rules:
- Dates: any format -> ISO YYYY-MM-DD; datetimes -> YYYY-MM-DDTHH:MM:SS
- Amounts: strip currency symbols, return numeric only
- Plates: uppercase
- null for unreadable/absent fields; never guess

Return ONLY valid JSON (no prose, no markdown fences):
{{
  "fields": {{field_template}},
  "confidence": 0.95,
  "raw": "verbatim text extracted"
}}
"""

_VERSIONS: dict[str, str] = {
    "V1": _V1,
    "V2": _V2,
    "V3": _V3,
    "V4": _V4,
    "V5": _V5,
}


def build_prompt(doc_type: DocType, version: str = PROMPT_VERSION) -> str:
    template = _VERSIONS[version]
    field_descriptions = _FIELD_DESCRIPTIONS.get(doc_type, "- Extract all visible fields")
    field_keys = FIELD_KEYS.get(doc_type, [])
    field_template = ", ".join(f'"{k}": null' for k in field_keys)
    field_confidence_template = ", ".join(f'"{k}": 1.0' for k in field_keys)
    return template.format(
        doc_type=doc_type.value,
        field_descriptions=field_descriptions,
        field_template="{" + field_template + "}",
        field_confidence_template="{" + field_confidence_template + "}",
    )
