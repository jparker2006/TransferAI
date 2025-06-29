"""TransferAI DAG Executor.

Production-ready topological executor that validates DAG nodes via verify_dag(),
dispatches tool calls, and returns results keyed by node_id.
"""

from __future__ import annotations

import importlib
import json
import sys
import asyncio
import os
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, NamedTuple
from agent.llm_client import chat

# Add project root to path for imports when run as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from agent.verify_dag import verify_dag
else:
    from .verify_dag import verify_dag


# ---------------------------------------------------------------------------
# Event bus for parallel execution tracking ----------------------------------
# ---------------------------------------------------------------------------


class TaskEvent(NamedTuple):
    type: str  # "started" or "finished"
    node_id: str


_EVENT_BUS: Optional[asyncio.Queue[TaskEvent]] = None


def get_event_bus() -> asyncio.Queue[TaskEvent]:
    """Return the shared event bus for parallel execution tracking."""
    global _EVENT_BUS
    if _EVENT_BUS is None:
        _EVENT_BUS = asyncio.Queue()
    return _EVENT_BUS


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


def _resolve_tool_module(tool_name: str) -> Any:
    """Resolve tool name to module, handling both naming patterns.
    
    Args:
        tool_name: Tool name from DAG node (e.g., "course_search" or "course_search_tool")
        
    Returns:
        Imported module object
        
    Raises:
        ImportError: If no module can be found for the tool name
    """
    # Try multiple module name patterns
    module_patterns = [
        f"tools.{tool_name}",  # Direct match (e.g., tools.course_search)
        f"tools.{tool_name}_tool",  # Add _tool suffix (e.g., tools.course_search_tool)
    ]
    
    # If tool_name already ends with _tool, also try without it
    if tool_name.endswith("_tool"):
        base_name = tool_name[:-5]  # Remove "_tool" suffix
        module_patterns.insert(1, f"tools.{base_name}")
    
    last_exc = None
    for pattern in module_patterns:
        try:
            return importlib.import_module(pattern)
        except ImportError as exc:
            last_exc = exc
            continue
    
    # If all patterns failed, raise the last exception
    available_patterns = ", ".join(module_patterns)
    raise ImportError(f"Could not import tool module. Tried: {available_patterns}") from last_exc


def _find_tool_object(module: Any, tool_name: str) -> Any:
    """Find the StructuredTool object in a module using various naming conventions.
    
    Args:
        module: Imported module object
        tool_name: Original tool name from DAG node
        
    Returns:
        StructuredTool object or None if not found
    """
    # Generate potential StructuredTool object names
    base_name = tool_name.replace("_tool", "") if tool_name.endswith("_tool") else tool_name
    
    potential_names = [
        # CourseSearchTool pattern
        f"{''.join(word.capitalize() for word in base_name.split('_'))}Tool",
        # course_search_tool -> CourseSearchTool (if original had _tool)
        f"{''.join(word.capitalize() for word in tool_name.split('_'))}",
        # Exact matches
        tool_name,
        base_name,
        # MajorRequirementTool (special case)
        f"{''.join(word.capitalize() for word in tool_name.split('_'))}",
    ]
    
    for name in potential_names:
        tool_obj = getattr(module, name, None)
        if tool_obj is not None and hasattr(tool_obj, "invoke"):
            return tool_obj
    
    return None


