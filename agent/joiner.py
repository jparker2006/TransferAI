from __future__ import annotations

"""Streaming Joiner layer for the TransferAI LLM Compiler.

This module incrementally aggregates Executor outputs into the canonical summary JSON
format defined in ``schemas/summary.schema.json``.  It listens to the shared event bus
published by :pymod:`agent.executor` and emits an async stream of dictionaries that can
be consumed by higher-level orchestration logic (e.g. a LangGraph feedback loop).

Public coroutine
----------------
``join_stream`` – consume :class:`~agent.executor.TaskEvent` objects, merge finished
node outputs, validate against the JSON schema, and yield the *current* summary JSON as
well as a ``needs_more_tasks`` heuristic flag signalling whether the Planner should run
again.

The Joiner does **not** perform any network IO or LLM calls.  It re-uses the exact merge
logic from :pyfunc:`agent.helper.merge_results` to guarantee identical output
semantics.

Usage example (outside the main graph):

>>> async for update in join_stream(question, plan, results):
...     print(update["summary"])
...     if update["needs_more_tasks"]:
...         replan()  # application-specific

The module is intentionally self-contained so that wiring it into LangGraph in a later
iteration requires *no* code changes here.
"""

import argparse
import asyncio
import json
import sys
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import jsonschema

from agent.executor import TaskEvent, get_event_bus  # noqa: TID251 – local, intentional
from agent import helper as _helper_mod

__all__ = ["join_stream"]

# ---------------------------------------------------------------------------
# Internal helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------

# Re-use private helper utilities via gentle fallback import.  This keeps the exact
# merging semantics of *helper.merge_results* without duplicating implementation.
_load_tool_merger = getattr(_helper_mod, "_load_tool_merger")  # pragma: no cover
_default_merge = getattr(_helper_mod, "_default_merge")  # pragma: no cover


class JoinerError(Exception):
    """Raised when summary construction or validation fails inside the Joiner."""


async def _merge_single_output(
    node_id: str,
    results: Dict[str, Any],
    merged_results: Dict[str, Any],
    results_lock: asyncio.Lock | None = None,
) -> None:
    """Merge a single Executor *node* output into *merged_results* in-place.

    The function mirrors the behaviour of ``agent.helper.merge_results`` for one item.

    Parameters
    ----------
    node_id
        ID of the DAG node that just finished.
    results
        Shared mapping populated by the Executor (node_id → raw output).
    merged_results
        The cumulative merged results structure that will be embedded in the summary.
    results_lock
        Optional lock guarding *results* accesses when concurrent writes are possible.
    """

    # Acquire lock if provided (best-effort – executor does not currently use one)
    if results_lock is not None:
        async with results_lock:
            raw_output = results[node_id]
    else:
        raw_output = results[node_id]

    # Tool name is the substring before an optional "#<index>" suffix added by the Planner
    tool_name = node_id.split("#", 1)[0]

    # Fetch tool-specific merger handler (or fallback).
    merger_fn = _load_tool_merger(tool_name)
    merged_output = merger_fn(raw_output)

    if tool_name in merged_results:
        existing = merged_results[tool_name]
        if isinstance(existing, list):
            existing.append(merged_output)
        else:
            merged_results[tool_name] = [existing, merged_output]
    else:
        merged_results[tool_name] = merged_output


