#!/usr/bin/env python3
"""Generate the <AvailableTools> section of agent/planner_prompt.xml.

This helper introspects every StructuredTool declared in the ``tools`` package and
emits XML describing each tool, including an example that lists **all** accepted
argument keys.  Run the script and redirect output into the desired prompt file,
for example:

    python scripts/build_planner_prompt.py > agent/planner_prompt.xml

A more sophisticated pipeline could merge this output with the static parts of
``planner_prompt.xml`` (Role, NodeSchema, etc.), but this standalone generator
handles the part that is most prone to drift – the tool metadata.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Dict, List

# ---------------------------------------------------------------------------
# Constants -----------------------------------------------------------------
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = PROJECT_ROOT / "tools"

# Insert project root into sys.path so we can import tool modules regardless of
# the caller's CWD.
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _iter_tool_objects():  # noqa: D401
    """Yield every StructuredTool instance found in ``tools`` modules."""

    try:
        from langchain.tools import StructuredTool  # noqa: WPS433 (third-party import)
    except ImportError as exc:  # pragma: no cover – should be installed in runtime
        raise RuntimeError(
            "langchain is required to introspect StructuredTool objects. Install with: pip install langchain"
        ) from exc

    for py_file in TOOLS_DIR.glob("*_tool.py"):
        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:  # type: ignore[truthy-iterable]
            module = importlib.util.module_from_spec(spec)
            # Manually register the module in sys.modules *before* execution so that
            # runtime helpers (e.g., ``dataclasses``) can resolve the partially
            # initialised module during class decoration.
            sys.modules[module_name] = module  # type: ignore[assignment]
            spec.loader.exec_module(module)  # type: ignore[arg-type]
        else:  # pragma: no cover – unlikely but defensive
            continue

        for attr_name, attr_value in vars(module).items():
            if isinstance(attr_value, (StructuredTool,)):
                yield attr_value


def _json_placeholder(json_type: str | List[str]) -> str:  # noqa: D401, C901
    """Return a placeholder JSON value for a given schema type."""

    # If ``type`` is a list, take the first entry for placeholder purposes.
    if isinstance(json_type, list):
        json_type = json_type[0]

    match json_type:  # noqa: WPS523 – modern Python match-case
        case "string":
            return '"<string>"'
        case "integer" | "number":
            return "0"
        case "boolean":
            return "false"
        case "array":
            return "[]"
        case "object":
            return "{}"
        case _:
            return "null"  # Fallback for unknown/complex types


def _generate_example(args_schema: Dict) -> str:  # noqa: D401
    """Build a JSON example string that includes **all** accepted keys."""

    properties = args_schema.get("properties", {})

    # Preserve property order for readability.
    parts: List[str] = []
    for key, spec in properties.items():
        placeholder = _json_placeholder(spec.get("type", "string"))
        parts.append(f'"{key}": {placeholder}')

    joined = ", ".join(parts)
    return f"{{ {joined} }}" if joined else "{}"


def _xml_escape(text: str) -> str:  # noqa: D401
    """Escape characters that are special in XML."""

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&apos;")
    )


# ---------------------------------------------------------------------------
# Block generation ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _build_available_tools_block() -> str:  # noqa: D401
    """Return the full <AvailableTools> ... </AvailableTools> XML block as a string."""

    tool_objects = sorted(_iter_tool_objects(), key=lambda t: t.name)

    lines: List[str] = []
    lines.append("<AvailableTools>")
    lines.append("  <![CDATA[")
    lines.append(
        "The following tools are auto-generated from the codebase. Each tool shows its name, description, and an example containing all accepted argument keys."
    )
    lines.append("  ]]>")

    for tool in tool_objects:
        description_xml = _xml_escape(tool.description.strip())
        args_schema_dict = tool.args_schema.model_json_schema()  # type: ignore[attr-defined]
        example_json = _generate_example(args_schema_dict)

        allowed_keys = ", ".join(args_schema_dict.get("properties", {}).keys())

        lines.append(f'  <Tool name="{tool.name}">')
        lines.append(f"    <Description>{description_xml}</Description>")
        lines.append(f"    <Example>{example_json}</Example>")
        lines.append(f"    <!-- Allowed keys: {allowed_keys} -->")
        lines.append("  </Tool>")

    lines.append("</AvailableTools>")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main ----------------------------------------------------------------------
# ---------------------------------------------------------------------------


def main() -> None:  # noqa: D401
    """Generate <AvailableTools> block and optionally inject into planner prompt."""

    import argparse

    parser = argparse.ArgumentParser(description="Generate or update the AvailableTools block in planner_prompt.xml")
    parser.add_argument(
        "--inplace",
        action="store_true",
        help="Replace the <AvailableTools>...</AvailableTools> block inside agent/planner_prompt.xml",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        default=PROJECT_ROOT / "agent" / "planner_prompt.xml",
        help="Path to planner_prompt.xml (only used with --inplace)",
    )

    args = parser.parse_args()

    new_block = _build_available_tools_block()

    if args.inplace:
        prompt_path: Path = args.prompt_path
        if not prompt_path.exists():
            raise FileNotFoundError(f"planner prompt not found: {prompt_path}")

        original_text = prompt_path.read_text(encoding="utf-8")

        # Use simple string locators – assume only one AvailableTools block.
        start_tag = "<AvailableTools>"
        end_tag = "</AvailableTools>"

        start_idx = original_text.find(start_tag)
        end_idx = original_text.find(end_tag)

        if start_idx == -1 or end_idx == -1:
            raise RuntimeError("Could not locate <AvailableTools> block in prompt file")

        end_idx += len(end_tag)  # include closing tag

        updated_text = original_text[:start_idx] + new_block + original_text[end_idx:]

        prompt_path.write_text(updated_text, encoding="utf-8")
        print(f"✅ Updated AvailableTools block in {prompt_path}")
    else:
        # Print to stdout (no XML header) so caller can redirect if desired.
        print(new_block)


if __name__ == "__main__":  # pragma: no cover – entry point
    main() 