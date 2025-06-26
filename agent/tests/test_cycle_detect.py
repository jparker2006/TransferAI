"""Cycle detection tests for DAG verification.

Tests that the verify_dag function properly detects and rejects cyclic
dependencies in execution plans.
"""

import json
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from agent.verify_dag import verify_dag, DAGValidationError  # noqa: E402

EXAMPLES = PROJECT_ROOT / "examples"


def test_cycle_plan_json_fails():
    """Test that the bundled cycle_plan.json is properly rejected."""
    cycle_plan_path = EXAMPLES / "cycle_plan.json"
    
    if not cycle_plan_path.exists():
        pytest.skip("cycle_plan.json not found in examples/")
    
    with cycle_plan_path.open() as f:
        cycle_nodes = json.load(f)
    
    with pytest.raises(DAGValidationError, match="cycle"):
        verify_dag(cycle_nodes)


def test_simple_two_node_cycle():
    """Test detection of a simple A -> B -> A cycle."""
    cycle_nodes = [
        {
            "id": "node_a",
            "tool": "course_search",
            "args": {"query": "math"},
            "depends_on": ["node_b"]
        },
        {
            "id": "node_b",
            "tool": "course_detail", 
            "args": {"course_code": "MATH 101"},
            "depends_on": ["node_a"]
        }
    ]
    
    with pytest.raises(DAGValidationError, match="cycle"):
        verify_dag(cycle_nodes)


def test_three_node_cycle():
    """Test detection of A -> B -> C -> A cycle."""
    cycle_nodes = [
        {
            "id": "search",
            "tool": "course_search",
            "args": {"query": "physics"},
            "depends_on": ["analyze"]
        },
        {
            "id": "detail",
            "tool": "course_detail",
            "args": {"course_code": "PHYS 101"},
            "depends_on": ["search"]
        },
        {
            "id": "analyze",
            "tool": "llm_step",
            "args": {"instructions": "Analyze results"},
            "depends_on": ["detail"]
        }
    ]
    
    with pytest.raises(DAGValidationError, match="cycle"):
        verify_dag(cycle_nodes)


def test_self_referencing_cycle():
    """Test detection of a node that depends on itself."""
    cycle_nodes = [
        {
            "id": "self_ref",
            "tool": "course_search",
            "args": {"query": "chemistry"},
            "depends_on": ["self_ref"]  # Points to itself
        }
    ]
    
    with pytest.raises(DAGValidationError, match="cycle"):
        verify_dag(cycle_nodes)


def test_complex_cycle_with_valid_branches():
    """Test cycle detection in a more complex graph with valid branches."""
    # Graph: A -> B -> C -> D -> B (cycle)
    #        A -> E (valid branch)
    cycle_nodes = [
        {
            "id": "start",
            "tool": "course_search",
            "args": {"query": "start"},
            "depends_on": []
        },
        {
            "id": "branch_good",
            "tool": "course_detail",
            "args": {"course_code": "GOOD 101"},
            "depends_on": ["start"]
        },
        {
            "id": "cycle_b",
            "tool": "course_search",
            "args": {"query": "cycle_b"},
            "depends_on": ["start", "cycle_d"]  # This creates the cycle: B -> C -> D -> B
        },
        {
            "id": "cycle_c",
            "tool": "course_detail",
            "args": {"course_code": "CYCLE 201"},
            "depends_on": ["cycle_b"]
        },
        {
            "id": "cycle_d",
            "tool": "llm_step",
            "args": {"instructions": "Process cycle_d"},
            "depends_on": ["cycle_c", "cycle_b"]  # Creates cycle: B -> C -> D -> B
        }
    ]
    
    with pytest.raises(DAGValidationError, match="cycle"):
        verify_dag(cycle_nodes)


def test_acyclic_graph_passes():
    """Test that a valid acyclic graph passes verification."""
    acyclic_nodes = [
        {
            "id": "root",
            "tool": "course_search", 
            "args": {"query": "root"},
            "depends_on": []
        },
        {
            "id": "branch_a",
            "tool": "course_detail",
            "args": {"course_code": "BRANCH 101"},
            "depends_on": ["root"]
        },
        {
            "id": "branch_b",
            "tool": "course_detail", 
            "args": {"course_code": "BRANCH 102"},
            "depends_on": ["root"]
        },
        {
            "id": "merge",
            "tool": "llm_step",
            "args": {"instructions": "Merge results"},
            "depends_on": ["branch_a", "branch_b"]
        }
    ]
    
    # Should not raise an exception
    sorted_nodes = verify_dag(acyclic_nodes)
    assert len(sorted_nodes) == 4
    
    # Verify topological ordering (root should come first, merge should come last)
    node_ids = [node["id"] for node in sorted_nodes]
    assert node_ids[0] == "root"
    assert node_ids[-1] == "merge" 