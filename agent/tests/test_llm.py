from __future__ import annotations

"""Unit test for executor – verifies that llm_step nodes call the llm_client.

The test patches :func:`agent.llm_client.chat` so that **no external network** or
API key is required.  This keeps the test-suite offline-safe.
"""

import json
from typing import Any, Dict

import pytest

from agent import executor as ex


@pytest.fixture(autouse=True)
def _isolation(monkeypatch):  # noqa: D401 – fixture auto-used for isolation
    """Patch the chat function globally so tests never hit the real API."""

    monkeypatch.setattr(
        "agent.llm_client.chat",
        lambda instructions, context=None, model="gpt-4o", temperature=0.4: "Hello!",
    )

    # Executor imported the chat symbol at module-import time – patch it too
    monkeypatch.setattr(
        "agent.executor.chat",
        lambda instructions, context=None, model="gpt-4o", temperature=0.4: "Hello!",
    )


def test_llm_step_basic() -> None:  # noqa: D401
    """A single llm_step should return the mocked response."""

    plan = [
        {
            "id": "greet",
            "tool": "llm_step",
            "args": {"instructions": "Say hi"},
            # *depends_on* intentionally left out – run_plan should normalise it.
        }
    ]

    results: Dict[str, Any] = ex.run_plan(plan)

    assert results["greet"]["text"] == "Hello!", "LLM response mismatch" 