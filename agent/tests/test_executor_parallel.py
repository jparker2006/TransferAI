"""Test parallel execution in agent.executor."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest

from agent.executor import async_execute, execute, get_event_bus, TaskEvent


@pytest.fixture
def mock_tools():
    """Mock tools that sleep to simulate work."""
    
    async def mock_tool_a(**kwargs):
        await asyncio.sleep(0.1)
        return {"result": "tool_a"}
    
    async def mock_tool_b(**kwargs):
        await asyncio.sleep(0.1)
        return {"result": "tool_b"}
    
    async def mock_tool_c(**kwargs):
        await asyncio.sleep(0.1)
        return {"result": "tool_c"}
    
    tools = {
        "course_search": mock_tool_a,
        "faq_search": mock_tool_b,
        "glossary": mock_tool_c,
    }
    
    def mock_import(module_name):
        tool_name = module_name.split(".")[-1]
        if tool_name in tools:
            # Create a simple mock that only has the run method
            class MockModule:
                def __init__(self):
                    self.run = tools[tool_name]
                def __getattr__(self, name):
                    # Return None for any attribute that _find_tool_object might look for
                    return None
            return MockModule()
        raise ImportError(f"No module named '{module_name}'")
    
    return mock_import


@pytest.mark.asyncio
async def test_parallel_execution_no_deps(mock_tools):
    """Test that independent tasks run in parallel."""
    nodes = [
        {"id": "task1", "tool": "course_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "task2", "tool": "faq_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "task3", "tool": "glossary", "args": {"query": "test"}, "depends_on": []},
    ]
    
    with patch("agent.executor.importlib.import_module", side_effect=mock_tools):
        start_time = time.time()
        results = await async_execute(nodes, max_concurrency=3)
        elapsed = time.time() - start_time
    
    # Should complete in ~0.1s (parallel) not ~0.3s (sequential)
    assert elapsed < 0.15
    assert len(results) == 3
    assert results["task1"]["result"] == "tool_a"
    assert results["task2"]["result"] == "tool_b"
    assert results["task3"]["result"] == "tool_c"


@pytest.mark.asyncio
async def test_sequential_execution_limited_concurrency(mock_tools):
    """Test that concurrency limit forces sequential execution."""
    nodes = [
        {"id": "task1", "tool": "course_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "task2", "tool": "faq_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "task3", "tool": "glossary", "args": {"query": "test"}, "depends_on": []},
    ]
    
    with patch("agent.executor.importlib.import_module", side_effect=mock_tools):
        start_time = time.time()
        results = await async_execute(nodes, max_concurrency=1)
        elapsed = time.time() - start_time
    
    # Should take ~0.3s (sequential) with concurrency=1
    assert elapsed > 0.28
    assert len(results) == 3


@pytest.mark.asyncio
async def test_dependency_ordering():
    """Test that dependencies are respected in parallel execution."""
    execution_order = []
    
    def create_tracking_tool(tool_name):
        async def tool(**kwargs):
            execution_order.append(f"{tool_name}_start")
            await asyncio.sleep(0.05)
            execution_order.append(f"{tool_name}_finish")
            return {"result": tool_name}
        return tool
    
    def mock_import(module_name):
        tool_name = module_name.split(".")[-1]
        # Create a simple mock that only has the run method
        class MockModule:
            def __init__(self):
                self.run = create_tracking_tool(tool_name)
            def __getattr__(self, name):
                # Return None for any attribute that _find_tool_object might look for
                return None
        return MockModule()
    
    nodes = [
        {"id": "task1", "tool": "course_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "task2", "tool": "faq_search", "args": {"query": "test"}, "depends_on": ["task1"]},
        {"id": "task3", "tool": "glossary", "args": {"query": "test"}, "depends_on": ["task1"]},
        {"id": "task4", "tool": "major_requirement", "args": {"major_name": "test"}, "depends_on": ["task2", "task3"]},
    ]
    
    with patch("agent.executor.importlib.import_module", side_effect=mock_import):
        results = await async_execute(nodes, max_concurrency=4)
    
    # task1 must complete before task2 and task3 start
    # task2 and task3 must complete before task4 starts
    assert "course_search_finish" in execution_order
    task1_finish_idx = execution_order.index("course_search_finish")
    
    # task2 and task3 should start after task1 finishes
    if "faq_search_start" in execution_order:
        assert execution_order.index("faq_search_start") > task1_finish_idx
    if "glossary_start" in execution_order:
        assert execution_order.index("glossary_start") > task1_finish_idx
    
    assert len(results) == 4


@pytest.mark.asyncio
async def test_event_bus_tracking():
    """Test that event bus tracks task start/finish events."""
    nodes = [
        {"id": "task1", "tool": "course_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "task2", "tool": "faq_search", "args": {"query": "test"}, "depends_on": []},
    ]
    
    async def mock_tool(**kwargs):
        await asyncio.sleep(0.01)
        return {"result": "done"}
    
    def mock_import(module_name):
        mock_module = AsyncMock()
        mock_module.run = mock_tool
        return mock_module
    
    # Clear event bus
    event_bus = get_event_bus()
    while not event_bus.empty():
        await event_bus.get()
    
    with patch("agent.executor.importlib.import_module", side_effect=mock_import):
        results = await async_execute(nodes, stream=True)
    
    # Should have 4 events: 2 started, 2 finished
    events = []
    while not event_bus.empty():
        events.append(await event_bus.get())
    
    assert len(events) == 4
    
    started_events = [e for e in events if e.type == "started"]
    finished_events = [e for e in events if e.type == "finished"]
    
    assert len(started_events) == 2
    assert len(finished_events) == 2
    
    started_nodes = {e.node_id for e in started_events}
    finished_nodes = {e.node_id for e in finished_events}
    
    assert started_nodes == {"task1", "task2"}
    assert finished_nodes == {"task1", "task2"}


def test_sync_wrapper_compatibility():
    """Test that sync execute() wrapper maintains compatibility."""
    nodes = [
        {"id": "task1", "tool": "llm_step", "args": {"instructions": "test"}, "depends_on": []},
    ]
    
    # Should work without async/await
    results = execute(nodes, max_concurrency=2)
    
    assert len(results) == 1
    assert "task1" in results
    assert "text" in results["task1"]


def test_sync_wrapper_with_mock_tools():
    """Test sync wrapper with mock tools (non-async)."""
    
    def mock_tool(**kwargs):
        return {"result": "sync_tool"}
    
    def mock_import(module_name):
        # Create a simple mock that only has the run method
        class MockModule:
            def __init__(self):
                self.run = mock_tool
            def __getattr__(self, name):
                # Return None for any attribute that _find_tool_object might look for
                return None
        mock_module = MockModule()
        return mock_module
    
    nodes = [
        {"id": "task1", "tool": "course_search", "args": {"query": "test"}, "depends_on": []},
    ]
    
    with patch("agent.executor.importlib.import_module", side_effect=mock_import):
        results = execute(nodes, max_concurrency=1)
    
    assert len(results) == 1
    assert results["task1"]["result"] == "sync_tool"


@pytest.mark.asyncio
async def test_error_handling_cancels_running_tasks():
    """Test that errors cancel other running tasks."""
    
    async def failing_tool(**kwargs):
        await asyncio.sleep(0.01)
        raise RuntimeError("Tool failed")
    
    async def slow_tool(**kwargs):
        await asyncio.sleep(1.0)  # Should be cancelled
        return {"result": "should_not_complete"}
    
    def mock_import(module_name):
        tool_name = module_name.split(".")[-1]
        # Create a simple mock that only has the run method
        class MockModule:
            def __init__(self):
                if tool_name == "course_search":
                    self.run = failing_tool
                else:
                    self.run = slow_tool
            def __getattr__(self, name):
                # Return None for any attribute that _find_tool_object might look for
                return None
        return MockModule()
    
    nodes = [
        {"id": "fail", "tool": "course_search", "args": {"query": "test"}, "depends_on": []},
        {"id": "slow", "tool": "faq_search", "args": {"query": "test"}, "depends_on": []},
    ]
    
    with patch("agent.executor.importlib.import_module", side_effect=mock_import):
        with pytest.raises(Exception):
            await async_execute(nodes, max_concurrency=2) 