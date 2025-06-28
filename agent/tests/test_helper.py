import json
from typing import Any, Dict

import datetime
import pytest
from jsonschema import ValidationError

from agent import helper


@pytest.fixture(autouse=True)
def fixed_datetime(monkeypatch):
    """Patch *datetime.utcnow* to a fixed timestamp for deterministic tests."""

    class _FixedDT(datetime.datetime):
        @classmethod
        def utcnow(cls):  # type: ignore[override]
            return cls(2024, 1, 1, 0, 0, 0)

    monkeypatch.setattr(helper, "datetime", _FixedDT)
    yield


def test_merge_results_happy_path():
    results: Dict[str, Any] = {
        "articulation_match_tool#1": {"foo": "bar"},
        "search_tool#2": {"bar": "baz"},
    }

    summary_json = helper.merge_results(results)
    summary = json.loads(summary_json)

    assert summary["metadata"]["tool_count"] == 2
    assert set(summary["merged_results"].keys()) == {"articulation_match_tool", "search_tool"}


def test_merge_results_empty():
    with pytest.raises(ValueError):
        helper.merge_results({})


def test_merge_results_schema_validation_failure(monkeypatch):
    def _raise(*_args, **_kwargs):
        raise ValidationError("forced failure")

    monkeypatch.setattr(helper.jsonschema, "validate", _raise)

    with pytest.raises(helper.HelperError):
        helper.merge_results({"search_tool#1": {"ok": True}}) 