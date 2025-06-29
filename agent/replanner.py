from __future__ import annotations

"""Adaptive Re-Planner for the TransferAI LLM Compiler.

This module closes the feedback loop between the streaming Joiner layer and the
planning subsystem.  Whenever the Joiner signals that *more* work is required,
we query the Planner again with rich execution context to obtain *additional*
DAG nodes.  Only *novel* nodes are surfaced to the caller; duplicates are
filtered out and dependency integrity is preserved.

The coroutine :func:`replan_loop` is intentionally generic so it can be wired
into LangGraph or any other orchestrator without modification.
"""

import asyncio
import json
import logging
from collections.abc import AsyncGenerator, AsyncIterable
from copy import deepcopy
from typing import Any, Dict, List
import importlib

from agent import planner as _planner_mod

# Import the *module* so we can always access ``verify_dag`` as an attribute.
_verify_dag_mod = importlib.import_module("agent.verify_dag")

__all__ = ["replan_loop"]

# Initialise module-level logger ------------------------------------------------
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Duplicate detection -------------------------------------------------------
# ---------------------------------------------------------------------------


def _is_duplicate(node: Dict[str, Any], seen: List[Dict[str, Any]]) -> bool:
    """Return *True* when *node* is a duplicate of any node in *seen*.

    Duplicate criteria:
    1. Same ``id`` value, **or**
    2. Same ``tool`` *and* deeply equal ``args`` mapping.
    """

    node_id = node.get("id")
    node_tool = node.get("tool")
    node_args = node.get("args", {})

    for other in seen:
        if node_id and node_id == other.get("id"):
            return True
        if (
            node_tool
            and node_tool == other.get("tool")
            and node_args == other.get("args", {})
        ):
            return True
    return False


# ---------------------------------------------------------------------------
# Re-planning coroutine -----------------------------------------------------
# ---------------------------------------------------------------------------

async def _call_planner(question_with_context: str) -> List[Dict[str, Any]]:
    """Run the planner in a thread to avoid blocking the event loop."""

    return await asyncio.to_thread(_planner_mod.get_plan, question_with_context)


async def replan_loop(
    question: str,
    initial_plan: List[Dict[str, Any]],
    joiner_stream: AsyncIterable[Dict[str, Any]],
    *,
    max_iterations: int = 3,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Adaptive planning loop.

    Parameters
    ----------
    question
        Original user question.
    initial_plan
        First set of DAG nodes produced by the Planner.
    joiner_stream
        Async iterable produced by :func:`agent.joiner.join_stream`.
    max_iterations
        Safeguard against infinite planning loops (default *3*).

    Yields
    ------
    dict
        ``{"new_nodes": list[dict], "iteration": int, "stop": bool}``
    """

    current_plan: List[Dict[str, Any]] = deepcopy(initial_plan)

    # ------------------------------------------------------------------
    # Iteration 0 – emit original plan ---------------------------------
    # ------------------------------------------------------------------
    iteration = 0
    yield {"new_nodes": deepcopy(initial_plan), "iteration": iteration, "stop": False}

    if max_iterations <= 0:
        yield {"new_nodes": [], "iteration": iteration, "stop": True}
        return

    # ------------------------------------------------------------------
    # Main feedback loop -----------------------------------------------
    # ------------------------------------------------------------------
    try:
        async for joiner_update in joiner_stream:
            needs_more: bool = bool(joiner_update.get("needs_more_tasks"))
            summary_json: str = str(joiner_update.get("summary", "{}"))

            logger.debug("Joiner update – needs_more=%s, iter=%s", needs_more, iteration)

            if not needs_more:
                # No further planning required.
                yield {"new_nodes": [], "iteration": iteration, "stop": True}
                return

            if iteration >= max_iterations:
                logger.debug("Max iterations %s reached – stopping replanner.", max_iterations)
                yield {"new_nodes": [], "iteration": iteration, "stop": True}
                return

            iteration += 1

            # ------------------------------------------------------------------
            # Build context-rich prompt ----------------------------------------
            # ------------------------------------------------------------------
            executed_plan_json = json.dumps(current_plan, ensure_ascii=False)
            contextual_question = (
                f"{question}\n\n<context>\nCURRENT SUMMARY:\n{summary_json}\n\n"
                f"EXECUTED NODES:\n{executed_plan_json}\n</context>"
            )

            logger.debug("Re-planner call (iteration %s)", iteration)

            try:
                candidate_nodes: List[Dict[str, Any]] = await _call_planner(contextual_question)
            except asyncio.CancelledError:
                raise  # bubble up – caller is shutting down
            except Exception as exc:  # noqa: BLE001 – surface downstream
                logger.exception("Planner failed in iteration %s: %s", iteration, exc)
                yield {"new_nodes": [], "iteration": iteration, "stop": True}
                return

            # Deduplicate ----------------------------------------------------
            delta_nodes: List[Dict[str, Any]] = [
                node for node in candidate_nodes if not _is_duplicate(node, current_plan)
            ]

            if not delta_nodes:
                logger.debug("Iteration %s produced no novel nodes – stopping.", iteration)
                yield {"new_nodes": [], "iteration": iteration, "stop": True}
                return

            # Combine & validate -------------------------------------------
            combined_plan = current_plan + delta_nodes
            try:
                _verify_dag_mod.verify_dag(combined_plan)
            except Exception as exc:  # noqa: BLE001 – validation error
                logger.exception("Combined plan failed validation: %s", exc)
                yield {"new_nodes": [], "iteration": iteration, "stop": True}
                return

            # Update *current_plan* *after* successful validation.
            current_plan.extend(delta_nodes)

            logger.debug("Iteration %s – %s new node(s) added", iteration, len(delta_nodes))

            yield {"new_nodes": deepcopy(delta_nodes), "iteration": iteration, "stop": False}

            # Continue loop – await next Joiner update --------------------

    except asyncio.CancelledError:
        logger.warning("Re-planner coroutine cancelled – exiting cleanly.")
        raise 