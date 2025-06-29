import sys
import types

# ------------------------------------------------------------------
# Inject minimal stub for langgraph if library not present ----------
# ------------------------------------------------------------------
if 'langgraph' not in sys.modules:
    lg = types.ModuleType('langgraph')
    graph_mod = types.ModuleType('langgraph.graph')

    class _DummyCompiled:
        def __init__(self, func):
            self._func = func
        def invoke(self, state):
            return self._func(state)
        def get_graph(self):
            class _G:  # noqa: D401
                def draw_mermaid(self):
                    return "graph TD;"
            return _G()

    class _DummyBuilder:
        def __init__(self, _state):
            self._seq = []
        def add_node(self, name, fn):
            self._seq.append(fn)
        def add_edge(self, _a, _b):
            pass
        def add_conditional_edges(self, *_a, **_k):
            pass
        def add_reducer(self, *_a, **_k):
            pass
        def compile(self):
            def _run(state):
                new_state = state.copy()
                for fn in self._seq:
                    new_state.update(fn(new_state))
                return new_state
            return _DummyCompiled(_run)
    def StateGraph(_s):
        return _DummyBuilder(_s)
    START = '__start__'
    END = '__end__'
    graph_mod.StateGraph = StateGraph
    graph_mod.START = START
    graph_mod.END = END
    lg.graph = graph_mod
    sys.modules['langgraph'] = lg
    sys.modules['langgraph.graph'] = graph_mod

import json
from typing import Any, Dict

import pytest

import agent.graph_runner as runner


@pytest.fixture
def _stub_pipeline(monkeypatch):
    """Stub planner / executor / composer / critic for deterministic tests."""

    # Stub planner → simple plan with no tools
    monkeypatch.setattr("agent.planner.get_plan", lambda _q: [])

    # Stub executor → empty results
    monkeypatch.setattr("agent.executor.execute", lambda _plan, stream=False: {})

    # Stub helper
    monkeypatch.setattr("agent.helper.merge_results", lambda _r: "{}")

    # Stub composer returns different drafts depending on call sequence
    drafts = ["DRAFT", "FINAL"]
    draft_index = [0]  # Use list to make it mutable in closure

    def _fake_compose(*_args: Any, **_kwargs: Any):
        result = drafts[draft_index[0] % len(drafts)]
        draft_index[0] += 1
        return result

    monkeypatch.setattr("agent.composer.compose_from_execution", _fake_compose)
    # Also stub the regular compose function
    monkeypatch.setattr("agent.composer.compose", _fake_compose)

    # Critic first low then high
    scores = [
        {"score": 0.3, "rationale": "too short"},
        {"score": 0.95, "rationale": "great"},
    ]

    monkeypatch.setattr("agent.critic.score", lambda *_a, **_k: scores.pop(0))


def test_run_full_with_retry(_stub_pipeline):
    md = runner.run_full("Will PSYC 1 transfer?", max_retries=1)
    assert md in {"FINAL", "DRAFT"}


def test_graph_state_keys(_stub_pipeline):
    g = runner._get_graph(1)
    state = g.invoke({
        "question": "Q", "plan": [], "results": {}, "summary": "{}", "markdown": "", "critic": {}, "retries": 0
    })
    assert set(state.keys()) == {
        "question", "plan", "results", "summary", "markdown", "critic", "retries"
    } 