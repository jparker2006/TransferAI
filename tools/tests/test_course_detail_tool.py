from __future__ import annotations

"""Unit tests for CourseDetailTool.

These tests rely only on the static JSON catalog shipped with the repository
and therefore run quickly without needing any network or DB access.
"""

import sys
import json
from pathlib import Path

import pytest

# Ensure project root (two levels up) is importable when running file directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.course_detail_tool import CourseDetailTool, CourseNotFoundError

# Reuse a single tool instance – its catalog is cached after first call.
TOOL = CourseDetailTool()


@pytest.mark.parametrize("variant", ["ARC 10", "arc10", "ARC10"])
def test_arc10_retrieval_invariants(variant: str) -> None:  # noqa: D401
    """Different spacing/case variants should yield identical records."""

    result = TOOL.run(course_code=variant)
    assert result["course_code"] == "ARC 10"
    assert result["course_title"].upper().startswith("STUDIO")


def test_missing_course_raises() -> None:  # noqa: D401
    """An unknown code should raise CourseNotFoundError."""

    with pytest.raises(CourseNotFoundError):
        TOOL.run(course_code="XYZ 999")


# -------------------------------------------------------------------------
# Broader schema/content tests --------------------------------------------
# -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code, required_keys",
    [
        ("STAT C1000", ["prerequisites", "transfer_info", "units", "sections"]),
        ("MATH 2", ["advisory", "course_title", "units"]),
    ],
)
def test_key_presence_and_schema_validation(code: str, required_keys: list[str]) -> None:  # noqa: D401
    """Ensure the returned dict respects Output schema and contains critical fields."""

    data = TOOL.run(course_code=code)

    # validate against declared Output model
    CourseDetailTool.Output(**data)

    for key in required_keys:
        assert key in data, f"{key} missing from {code} record"


def test_tool_has_schemas() -> None:  # noqa: D401
    """Contract enforcement – tool exposes input_schema/output_schema."""

    assert isinstance(TOOL.input_schema, dict)
    assert isinstance(TOOL.output_schema, dict) 