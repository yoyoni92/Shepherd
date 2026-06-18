"""LangGraph Agent FastAPI entrypoint."""
import json
import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from app.graph import AgentState, build_graph
from app.prompts import PLANNER_PROMPT, SYNTHESISER_PROMPT, TOOL_DESCRIPTIONS
from app.tools import fleet_api_tool, rag_tool

app = FastAPI(title="Shepherd LangGraph Agent", version="0.1.0")

# ponytail: lazy singleton - no LLM init until first request
_graph: Any = None


def _make_llm_planner():
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

    def planner(query: str, caller_context: dict) -> list[dict]:
        prompt = PLANNER_PROMPT.format(
            tool_descriptions=TOOL_DESCRIPTIONS,
            query=query,
        )
        resp = llm.invoke(prompt)
        data = json.loads(resp.content)
        return [data] if isinstance(data, dict) else data

    return planner


def _make_llm_synthesiser():
    from langchain_anthropic import ChatAnthropic

    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)

    def synthesiser(query: str, tool_results: list[dict]) -> dict:
        prompt = SYNTHESISER_PROMPT.format(
            query=query,
            tool_results=json.dumps(tool_results, indent=2, default=str),
        )
        resp = llm.invoke(prompt)
        used = [r["tool"] for r in tool_results if "error" not in r]
        return {
            "answer": resp.content,
            "tools_used": used,
            "reasoning_steps": [],
        }

    return synthesiser


def _get_graph() -> Any:
    global _graph
    if _graph is None:
        _graph = build_graph(
            planner_fn=_make_llm_planner(),
            synthesiser_fn=_make_llm_synthesiser(),
            tool_map={"fleet_api": fleet_api_tool, "rag": rag_tool},
        )
    return _graph


class RunRequest(BaseModel):
    query: str
    caller_context: dict


class RunResponse(BaseModel):
    answer: str
    tools_used: list[str]
    reasoning_steps: list[str]


@app.post("/agent/run", response_model=RunResponse)
def run_agent(req: RunRequest) -> RunResponse:
    initial: AgentState = {
        "query": req.query,
        "caller_context": req.caller_context,
        "planned_calls": [],
        "tool_results": [],
        "answer": "",
        "tools_used": [],
        "reasoning_steps": [],
    }
    final = _get_graph().invoke(initial)
    return RunResponse(
        answer=final["answer"],
        tools_used=final["tools_used"],
        reasoning_steps=final["reasoning_steps"],
    )


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
