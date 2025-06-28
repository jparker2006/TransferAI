"""Composer layer – turn structured summaries + raw tool outputs into Markdown answers.

This module keeps *all* LLM-facing logic for the final user-visible answer in
one place so that other parts of the pipeline (planner, executor) remain free
from presentation concerns.

Design goals:
• **Single public entry-point** – :func:`compose`.
• **No hard dependency** on OpenAI during unit tests – the downstream test can
  monkey-patch :pyfunc:`agent.llm_client.chat` to avoid network calls.
• **Markdown output** suitable for direct rendering in a chat UI or GitHub
  markdown viewer.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from agent import helper
from agent.llm_client import chat

# ---------------------------------------------------------------------------
# Prompt loading ------------------------------------------------------------
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_COMPOSER_PROMPT_PATH = _PROJECT_ROOT / "agent" / "composer_prompt.xml"


def _load_composer_prompt() -> str:
    """Load the composer system prompt from XML file."""
    if not _COMPOSER_PROMPT_PATH.exists():
        raise FileNotFoundError(f"Composer prompt not found: {_COMPOSER_PROMPT_PATH}")
    
    return _COMPOSER_PROMPT_PATH.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# Prompt --------------------------------------------------------------------
# ---------------------------------------------------------------------------

# Load the prompt once at module import
_COMPOSER_SYSTEM_PROMPT = _load_composer_prompt()

def compose(summary_json: str, tool_outputs: Dict[str, Any] | None = None) -> str:  # noqa: D401
    """Return a polished Markdown answer.

    Parameters
    ----------
    summary_json:
        A JSON *string* produced by the Helper layer that distils all relevant
        data (e.g. best sections, instructor rankings, conflicts) into a
        structured payload.
    tool_outputs:
        Optional raw tool output dictionary keyed by *node id* or tool name. It
        is passed as *context* so that the LLM can look up extra details when
        crafting the reply, but we avoid bloating the main instructions.
    """

    # Guard: ensure summary_json is indeed JSON – raises early for developer.
    try:
        json.loads(summary_json)
    except ValueError as exc:  # pragma: no cover – developer error
        raise ValueError("summary_json must be valid JSON string") from exc

    # Build instructions with executor results context
    instructions = f"""
{_COMPOSER_SYSTEM_PROMPT}

# EXECUTOR RESULTS
The following data was gathered by our academic planning tools:

{summary_json.strip()}

Please process this information and provide a warm, counselor-style response in Markdown format following the guidelines above.
"""

    # Delegates the heavy lifting to the shared chat helper.
    try:
        markdown = chat(instructions=instructions, context=tool_outputs or {})
    except Exception as exc:  # noqa: BLE001 – any failure -> fallback
        # Mirror Executor's offline fallback strategy so that unit-tests and
        # CLI usage work without OpenAI credentials or network access.
        if "OPENAI_API_KEY" in str(exc) or "openai" in str(type(exc)) or "openai" in str(exc).lower():
            markdown = "## 📋 Your Academic Path Forward\n\n<LLM unavailable in this environment>"
        else:
            raise

    return markdown

def compose_from_execution(question: str, results: Dict[str, Any]) -> str:  # noqa: D401
    """High-level convenience wrapper.

    Parameters
    ----------
    question
        The original user question. Currently unused by the underlying
        :func:`compose` implementation but kept for future prompt
        conditioning.
    results
        Raw Executor node-id → output mapping.

    Returns
    -------
    str
        A Markdown answer produced by the Composer LLM.
    """

    # Merge tool outputs using Helper layer
    summary_json: str = helper.merge_results(results)

    # Delegate to existing composer logic
    markdown: str = compose(summary_json, tool_outputs=results)

    return markdown

# ---------------------------------------------------------------------------
# CLI -----------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent.composer",
        description="Generate a Markdown answer from Executor results JSON.",
    )
    parser.add_argument("results_path", help="Path to Executor results JSON file.")
    parser.add_argument(
        "--question",
        required=True,
        help="Original user question (quoted).",
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="PATH",
        help="Optional file path for the generated Markdown. Print to stdout if omitted.",
    )
    return parser.parse_args(argv)

def _cli_main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    results_file = Path(args.results_path)
    if not results_file.exists():
        sys.exit(f"[composer] Results file not found: {results_file}")

    try:
        with results_file.open("r", encoding="utf-8") as fp:
            results = json.load(fp)
    except (json.JSONDecodeError, OSError) as exc:
        sys.exit(f"[composer] Failed to read results JSON: {exc}")

    try:
        markdown = compose_from_execution(args.question, results)
    except Exception as exc:  # pragma: no cover
        sys.exit(f"[composer] {exc}")

    if args.output:
        try:
            Path(args.output).write_text(markdown, encoding="utf-8")
        except OSError as exc:
            sys.exit(f"[composer] Failed to write Markdown: {exc}")
    else:
        print(markdown)

if __name__ == "__main__":  # pragma: no cover
    _cli_main() 