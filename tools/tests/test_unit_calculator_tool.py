from __future__ import annotations

"""Tests for UnitCalculatorTool (credit‐unit summation)."""

import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

# Make project root importable when running this file directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.unit_calculator_tool import UnitCalculatorTool  # noqa: E402
from tools.course_detail_tool import CourseNotFoundError  # noqa: E402

# Singleton tool instance
TOOL = UnitCalculatorTool

# ---------------------------------------------------------------------------
# 1 & 2. Happy-path totals + normalisation handling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "codes, expected_total",
    [
        (["MATH 7", "ARC 10"], 8.0),
        (["  math   7  ", "ARC 10"], 8.0),  # whitespace + mixed case
        (["ARC 10", "ARC 10"], 6.0),  # duplicate should count twice (3 + 3)
    ],
)
def test_total_units_happy_path(codes: list[str], expected_total: float) -> None:  # noqa: D401
    """Total units should match catalog values after normalisation."""

    out = TOOL.invoke({"course_codes": codes})

    assert pytest.approx(out["total_units"], rel=1e-4) == expected_total, out

    # Ensure breakdown has canonical codes and correct per-course values
    for raw in codes:
        norm = " ".join(raw.upper().split())
        assert norm in out["breakdown"], f"{norm} missing in breakdown"


# ---------------------------------------------------------------------------
# 3. Fractional (decimal) unit parsing
# ---------------------------------------------------------------------------


def test_fractional_units(monkeypatch: pytest.MonkeyPatch) -> None:  # noqa: D401
    """Courses with decimal unit strings should be handled correctly."""

    from tools.unit_calculator_tool import _load_catalog  # local import to patch

    fake_catalog = _load_catalog().copy()
    fake_catalog["TEST 1"] = {"units": "0.5 UNIT"}

    monkeypatch.setattr("tools.unit_calculator_tool._load_catalog", lambda: fake_catalog)

    out = TOOL.invoke({"course_codes": ["TEST 1"]})
    assert out["total_units"] == 0.5
    assert out["breakdown"] == {"TEST 1": 0.5}


# ---------------------------------------------------------------------------
# 5. Unknown course error handling
# ---------------------------------------------------------------------------


def test_unknown_course_raises() -> None:  # noqa: D401
    with pytest.raises(CourseNotFoundError):
        TOOL.invoke({"course_codes": ["NOPE 999"]})


# ---------------------------------------------------------------------------
# 6. Input validation – empty list should raise ValidationError
# ---------------------------------------------------------------------------


def test_empty_input_validation() -> None:  # noqa: D401
    with pytest.raises(ValidationError):
        TOOL.invoke({"course_codes": []}) 