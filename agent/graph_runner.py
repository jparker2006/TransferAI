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

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, START, END

from agent import planner as planner_mod
from agent import executor as executor_mod
from agent import helper as helper_mod
from agent import composer as composer_mod
from agent import critic as critic_mod
from agent import joiner as joiner_mod
from agent import replanner as replanner_mod

import asyncio

# ---------------------------------------------------------------------------
# Graph state ----------------------------------------------------------------
# ---------------------------------------------------------------------------


class CompilerState(TypedDict, total=False):
    question: str
    plan: List[Dict[str, Any]]
    results: Dict[str, Any]
    summary: str
    markdown: str
    critic: Dict[str, Any]
    retries: int
    needs_more_tasks: bool  # optional
    replans_done: int  # optional


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
    # Enable streaming so TaskEvent objects are published for joiner consumption
    results = executor_mod.execute(plan, stream=True) if plan else {}
    return {"results": results}


def helper_node(state: CompilerState) -> Dict[str, Any]:
    results = state["results"]
    summary_json = helper_mod.merge_results(results) if results else "{}"
    return {"summary": summary_json}


def composer_node(state: CompilerState) -> Dict[str, Any]:  # noqa: D401
    if os.getenv("OFFLINE"):
        # In offline mode, return a simple markdown response
        md = f"# Answer to: {state['question']}\n\nThis is a test response in offline mode."
    elif state["results"]:
        md = composer_mod.compose_from_execution(state["question"], state["results"])
    else:
        # If no new results, fall back to the existing summary only.
        md = composer_mod.compose(state.get("summary", "{}"))
    return {"markdown": md, "retries": state.get("retries", 0) + 1}


def critic_node(state: CompilerState) -> Dict[str, Any]:
    if os.getenv("OFFLINE"):
        # In offline mode, always return a high score to avoid retries
        critique = {"score": 1.0, "feedback": "Offline mode - no critique"}
    else:
        critique = critic_mod.score(state["markdown"], state["summary"])
    return {"critic": critique}


def joiner_node(state: CompilerState) -> Dict[str, Any]:  # noqa: D401
    """Aggregate executor outputs and decide whether more tasks are needed."""

    plan = state["plan"]
    results = state["results"]

    # Fast-path: if no results gathered yet, skip streaming logic.
    if not results:
        return {"summary": "{}"}

    # For now, bypass the streaming joiner and use helper directly
    # This avoids async context issues while maintaining the same logic
    try:
        summary_json = helper_mod.merge_results(results)
        
        # In offline mode, never ask for more tasks to avoid infinite loops
        if os.getenv("OFFLINE"):
            return {"summary": summary_json, "needs_more_tasks": False}
        
        # Simple heuristic: if we have results for all planned tools, we're done
        planned_tools = {node.get("tool") for node in plan if node.get("tool")}
        executed_tools = set()
        for node_id in results:
            tool_name = node_id.split("#", 1)[0]
            executed_tools.add(tool_name)
        
        coverage_ratio = len(executed_tools) / len(planned_tools) if planned_tools else 1.0
        needs_more = coverage_ratio < 0.6  # same threshold as joiner default
        
        update = {"summary": summary_json}
        if needs_more:
            update["needs_more_tasks"] = True
        return update
        
    except ValueError:
        # Results empty or invalid
        return {"summary": "{}"}


