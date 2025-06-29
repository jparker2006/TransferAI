import asyncio
from typing import Any, AsyncGenerator, Dict, List

import pytest

from agent.replanner import replan_loop

# ---------------------------------------------------------------------------
# Fixtures & helper generators ---------------------------------------------
# ---------------------------------------------------------------------------


@pytest.fixture()
def initial_plan() -> List[Dict[str, Any]]:
    return [
        {"id": "p#1", "tool": "p", "args": {}},
        {"id": "q#1", "tool": "q", "args": {}},
    ]


async def _dummy_joiner_stream(*updates: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
    """Yield provided updates sequentially with a tiny await between."""

    for upd in updates:
        await asyncio.sleep(0)
        yield upd


# ---------------------------------------------------------------------------
# Monkeypatch helpers -------------------------------------------------------
# ---------------------------------------------------------------------------


def _patch_planner(monkeypatch, plans: List[List[Dict[str, Any]]]):
    """Monkeypatch *agent.planner.get_plan* to pop from *plans* list sequentially."""

    from agent import planner as planner_mod  # local import

    plans_iter = iter(plans)

    def _fake_get_plan(_question: str):  # noqa: D401 – test stub
        try:
            return next(plans_iter)
        except StopIteration:  # pragma: no cover
            pytest.fail("planner.get_plan called too many times")

    monkeypatch.setattr(planner_mod, "get_plan", _fake_get_plan, raising=True)


@pytest.fixture(autouse=True)
def _patch_verify_dag(monkeypatch):
    """Stub out *agent.verify_dag.verify_dag* so it never raises during tests."""

    import types, importlib

    fake_mod = types.ModuleType("agent.verify_dag")
    fake_mod.verify_dag = lambda plan: plan  # type: ignore[arg-type]

    # Replace replanner's cached reference
    import agent.replanner as replanner_mod
    monkeypatch.setattr(replanner_mod, "_verify_dag_mod", fake_mod, raising=True)

    # Also ensure any new imports get the stub
    sys_modules_backup = importlib.import_module
    import sys  # noqa: WPS433 – test hack
    sys.modules["agent.verify_dag"] = fake_mod
    yield


# ---------------------------------------------------------------------------
# Test cases ----------------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_initial_yield_contains_original_plan(initial_plan, monkeypatch):
    _patch_planner(monkeypatch, plans=[[{"id": "x#1", "tool": "x", "args": {}}]])

    async def _stream():
        yield {"summary": "{}", "needs_more_tasks": False}

    gen = replan_loop("question", initial_plan, _stream())
    first = await gen.__anext__()
    assert first["iteration"] == 0
    assert first["new_nodes"] == initial_plan


@pytest.mark.asyncio
async def test_one_replan_iteration(initial_plan, monkeypatch):
    new_nodes = [
        {"id": "r#1", "tool": "r", "args": {}},
        {"id": "s#1", "tool": "s", "args": {}},
    ]
    _patch_planner(monkeypatch, plans=[new_nodes])

    stream_updates = [
        {"summary": "{}", "needs_more_tasks": True},
        {"summary": "{}", "needs_more_tasks": False},
    ]
    gen = replan_loop("question", initial_plan, _dummy_joiner_stream(*stream_updates))

    first = await gen.__anext__()  # initial
    second = await gen.__anext__()  # after replan
    third = await gen.__anext__()  # stop

    assert second["iteration"] == 1
    assert second["stop"] is False
    assert second["new_nodes"] == new_nodes

    assert third["stop"] is True
    assert third["new_nodes"] == []


@pytest.mark.asyncio
async def test_deduplication_skips_existing_ids(initial_plan, monkeypatch):
    # planner returns one duplicate (q#1) and one novel (t#1)
    candidate = [
        {"id": "q#1", "tool": "q", "args": {}},
        {"id": "t#1", "tool": "t", "args": {}},
    ]
    _patch_planner(monkeypatch, plans=[candidate])

    stream_updates = [
        {"summary": "{}", "needs_more_tasks": True},
        {"summary": "{}", "needs_more_tasks": False},
    ]

    gen = replan_loop("question", initial_plan, _dummy_joiner_stream(*stream_updates))

    await gen.__anext__()  # initial
    delta = await gen.__anext__()

    assert delta["new_nodes"] == [{"id": "t#1", "tool": "t", "args": {}}]


@pytest.mark.asyncio
async def test_max_iterations_enforced(initial_plan, monkeypatch):
    # Planner will be called twice but max_iterations is 1
    _patch_planner(
        monkeypatch,
        plans=[[{"id": "u#1", "tool": "u", "args": {}}], [{"id": "v#1", "tool": "v", "args": {}}]],
    )

    stream_updates = [
        {"summary": "{}", "needs_more_tasks": True},
        {"summary": "{}", "needs_more_tasks": True},  # would normally trigger second replan
        {"summary": "{}", "needs_more_tasks": False},
    ]

    gen = replan_loop(
        "question", initial_plan, _dummy_joiner_stream(*stream_updates), max_iterations=1
    )

    await gen.__anext__()  # initial
    _ = await gen.__anext__()  # first replan
    final = await gen.__anext__()  # should stop – no second replan

    assert final["stop"] is True


@pytest.mark.asyncio
async def test_cancellation_propagates(initial_plan, monkeypatch):
    new_nodes = [{"id": "w#1", "tool": "w", "args": {}}]
    _patch_planner(monkeypatch, plans=[new_nodes])

    # Infinite joiner stream that always asks for more tasks
    async def _joiner_forever():
        while True:
            yield {"summary": "{}", "needs_more_tasks": True}
            await asyncio.sleep(0)

    gen = replan_loop("question", initial_plan, _joiner_forever())

    # Prime the generator
    await gen.__anext__()

    # Create task consuming the generator and cancel it
    consume_task = asyncio.create_task(gen.__anext__())
    await asyncio.sleep(0)
    consume_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await consume_task 