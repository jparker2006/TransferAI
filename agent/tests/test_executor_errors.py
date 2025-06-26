"""Error handling tests for the DAG executor.

Tests various failure modes including unknown tools, schema validation errors,
and LLM client failures to ensure proper error propagation and handling.
"""

import json
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from agent import executor as ex  # noqa: E402
from agent.executor import ExecutorError  # noqa: E402
from agent.verify_dag import DAGValidationError  # noqa: E402


def _run_plan(plan):
    """Helper to run a plan from list format."""
    return ex.run_plan(plan)


def test_unknown_tool_fails():
    """Test that unknown tool names raise appropriate errors."""
    plan = [
        {
            "id": "unknown",
            "tool": "does_not_exist_tool",
            "args": {},
            "depends_on": []
        }
    ]
    
    with pytest.raises(ExecutorError, match="DAG validation failed"):
        _run_plan(plan)


def test_bad_tool_args_fail_validation():
    """Test that invalid tool arguments fail schema validation."""
    plan = [
        {
            "id": "bad_args",
            "tool": "course_detail",
            "args": {},  # Missing required 'course_code'
            "depends_on": []
        }
    ]
    
    with pytest.raises(ExecutorError, match="DAG validation failed"):
        _run_plan(plan)


def test_invalid_query_args():
    """Test course_search with invalid query type."""
    plan = [
        {
            "id": "bad_query",
            "tool": "course_search",
            "args": {"query": 123},  # Should be string, not int
            "depends_on": []
        }
    ]
    
    with pytest.raises(ExecutorError, match="DAG validation failed"):
        _run_plan(plan)


def test_llm_client_exception_propagates(monkeypatch):
    """Test that LLM client exceptions are properly handled."""
    # Mock chat to raise an exception that doesn't match the fallback patterns
    def failing_chat(*args, **kwargs):
        raise RuntimeError("Custom LLM error")
    
    monkeypatch.setattr("agent.llm_client.chat", failing_chat)
    monkeypatch.setattr("agent.executor.chat", failing_chat)
    
    plan = [
        {
            "id": "failing_llm",
            "tool": "llm_step",
            "args": {"instructions": "This will fail"},
            "depends_on": []
        }
    ]
    
    with pytest.raises(ExecutorError, match="LLM call failed"):
        _run_plan(plan)


def test_llm_openai_missing_graceful_fallback(monkeypatch):
    """Test that missing OpenAI package falls back gracefully."""
    # Mock chat to raise an ImportError with 'openai' in the message
    def openai_missing_chat(*args, **kwargs):
        raise ImportError("The 'openai' package is required for LLM execution")
    
    monkeypatch.setattr("agent.llm_client.chat", openai_missing_chat)
    monkeypatch.setattr("agent.executor.chat", openai_missing_chat)
    
    plan = [
        {
            "id": "missing_openai",
            "tool": "llm_step",
            "args": {"instructions": "Should fallback"},
            "depends_on": []
        }
    ]
    
    results = _run_plan(plan)
    assert results["missing_openai"]["text"] == "<llm unavailable>"


def test_llm_api_key_missing_graceful_fallback(monkeypatch):
    """Test that missing API key falls back gracefully."""
    # Mock chat to raise a RuntimeError with API key message
    def api_key_missing_chat(*args, **kwargs):
        raise RuntimeError("OPENAI_API_KEY is not set. Create a .env file")
    
    monkeypatch.setattr("agent.llm_client.chat", api_key_missing_chat)
    monkeypatch.setattr("agent.executor.chat", api_key_missing_chat)
    
    plan = [
        {
            "id": "missing_key",
            "tool": "llm_step", 
            "args": {"instructions": "Should fallback"},
            "depends_on": []
        }
    ]
    
    results = _run_plan(plan)
    assert results["missing_key"]["text"] == "<llm unavailable>"


def test_tool_import_error():
    """Test handling of tool import failures."""
    plan = [
        {
            "id": "import_fail",
            "tool": "nonexistent_module_tool",
            "args": {},
            "depends_on": []
        }
    ]
    
    # This should fail at the validation stage with unknown tool
    with pytest.raises(ExecutorError, match="DAG validation failed"):
        _run_plan(plan)


def test_malformed_node_structure():
    """Test handling of malformed node structures."""
    # Missing required 'id' field
    plan = [
        {
            "tool": "course_search",
            "args": {"query": "test"},
            "depends_on": []
        }
    ]
    
    with pytest.raises(ExecutorError, match="DAG validation failed"):
        _run_plan(plan)


def test_circular_dependency_detection():
    """Test that circular dependencies are detected."""
    plan = [
        {
            "id": "node_a",
            "tool": "course_search",
            "args": {"query": "test"},
            "depends_on": ["node_b"]
        },
        {
            "id": "node_b", 
            "tool": "course_detail",
            "args": {"course_code": "CS 101"},
            "depends_on": ["node_a"]  # Creates cycle: A -> B -> A
        }
    ]
    
    with pytest.raises(ExecutorError, match="DAG validation failed"):
        _run_plan(plan) 