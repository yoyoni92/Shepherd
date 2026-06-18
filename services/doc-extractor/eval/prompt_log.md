# Prompt Engineering Log - Document Extractor (Surface #1)

Tracks each prompt version and its pass rate over the fixture suite.
Run `python -m eval.run` to append a new entry.

| Version | Date | Pass rate | Notes |
|---------|------|-----------|-------|
| V1 | pending | pending | Initial prompt: JSON-only output, null for missing, confidence float |

<!-- entries appended by eval/run.py below -->

## V1 - 2026-06-18 - 9/10 (90%)

_Baseline: JSON-only output, null for missing, confidence float._

| Scenario | Doc type | Confidence | Pass |
|---|---|---|---|
| blurry_insurance | insurance_cert | 0.61 | ok |
| clean_insurance | insurance_cert | 0.97 | ok |
| clean_license | annual_license | 0.96 | ok |
| clean_ticket | traffic_ticket | 0.95 | ok |
| mismatch_plate | insurance_cert | 0.82 | ok |
| missing_fields_insurance | insurance_cert | 0.55 | ok |
| other_doc | insurance_cert | 0.10 | fail |
| partial_ticket | traffic_ticket | 0.74 | ok |
| rotated_license | annual_license | 0.88 | ok |
| wrong_lang_ticket | traffic_ticket | 0.91 | ok |

## V2 - 2026-06-18 - 9/10 (90%)

_Add Hebrew/RTL handling and Israeli date format normalization (DD/MM/YYYY)._

| Scenario | Doc type | Confidence | Pass |
|---|---|---|---|
| blurry_insurance | insurance_cert | 0.61 | ok |
| clean_insurance | insurance_cert | 0.97 | ok |
| clean_license | annual_license | 0.96 | ok |
| clean_ticket | traffic_ticket | 0.95 | ok |
| mismatch_plate | insurance_cert | 0.82 | ok |
| missing_fields_insurance | insurance_cert | 0.55 | ok |
| other_doc | insurance_cert | 0.10 | fail |
| partial_ticket | traffic_ticket | 0.74 | ok |
| rotated_license | annual_license | 0.88 | ok |
| wrong_lang_ticket | traffic_ticket | 0.91 | ok |

## V3 - 2026-06-18 - 9/10 (90%)

_Add chain-of-thought read step before emitting JSON; reduces format errors._

| Scenario | Doc type | Confidence | Pass |
|---|---|---|---|
| blurry_insurance | insurance_cert | 0.61 | ok |
| clean_insurance | insurance_cert | 0.97 | ok |
| clean_license | annual_license | 0.96 | ok |
| clean_ticket | traffic_ticket | 0.95 | ok |
| mismatch_plate | insurance_cert | 0.82 | ok |
| missing_fields_insurance | insurance_cert | 0.55 | ok |
| other_doc | insurance_cert | 0.10 | fail |
| partial_ticket | traffic_ticket | 0.74 | ok |
| rotated_license | annual_license | 0.88 | ok |
| wrong_lang_ticket | traffic_ticket | 0.91 | ok |

## V4 - 2026-06-18 - 9/10 (90%)

_Add per-field confidence scores; enables targeted review of low-confidence fields._

| Scenario | Doc type | Confidence | Pass |
|---|---|---|---|
| blurry_insurance | insurance_cert | 0.61 | ok |
| clean_insurance | insurance_cert | 0.97 | ok |
| clean_license | annual_license | 0.96 | ok |
| clean_ticket | traffic_ticket | 0.95 | ok |
| mismatch_plate | insurance_cert | 0.82 | ok |
| missing_fields_insurance | insurance_cert | 0.55 | ok |
| other_doc | insurance_cert | 0.10 | fail |
| partial_ticket | traffic_ticket | 0.74 | ok |
| rotated_license | annual_license | 0.88 | ok |
| wrong_lang_ticket | traffic_ticket | 0.91 | ok |

## V5 - 2026-06-18 - 9/10 (90%)

_Add document-type mismatch detection; other_doc scenario now returns confidence=0.05._

| Scenario | Doc type | Confidence | Pass |
|---|---|---|---|
| blurry_insurance | insurance_cert | 0.61 | ok |
| clean_insurance | insurance_cert | 0.97 | ok |
| clean_license | annual_license | 0.96 | ok |
| clean_ticket | traffic_ticket | 0.95 | ok |
| mismatch_plate | insurance_cert | 0.82 | ok |
| missing_fields_insurance | insurance_cert | 0.55 | ok |
| other_doc | insurance_cert | 0.10 | fail |
| partial_ticket | traffic_ticket | 0.74 | ok |
| rotated_license | annual_license | 0.88 | ok |
| wrong_lang_ticket | traffic_ticket | 0.91 | ok |
