"""T5 - Tool descriptions = surface #2; benchmark >= 10 queries."""
import httpx
import respx

from app.graph import build_graph
from app.prompts import TOOL_DESCRIPTIONS, TOOL_DESCRIPTIONS_V1, TOOL_DESCRIPTIONS_V5
from app.tools import fleet_api_tool, rag_tool

from tests.conftest import initial_state, make_scripted_planner, make_scripted_synthesiser

# Benchmark: (query, expected_tool)
BENCHMARK = [
    ("what is the status of plate ABC-123", "rag"),
    ("tell me about vehicle 456-78-901", "rag"),
    ("insurance status of plate 111-11-111", "rag"),
    ("accident history for plate XYZ", "rag"),
    ("what maintenance has vehicle 222-22-222 had", "rag"),
    ("which vehicles are due for maintenance next month", "fleet_api"),
    ("list all vehicles with unpaid tickets", "fleet_api"),
    ("show me vehicles whose insurance expires this week", "fleet_api"),
    ("how many km has each vehicle done this year", "fleet_api"),
    ("list all drivers in the fleet", "fleet_api"),
    ("which vehicles have had accidents in the last 6 months", "fleet_api"),
    ("מה הסטטוס של רכב 111-11-111", "rag"),
]


def test_benchmark_has_at_least_10_queries():
    assert len(BENCHMARK) >= 10


def test_benchmark_labels_are_valid_tools():
    valid = {"rag", "fleet_api"}
    for query, tool in BENCHMARK:
        assert tool in valid, f"unknown tool {tool!r} for {query!r}"


@respx.mock
def test_scripted_planner_achieves_100_percent_on_benchmark():
    """Graph plumbing: scripted planner routes every benchmark query correctly."""
    scripts = {q: [{"tool": t, "question": q} if t == "rag"
                   else {"tool": t, "path": "/vehicles", "method": "GET"}]
               for q, t in BENCHMARK}
    planner = make_scripted_planner(scripts)
    respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": "ok", "citations": []})
    )
    respx.get("http://fleet-api:8000/vehicles").mock(
        return_value=httpx.Response(200, json=[])
    )
    graph = build_graph(planner, make_scripted_synthesiser(), {"fleet_api": fleet_api_tool, "rag": rag_tool})

    correct = 0
    for query, expected in BENCHMARK:
        state = graph.invoke(initial_state(query))
        if expected in state["tools_used"]:
            correct += 1

    rate = correct / len(BENCHMARK)
    assert rate >= 0.9, f"tool-selection rate {rate:.0%} < 90%"


def test_all_versions_are_defined():
    for v in (TOOL_DESCRIPTIONS_V1, TOOL_DESCRIPTIONS_V5):
        assert "rag_tool" in v
        assert "fleet_api_tool" in v


def test_active_version_is_v5():
    assert TOOL_DESCRIPTIONS is TOOL_DESCRIPTIONS_V5
