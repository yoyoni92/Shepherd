"""Benchmark tool-description versions V1..V5 against BENCHMARK queries.

Usage:
  poetry run python -m eval.run            # scripted (deterministic)
  poetry run python -m eval.run --live     # real LLM (requires ANTHROPIC_API_KEY)
"""
import json
import sys
from datetime import date

from app.prompts import (
    TOOL_DESCRIPTIONS_V1,
    TOOL_DESCRIPTIONS_V2,
    TOOL_DESCRIPTIONS_V3,
    TOOL_DESCRIPTIONS_V4,
    TOOL_DESCRIPTIONS_V5,
    PLANNER_PROMPT,
)

VERSIONS = {
    "V1": TOOL_DESCRIPTIONS_V1,
    "V2": TOOL_DESCRIPTIONS_V2,
    "V3": TOOL_DESCRIPTIONS_V3,
    "V4": TOOL_DESCRIPTIONS_V4,
    "V5": TOOL_DESCRIPTIONS_V5,
}

BENCHMARK = [
    ("status of plate ABC-123", "rag_tool"),
    ("tell me about vehicle 456-78-901", "rag_tool"),
    ("insurance status of plate 111-11-111", "rag_tool"),
    ("accident history for plate XYZ", "rag_tool"),
    ("maintenance history of vehicle 222-22-222", "rag_tool"),
    ("which vehicles are due for maintenance next month", "fleet_api_tool"),
    ("list all vehicles with unpaid tickets", "fleet_api_tool"),
    ("vehicles whose insurance expires this week", "fleet_api_tool"),
    ("how many km has each vehicle done this year", "fleet_api_tool"),
    ("list all drivers in the fleet", "fleet_api_tool"),
    ("vehicles with accidents in the last 6 months", "fleet_api_tool"),
    ("מה הסטטוס של רכב 111-11-111", "rag_tool"),
]


def _scripted_call(query: str, tool_descriptions: str) -> str:
    """Deterministic mock: checks for plate/single-vehicle keywords."""
    single_vehicle_kw = ["plate", "vehicle 4", "vehicle 2", "vehicle 1", "רכב", "profile of", "history for"]
    for kw in single_vehicle_kw:
        if kw.lower() in query.lower():
            return "rag_tool"
    return "fleet_api_tool"


def _live_call(query: str, tool_descriptions: str) -> str:
    from langchain_anthropic import ChatAnthropic
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    prompt = PLANNER_PROMPT.format(tool_descriptions=tool_descriptions, query=query)
    resp = llm.invoke(prompt)
    try:
        data = json.loads(resp.content)
        return data.get("tool", "unknown")
    except Exception:
        return "parse_error"


def run(live: bool = False) -> None:
    call_fn = _live_call if live else _scripted_call
    today = date.today().isoformat()
    mode = "live LLM" if live else "scripted mock"
    print(f"\nBenchmark mode: {mode}  date: {today}\n")

    for version, desc in VERSIONS.items():
        correct = 0
        rows = []
        for query, expected in BENCHMARK:
            got = call_fn(query, desc)
            passed = got == expected
            correct += int(passed)
            rows.append((query[:40], expected, "ok" if passed else f"got {got}"))

        rate = correct / len(BENCHMARK)
        print(f"{version}: {correct}/{len(BENCHMARK)} ({rate:.0%})")
        for q, exp, status in rows:
            mark = "  " if status == "ok" else "! "
            print(f"  {mark}{q:<42} {exp:<15} {status}")
        print()


if __name__ == "__main__":
    run(live="--live" in sys.argv)
