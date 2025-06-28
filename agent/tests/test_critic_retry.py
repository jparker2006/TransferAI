import json
from typing import Any, Dict

import pytest

from agent import critic
from agent import retry_composer


@pytest.fixture
def _stub_chat(monkeypatch):
    """Provide deterministic responses for composer & critic LLM calls."""

    responses = [
        "DRAFT",  # first composer draft
        json.dumps({"score": 0.4, "rationale": "too short"}),  # critic low score
        "FINAL",  # composer retry
        json.dumps({"score": 0.95, "rationale": "great"}),  # critic high score
    ]

    def _fake_chat(*_args: Any, **_kwargs: Any):  # noqa: ANN001, D401
        return responses.pop(0)

    # Patch all chat entry points that may have been imported
    monkeypatch.setattr("agent.llm_client.chat", _fake_chat)
    import agent.composer as composer_module
    import agent.critic as critic_module
    monkeypatch.setattr(composer_module, "chat", _fake_chat)
    monkeypatch.setattr(critic_module, "chat", _fake_chat)

    # Also stub helper.merge_results to avoid unrelated logic
    monkeypatch.setattr("agent.helper.merge_results", lambda _r: "{}")


def test_compose_retry_success(_stub_chat):  # noqa: ANN001
    results = {"dummy_tool#1": {"foo": "bar"}}
    md = retry_composer.compose_with_retry("Q?", results, threshold=0.8, max_retries=1)

    assert md.startswith("FINAL")
    assert "critic_score=" in md


def test_no_retry_when_high_score(monkeypatch):
    # Stub chat to immediately return high score so composer called once
    responses = [
        "ONLY_DRAFT",
        json.dumps({"score": 0.9, "rationale": "ok"}),
    ]

    def _fake_chat(*_args: Any, **_kwargs: Any):  # noqa: ANN001
        return responses.pop(0)

    monkeypatch.setattr("agent.llm_client.chat", _fake_chat)
    monkeypatch.setattr("agent.composer.chat", _fake_chat)
    monkeypatch.setattr("agent.critic.chat", _fake_chat)
    monkeypatch.setattr("agent.helper.merge_results", lambda _r: "{}")

    results: Dict[str, Any] = {"search_tool#1": {"foo": "bar"}}
    md = retry_composer.compose_with_retry("What?", results, threshold=0.8, max_retries=1)

    assert md.startswith("ONLY_DRAFT")
    assert "retries=0" in md 