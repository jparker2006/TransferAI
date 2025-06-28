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

import json
from typing import Any, Dict
from pathlib import Path

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
    markdown = chat(instructions=instructions, context=tool_outputs or {})

    return markdown 