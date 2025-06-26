"""Integration tests for the DAG verification and execution pipeline."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parents[2]  # agent/tests/test_pipeline.py -> TransferAI/
sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup to avoid import errors
from agent.verify_dag import verify_dag  # noqa: E402
from agent.executor import execute, run_plan  # noqa: E402

EXAMPLES = PROJECT_ROOT / "examples"


def load(name):
    """Load a JSON fixture from the examples directory."""
    return json.loads((EXAMPLES / name).read_text())


@pytest.fixture(autouse=True)
def _mock_llm_client(monkeypatch):
    """Mock LLM client to avoid network calls during tests."""
    monkeypatch.setattr(
        "agent.llm_client.chat",
        lambda instructions, context=None, model="gpt-4o", temperature=0.4: "OK",
    )
    monkeypatch.setattr(
        "agent.executor.chat",
        lambda instructions, context=None, model="gpt-4o", temperature=0.4: "OK",
    )


# Test data for parametrized tests
VALID_PLANS = [
    # File-based plan
    pytest.param(
        "file:valid_plan.json",
        {"n1", "n2"},  # expected node IDs
        id="valid_plan_file"
    ),
    # Inline minimal plan with llm_step
    pytest.param(
        [
            {
                "id": "llm_test",
                "tool": "llm_step",
                "args": {"instructions": "Say hello"},
                "depends_on": []
            }
        ],
        {"llm_test"},
        id="inline_llm_step"
    ),
    # Inline plan with tool + llm combination
    pytest.param(
        [
            {
                "id": "search",
                "tool": "course_search",
                "args": {"query": "math"},
                "depends_on": []
            },
            {
                "id": "analyze",
                "tool": "llm_step", 
                "args": {"instructions": "Analyze the search results"},
                "depends_on": ["search"]
            }
        ],
        {"search", "analyze"},
        id="tool_plus_llm"
    )
]


@pytest.mark.parametrize("plan_input,expected_node_ids", VALID_PLANS)
def test_valid_plans_execute_successfully(plan_input: Any, expected_node_ids: set):
    """Test that various valid DAGs can be verified and executed successfully."""
    
    # Load plan data
    if isinstance(plan_input, str) and plan_input.startswith("file:"):
        filename = plan_input[5:]  # Remove "file:" prefix
        nodes = verify_dag(load(filename))
        results = execute(nodes)
    else:
        # Inline plan
        results = run_plan(plan_input)
    
    # Verify all expected nodes executed
    assert set(results.keys()) == expected_node_ids, f"Missing nodes in results: {expected_node_ids - set(results.keys())}"
    
    # Verify no empty results
    for node_id, result in results.items():
        assert result is not None, f"Node {node_id} returned None"
        assert result != {}, f"Node {node_id} returned empty dict"
    
    # Verify LLM steps return text
    for node_id, result in results.items():
        if "text" in result:  # LLM step result
            assert isinstance(result["text"], str), f"LLM node {node_id} didn't return string"
            assert len(result["text"]) > 0, f"LLM node {node_id} returned empty text"


def test_cycle_plan_fails():
    """Test that a cyclic DAG fails verification."""
    with pytest.raises(Exception, match="cycle|acyclic"):
        verify_dag(load("cycle_plan.json"))
