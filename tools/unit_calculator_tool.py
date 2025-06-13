from __future__ import annotations

"""TransferAI – Unit Calculator Tool

Given a list of course codes, sum their credit units using the same local
catalogue utilised by :pyattr:`tools.course_detail_tool.CourseDetailTool`.

Example
-------
>>> from tools.unit_calculator_tool import UnitCalculatorTool
>>> UnitCalculatorTool.invoke({"course_codes": ["MATH 7", "CHEM 11"]})
{'total_units': 10.0, 'breakdown': {'MATH 7': 5.0, 'CHEM 11': 5.0}}
"""

from typing import Any, Dict, List
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is importable when running as a standalone script
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator

from tools.course_detail_tool import (
    _normalise_code,
    _load_catalog,
    CourseNotFoundError,
)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class UCIn(BaseModel):  # noqa: D401
    """Input schema – requires at least one course code."""

    course_codes: List[str] = Field(..., min_length=1)

    # Trim whitespace for each provided code (list-level transform)
    @field_validator("course_codes", mode="before")
    def _strip_list(cls, v: List[str]) -> List[str]:  # noqa: D401, N805
        return [str(item).strip() for item in v]


class UCOut(BaseModel):  # noqa: D401
    """Output schema – total units and per-course breakdown."""

    total_units: float
    breakdown: Dict[str, float]


# ---------------------------------------------------------------------------
# Core computation helper
# ---------------------------------------------------------------------------


def _sum_units(*, course_codes: List[str]) -> Dict[str, Any]:  # noqa: D401
    """Return total unit count and per-course breakdown for *course_codes*."""

    catalog = _load_catalog()
    breakdown: Dict[str, float] = {}
    total_units = 0.0

    for raw_code in course_codes:
        norm = _normalise_code(raw_code)

        if norm not in catalog:
            raise CourseNotFoundError(f"{norm} not found in catalog")

        units_str = catalog[norm].get("units", "")
        match = re.match(r"([\d.]+)", units_str)
        if not match:
            raise RuntimeError(f"Could not parse units for {norm}: {units_str}")

        units_val = float(match.group(1))
        total_units += units_val

        # Store canonical unit value once per unique course for breakdown
        if norm not in breakdown:
            breakdown[norm] = units_val

    return UCOut(total_units=total_units, breakdown=breakdown).model_dump(mode="json")


# ---------------------------------------------------------------------------
# StructuredTool wrapper
# ---------------------------------------------------------------------------


UnitCalculatorTool: StructuredTool = StructuredTool.from_function(
    func=_sum_units,
    name="unit_calculator",
    description=(
        "Given a list of course codes, return the total credit units and per-course "
        "breakdown based on the local SMC/UCSD catalogue."
    ),
    args_schema=UCIn,
    return_schema=UCOut,
)

# Export symbol
__all__ = ["UnitCalculatorTool"]

# ---------------------------------------------------------------------------
# Manual demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    print(
        UnitCalculatorTool.invoke({
            "course_codes": [
                "MATH 7",
                "ARC 10",
                "ACCTG 1"
            ]
        })
    )
