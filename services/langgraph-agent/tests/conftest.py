"""Shared fixtures: scripted planner/synthesiser, initial state helper."""
import pytest

ADMIN_CTX = {"role": "admin"}
DRIVER_CTX = {"role": "driver", "driver_id": "driver-123"}


def make_scripted_planner(scripts: dict[str, list[dict]]):
    """scripts maps a query substring to the planned calls to return."""
    def planner(query: str, caller_context: dict) -> list[dict]:
        for kw, calls in scripts.items():
            if kw.lower() in query.lower():
                return calls
        return [{"tool": "clarify", "message": "ambiguous query"}]
    return planner


def make_scripted_synthesiser(answer: str = "test answer"):
    def synthesiser(query: str, tool_results: list[dict]) -> dict:
        return {
            "answer": answer,
            "tools_used": [r["tool"] for r in tool_results if "error" not in r],
            "reasoning_steps": ["synthesised from tool results"],
        }
    return synthesiser


def initial_state(query: str, caller_context: dict | None = None) -> dict:
    return {
        "query": query,
        "caller_context": caller_context or ADMIN_CTX,
        "planned_calls": [],
        "tool_results": [],
        "answer": "",
        "tools_used": [],
        "reasoning_steps": [],
        "citations": [],
    }
