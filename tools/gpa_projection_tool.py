from __future__ import annotations

"""TransferAI – GPA Projection Tool

Predict a student's future GPA after a set of planned courses.

Features
--------
* Supports two distinct calculations:
  1. **SMC cumulative GPA** – standard 4-point scale (no ± grades).
  2. **UC transfer GPA** – UC plus/minus 4-point scale.
* Filters P/NP/W/I, zero-unit courses, and (placeholder) non-transferable
  courses when calculating the UC transfer GPA.
* Future extension hooks: repeat-policy overrides, ASSIST transferability check.
* Exposed via :pydata:`langchain_core.tools.StructuredTool` so agents can invoke
  it seamlessly.

Note
----
- This tool assumes all units are in *semester* units (SMC standard).
- UC transfer GPA is computed using **only** UC-transferable SMC courses.
- Unit conversion (quarter ↔ semester) is *not* handled in this version.
"""

from dataclasses import dataclass
import logging
from pathlib import Path
import sys
from typing import Dict, List, Literal, Optional, Tuple

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator, model_validator, PositiveFloat, conlist, NonNegativeFloat

# ---------------------------------------------------------------------------
# Ensure project root importable when executed directly ----------------------
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":  # pragma: no cover – CLI/debug support
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging --------------------------------------------------------------------
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants ------------------------------------------------------------------
# ---------------------------------------------------------------------------

SMC_POINTS: Dict[str, float] = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}

UC_POINTS: Dict[str, float] = {
    "A+": 4.0,
    "A": 4.0,
    "A-": 3.7,
    "B+": 3.3,
    "B": 3.0,
    "B-": 2.7,
    "C+": 2.3,
    "C": 2.0,
    "C-": 1.7,
    "D+": 1.3,
    "D": 1.0,
    "D-": 0.7,
    "F": 0.0,
}

SKIP_GRADES = {"P", "NP", "W", "I"}

# ---------------------------------------------------------------------------
# Helpers --------------------------------------------------------------------
# ---------------------------------------------------------------------------

def truncate(value: float, decimals: int = 2) -> float:  # noqa: D401
    """Truncate *value* to *decimals* (no rounding)."""

    factor = 10 ** decimals
    return int(value * factor) / factor


def is_uc_transferable(course_code: str) -> bool:  # noqa: D401
    """Stub – always returns True for now (ASSIST integration todo)."""

    return True

# ---------------------------------------------------------------------------
# Pydantic schemas -----------------------------------------------------------
# ---------------------------------------------------------------------------


class CoursePlan(BaseModel):  # noqa: D401
    """One planned course entry."""

    course_code: str = Field(..., description="SMC course code, e.g. 'MATH 8'.")
    units: NonNegativeFloat = Field(..., description="Semester credit units (>=0; zero-unit courses are ignored in GPA calc).")
    letter_grade: str = Field(..., description="Expected letter grade e.g. 'A', 'B+' or 'P'.")

    # Normalise grade string early
    @field_validator("letter_grade", mode="before")
    @classmethod
    def _clean_grade(cls, v: str) -> str:  # noqa: D401, N805
        return str(v).strip().upper()


class GPAIn(BaseModel):  # noqa: D401
    """Input schema for GPA projection."""

    current_gpa: float = Field(..., ge=0.0, le=4.0)
    units_completed: PositiveFloat = Field(..., description="Total graded units already completed.")
    planned_courses: conlist(CoursePlan, min_length=0)  # type: ignore[type-arg]
    gpa_type: Literal["smc", "uc"]

    # Root-level sanity checks
    @model_validator(mode="after")
    def _check_courses(cls, data):  # noqa: D401, N805
        if data.units_completed <= 0:
            raise ValueError("units_completed must be > 0")
        return data


class GPAOut(BaseModel):  # noqa: D401
    """Output schema returned by the tool."""

    projected_gpa: float
    total_units: float
    assumptions: str

# ---------------------------------------------------------------------------
# Core calculation -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _calculate_projection(
    *,
    current_gpa: float,
    units_completed: float,
    planned_courses: List[CoursePlan],
    gpa_type: Literal["smc", "uc"],
) -> GPAOut:  # noqa: D401
    """Compute projected GPA given planned courses."""

    logger.info("Starting GPA projection: type=%s, current_gpa=%.3f, units_completed=%.1f", gpa_type, current_gpa, units_completed)

    if gpa_type == "smc":
        point_map = SMC_POINTS
    else:
        point_map = UC_POINTS

    new_points = 0.0
    new_units = 0.0
    ignored_units = 0.0

    for course in planned_courses:
        grade = course.letter_grade
        units = course.units

        # Normalise SMC simple scale by dropping +/- modifiers
        if gpa_type == "smc" and grade.endswith(('+', '-')):
            grade = grade[0]

        # Skip P/NP/W/I or zero-unit courses
        if grade in SKIP_GRADES or units == 0:
            ignored_units += units
            continue

        # UC transferability filter
        if gpa_type == "uc" and not is_uc_transferable(course.course_code):
            ignored_units += units
            continue

        if grade not in point_map:
            raise ValueError(f"Unsupported grade '{grade}' for GPA type '{gpa_type}'.")

        gp = point_map[grade]
        new_points += gp * units
        new_units += units
        logger.debug("Accepted %s (%s units, grade=%s→%.1f points)", course.course_code, units, grade, gp)

    # If no new graded units, just echo current GPA
    if new_units == 0:
        projected = truncate(current_gpa, 2)
        total_u = units_completed
    else:
        total_points = current_gpa * units_completed + new_points
        total_u = units_completed + new_units
        projected = truncate(total_points / total_u, 2)

    assumptions = []
    if ignored_units:
        assumptions.append(f"Ignored {int(ignored_units)} unit(s) with non-graded designations or non-transferable.")
    assumptions.append("UC plus/minus scale" if gpa_type == "uc" else "SMC simple A-F scale")

    return GPAOut(projected_gpa=projected, total_units=total_u, assumptions="; ".join(assumptions)).model_dump(mode="json")


# ---------------------------------------------------------------------------
# StructuredTool wrapper ----------------------------------------------------
# ---------------------------------------------------------------------------


GPAProjectionTool: StructuredTool = StructuredTool.from_function(
    func=_calculate_projection,
    name="gpa_projection",
    description="Project a student's future GPA after planned courses using either the SMC (A-F) or UC transfer (plus/minus) scale.",
    args_schema=GPAIn,
    return_schema=GPAOut,
)

__all__ = ["GPAProjectionTool"]

# ---------------------------------------------------------------------------
# Manual CLI demo ------------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    sample = {
        "current_gpa": 3.25,
        "units_completed": 60,
        "planned_courses": [
            {"course_code": "MATH 8", "units": 5, "letter_grade": "A"},
            {"course_code": "PHYS 22", "units": 5, "letter_grade": "B+"},
            {"course_code": "HIST 1", "units": 3, "letter_grade": "W"},
            {"course_code": "CS 3", "units": 4, "letter_grade": "D"},
        ],
        "gpa_type": "smc",
    }
    import json as _json

    print(_json.dumps(GPAProjectionTool.invoke(sample), indent=2))

# Expose `truncate` at the builtins level so external modules/tests can use it
import builtins as _builtins

_builtins.truncate = truncate
