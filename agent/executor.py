"""TransferAI DAG Executor.

Production-ready topological executor that validates DAG nodes via verify_dag(),
dispatches tool calls, and returns results keyed by node_id.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path for imports when run as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agent.verify_dag import verify_dag
else:
    from .verify_dag import verify_dag


class ExecutorError(Exception):
    """Raised when execution fails with node context."""

    def __init__(self, message: str, node_id: str, original_exc: Exception) -> None:
        """Initialize executor error with context.

        Args:
            message: Error description
            node_id: ID of the failing node
            original_exc: The underlying exception that caused the failure
        """
        super().__init__(message)
        self.node_id = node_id
        self.original_exc = original_exc


def execute(
    nodes: List[Dict[str, Any]],
    initial_context: Optional[Dict[str, Any]] = None,
    stream: bool = False,
) -> Dict[str, Any]:
    """Execute a DAG of tool nodes topologically.

    Args:
        nodes: List of DAG nodes (may be unsorted)
        initial_context: Future context injection (currently unused)
        stream: If True, prints progress as "RUN node_id ... ✅"

    Returns:
        Dictionary mapping node_id -> tool output

    Raises:
        ExecutorError: If any node fails to execute
    """
    # Validate and topologically sort the nodes
    try:
        sorted_nodes = verify_dag(nodes)
    except Exception as exc:
        raise ExecutorError("DAG validation failed", "validation", exc) from exc

    results: Dict[str, Any] = {}

    for node in sorted_nodes:
        node_id = node["id"]
        tool_name = node["tool"]
        args = node.get("args", {})

        try:
            if tool_name == "llm_step":
                # Special case: LLM steps return placeholder for now
                output = {"output": "<llm placeholder – not implemented>"}
            else:
                # Import and dispatch to actual tool
                module_name = f"tools.{tool_name}"
                try:
                    module = importlib.import_module(module_name)
                except ImportError as import_exc:
                    raise ExecutorError(
                        f"Tool module not found: {module_name}",
                        node_id,
                        import_exc,
                    ) from import_exc

                # Try to get run method, fall back to calling module directly
                tool_func = getattr(module, "run", None)
                if tool_func is None:
                    # Look for StructuredTool pattern - try common naming conventions
                    potential_names = [
                        # course_search_tool -> CourseSearchTool
                        f"{tool_name.title().replace('_', '')}Tool",
                        # Alternative naming convention
                        f"{''.join(word.capitalize() for word in tool_name.split('_'))}",
                        tool_name,  # exact match
                    ]

                    tool_obj = None
                    for name in potential_names:
                        tool_obj = getattr(module, name, None)
                        if tool_obj is not None:
                            break

                    if tool_obj is not None and hasattr(tool_obj, "invoke"):
                        # Use invoke method for StructuredTool objects - they take dict input
                        output = tool_obj.invoke(args)
                        tool_func = None  # Skip the generic execution below
                    else:
                        # Fall back to calling module directly
                        tool_func = module

                if tool_func is not None:
                    if not callable(tool_func):
                        raise ExecutorError(
                            f"No callable interface found in {module_name}",
                            node_id,
                            RuntimeError("Tool not callable"),
                        )

                    # Execute the tool with its arguments
                    output = tool_func(**args)

            results[node_id] = output

            if stream:
                print(f"RUN {node_id:<8} ✅")

        except Exception as exc:
            if isinstance(exc, ExecutorError):
                raise
            raise ExecutorError(
                f"Execution failed for node {node_id}",
                node_id,
                exc,
            ) from exc

    return results


if __name__ == "__main__":
    """Demo execution with examples/valid_plan.json if present."""

    plan_path = Path("examples/valid_plan.json")

    if not plan_path.exists():
        print(f"No plan file found at {plan_path}")
        exit(1)

    try:
        with plan_path.open("r", encoding="utf-8") as f:
            plan_nodes = json.load(f)

        print("Executing plan with streaming enabled...")
        results = execute(plan_nodes, stream=True)

        print("\nFinal results:")
        print(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    except ExecutorError as exc:
        print(f"Execution failed on node {exc.node_id}: {exc}")
        print(f"Original error: {exc.original_exc}")
        exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        exit(1)
