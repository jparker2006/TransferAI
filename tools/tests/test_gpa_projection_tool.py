import sys
from pathlib import Path

# Ensure project root on path for `tools` imports when pytest discovers tests
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import math
import types
import pytest

from tools.gpa_projection_tool import GPAProjectionTool, is_uc_transferable

# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------

def _invoke(payload):  # noqa: D401
    """Thin wrapper to run the StructuredTool conveniently."""

    return GPAProjectionTool.invoke(payload)

# ---------------------------------------------------------------------------
# 1. Basic valid projections -------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "current_gpa,units_completed,planned,expected",
    [
        # Simple SMC example A/B/C (4,3,2 points)
        (
            3.0,
            60,
            [
                {"course_code": "MATH 8", "units": 5, "letter_grade": "A"},
                {"course_code": "ENG 2", "units": 3, "letter_grade": "B"},
                {"course_code": "HIST 5", "units": 4, "letter_grade": "C"},
            ],
            3.01,  # recalculated with weighted semester-unit method and truncated
        ),
        # UC plus/minus scale with A- and B+
        (
            3.2,
            45,
            [
                {"course_code": "PHYS 22", "units": 5, "letter_grade": "A-"},  # 3.7
                {"course_code": "CHEM 11", "units": 5, "letter_grade": "B+"},  # 3.3
            ],
            3.25,
        ),
        # Mixed with F lowering GPA
        (
            3.5,
            30,
            [
                {"course_code": "BIO 1", "units": 4, "letter_grade": "F"},
            ],
            3.08,
        ),
    ],
)
@pytest.mark.parametrize("gpa_type", ["smc", "uc"])
def test_basic_projections(current_gpa, units_completed, planned, expected, gpa_type):
    if gpa_type == "smc":
        # Strip any +/- modifiers for SMC case to avoid validation failure
        for c in planned:
            lg = c["letter_grade"].rstrip("+-")
            c["letter_grade"] = lg if lg else c["letter_grade"]
    payload = {
        "current_gpa": current_gpa,
        "units_completed": units_completed,
        "planned_courses": planned,
        "gpa_type": gpa_type,
    }
    out = _invoke(payload)
    assert math.isclose(out["projected_gpa"], expected, rel_tol=1e-3)


# ---------------------------------------------------------------------------
# 2. Filtering behaviour -----------------------------------------------------
# ---------------------------------------------------------------------------


def test_filtering_special_grades():
    payload = {
        "current_gpa": 3.0,
        "units_completed": 40,
        "planned_courses": [
            {"course_code": "PE 1", "units": 2, "letter_grade": "P"},
            {"course_code": "SOC 2", "units": 3, "letter_grade": "NP"},
            {"course_code": "MATH 8", "units": 5, "letter_grade": "A"},
            {"course_code": "ART 1", "units": 0, "letter_grade": "A"},  # zero unit
        ],
        "gpa_type": "smc",
    }
    out = _invoke(payload)
    # Only the 5 units of A should count → new GPA = (3*40+4*5)/(45) = 3.11 truncated
    assert math.isclose(out["projected_gpa"], 3.11, rel_tol=1e-5)
    assert "Ignored" in out["assumptions"]


# ---------------------------------------------------------------------------
# 3. Truncation check --------------------------------------------------------
# ---------------------------------------------------------------------------


def test_truncate_not_round():
    # Designed to produce 3.229 → 3.22
    payload = {
        "current_gpa": 3.0,
        "units_completed": 50,
        "planned_courses": [
            {"course_code": "PHYS 22", "units": 5, "letter_grade": "B+"},  # 3.3
        ],
        "gpa_type": "uc",
    }
    out = _invoke(payload)
    assert out["projected_gpa"] == 3.02


# ---------------------------------------------------------------------------
# 4. Validation errors -------------------------------------------------------
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {  # GPA too high
            "current_gpa": 4.5,
            "units_completed": 30,
            "planned_courses": [],
            "gpa_type": "smc",
        },
        {  # units_completed zero
            "current_gpa": 3.0,
            "units_completed": 0,
            "planned_courses": [],
            "gpa_type": "smc",
        },
        {  # invalid grade
            "current_gpa": 3.0,
            "units_completed": 20,
            "planned_courses": [
                {"course_code": "MATH 8", "units": 5, "letter_grade": "Z"}
            ],
            "gpa_type": "smc",
        },
        {  # invalid gpa_type
            "current_gpa": 3.0,
            "units_completed": 20,
            "planned_courses": [],
            "gpa_type": "abc",
        },
    ],
)
def test_validation_errors(payload):
    with pytest.raises(ValueError):
        _invoke(payload)


# ---------------------------------------------------------------------------
# 5. UC transferability filter ----------------------------------------------
# ---------------------------------------------------------------------------


def test_uc_transferability_filter(monkeypatch):
    # Pretend only MATH 8 is transferable
    def fake_transferable(code: str) -> bool:  # noqa: D401
        return code == "MATH 8"

    monkeypatch.setattr(
        "tools.gpa_projection_tool.is_uc_transferable",
        fake_transferable,
        raising=True,
    )

    payload = {
        "current_gpa": 3.0,
        "units_completed": 60,
        "planned_courses": [
            {"course_code": "MATH 8", "units": 5, "letter_grade": "A"},
            {"course_code": "PHYS 22", "units": 5, "letter_grade": "A-"},
        ],
        "gpa_type": "uc",
    }
    out = _invoke(payload)
    # Only MATH 8 should count (A+ and A are both 4.0 for UC)
    expected = truncate((3.0 * 60 + 4.0 * 5) / 65, 2)
    assert math.isclose(out["projected_gpa"], expected, rel_tol=1e-5)
    assert "Ignored" in out["assumptions"]
