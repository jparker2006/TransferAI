from __future__ import annotations

"""TransferAI – Course Detail Retrieval Tool (SKELETON)

This module implements the public interface for ``CourseDetailTool`` which can be
called from the LLM runtime as:

```python
from llm.tools.course_detail_tool import CourseDetailTool

result = CourseDetailTool().run(course_code="MATH 7")
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
    """High-level response model returned by :py:meth:`CourseDetailTool.run`."""

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
# Tool base-class stub
# ---------------------------------------------------------------------------


# New uniform base
from tools.base_tool import BaseTool

# ---------------------------------------------------------------------------
# CourseDetailTool (primary public object)
# ---------------------------------------------------------------------------


class CourseDetailTool(BaseTool):  # type: ignore[too-few-public-methods]
    """Return rich metadata for a given ``course_code``.

    Example
    -------
    >>> tool = CourseDetailTool()
    >>> detail = tool.run(course_code="ARC 10")
    >>> detail["course_title"]
    "ARCHITECTURAL HISTORY"
    """

    # ------------------------------------------------------------------
    # Pydantic contracts ------------------------------------------------
    # ------------------------------------------------------------------

    class Input(BaseModel):  # noqa: D401, WPS430
        """Single required parameter for lookup."""

        course_code: str

    class Output(CourseDetail):  # noqa: D401
        """Alias: we expose CourseDetail directly as Output model."""

        pass

    # ---------------------------------------------------------------------
    # Internal helpers (implementation WIP)
    # ---------------------------------------------------------------------

    _catalog_cache: Optional[Dict[str, dict]] = None  # Lazy global cache

    # NOTE: Implementation intentionally omitted – fill in later.

    # TODO: PORT path to settings or ENV variable once config management lands.
    _CATALOG_DIR = Path(__file__).resolve().parents[1] / "data" / "SMC_catalog" / "parsed_programs"

    # Public API ------------------------------------------------------------

    def run(self, **inputs: Any) -> Dict[str, Any]:  # noqa: D401
        """Lookup *course_code* inside the local catalogue and return details.

        Parameters
        ----------
        course_code:
            Alphanumeric code with optional spacing/case, e.g. ``'math7'``,
            ``'MATH 7'``, ``'Math 7'``, etc.

        Returns
        -------
        dict
            JSON-serialisable dictionary that conforms to
            :pyattr:`output_schema`.
        """

        # ------------------------------------------------------------------
        # TODO: Validate & normalise input
        # TODO: Load catalogue data (with caching)
        # TODO: Perform lookup w/ graceful error handling
        # TODO: Validate raw JSON against :class:`CourseDetail` model
        # ------------------------------------------------------------------

        if "course_code" not in inputs:
            raise ValueError("`course_code` parameter required")

        raw_code = inputs["course_code"]
        if not isinstance(raw_code, str):
            raise TypeError("`course_code` must be a string")

        normalised = self._normalise_code(raw_code)

        catalog = self._load_catalog()

        if normalised not in catalog:
            raise CourseNotFoundError(f"Course '{normalised}' not found in catalog")

        raw_data = catalog[normalised]

        try:
            detail = CourseDetail(**raw_data)
        except Exception as exc:  # noqa: BLE001
            # Wrap any model validation issues so the caller always deals with
            # CourseNotFoundError for lookup failures/invalid data.
            raise CourseNotFoundError(
                f"Course '{normalised}' found but could not be validated: {exc}"
            ) from exc

        return detail.model_dump(mode="json", exclude_none=True)

    # ------------------------------------------------------------------
    # Private utility methods (all TODO-stubs)
    # ------------------------------------------------------------------

    @staticmethod
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

    @classmethod
    def _load_catalog(cls) -> Dict[str, dict]:  # noqa: D401
        """Eagerly parse *all* program JSON files into a {course_code: data} map.

        The result is memoised on the class object to prevent repeated disk I/O
        during the life-time of the Python interpreter.
        """
        import json
        import warnings

        if cls._catalog_cache is not None:
            return cls._catalog_cache

        catalog_path = cls._CATALOG_DIR
        if not catalog_path.exists():
            raise RuntimeError(f"Catalog directory not found: {catalog_path}")

        mapping: Dict[str, dict] = {}

        for json_file in catalog_path.glob("*.json"):
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

                norm_code = cls._normalise_code(raw_code)

                if norm_code in mapping:
                    # Silently skip subsequent duplicates; first occurrence wins.
                    continue

                # Inject department if missing but inferable
                if "department" not in course and program_data.get("program_name"):
                    course["department"] = program_data["program_name"]

                mapping[norm_code] = course

        cls._catalog_cache = mapping
        return mapping

    # ------------------------------------------------------------------
    # Quick manual test -------------------------------------------------
    # ------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    tool = CourseDetailTool()
    try:
        info = tool.run(course_code="ARC 10")
        print("ARC 10 Title:", info.get("course_title"))
    except CourseNotFoundError as err:
        print("Error:", err) 