from __future__ import annotations

"""Helper module that merges individual tool outputs into a canonical summary JSON.

This is part of the TransferAI "LLM Compiler" pipeline:
Planner → Executor → Helper (this module) → Composer → …

Public API
----------
merge_results(results: Dict[str, Any], schema_version: str = "0.1") -> str
    Merge a mapping of node-id → raw tool output into a JSON string that conforms
    to ``schemas/summary.schema.json``.  The function relies on optional
    per-tool merger helpers located under ``agent.helpers.<tool_name>``.

CLI
---
The module can also be invoked from the command line for ad-hoc usage::

    python -m agent.helper path/to/execution_results.json -o summary.json

The input file must contain a JSON object in the same shape expected by
``merge_results``.
"""

from pathlib import Path
import argparse
import importlib
import json
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict

import jsonschema

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class HelperError(Exception):
    """Raised when summary construction or validation fails."""


# ---------------------------------------------------------------------------
# Internal helper loading
# ---------------------------------------------------------------------------


def _load_tool_merger(tool_name: str) -> Callable[[Any], Any]:
    """Return a *merge* function for the given tool.

    The function looks for a module ``agent.helpers.<tool_name>`` that exports a
    callable named ``merge``.  If the module or attribute is missing, it falls
    back to :func:`_default_merge` which returns the raw output verbatim (or
    attempts to parse JSON strings).
    """

    try:
        module = importlib.import_module(f"agent.helpers.{tool_name}")
        merge_fn = getattr(module, "merge", None)
        if callable(merge_fn):
            return merge_fn  # type: ignore[return-value]
    except ModuleNotFoundError:
        # No custom merger – fall back to default
        pass

    return _default_merge


# ---------------------------------------------------------------------------
# Default merge strategy
# ---------------------------------------------------------------------------


def _default_merge(raw_output: Any) -> Any:  # noqa: ANN401 – tool outputs are arbitrary
    """Fallback merge implementation.

    • If *raw_output* is a ``str`` we *try* to JSON-decode it; on failure we
      return the original string.
    • Otherwise we return *raw_output* unchanged.
    """

    if isinstance(raw_output, str):
        try:
            return json.loads(raw_output)
        except json.JSONDecodeError:
            return raw_output
    return raw_output


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def merge_results(results: Dict[str, Any], schema_version: str = "0.1") -> str:
    """Merge *results* → canonical JSON string.

    Parameters
    ----------
    results
        Mapping from *node_id* to raw tool output as returned by the Executor.
    schema_version
        Version string to embed in the generated metadata. Defaults to "0.1".

    Returns
    -------
    str
        A *UTF-8* JSON-encoded string that validates against
        ``schemas/summary.schema.json``.

    Raises
    ------
    ValueError
        If *results* is empty.
    HelperError
        If validation against the schema fails or the schema file cannot be
        located.
    """

    if not results:
        raise ValueError("Results mapping must not be empty.")

    merged_results: Dict[str, Any] = {}

    for node_id, raw_output in results.items():
        # Heuristic: tool name precedes an optional "#" suffix (node index).
        tool_name = node_id.split("#", 1)[0]

        merger_fn = _load_tool_merger(tool_name)
        merged_output = merger_fn(raw_output)

        if tool_name in merged_results:
            # Consolidate multiple nodes for the same tool into a list.
            existing = merged_results[tool_name]
            if isinstance(existing, list):
                existing.append(merged_output)
            else:
                merged_results[tool_name] = [existing, merged_output]
        else:
            merged_results[tool_name] = merged_output

    summary = {
        "merged_results": merged_results,
        "metadata": {
            "tool_count": len(merged_results),
            "generated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "schema_version": schema_version,
        },
    }

    # ---------------------------------------------------------------------
    # Validate summary against JSON schema
    # ---------------------------------------------------------------------
    schema_path = Path(__file__).resolve().parent.parent / "schemas" / "summary.schema.json"
    try:
        with schema_path.open("r", encoding="utf-8") as fp:
            schema = json.load(fp)
        jsonschema.validate(summary, schema)
    except FileNotFoundError as exc:
        raise HelperError(f"Schema file not found: {schema_path}") from exc
    except jsonschema.ValidationError as exc:
        raise HelperError(f"Summary violates schema: {exc.message}") from exc

    return json.dumps(summary, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent.helper",
        description="Merge Executor results JSON into a canonical summary.",
    )
    parser.add_argument(
        "results_path",
        help="Path to a JSON file containing the Executor's node-id → output mapping.",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="Optional file path to write the summary JSON. If omitted, prints to stdout.",
    )
    return parser.parse_args(argv)


def _cli_main(argv: list[str] | None = None) -> None:  # noqa: D401 – imperative mood
    args = _parse_args(argv)
    results_file = Path(args.results_path)

    try:
        with results_file.open("r", encoding="utf-8") as fp:
            results = json.load(fp)
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(f"[helper] Failed to load results JSON: {exc}")

    try:
        summary_json = merge_results(results)
    except (ValueError, HelperError) as exc:
        sys.exit(f"[helper] {exc}")

    if args.output:
        try:
            Path(args.output).write_text(summary_json, encoding="utf-8")
        except OSError as exc:
            sys.exit(f"[helper] Failed to write summary JSON: {exc}")
    else:
        print(summary_json)


if __name__ == "__main__":  # pragma: no cover
    _cli_main() 