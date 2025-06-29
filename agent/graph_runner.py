from __future__ import annotations

"""LangGraph-powered execution pipeline for the TransferAI LLM Compiler.

Nodes (linear, with retry loop):
    1. planner   – agent.planner.get_plan
    2. executor  – agent.executor.execute
    3. helper    – agent.helper.merge_results
    4. composer  – agent.composer.compose_from_execution
    5. critic    – agent.critic.score → cond. branch to composer when score < TH

The exposed helper ``run_full`` runs the entire graph and returns Markdown.
"""

from pathlib import Path
import os
import json
import argparse
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from agent import planner as planner_mod
from agent import executor as executor_mod
from agent import helper as helper_mod
from agent import composer as composer_mod
from agent import critic as critic_mod

# ---------------------------------------------------------------------------
# Graph state ----------------------------------------------------------------
# ---------------------------------------------------------------------------


class CompilerState(TypedDict):
    question: str
    plan: List[Dict[str, Any]]
    results: Dict[str, Any]
    summary: str
    markdown: str
    critic: Dict[str, Any]
    retries: int


# ---------------------------------------------------------------------------
# Node wrappers --------------------------------------------------------------
# ---------------------------------------------------------------------------


def planner_node(state: CompilerState) -> Dict[str, Any]:  # noqa: D401
    question = state["question"]

    if os.getenv("OFFLINE"):
        # Offline deterministic stub
        plan: List[Dict[str, Any]] = []
    else:
        plan = planner_mod.get_plan(question)
    return {"plan": plan}


def executor_node(state: CompilerState) -> Dict[str, Any]:
    plan = state["plan"]
    results = executor_mod.execute(plan, stream=False) if plan else {}
    return {"results": results}


def helper_node(state: CompilerState) -> Dict[str, Any]:
    results = state["results"]
    summary_json = helper_mod.merge_results(results) if results else "{}"
    return {"summary": summary_json}


def composer_node(state: CompilerState) -> Dict[str, Any]:
    md = composer_mod.compose_from_execution(state["question"], state["results"])
    return {"markdown": md, "retries": state.get("retries", 0) + 1}


def critic_node(state: CompilerState) -> Dict[str, Any]:
    critique = critic_mod.score(state["markdown"], state["summary"])
    return {"critic": critique}


# ---------------------------------------------------------------------------
# Graph builder --------------------------------------------------------------
# ---------------------------------------------------------------------------


def _build_graph(max_retries: int = 1):  # noqa: D401
    builder = StateGraph(CompilerState)

    # Register nodes
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("helper", helper_node)
    builder.add_node("composer", composer_node)
    builder.add_node("critic", critic_node)

    # Linear edges
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_edge("executor", "helper")
    builder.add_edge("helper", "composer")
    builder.add_edge("composer", "critic")

    # Conditional edge based on critic score
    def _should_retry(state: CompilerState) -> str:
        score = float(state.get("critic", {}).get("score", 0))
        retries = state.get("retries", 0)
        if score < 0.8 and retries <= max_retries:
            return "composer"
        return END

    builder.add_conditional_edges("critic", _should_retry)

    return builder.compile()


_GRAPH_CACHE: Dict[int, Any] = {}


def _get_graph(max_retries: int):
    if max_retries not in _GRAPH_CACHE:
        _GRAPH_CACHE[max_retries] = _build_graph(max_retries)
    return _GRAPH_CACHE[max_retries]


# ---------------------------------------------------------------------------
# Public helpers -------------------------------------------------------------
# ---------------------------------------------------------------------------


def run_full(question: str, max_retries: int = 1) -> str:  # noqa: D401
    """Execute the full pipeline and return Markdown answer."""

    graph = _get_graph(max_retries)
    state: CompilerState = {
        "question": question,
        "plan": [],
        "results": {},
        "summary": "{}",
        "markdown": "",
        "critic": {},
        "retries": 0,
    }

    final_state = graph.invoke(state)
    return final_state["markdown"]


# ---------------------------------------------------------------------------
# CLI -----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None):
    p = argparse.ArgumentParser(prog="agent.graph_runner", description="Run full LLM Compiler pipeline")
    p.add_argument("question", help="Student question in quotes")
    p.add_argument("--retries", type=int, default=1, help="Max composer retries (default 1)")
    p.add_argument("--mermaid", metavar="PATH", help="Optional path to save Mermaid diagram")
    return p.parse_args(argv)


def _cli_main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = _parse_args(argv)
    if args.mermaid:
        g = _get_graph(args.retries)
        Path(args.mermaid).write_text(g.get_graph().draw_mermaid(), encoding="utf-8")
        print(f"Mermaid graph saved to {args.mermaid}")

    answer = run_full(args.question, max_retries=args.retries)
    print(answer)


if __name__ == "__main__":
    _cli_main() 