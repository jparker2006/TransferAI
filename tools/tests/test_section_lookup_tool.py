from __future__ import annotations

"""Unit tests for SectionLookupTool.

These tests verify:
1. Canonical course_code normalisation and section data retrieval.
2. Handling of mixed-case / spacing variants.
3. Schema compliance of returned section objects.
4. Propagation of CourseNotFoundError for unknown codes.
5. Behaviour when the underlying CourseDetailTool returns no sections (monkey-patched).
"""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

# Ensure project root importable when running test directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.section_lookup_tool import SectionLookupTool  # noqa: E402
from tools.course_detail_tool import CourseNotFoundError, Section  # noqa: E402

TOOL = SectionLookupTool  # Singleton StructuredTool


# ---------------------------------------------------------------------------
# 1-3. Successful retrieval & schema validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant",
    ["MATH 7", "math7", "  Arc 10  "]
)
def test_section_lookup_normalisation(variant: str) -> None:  # noqa: D401
    """Different casing/spacing variants should resolve to canonical code."""

    out = TOOL.invoke({"course_code": variant})

    # Canonical code must be upper-case with single space
    assert " " in out["course_code"], out
    assert out["course_code"] == out["course_code"].upper(), out

    # sections list should not be empty for known catalog courses
    assert isinstance(out["sections"], list) and out["sections"], "No sections returned"

    # Validate each section against the shared model
    for sec in out["sections"]:
        Section(**sec)  # will raise if schema mismatch


# ---------------------------------------------------------------------------
# 4. Unknown course raises
# ---------------------------------------------------------------------------


def test_unknown_course() -> None:  # noqa: D401
    with pytest.raises(CourseNotFoundError):
        TOOL.invoke({"course_code": "NOPE 999"})


# ---------------------------------------------------------------------------
# 5. Empty sections list handling via monkey-patch
# ---------------------------------------------------------------------------


def test_empty_sections(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D401
    """If CourseDetailTool returns no sections the tool should echo an empty list."""

    fake_detail = {
        "course_code": "TEST 1",
        "sections": [],
    }

    from tools import section_lookup_tool as sl_mod  # local import for object ref

    class _Stub:
        """Minimal stub mimicking CourseDetailTool with an invoke method."""

        @staticmethod
        def invoke(args):  # type: ignore[override]
            return fake_detail

    # Replace the CourseDetailTool reference in the module with our stub
    monkeypatch.setattr(sl_mod, "CourseDetailTool", _Stub, raising=True)

    out = TOOL.invoke({"course_code": "TEST 1"})
    assert out["sections"] == []
    assert out["course_code"] == "TEST 1" 