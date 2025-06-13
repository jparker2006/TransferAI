from __future__ import annotations

"""TransferAI – Course Detail Retrieval Tool (SKELETON)

This module implements the public interface for ``CourseDetailTool`` which can be
called from the LLM runtime as:

```python
from llm.tools.course_detail_tool import CourseDetailTool

detail = CourseDetailTool.invoke({"course_code": "MATH 7"})
```

The concrete behaviour (JSON catalogue loading, validation, normalisation, etc.)
will be added in a subsequent commit.  For now *all* implementation points are
represented by explicit ``TODO`` markers so that unit-tests import the module
successfully while signalling incomplete areas to developers.

# ---------------------------------------------------------------------------
# ⚠️  DUPLICATE COURSE CODES NOTE – 2025-TODO
# ---------------------------------------------------------------------------
# While indexing the catalog we discovered many legitimate duplicates: the same
# `course_code` appears in more than one program file (Independent Studies,
# cross-listed subjects, shared STAT/MATH courses, etc.).  For now the loader
# keeps *only the first* occurrence and silently ignores the rest.  The records
# are currently identical, so behaviour is correct for downstream consumers.
#
# If/when the data-engineering team delivers fully de-duplicated JSON—or if
# departments start diverging in their definitions—we should revisit `_load_catalog`
# and implement one of the following strategies:
#   1. Merge identical records and validate checksum equality.
#   2. Choose "last wins" instead of "first wins".
#   3. Emit a structured log or metrics signal for duplicates found.
#   4. Provide a `get_all(course_code)` helper that returns *all* versions.
#
# Keep this block as a reminder until the catalog pipeline is cleaned up.
# ---------------------------------------------------------------------------
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

# Pydantic 2.x imports
from pydantic import BaseModel, Field, field_validator, ConfigDict

# LangChain import (new dependency per refactor)
from langchain_core.tools import StructuredTool

# ---------------------------------------------------------------------------
# Public Exceptions
# ---------------------------------------------------------------------------


class CourseNotFoundError(RuntimeError):
    """Raised when a course_code cannot be located in the local catalogue."""


# ---------------------------------------------------------------------------
# Pydantic output models (partial – extend as needed)
# ---------------------------------------------------------------------------


class Section(BaseModel):
    """Representation of an individual course section (meeting offering).

    NOTE: The exact schema may evolve – fields are marked Optional for now until
    a catalogue survey is completed.
    """

    section_number: str
    schedule: List[Dict[str, Any]]
    notes: Optional[List[str]] = None
    duration: Optional[str] = None
    modality: Optional[str] = None
    co_enrollment_with: Optional[str] = Field(None, alias="co_enrollment_with")


class CourseDetail(BaseModel):
    """High-level response model returned by :pyattr:`CourseDetailTool`."""

    course_code: str
    course_title: str
    units: str
    transfer_info: Optional[List[str]] = None
    description: Optional[str] = None
    prerequisites: Optional[str] = None
    prerequisite_notes: Optional[str] = None
    corequisites: Optional[str] = None
    advisory: Optional[str] = None
    advisory_notes: Optional[str] = None
    department: Optional[str] = None  # May not exist in the raw data
    sections: Optional[List[Section]] = None  # Consider making this optional/omitted

    # Any additional raw keys can be added later.

    # Validators -------------------------------------------------------------

    @field_validator("course_code", mode="before")  # type: ignore[arg-type]
    def _strip_course_code(cls, v: str) -> str:  # noqa: D401, N805
        """Enforce canonical spacing/capitalisation on *output* values."""
        return " ".join(str(v).upper().split())

    # Allow unknown fields to pass through untouched
    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# New I/O schemas for LangChain StructuredTool
# ---------------------------------------------------------------------------


class CDIn(BaseModel):  # noqa: D401
    """Input schema – single required parameter."""

    course_code: str


class CDOut(CourseDetail):  # noqa: D401
    """Alias for output – inherits all CourseDetail fields."""

    pass


# ---------------------------------------------------------------------------
# Module-level helpers (moved from legacy class implementation)
# ---------------------------------------------------------------------------


_CATALOG_DIR = Path(__file__).resolve().parents[1] / "data" / "SMC_catalog" / "parsed_programs"
_CATALOG_CACHE: Optional[Dict[str, dict]] = None  # Lazy global cache


def _normalise_code(code: str) -> str:  # noqa: D401
    """Return canonical course-code format (e.g., 'ARC10' → 'ARC 10')."""
    import re  # local import – stdlib

    # Collapse whitespace & upper-case first.
    cleaned = re.sub(r"\s+", " ", code.strip().upper())

    # Split alpha prefix, numeric part, and optional suffix letters.
    # Examples:
    #   'MATH31A'  -> groups('MATH', '31', 'A')
    #   'ARC 10'   -> groups('ARC', '10', '')
    #   'cs50'     -> groups('CS', '50', '')
    match = re.match(r"^([A-Z]+)\s*(\d+)([A-Z]?)$", cleaned)
    if not match:
        # Fallback: just return collapsed/upper string
        return cleaned

    prefix, number, suffix = match.groups()
    return f"{prefix} {number}{suffix}"


def _load_catalog() -> Dict[str, dict]:  # noqa: D401
    """Return a {course_code: data} mapping, memoised for process lifetime."""
    import json
    import warnings

    global _CATALOG_CACHE  # noqa: PLW0603 – intentional module-level cache

    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE

    if not _CATALOG_DIR.exists():
        raise RuntimeError(f"Catalog directory not found: {_CATALOG_DIR}")

    mapping: Dict[str, dict] = {}

    for json_file in _CATALOG_DIR.glob("*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as fh:
                program_data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            warnings.warn(f"Failed to load {json_file}: {exc}")
            continue

        for course in program_data.get("courses", []):
            raw_code = course.get("course_code")
            if not raw_code:
                continue

            norm_code = _normalise_code(raw_code)

            if norm_code in mapping:
                # Silently skip subsequent duplicates; first occurrence wins.
                continue

            # Inject department if missing but inferable
            if "department" not in course and program_data.get("program_name"):
                course["department"] = program_data["program_name"]

            mapping[norm_code] = course

    _CATALOG_CACHE = mapping
    return mapping


# ---------------------------------------------------------------------------
# LangChain adapter function – replaces former `run` method
# ---------------------------------------------------------------------------


def _lookup_course(*, course_code: str) -> Dict[str, Any]:  # noqa: D401
    """Lookup *course_code* in local catalogue and return a JSON-serialisable dict."""

    raw_code = course_code

    normalised = _normalise_code(raw_code)

    catalog = _load_catalog()

    if normalised not in catalog:
        raise CourseNotFoundError(f"Course '{normalised}' not found in catalog")

    raw_data = catalog[normalised]

    try:
        detail = CourseDetail(**raw_data)
    except Exception as exc:  # noqa: BLE001
        # Wrap validation issues so caller always deals with CourseNotFoundError
        raise CourseNotFoundError(
            f"Course '{normalised}' found but could not be validated: {exc}"
        ) from exc

    # Return plain dict for easy JSON serialisation while still satisfying
    # `return_schema` validation in StructuredTool.
    return detail.model_dump(mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# Public StructuredTool instance – *the* module export
# ---------------------------------------------------------------------------


CourseDetailTool: StructuredTool = StructuredTool.from_function(
    func=_lookup_course,
    name="course_detail",
    description=(
        "Return the catalog record (title, units, prereqs, etc.) for a "
        "Santa Monica College or UCSD course. Input: course_code."
    ),
    args_schema=CDIn,
    return_schema=CDOut,
)

object.__setattr__(CourseDetailTool, "return_schema", CDOut)


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------


__all__ = ["CourseDetailTool"]


# ---------------------------------------------------------------------------
# Quick manual test ---------------------------------------------------------
# ---------------------------------------------------------------------------

import json

if __name__ == "__main__":  # pragma: no cover
    try:
        info = CourseDetailTool.invoke({"course_code": "CS 17"})
        print(json.dumps(info, indent=2))
    except CourseNotFoundError as err:
        print("Error:", err) 