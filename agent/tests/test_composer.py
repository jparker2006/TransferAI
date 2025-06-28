import json

import agent.composer as composer


def test_compose_markdown(monkeypatch):
    """Composer should return the markdown provided by mocked chat helper."""

    fake_response = "**Recommended sections**\n\n* MATH 8 – Dr. Kim"

    # Monkey-patch the chat helper so no external call is made.
    monkeypatch.setattr(
        "agent.composer.chat",
        lambda instructions, context=None, model="gpt-4o": fake_response,
    )

    summary = json.dumps({
        "best_sections": [
            {"section_id": "1234", "instructor": "Kim"}
        ]
    })

    result = composer.compose(summary, tool_outputs={})
    assert result == fake_response 