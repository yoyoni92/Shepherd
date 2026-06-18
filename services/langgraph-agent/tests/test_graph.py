"""T2/T3/T4 - Planner routing, tool-exec state, synthesiser output shape."""
import httpx
import pytest
import respx

from app.graph import build_graph
from app.tools import fleet_api_tool, rag_tool

from tests.conftest import (
    ADMIN_CTX,
    DRIVER_CTX,
    initial_state,
    make_scripted_planner,
    make_scripted_synthesiser,
)

TOOL_MAP = {"fleet_api": fleet_api_tool, "rag": rag_tool}


# --- T2: planner selects right tool ---

@respx.mock
def test_plate_query_routes_to_rag():
    planner = make_scripted_planner({
        "status of plate": [{"tool": "rag", "question": "status of plate X"}],
    })
    respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": "ok", "citations": []})
    )
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("status of plate X"))
    assert "rag" in state["tools_used"]


@respx.mock
def test_fleet_analytics_routes_to_fleet_api():
    planner = make_scripted_planner({
        "vehicles due next month": [
            {"tool": "fleet_api", "path": "/vehicles", "method": "GET"}
        ],
    })
    respx.get("http://fleet-api:8000/vehicles").mock(
        return_value=httpx.Response(200, json=[])
    )
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("which vehicles due next month AND unpaid ticket"))
    assert "fleet_api" in state["tools_used"]


def test_ambiguous_query_routes_to_clarify():
    planner = make_scripted_planner({})  # no match -> clarify
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("something completely ambiguous xyz"))
    assert state["answer"] == "ambiguous query"
    assert state["tools_used"] == []


def test_clarify_skips_tool_exec():
    planner = make_scripted_planner({"ambiguous": [{"tool": "clarify", "message": "which vehicle?"}]})
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("ambiguous"))
    assert state["answer"] == "which vehicle?"
    assert state["tool_results"] == []


# --- T3: tool-exec node + state ---

@respx.mock
def test_multi_tool_sequence_preserves_order():
    planner = make_scripted_planner({
        "two tools": [
            {"tool": "rag", "question": "profile of X"},
            {"tool": "fleet_api", "path": "/reports", "method": "GET"},
        ],
    })
    respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": "profile", "citations": []})
    )
    respx.get("http://fleet-api:8000/reports").mock(
        return_value=httpx.Response(200, json=[])
    )
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("two tools query"))
    assert state["tool_results"][0]["tool"] == "rag"
    assert state["tool_results"][1]["tool"] == "fleet_api"


@respx.mock
def test_one_tool_failure_does_not_crash_run():
    planner = make_scripted_planner({
        "partial": [
            {"tool": "rag", "question": "fail query"},
            {"tool": "fleet_api", "path": "/vehicles", "method": "GET"},
        ],
    })
    respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(503)  # rag fails
    )
    respx.get("http://fleet-api:8000/vehicles").mock(
        return_value=httpx.Response(200, json=[])
    )
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("partial failure query"))
    rag_result = next(r for r in state["tool_results"] if r["tool"] == "rag")
    assert "error" in rag_result
    fleet_result = next(r for r in state["tool_results"] if r["tool"] == "fleet_api")
    assert "result" in fleet_result
    assert state["answer"] == "test answer"  # synthesiser still ran


# --- T4: synthesiser output shape ---

@respx.mock
def test_synthesiser_output_shape():
    planner = make_scripted_planner({"query": [{"tool": "rag", "question": "q"}]})
    respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": "some answer", "citations": ["X"]})
    )
    graph = build_graph(planner, make_scripted_synthesiser("grounded answer"), TOOL_MAP)
    state = graph.invoke(initial_state("some query"))
    assert isinstance(state["answer"], str) and state["answer"]
    assert isinstance(state["tools_used"], list)
    assert isinstance(state["reasoning_steps"], list)


def test_unknown_tool_in_plan_adds_error_result():
    planner = make_scripted_planner({
        "ghost": [{"tool": "ghost_tool", "arg": "x"}],
    })
    graph = build_graph(planner, make_scripted_synthesiser(), TOOL_MAP)
    state = graph.invoke(initial_state("ghost query"))
    assert any(r.get("error") == "unknown tool" for r in state["tool_results"])


@respx.mock
def test_synthesiser_only_references_tool_outputs():
    """Verify synthesiser receives tool results (no invented data path)."""
    rag_answer = "Vehicle 999-99-999 insurance expires 2027-01-01"
    received: list[list[dict]] = []

    def capturing_synthesiser(query: str, tool_results: list[dict]) -> dict:
        received.append(tool_results)
        return {"answer": "ok", "tools_used": [], "reasoning_steps": []}

    planner = make_scripted_planner({"vehicle": [{"tool": "rag", "question": "vehicle status"}]})
    respx.post("http://rag:8000/query").mock(
        return_value=httpx.Response(200, json={"answer": rag_answer, "citations": []})
    )
    graph = build_graph(planner, capturing_synthesiser, TOOL_MAP)
    graph.invoke(initial_state("vehicle query"))
    assert len(received) == 1
    assert received[0][0]["result"]["answer"] == rag_answer