def replanner_node(state: CompilerState) -> Dict[str, Any]:  # noqa: D401
    """Invoke adaptive replanner to append additional DAG nodes."""

    question = state["question"]
    initial_plan = state["plan"]
    summary_json = state["summary"]

    # For now, directly call the planner with context instead of using the async replanner
    # This avoids async context issues while still expanding the plan
    try:
        contextual_question = (
            f"{question}\n\n<context>\nCURRENT SUMMARY:\n{summary_json}\n\n"
            f"EXECUTED NODES:\n{json.dumps(initial_plan, ensure_ascii=False)}\n</context>"
        )
        
        if os.getenv("OFFLINE"):
            # In offline mode, just add a simple search node
            new_nodes = [{"id": f"replan_{len(initial_plan)}", "tool": "course_search", "args": {"query": "test"}, "depends_on": []}]
        else:
            candidate_nodes = planner_mod.get_plan(contextual_question)
            # Simple deduplication: remove nodes with IDs that already exist
            existing_ids = {node.get("id") for node in initial_plan}
            new_nodes = [node for node in candidate_nodes if node.get("id") not in existing_ids]
        
        if new_nodes:
            extended_plan = initial_plan + new_nodes
        else:
            extended_plan = initial_plan

        return {
            "plan": extended_plan,
            "results": {},  # reset for next executor pass
            "replans_done": state.get("replans_done", 0) + 1,
            "needs_more_tasks": False,  # reset
        }
        
    except Exception:
        # If replanning fails, just continue with existing plan
        return {
            "plan": initial_plan,
            "results": {},
            "replans_done": state.get("replans_done", 0) + 1,
            "needs_more_tasks": False,
        }


# ---------------------------------------------------------------------------
# Graph builder --------------------------------------------------------------
# ---------------------------------------------------------------------------


def _build_graph(max_retries: int = 1, max_replans: int | None = None):  # noqa: D401
    builder = StateGraph(CompilerState)

    legacy_mode = max_replans is None

    # Register nodes
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("helper", helper_node)
    builder.add_node("composer", composer_node)
    builder.add_node("critic", critic_node)

    if not legacy_mode:
        builder.add_node("joiner", joiner_node)
        builder.add_node("replanner", replanner_node)

    # Linear edges
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    if legacy_mode:
        builder.add_edge("executor", "helper")
    else:
        builder.add_edge("executor", "joiner")
        # joiner uses conditional edges only - no regular edges
        builder.add_edge("replanner", "executor")
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

    if not legacy_mode:
        def _needs_more(state: CompilerState) -> str:  # noqa: D401 – simple routing
            needs_more = state.get("needs_more_tasks")
            replans_done = state.get("replans_done", 0)
            if needs_more and replans_done < max_replans:
                return "replanner"
            return "helper"

        builder.add_conditional_edges("joiner", _needs_more)

    return builder.compile()


_GRAPH_CACHE: Dict[tuple[int, int | None], Any] = {}


def _get_graph(max_retries: int, max_replans: int | None = None):
    key = (max_retries, max_replans)
    if key not in _GRAPH_CACHE:
        _GRAPH_CACHE[key] = _build_graph(max_retries, max_replans)
    return _GRAPH_CACHE[key]


# ---------------------------------------------------------------------------
# Public helpers -------------------------------------------------------------
# ---------------------------------------------------------------------------


def run_full(question: str, *, max_retries: int = 1, max_replans: int | None = None) -> str:  # noqa: D401
    """Execute the full pipeline and return Markdown answer."""

    graph = _get_graph(max_retries, max_replans)
    state: CompilerState = {
        "question": question,
        "plan": [],
        "results": {},
        "summary": "{}",
        "markdown": "",
        "critic": {},
        "retries": 0,
        "needs_more_tasks": False,
        "replans_done": 0,
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
    p.add_argument("--replans", type=int, help="Max replanner iterations (omit for legacy mode)")
    p.add_argument("--mermaid", metavar="PATH", help="Optional path to save Mermaid diagram")
    return p.parse_args(argv)


def _cli_main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = _parse_args(argv)
    if args.mermaid:
        g = _get_graph(args.retries, args.replans)
        Path(args.mermaid).write_text(g.get_graph().draw_mermaid(), encoding="utf-8")
        print(f"Mermaid graph saved to {args.mermaid}")

    answer = run_full(args.question, max_retries=args.retries, max_replans=args.replans)
    print(answer)


if __name__ == "__main__":
    _cli_main() 