async def async_execute(
    nodes: List[Dict[str, Any]],
    initial_context: Optional[Dict[str, Any]] = None,
    stream: bool = False,
    max_concurrency: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a DAG of tool nodes with async parallelism.

    Args:
        nodes: List of DAG nodes (may be unsorted)
        initial_context: Future context injection (currently unused)
        stream: If True, emits TaskStarted/TaskFinished events
        max_concurrency: Max concurrent tasks (default from MAX_CONCURRENCY env or 4)

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

    if max_concurrency is None:
        max_concurrency = int(os.getenv("MAX_CONCURRENCY", "4"))

    # Build dependency tracking
    node_map = {node["id"]: node for node in sorted_nodes}
    dep_count = {node["id"]: len(node.get("depends_on", [])) for node in sorted_nodes}
    children = defaultdict(list)
    for node in sorted_nodes:
        for dep in node.get("depends_on", []):
            children[dep].append(node["id"])

    results: Dict[str, Any] = {}
    ready = {node_id for node_id, count in dep_count.items() if count == 0}
    running = set()
    event_bus = get_event_bus() if stream else None

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _execute_node(node_id: str) -> None:
        async with semaphore:
            if event_bus:
                await event_bus.put(TaskEvent("started", node_id))

            try:
                node = node_map[node_id]
                tool_name = node["tool"]
                args = node.get("args", {})

                if tool_name == "llm_step":
                    # LLM reasoning step
                    prompt: str = args.get("instructions", "")
                    try:
                        output_text = chat(prompt, context=results)
                    except Exception as exc:
                        if "OPENAI_API_KEY" in str(exc) or "openai" in str(type(exc)):
                            output_text = "<llm unavailable>"
                        elif "openai" in str(exc).lower():
                            output_text = "<llm unavailable>"
                        else:
                            raise ExecutorError("LLM call failed", node_id, exc) from exc
                    output = {"text": output_text}
                else:
                    # Tool execution
                    try:
                        module = _resolve_tool_module(tool_name)
                    except ImportError as import_exc:
                        raise ExecutorError(
                            f"Tool module not found for '{tool_name}'", node_id, import_exc
                        ) from import_exc

                    tool_obj = _find_tool_object(module, tool_name)
                    if tool_obj is not None:
                        result = tool_obj.invoke(args)
                        if asyncio.iscoroutine(result):
                            output = await result
                        else:
                            output = result
                    else:
                        tool_func = getattr(module, "run", None)
                        if tool_func is None:
                            tool_func = module
                        if not callable(tool_func):
                            raise ExecutorError(
                                f"No callable interface found for tool '{tool_name}'",
                                node_id,
                                RuntimeError("Tool not callable"),
                            )
                        result = tool_func(**args)
                        if asyncio.iscoroutine(result):
                            output = await result
                        else:
                            output = result

                results[node_id] = output

            except Exception as exc:
                if isinstance(exc, ExecutorError):
                    raise
                raise ExecutorError(f"Execution failed for node {node_id}", node_id, exc) from exc
            finally:
                if event_bus:
                    await event_bus.put(TaskEvent("finished", node_id))

    # Main execution loop
    while ready or running:
        # Start all ready tasks
        tasks = []
        for node_id in list(ready):
            ready.remove(node_id)
            running.add(node_id)
            task = asyncio.create_task(_execute_node(node_id))
            tasks.append((node_id, task))

        if not tasks:
            # Wait for at least one running task to complete
            if running:
                await asyncio.sleep(0.01)
                continue
            else:
                break

        # Wait for tasks to complete
        for node_id, task in tasks:
            try:
                await task
                running.remove(node_id)

                # Release children
                for child_id in children[node_id]:
                    dep_count[child_id] -= 1
                    if dep_count[child_id] == 0:
                        ready.add(child_id)

            except Exception:
                # Cancel all running tasks and re-raise
                for _, t in tasks:
                    if not t.done():
                        t.cancel()
                raise

    return results


def execute(
    nodes: List[Dict[str, Any]],
    initial_context: Optional[Dict[str, Any]] = None,
    stream: bool = False,
    max_concurrency: Optional[int] = None,
) -> Dict[str, Any]:
    """Execute a DAG of tool nodes (sync wrapper for async_execute).

    Args:
        nodes: List of DAG nodes (may be unsorted)
        initial_context: Future context injection (currently unused)
        stream: If True, prints progress as "RUN node_id ... ✅"
        max_concurrency: Max concurrent tasks (default from env or 4)

    Returns:
        Dictionary mapping node_id -> tool output

    Raises:
        ExecutorError: If any node fails to execute
    """
    results = asyncio.run(async_execute(nodes, initial_context, stream, max_concurrency))
    
    if stream:
        # Print legacy progress messages for compatibility
        for node_id in results:
            print(f"RUN {node_id:<8} ✅")
    
    return results


if __name__ == "__main__":
    """Execute a plan from a JSON file.
    
    Usage:
        python -m agent.executor [plan_file.json]
        
    If no file is specified, defaults to examples/valid_plan.json
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="agent.executor",
        description="Validate and execute a plan, optionally saving results.",
    )
    parser.add_argument(
        "plan_file",
        nargs="?",
        default="examples/valid_plan.json",
        help="Path to plan JSON file (default: examples/valid_plan.json)",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="If provided, write execution results to this JSON file instead of stdout.",
    )
    parser.add_argument(
        "--max-concurrency",
        type=int,
        metavar="N",
        help="Maximum number of concurrent tasks (default: env MAX_CONCURRENCY or 4)",
    )

    args = parser.parse_args()

    plan_path = Path(args.plan_file)

    if not plan_path.exists():
        print(f"No plan file found at {plan_path}")
        exit(1)

    try:
        with plan_path.open("r", encoding="utf-8") as f:
            plan_nodes = json.load(f)

        print("Executing plan with streaming enabled...")
        results = execute(plan_nodes, stream=True, max_concurrency=args.max_concurrency)

        if args.output:
            try:
                Path(args.output).write_text(
                    json.dumps(results, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                print(f"\nResults written to {args.output}")
            except OSError as exc:
                print(f"Failed to write results to {args.output}: {exc}")
                exit(1)
        else:
            print("\nFinal results:")
            print(json.dumps(results, indent=2, ensure_ascii=False, default=str))

    except ExecutorError as exc:
        print(f"Execution failed on node {exc.node_id}: {exc}")
        print(f"Original error: {exc.original_exc}")
        exit(1)
    except Exception as exc:
        print(f"Unexpected error: {exc}")
        exit(1)


# ---------------------------------------------------------------------------
# Convenience helper used by unit-tests ------------------------------------
# ---------------------------------------------------------------------------


def run_plan(plan_json_or_nodes: "str | List[Dict[str, Any]]", *, stream: bool = False):
    """Validate & execute a plan provided as JSON string or list of nodes.

    The helper normalises missing *depends_on* fields to an empty list so that
    ad-hoc test fixtures are less verbose.
    """

    if isinstance(plan_json_or_nodes, str):
        nodes = json.loads(plan_json_or_nodes)
    else:
        nodes = plan_json_or_nodes

    # Ensure mandatory key exists (unit-test convenience)
    for node in nodes:
        node.setdefault("depends_on", [])

    return execute(nodes, stream=stream)
