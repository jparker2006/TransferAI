import asyncio
import json
import random
from typing import Any, Dict, List

import pytest

from agent.executor import TaskEvent, get_event_bus
from agent.joiner import join_stream
from agent import helper as helper_mod

# ---------------------------------------------------------------------------
# Fixtures ------------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_event_bus():
    """Ensure a fresh in-memory event bus for each test run."""

    # Lazily import to avoid circulars
    import agent.executor as executor_mod

    # Reset the global bus before and after each test
    executor_mod._EVENT_BUS = None  # type: ignore[attr-defined]  # noqa: SLF001
    yield
    executor_mod._EVENT_BUS = None  # type: ignore[attr-defined]  # noqa: SLF001


@pytest.fixture()
def dummy_plan() -> List[Dict[str, Any]]:
    """Return a deterministic 4-node plan used across tests."""

    tools = ["foo", "bar", "baz", "qux"]
    return [
        {"id": f"{tool}#1", "tool": tool, "args": {}, "depends_on": []} for tool in tools
    ]


@pytest.fixture()
def dummy_results() -> Dict[str, Any]:
    """Shared mapping simulating Executor results."""

    return {}


@pytest.fixture()
def enqueue_event():
    """Return a callable that enqueues *finished* events lazily.

    We defer ``get_event_bus()`` until the first call so it happens inside an
    active event loop (pytest's asyncio plugin).
    """

    def _enqueue(node_id: str) -> None:  # noqa: D401 – factory style
        bus = get_event_bus()
        bus.put_nowait(TaskEvent("finished", node_id))

    return _enqueue


# ---------------------------------------------------------------------------
# Helper utilities ----------------------------------------------------------
# ---------------------------------------------------------------------------


async def _collect_stream(gen):
    """Collect all items from *gen* into a list and return it."""

    collected = []
    async for item in gen:
        collected.append(item)
    return collected


# ---------------------------------------------------------------------------
# Test cases ----------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_yields_per_finished_task(dummy_plan, dummy_results, enqueue_event):
    """A summary should be yielded for *each* finished task."""

    async def _producer() -> None:
        for node in dummy_plan:
            dummy_results[node["id"]] = {"val": node["tool"]}
            enqueue_event(node["id"])
            await asyncio.sleep(0)  # allow Joiner to run

    producer_task = asyncio.create_task(_producer())
    consumer_task = asyncio.create_task(
        _collect_stream(join_stream("", dummy_plan, dummy_results))
    )

    summaries = await consumer_task
    await producer_task

    assert len(summaries) == len(dummy_plan)

    # Final summary must list *all* tools
    final_summary = json.loads(summaries[-1]["summary"])
    assert set(final_summary["merged_results"].keys()) == {n["tool"] for n in dummy_plan}


@pytest.mark.asyncio
async def test_final_summary_matches_helper_merge(dummy_plan, dummy_results, enqueue_event):
    """Joiner final summary should byte-match Helper layer output."""

    # Enqueue all events up-front
    for node in dummy_plan:
        dummy_results[node["id"]] = {"val": node["tool"]}
        enqueue_event(node["id"])

    collected = await _collect_stream(join_stream("", dummy_plan, dummy_results))
    joiner_json = json.loads(collected[-1]["summary"])
    helper_json = json.loads(helper_mod.merge_results(dummy_results))

    # Ignore timestamp differences
    joiner_json["metadata"]["generated_at"] = "0"
    helper_json["metadata"]["generated_at"] = "0"

    assert joiner_json == helper_json


@pytest.mark.asyncio
async def test_needs_more_tasks_toggle(enqueue_event):
    """`needs_more_tasks` should flip from True to False as coverage improves."""

    plan = [
        {"id": "a#1", "tool": "a", "args": {}},
        {"id": "b#1", "tool": "b", "args": {}},
        {"id": "c#1", "tool": "c", "args": {}},
    ]
    results: Dict[str, Any] = {}

    async def _producer() -> None:
        # First produce only one result, causing low coverage
        results["a#1"] = {"val": "a"}
        enqueue_event("a#1")
        await asyncio.sleep(0)
        # Now produce remaining two → coverage 1.0
        for node_id in ("b#1", "c#1"):
            results[node_id] = {"val": node_id.split("#", 1)[0]}
            enqueue_event(node_id)
            await asyncio.sleep(0)

    gen = join_stream("", plan, results, replan_threshold=0.6)

    producer_task = asyncio.create_task(_producer())
    collected = await _collect_stream(gen)
    await producer_task

    assert collected[0]["needs_more_tasks"] is True
    assert collected[-1]["needs_more_tasks"] is False


@pytest.mark.asyncio
async def test_race_conditions_safe(dummy_plan, dummy_results, enqueue_event):
    """Stress-test concurrent writes with random jitter to surface race issues."""

    iterations = 100

    async def _run_once() -> None:
        # Reset state each inner iteration
        dummy_results.clear()
        for node in dummy_plan:
            await asyncio.sleep(random.uniform(0, 0.01))
            dummy_results[node["id"]] = {"val": node["tool"]}
            enqueue_event(node["id"])

        # Drain the joiner
        async for _ in join_stream("", dummy_plan, dummy_results):
            pass

    for _ in range(iterations):
        await _run_once() 