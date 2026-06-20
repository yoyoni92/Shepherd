"""LangGraph stateful agent: planner -> tool_exec -> synthesiser."""
from typing import Any, Callable, TypedDict

from langgraph.graph import END, StateGraph


class AgentState(TypedDict):
    query: str
    caller_context: dict
    planned_calls: list[dict]   # set by planner, e.g. [{"tool": "rag", "question": "..."}]
    tool_results: list[dict]    # accumulated by tool_exec in order
    answer: str
    tools_used: list[str]
    reasoning_steps: list[str]
    citations: list[str]        # collected from rag tool results by the synthesiser


def _collect_citations(tool_results: list[dict]) -> list[str]:
    """Pull RAG citations out of the tool results (deduped, order-preserving)."""
    cites: list[str] = []
    for r in tool_results:
        if r.get("tool") != "rag":
            continue
        for c in (r.get("result") or {}).get("citations") or []:
            if c not in cites:
                cites.append(c)
    return cites


def build_graph(
    planner_fn: Callable[[str, dict], list[dict]],
    synthesiser_fn: Callable[[str, list[dict]], dict],
    tool_map: dict[str, Callable],
) -> Any:
    """
    planner_fn(query, caller_context) -> list of planned calls, e.g.:
      [{"tool": "rag", "question": "..."}]
      [{"tool": "fleet_api", "path": "/vehicles", "method": "GET"}]
      [{"tool": "clarify", "message": "..."}]
      [{"tool": "rag", ...}, {"tool": "fleet_api", ...}]   # multi-step

    synthesiser_fn(query, tool_results) -> {"answer", "tools_used", "reasoning_steps"}

    tool_map: {"fleet_api": fleet_api_tool, "rag": rag_tool}
    """

    def planner_node(state: AgentState) -> dict:
        calls = planner_fn(state["query"], state["caller_context"])
        tools = [c["tool"] for c in calls]
        return {
            "planned_calls": calls,
            "reasoning_steps": state["reasoning_steps"] + [f"planned: {tools}"],
        }

    def tool_exec_node(state: AgentState) -> dict:
        results = list(state["tool_results"])
        used = list(state["tools_used"])
        steps = list(state["reasoning_steps"])
        for call in state["planned_calls"]:
            tool_name = call["tool"]
            tool = tool_map.get(tool_name)
            if tool is None:
                results.append({"tool": tool_name, "error": "unknown tool"})
                continue
            try:
                # strip "tool" key; caller_context injected from state
                args = {k: v for k, v in call.items() if k != "tool"}
                args["caller_context"] = state["caller_context"]
                result = tool(**args)
                results.append({"tool": tool_name, "result": result})
                used.append(tool_name)
                steps.append(f"executed: {tool_name}")
            except Exception as exc:
                # ponytail: catch-all so one bad tool doesn't kill the run
                results.append({"tool": tool_name, "error": str(exc)})
                steps.append(f"error: {tool_name} - {exc}")
        return {"tool_results": results, "tools_used": used, "reasoning_steps": steps}

    def synthesiser_node(state: AgentState) -> dict:
        # clarify path: answer is the clarification message, no LLM call needed
        if state["planned_calls"] and state["planned_calls"][0]["tool"] == "clarify":
            msg = state["planned_calls"][0].get("message", "Please clarify your request.")
            return {
                "answer": msg,
                "tools_used": [],
                "reasoning_steps": state["reasoning_steps"] + ["clarify: no tool needed"],
                "citations": [],
            }
        out = synthesiser_fn(state["query"], state["tool_results"])
        return {
            "answer": out["answer"],
            "tools_used": out.get("tools_used", state["tools_used"]),
            "reasoning_steps": state["reasoning_steps"] + out.get("reasoning_steps", []),
            "citations": _collect_citations(state["tool_results"]),
        }

    def _route(state: AgentState) -> str:
        if state["planned_calls"] and state["planned_calls"][0]["tool"] == "clarify":
            return "synthesiser"
        return "tool_exec"

    workflow = StateGraph(AgentState)
    workflow.add_node("planner", planner_node)
    workflow.add_node("tool_exec", tool_exec_node)
    workflow.add_node("synthesiser", synthesiser_node)
    workflow.set_entry_point("planner")
    workflow.add_conditional_edges("planner", _route)
    workflow.add_edge("tool_exec", "synthesiser")
    workflow.add_edge("synthesiser", END)

    return workflow.compile()