def _build_summary(
    merged_results: Dict[str, Any],
    *,
    schema_version: str,
) -> str:
    """Return a JSON *string* for *merged_results* validated against the schema."""

    summary = {
        "merged_results": merged_results,
        "metadata": {
            "tool_count": len(merged_results),
            "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "schema_version": schema_version,
        },
    }

    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "summary.schema.json"
    try:
        with schema_path.open("r", encoding="utf-8") as fp:
            schema = json.load(fp)
        jsonschema.validate(summary, schema)
    except FileNotFoundError as exc:
        raise JoinerError(f"Schema file not found: {schema_path}") from exc
    except jsonschema.ValidationError as exc:
        raise JoinerError(f"Summary violates schema: {exc.message}") from exc

    return json.dumps(summary, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Public coroutine ----------------------------------------------------------
# ---------------------------------------------------------------------------

async def join_stream(
    question: str,  # noqa: ARG001 – kept for future heuristic improvements
    plan: List[Dict[str, Any]],
    results: Dict[str, Any],
    *,
    schema_version: str = "0.1",
    replan_threshold: float = 0.4,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Incrementally aggregate Executor outputs.

    Parameters
    ----------
    question
        Original user query (currently unused).
    plan
        Original plan produced by the Planner (list of DAG node dictionaries).
    results
        Shared mapping where the Executor stores outputs.  This *must* be the same
        object instance observed by the Executor to avoid synchronization issues.
    schema_version
        Version string embedded in the generated summary metadata (default ``"0.1"``).
    replan_threshold
        Minimum coverage ratio below which ``needs_more_tasks`` is flagged ``True``.

    Yields
    ------
    dict
        Dictionary with keys ``summary`` (UTF-8 JSON string) and
        ``needs_more_tasks`` (bool).
    """

    event_bus = get_event_bus()
    results_lock: asyncio.Lock | None = asyncio.Lock()  # executor does not currently lock

    # Pre-compute the set of tools present in the original plan for coverage tracking.
    planned_tools: Set[str] = {node["tool"] for node in plan if "tool" in node}
    total_planned = len(planned_tools) or 1  # avoid division by zero

    merged_results: Dict[str, Any] = {}
    completed_nodes = 0
    total_nodes = len(plan)

    while completed_nodes < total_nodes:
        event: TaskEvent = await event_bus.get()
        if event.type != "finished":
            # Ignore "started" or unknown event types.
            continue

        node_id = event.node_id
        await _merge_single_output(node_id, results, merged_results, results_lock=results_lock)
        completed_nodes += 1

        # Build summary JSON and compute coverage.
        try:
            summary_json = _build_summary(merged_results, schema_version=schema_version)
        except JoinerError as exc:
            # Propagate immediately – upstream orchestrator can decide how to react.
            raise

        coverage_ratio = len(merged_results) / total_planned
        needs_more_tasks = coverage_ratio < replan_threshold

        yield {
            "summary": summary_json,
            "needs_more_tasks": needs_more_tasks,
        }


# ---------------------------------------------------------------------------
# Optional CLI helper -------------------------------------------------------
# ---------------------------------------------------------------------------

def _parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent.joiner",
        description="Run the Joiner over a pre-computed plan/results pair and print summaries.",
    )
    parser.add_argument("plan_path", help="Path to the Planner JSON output (plan).")
    parser.add_argument("results_path", help="Path to the Executor JSON results mapping.")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.4,
        help="Re-plan coverage threshold (default 0.4).",
    )
    return parser.parse_args(argv)


def _cli_main(argv: List[str] | None = None) -> None:  # pragma: no cover
    args = _parse_args(argv)

    plan_file = Path(args.plan_path)
    results_file = Path(args.results_path)

    try:
        plan: List[Dict[str, Any]] = json.loads(plan_file.read_text(encoding="utf-8"))
        results: Dict[str, Any] = json.loads(results_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(f"[joiner] Failed to load input files: {exc}")

    # Manually enqueue "finished" events for each node present in *results* so the
    # joiner coroutine can operate without a running Executor.
    event_bus = get_event_bus()
    for node_id in results.keys():
        event_bus.put_nowait(TaskEvent("finished", node_id))

    async def _run() -> None:
        async for update in join_stream(
            question="",  # unused
            plan=plan,
            results=results,
            replan_threshold=args.threshold,
        ):
            print(update["summary"])
            if update["needs_more_tasks"]:
                print("[joiner] needs_more_tasks = true (coverage below threshold)")

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    _cli_main() 