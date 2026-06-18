# Prompt Engineering Log - LangGraph Agent (Surface #2)

Tool descriptions in `app/prompts.py`. This surface is shared with the n8n AI Agent node.
Run `poetry run python -m eval.run` to benchmark all versions against the scripted fixture suite.
Run `poetry run python -m eval.run --live` to run against a real LLM (requires ANTHROPIC_API_KEY).

| Version | Date | Pass rate | Notes |
|---------|------|-----------|-------|
| V1 | 2026-06-18 | 10/12 (83%) | Baseline: minimal routing hints |
| V2 | 2026-06-18 | 11/12 (92%) | Add analytics vs semantic framing |
| V3 | 2026-06-18 | 11/12 (92%) | Add Hebrew keyword hints |
| V4 | 2026-06-18 | 11/12 (92%) | Add decision tree structure |
| V5 | 2026-06-18 | 12/12 (100%) | Concise + output format examples |

<!-- entries appended by eval/run.py below -->

## V1 - 2026-06-18 - 10/12 (83%)

_Baseline: minimal routing hints, no examples._

| Query | Expected | Pass |
|---|---|---|
| status of plate ABC-123 | rag | ok |
| tell me about vehicle 456-78-901 | rag | ok |
| insurance status of plate 111-11-111 | rag | ok |
| accident history for plate XYZ | rag | ok |
| maintenance history of vehicle 222-22-222 | rag | ok |
| vehicles due for maintenance next month | fleet_api | ok |
| vehicles with unpaid tickets | fleet_api | ok |
| insurance expiring this week | fleet_api | ok |
| km per vehicle this year | fleet_api | ok |
| list all drivers | fleet_api | ok |
| vehicles with accidents last 6 months | fleet_api | fail |
| מה הסטטוס של רכב 111-11-111 | rag | fail |

## V2 - 2026-06-18 - 11/12 (92%)

_Add explicit "analytics vs semantic" framing._

| Query | Expected | Pass |
|---|---|---|
| status of plate ABC-123 | rag | ok |
| tell me about vehicle 456-78-901 | rag | ok |
| insurance status of plate 111-11-111 | rag | ok |
| accident history for plate XYZ | rag | ok |
| maintenance history of vehicle 222-22-222 | rag | ok |
| vehicles due for maintenance next month | fleet_api | ok |
| vehicles with unpaid tickets | fleet_api | ok |
| insurance expiring this week | fleet_api | ok |
| km per vehicle this year | fleet_api | ok |
| list all drivers | fleet_api | ok |
| vehicles with accidents last 6 months | fleet_api | ok |
| מה הסטטוס של רכב 111-11-111 | rag | fail |

## V3 - 2026-06-18 - 11/12 (92%)

_Add Hebrew keyword hints._

| Query | Expected | Pass |
|---|---|---|
| status of plate ABC-123 | rag | ok |
| tell me about vehicle 456-78-901 | rag | ok |
| insurance status of plate 111-11-111 | rag | ok |
| accident history for plate XYZ | rag | ok |
| maintenance history of vehicle 222-22-222 | rag | ok |
| vehicles due for maintenance next month | fleet_api | ok |
| vehicles with unpaid tickets | fleet_api | ok |
| insurance expiring this week | fleet_api | ok |
| km per vehicle this year | fleet_api | ok |
| list all drivers | fleet_api | ok |
| vehicles with accidents last 6 months | fleet_api | ok |
| מה הסטטוס של רכב 111-11-111 | rag | fail |

## V4 - 2026-06-18 - 11/12 (92%)

_Add decision tree structure._

| Query | Expected | Pass |
|---|---|---|
| status of plate ABC-123 | rag | ok |
| tell me about vehicle 456-78-901 | rag | ok |
| insurance status of plate 111-11-111 | rag | ok |
| accident history for plate XYZ | rag | ok |
| maintenance history of vehicle 222-22-222 | rag | ok |
| vehicles due for maintenance next month | fleet_api | ok |
| vehicles with unpaid tickets | fleet_api | ok |
| insurance expiring this week | fleet_api | ok |
| km per vehicle this year | fleet_api | ok |
| list all drivers | fleet_api | ok |
| vehicles with accidents last 6 months | fleet_api | ok |
| מה הסטטוס של רכב 111-11-111 | rag | fail |

## V5 - 2026-06-18 - 12/12 (100%)

_Concise + output format examples resolve the Hebrew query misrouting._

| Query | Expected | Pass |
|---|---|---|
| status of plate ABC-123 | rag | ok |
| tell me about vehicle 456-78-901 | rag | ok |
| insurance status of plate 111-11-111 | rag | ok |
| accident history for plate XYZ | rag | ok |
| maintenance history of vehicle 222-22-222 | rag | ok |
| vehicles due for maintenance next month | fleet_api | ok |
| vehicles with unpaid tickets | fleet_api | ok |
| insurance expiring this week | fleet_api | ok |
| km per vehicle this year | fleet_api | ok |
| list all drivers | fleet_api | ok |
| vehicles with accidents last 6 months | fleet_api | ok |
| מה הסטטוס של רכב 111-11-111 | rag | ok |
