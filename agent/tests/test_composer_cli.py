import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

import agent.composer as composer_module


@pytest.fixture(autouse=True)
def _stub_llm(monkeypatch):
    """Monkey-patch *agent.llm_client.chat* to avoid network access."""

    def _fake_chat(*_args: Any, **_kwargs: Any) -> str:  # noqa: ANN401
        return "**TEST-REPLY**"

    # Patch the *imported* reference inside composer_module so the stub gets
    # used without affecting other modules.
    monkeypatch.setattr(composer_module, "chat", _fake_chat)

    # Also stub helper.merge_results so we don't depend on that logic here
    summary_stub = json.dumps(
        {
            "merged_results": {},
            "metadata": {
                "tool_count": 0,
                "generated_at": "2024-01-01T00:00:00Z",
                "schema_version": "0.1",
            },
        }
    )

    monkeypatch.setattr("agent.helper.merge_results", lambda _results: summary_stub)


def test_compose_from_execution():
    md = composer_module.compose_from_execution(
        question="Will my PSYC 1 course transfer?",
        results={"search_tool#1": {"foo": "bar"}},
    )
    assert "**TEST-REPLY**" in md


@pytest.mark.skipif(sys.platform.startswith("win"), reason="subprocess quoting quirks on Windows")
def test_cli_roundtrip(tmp_path: Path):
    # Prepare fake results JSON
    results_json_path = tmp_path / "results.json"
    results_json_path.write_text('{"search_tool#1": {"foo": "bar"}}', encoding="utf-8")

    # Invoke module via subprocess so that __main__ path is taken
    # Run from parent directory so agent module can be found
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "agent.composer",
            str(results_json_path),
            "--question",
            "Does this transfer?",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,  # Go up to TransferAI root
    )

    assert proc.returncode == 0, proc.stderr
    # Basic sanity: some Markdown header is present
    assert proc.stdout.strip().startswith("##"), proc.stdout 