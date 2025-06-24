"""TransferAI DAG Verification Module

This module provides comprehensive validation of planner-produced DAGs against
JSON Schemas and structural rules. It ensures DAG integrity before execution.

Key Features:
- Node validation against dag_node.schema.json
- Tool argument validation against tool-specific schemas
- Structural validation (acyclicity, unique IDs, valid dependencies)
- Topological sorting for execution order
"""

import json
from pathlib import Path
from typing import Dict, List

import jsonschema
import networkx as nx


class DAGValidationError(ValueError):
    """Raised when DAG validation fails with detailed error information."""

    def __init__(self, reason: str, node_id: str = None):
        self.reason = reason
        self.node_id = node_id
        super().__init__(reason)


# Load schemas at module level for efficiency
_SCHEMA_ROOT = Path(__file__).parent.parent / "schemas"
DAG_SCHEMA = json.loads((_SCHEMA_ROOT / "dag_node.schema.json").read_text())
TOOL_SCHEMAS = {
    p.stem.replace(".schema", ""): json.loads(p.read_text())
    for p in (_SCHEMA_ROOT / "tools").glob("*.schema.json")
}


def validate_node(node: Dict) -> None:
    """Validate a single DAG node against schemas and constraints.

    Args:
        node: Dictionary representing a DAG node

    Raises:
        DAGValidationError: If node fails validation
    """
    node_id = node.get("id", "<unknown>")

    # Validate against dag_node schema
    try:
        jsonschema.validate(node, DAG_SCHEMA)
    except jsonschema.ValidationError as e:
        raise DAGValidationError(f"Node schema validation failed: {e.message}", node_id)

    tool_name = node.get("tool")
    if not tool_name:
        raise DAGValidationError("Node missing 'tool' field", node_id)

    # Skip tool validation for LLM steps
    if tool_name == "llm_step":
        return

    # Validate tool exists
    if tool_name not in TOOL_SCHEMAS:
        available_tools = sorted(TOOL_SCHEMAS.keys())
        raise DAGValidationError(
            f"Unknown tool '{tool_name}'. Available: {available_tools}", node_id
        )

    # Validate args against tool schema
    tool_schema = TOOL_SCHEMAS[tool_name]
    args = node.get("args", {})

    try:
        jsonschema.validate(args, tool_schema)
    except jsonschema.ValidationError as e:
        raise DAGValidationError(
            f"Tool args validation failed for '{tool_name}': {e.message}", node_id
        )


def verify_dag(nodes: List[Dict]) -> List[Dict]:
    """Verify and topologically sort a complete DAG.

    Args:
        nodes: List of DAG node dictionaries

    Returns:
        Topologically sorted list of valid nodes

    Raises:
        DAGValidationError: If DAG structure is invalid
    """
    if not nodes:
        return []

    # Validate individual nodes
    for node in nodes:
        validate_node(node)

    # Check for unique node IDs
    node_ids = [node["id"] for node in nodes]
    if len(node_ids) != len(set(node_ids)):
        duplicates = [nid for nid in set(node_ids) if node_ids.count(nid) > 1]
        raise DAGValidationError(f"Duplicate node IDs found: {duplicates}")

    # Build ID lookup for dependency validation
    id_set = set(node_ids)

    # Validate dependencies exist
    for node in nodes:
        node_id = node["id"]
        dependencies = node.get("depends_on", [])

        for dep_id in dependencies:
            if dep_id not in id_set:
                raise DAGValidationError(
                    f"Node '{node_id}' depends on non-existent node '{dep_id}'"
                )

    # Build NetworkX graph for cycle detection and topological sort
    graph = nx.DiGraph()

    # Add nodes
    for node in nodes:
        graph.add_node(node["id"], data=node)

    # Add edges (dependencies)
    for node in nodes:
        node_id = node["id"]
        for dep_id in node.get("depends_on", []):
            graph.add_edge(dep_id, node_id)  # dep -> node

    # Check for cycles
    if not nx.is_directed_acyclic_graph(graph):
        cycles = list(nx.simple_cycles(graph))
        raise DAGValidationError(f"DAG contains cycles: {cycles}")

    # Return topologically sorted nodes
    try:
        sorted_ids = list(nx.topological_sort(graph))
        return [graph.nodes[nid]["data"] for nid in sorted_ids]
    except nx.NetworkXError as e:
        raise DAGValidationError(f"Topological sort failed: {e}")


def _create_sample_dag() -> List[Dict]:
    """Create a sample valid DAG for demonstration."""
    return [
        {
            "id": "search_courses",
            "tool": "course_search_tool",
            "args": {"query": "computer science", "top_k": 3},
            "depends_on": []
        },
        {
            "id": "get_details",
            "tool": "course_detail_tool",
            "args": {"course_code": "CS 55"},
            "depends_on": ["search_courses"]
        },
        {
            "id": "analyze_result",
            "tool": "llm_step",
            "args": {"prompt": "Analyze the course details"},
            "depends_on": ["get_details"]
        }
    ]


if __name__ == "__main__":
    print("TransferAI DAG Verification Module")
    print("==================================")

    # Try to load example plan if it exists
    example_path = Path("examples/valid_plan.json")
    if example_path.exists():
        try:
            with example_path.open() as f:
                example_nodes = json.load(f)
            sorted_nodes = verify_dag(example_nodes)
            print(f"✓ Example DAG validated successfully ({len(sorted_nodes)} nodes)")
        except Exception as e:
            print(f"✗ Example DAG validation failed: {e}")
    else:
        # Use built-in sample
        try:
            sample_nodes = _create_sample_dag()
            sorted_nodes = verify_dag(sample_nodes)
            print(f"✓ Sample DAG validated successfully ({len(sorted_nodes)} nodes)")
            print(f"Execution order: {[n['id'] for n in sorted_nodes]}")
        except DAGValidationError as e:
            print(f"✗ Sample DAG validation failed: {e.reason}")

    print(f"\nLoaded {len(TOOL_SCHEMAS)} tool schemas:")
    for tool_name in sorted(TOOL_SCHEMAS.keys()):
        print(f"  - {tool_name}")
