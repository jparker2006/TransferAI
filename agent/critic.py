from __future__ import annotations

"""Critic module – rates the Composer's Markdown answer.

The critic LLM evaluates the quality of the generated response using a
checklist derived from ``composer_prompt.xml``.  It returns a numeric score
between 0 and 1 together with a short rationale so that the pipeline can decide
whether to retry composition.
"""

from pathlib import Path
import argparse
import json
import sys
from typing import Dict, Any

from agent.llm_client import chat

# ---------------------------------------------------------------------------
# Prompt loading ------------------------------------------------------------
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent
_CHECKER_PROMPT_XML = _PROJECT_ROOT / "agent" / "checker_prompt.xml"
_CHECKER_PROMPT_TXT = _PROJECT_ROOT / "agent" / "checker_prompt.txt"  # legacy
_COMPOSER_PROMPT_PATH = _PROJECT_ROOT / "agent" / "composer_prompt.xml"  # fallback


def _load_quality_checklist() -> str:
    """Extract the <checklist>…</checklist> section from the composer prompt.

    For simplicity we load the whole file and use it verbatim as context.  In
    the future we could parse the XML properly.
    """

    if _CHECKER_PROMPT_XML.exists():
        return _CHECKER_PROMPT_XML.read_text(encoding="utf-8")

    if _CHECKER_PROMPT_TXT.exists():
        return _CHECKER_PROMPT_TXT.read_text(encoding="utf-8")

    if _COMPOSER_PROMPT_PATH.exists():
        return _COMPOSER_PROMPT_PATH.read_text(encoding="utf-8")

    raise FileNotFoundError("Neither checker_prompt.txt nor composer_prompt.xml found for critic.")


_QUALITY_CHECKLIST = _load_quality_checklist()


# ---------------------------------------------------------------------------
# Public API ----------------------------------------------------------------
# ---------------------------------------------------------------------------

def score(markdown: str, summary_json: str, model: str = "gpt-3.5-turbo") -> Dict[str, Any]:
    """Return a quality score in \[0,1].

    The LL.M is instructed to respond with a JSON object:
    ``{"score": <float 0-1>, "rationale": "..."}``

    In offline environments (no OpenAI/ key) a stub result is returned instead
    so that unit tests and CI remain functional.
    """

    system_prompt = (
        "You are TransferAI's *Critic*.  Given a Markdown answer produced by the "
        "Composer and the structured summary of tool outputs, assess the answer "
        "on the following checklist (taken from the Composer prompt).  Return a "
        "JSON object with exactly two keys: 'score' (0-1 float) and 'rationale' "
        "(short sentence).  Use the full checklist as evaluation criteria.  "
        "Do NOT wrap JSON in markdown fences."
    )

    user_content = (
        f"## QUALITY CHECKLIST\n{_QUALITY_CHECKLIST}\n\n"
        f"## SUMMARY JSON\n{summary_json}\n\n"
        f"## MARKDOWN ANSWER\n{markdown}"
    )

    try:
        reply = chat(instructions=system_prompt + "\n\n" + user_content, context={})
        # Attempt to parse JSON reply
        result = json.loads(reply.strip())
        if not (isinstance(result, dict) and "score" in result):
            raise ValueError("Critic response missing required keys")
        # Clamp score into 0-1 range just in case
        result["score"] = max(0.0, min(1.0, float(result["score"])))
        return result  # type: ignore[return-value]
    except Exception as exc:  # noqa: BLE001
        # Offline / parsing failure fallback
        return {"score": 0.5, "rationale": f"<offline stub: {exc}>"}


# ---------------------------------------------------------------------------
# CLI -----------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="agent.critic",
        description="Score a Markdown answer against the tool summary JSON.",
    )
    parser.add_argument("answer_md", help="Path to Markdown answer file.")
    parser.add_argument("summary_json", help="Path to summary JSON file.")
    return parser.parse_args(argv)


def _cli_main(argv: list[str] | None = None) -> None:  # pragma: no cover
    args = _parse_args(argv)

    try:
        markdown = Path(args.answer_md).read_text(encoding="utf-8")
        summary_json_str = Path(args.summary_json).read_text(encoding="utf-8")
    except OSError as exc:
        sys.exit(f"[critic] Failed to read input files: {exc}")

    result = score(markdown, summary_json_str)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    _cli_main() 