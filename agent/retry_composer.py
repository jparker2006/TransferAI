from __future__ import annotations

"""Retry-aware composer wrapper.

If the Critic is not satisfied with the first Composer draft (score < threshold)
we invoke the Composer one more time (up to *max_retries*).
"""

from typing import Any, Dict

from agent import helper
from agent import critic  # type: ignore  # circular import avoided in runtime
from agent import composer as base_composer


def compose_with_retry(
    question: str,
    results: Dict[str, Any],
    *,
    threshold: float = 0.8,
    max_retries: int = 1,
) -> str:
    """Return a Markdown answer that passes the Critic threshold.

    Parameters
    ----------
    question
        Original user question – forwarded to Composer.
    results
        Executor results mapping.
    threshold
        Minimum acceptable critic score (\[0,1]).
    max_retries
        Number of additional Composer attempts allowed after the first draft.
    """

    attempt = 0
    while True:
        markdown = base_composer.compose_from_execution(question, results)

        # Evaluate with critic
        summary_json = helper.merge_results(results)
        critique = critic.score(markdown, summary_json)
        score = float(critique.get("score", 0.0))

        if score >= threshold or attempt >= max_retries:
            # Embed critic metadata as comment for transparency
            markdown += f"\n\n<!-- critic_score={score:.2f} retries={attempt} -->"
            return markdown

        attempt += 1 