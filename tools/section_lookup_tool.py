from __future__ import annotations

"""TransferAI – Section Lookup Tool

Return the scheduled sections (meeting times, modality, instructor, etc.) for a
single Santa Monica College course.  The tool reuses the existing
:pyattr:`tools.course_detail_tool.CourseDetailTool` to avoid reloading the
catalogue.

Note
----
Academic‐term filtering and additional validation will be added in a future
release.  For now, the tool merely echoes whatever section data exists in the
static JSON catalogue.
"""

from typing import List
import sys
from pathlib import Path

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Ensure project root on sys.path for standalone execution -------------------
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

from tools.course_detail_tool import (  # noqa: E402
    CourseDetailTool,
    CourseNotFoundError,
    Section,  # Reuse existing Section model
)

# ---------------------------------------------------------------------------
# Pydantic schemas -----------------------------------------------------------
# ---------------------------------------------------------------------------


class SLIn(BaseModel):  # noqa: D401
    """Input schema – requires a single course code."""

    course_code: str = Field(..., description="Canonical or raw course code, e.g. 'MATH 7'.")


class SLOut(BaseModel):  # noqa: D401
    """Output schema containing section details."""

    course_code: str
    sections: List[Section]


# ---------------------------------------------------------------------------
# Core function --------------------------------------------------------------
# ---------------------------------------------------------------------------


def _lookup_sections(*, course_code: str):  # type: ignore[override]
    """Retrieve section list for *course_code* via CourseDetailTool."""

    # Delegate to CourseDetailTool which already handles normalisation & errors
    detail_dict = CourseDetailTool.invoke({"course_code": course_code})

    # The StructuredTool returns a dict; reconstruct CourseDetail for typing
    sections_data = detail_dict.get("sections", [])

    return SLOut(course_code=detail_dict["course_code"], sections=sections_data).model_dump(
        mode="json"
    )


# ---------------------------------------------------------------------------
# StructuredTool wrapper -----------------------------------------------------
# ---------------------------------------------------------------------------


SectionLookupTool: StructuredTool = StructuredTool.from_function(
    func=_lookup_sections,
    name="section_lookup",
    description="Return scheduled sections (days, times, instructor, etc.) for an SMC course.",
    args_schema=SLIn,
    return_schema=SLOut,
)

# Public export --------------------------------------------------------------

__all__ = ["SectionLookupTool"]

# ---------------------------------------------------------------------------
# Manual demo ----------------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import json  # local import

    try:
        result = SectionLookupTool.invoke({"course_code": "MUSIC 27"})
        print(json.dumps(result, indent=2))
    except CourseNotFoundError as err:
        print("Error:", err) 