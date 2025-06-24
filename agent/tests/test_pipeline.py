"""Integration tests for the DAG verification and execution pipeline."""

import json
import sys
from pathlib import Path
import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parents[2]  # agent/tests/test_pipeline.py -> TransferAI/
sys.path.insert(0, str(PROJECT_ROOT))

# Import after path setup to avoid import errors
from agent.verify_dag import verify_dag  # noqa: E402
from agent.executor import execute  # noqa: E402

EXAMPLES = PROJECT_ROOT / "examples"


def load(name):
    """Load a JSON fixture from the examples directory."""
    return json.loads((EXAMPLES / name).read_text())


def test_valid_plan_runs():
    """Test that a valid DAG can be verified and executed successfully."""
    nodes = verify_dag(load("valid_plan.json"))
    results = execute(nodes)
    assert "n2" in results, "LLM step did not run"


def test_cycle_plan_fails():
    """Test that a cyclic DAG fails verification."""
    with pytest.raises(Exception):
        verify_dag(load("cycle_plan.json"))
