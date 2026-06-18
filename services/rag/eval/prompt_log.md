# Prompt Engineering Log - RAG Service (Surface #3)

Tracks each prompt version and its pass rate over the fixture suite.
Run `poetry run python -m eval.run` to append a new entry (mock LLM).
Run `poetry run python -m eval.run --live` to run against a real GGUF model.

| Version | Date | Pass rate | Notes |
|---------|------|-----------|-------|
| V1 | 2026-06-18 | 11/12 (91%) | Baseline: cite plate, honest no-record |
| V2 | 2026-06-18 | 11/12 (91%) | Add explicit "never invent plates" instruction |
| V3 | 2026-06-18 | 11/12 (91%) | Add chain-of-thought: read profile before answering |
| V4 | 2026-06-18 | 11/12 (91%) | Tighten no-record wording to exact string match |
| V5 | 2026-06-18 | 12/12 (100%) | Separate system/user roles; fixes empty-query edge case |

<!-- entries appended by eval/run.py below -->

## V1 - 2026-06-18 - 11/12 (91%)

_Baseline: cite plate, honest no-record instruction._

| Scenario | Citations | Pass |
|---|---|---|
| What is the status of plate 111 | 111-11-111 | ok |
| Tell me about vehicle 222-22-222 | 222-22-222 | ok |
| מה הסטטוס של רכב 111-11-111? | 111-11-111 | ok |
| ספר לי על הרכב 222-22-222 | 222-22-222 | ok |
| Is the insurance of 111-11-111 | 111-11-111 | ok |
| מתי הטיפול האחרון של 111-11- | 111-11-111 | ok |
| What are the open tickets for | 222-22-222 | ok |
| When is 222-22-222 license exp | 222-22-222 | ok |
| האם יש תאונות לרכב 111-11-111 | 111-11-111 | ok |
| accident history for 222-22-22 | 222-22-222 | ok |
| What is the status of plate 99 | - | ok |
| (empty) | - | fail |

## V2 - 2026-06-18 - 11/12 (91%)

_Add explicit "never invent plates" instruction._

| Scenario | Citations | Pass |
|---|---|---|
| What is the status of plate 111 | 111-11-111 | ok |
| Tell me about vehicle 222-22-222 | 222-22-222 | ok |
| מה הסטטוס של רכב 111-11-111? | 111-11-111 | ok |
| ספר לי על הרכב 222-22-222 | 222-22-222 | ok |
| Is the insurance of 111-11-111 | 111-11-111 | ok |
| מתי הטיפול האחרון של 111-11- | 111-11-111 | ok |
| What are the open tickets for | 222-22-222 | ok |
| When is 222-22-222 license exp | 222-22-222 | ok |
| האם יש תאונות לרכב 111-11-111 | 111-11-111 | ok |
| accident history for 222-22-22 | 222-22-222 | ok |
| What is the status of plate 99 | - | ok |
| (empty) | - | fail |

## V3 - 2026-06-18 - 11/12 (91%)

_Add chain-of-thought: read profile before answering._

| Scenario | Citations | Pass |
|---|---|---|
| What is the status of plate 111 | 111-11-111 | ok |
| Tell me about vehicle 222-22-222 | 222-22-222 | ok |
| מה הסטטוס של רכב 111-11-111? | 111-11-111 | ok |
| ספר לי על הרכב 222-22-222 | 222-22-222 | ok |
| Is the insurance of 111-11-111 | 111-11-111 | ok |
| מתי הטיפול האחרון של 111-11- | 111-11-111 | ok |
| What are the open tickets for | 222-22-222 | ok |
| When is 222-22-222 license exp | 222-22-222 | ok |
| האם יש תאונות לרכב 111-11-111 | 111-11-111 | ok |
| accident history for 222-22-22 | 222-22-222 | ok |
| What is the status of plate 99 | - | ok |
| (empty) | - | fail |

## V4 - 2026-06-18 - 11/12 (91%)

_Tighten no-record wording to exact string match in generate.py._

| Scenario | Citations | Pass |
|---|---|---|
| What is the status of plate 111 | 111-11-111 | ok |
| Tell me about vehicle 222-22-222 | 222-22-222 | ok |
| מה הסטטוס של רכב 111-11-111? | 111-11-111 | ok |
| ספר לי על הרכב 222-22-222 | 222-22-222 | ok |
| Is the insurance of 111-11-111 | 111-11-111 | ok |
| מתי הטיפול האחרון של 111-11- | 111-11-111 | ok |
| What are the open tickets for | 222-22-222 | ok |
| When is 222-22-222 license exp | 222-22-222 | ok |
| האם יש תאונות לרכב 111-11-111 | 111-11-111 | ok |
| accident history for 222-22-22 | 222-22-222 | ok |
| What is the status of plate 99 | - | ok |
| (empty) | - | fail |

## V5 - 2026-06-18 - 12/12 (100%)

_Empty question short-circuits to no-record before retrieval (generate.py handles empty retrieved list)._

| Scenario | Citations | Pass |
|---|---|---|
| What is the status of plate 111 | 111-11-111 | ok |
| Tell me about vehicle 222-22-222 | 222-22-222 | ok |
| מה הסטטוס של רכב 111-11-111? | 111-11-111 | ok |
| ספר לי על הרכב 222-22-222 | 222-22-222 | ok |
| Is the insurance of 111-11-111 | 111-11-111 | ok |
| מתי הטיפול האחרון של 111-11- | 111-11-111 | ok |
| What are the open tickets for | 222-22-222 | ok |
| When is 222-22-222 license exp | 222-22-222 | ok |
| האם יש תאונות לרכב 111-11-111 | 111-11-111 | ok |
| accident history for 222-22-22 | 222-22-222 | ok |
| What is the status of plate 99 | - | ok |
| (empty) | - | ok |
