from __future__ import annotations

"""TransferAI – Professor Rating Retrieval Tool

Given a professor name or department, return Rate-My-Professor-style metrics for
Santa Monica College instructors along with a handful of top comments.  The
information is served out of an on-disk JSON snapshot under
``data/Professor_Ratings/santa_monica_college_professors_rag.json``.

The tool also cross-references the local course catalogue JSONs to determine
which SMC courses each instructor currently teaches.
"""

from pathlib import Path
import json
import glob
from typing import Any, Dict, List, Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Constants – file paths -----------------------------------------------------
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[1]
_RMP_JSON = _ROOT / "data" / "Professor_Ratings" / "santa_monica_college_professors_rag.json"
_CATALOG_GLOB = _ROOT / "data" / "SMC_catalog" / "parsed_programs" / "*.json"

# ---------------------------------------------------------------------------
# Exceptions ----------------------------------------------------------------
# ---------------------------------------------------------------------------


class ProfessorNotFoundError(RuntimeError):
    """Raised when no professor matches the given query parameters."""


# ---------------------------------------------------------------------------
# Lazy singleton loaders -----------------------------------------------------
# ---------------------------------------------------------------------------


_RMP_CACHE: Optional[List[dict]] = None  # Raw list of professors
_COURSE_MAP: Optional[Dict[str, List[str]]] = None  # instructor name → list[course_code]


def _load_rmp() -> List[dict]:  # noqa: D401
    """Return the raw Rate-My-Professor list, memoised."""

    global _RMP_CACHE  # noqa: PLW0603 – intentional module-level cache

    if _RMP_CACHE is not None:
        return _RMP_CACHE

    if not _RMP_JSON.exists():
        raise RuntimeError(f"RMP JSON not found at {_RMP_JSON}")

    with _RMP_JSON.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    _RMP_CACHE = data.get("professors", [])
    return _RMP_CACHE


def _build_course_map() -> Dict[str, List[str]]:  # noqa: D401
    """Return a mapping of *instructor name* → list of course codes."""

    global _COURSE_MAP  # noqa: PLW0603

    if _COURSE_MAP is not None:
        return _COURSE_MAP

    mapping: Dict[str, List[str]] = {}

    for json_path in glob.glob(str(_CATALOG_GLOB)):
        try:
            with open(json_path, "r", encoding="utf-8") as fh:
                program = json.load(fh)
        except Exception:  # noqa: BLE001
            continue

        for course in program.get("courses", []):
            course_code = course.get("course_code")
            for section in course.get("sections", []):
                for meeting in section.get("schedule", []):
                    instructor_raw = meeting.get("instructor")
                    if not instructor_raw:
                        continue

                    # Store canonicalised instructor string
                    name_norm = _normalise_name(instructor_raw)
                    mapping.setdefault(name_norm, []).append(course_code)

    _COURSE_MAP = mapping
    return mapping


# ---------------------------------------------------------------------------
# Helpers -------------------------------------------------------------------
# ---------------------------------------------------------------------------


def _normalise_name(name: str) -> str:  # noqa: D401
    """Return a case-folded, stripped representation suitable for matching."""

    return " ".join(name.strip().lower().split())


# ---------------------------------------------------------------------------
# Pydantic I/O models --------------------------------------------------------
# ---------------------------------------------------------------------------


class PRIn(BaseModel):  # noqa: D401
    """Input schema – at least one of instructor_name or department required."""

    instructor_name: Optional[str] = Field(None, description="Full or partial instructor name.")
    department: Optional[str] = Field(None, description="Department name, e.g. 'Mathematics'.")
    course_code: Optional[str] = Field(
        None,
        description="SMC course code (e.g. 'ACCTG 1') to find all instructors teaching it.",
    )

    @field_validator("department")  # type: ignore[misc]
    def _empty_to_none(cls, v: Optional[str]):  # noqa: D401, N805
        return v.strip() if isinstance(v, str) and v.strip() else None

    @field_validator("instructor_name")  # type: ignore[misc]
    def _empty_to_none2(cls, v: Optional[str]):  # noqa: D401, N805
        return v.strip() if isinstance(v, str) and v.strip() else None

    # Root-level validation to enforce at least one parameter
    @model_validator(mode="after")
    def _check_params(cls, data):  # noqa: D401, N805
        if not data.instructor_name and not data.department and not data.course_code:
            raise ValueError("At least one of instructor_name, department, or course_code is required.")
        return data


class ProfessorOut(BaseModel):  # noqa: D401
    """Per-professor output model."""

    name: str
    department: str
    rating: float
    difficulty: float
    num_ratings: int
    would_take_again_percent: float
    top_comments: List[str]


class PROut(BaseModel):  # noqa: D401
    """Top-level response model."""

    professors: List[ProfessorOut]


# ---------------------------------------------------------------------------
# Core function --------------------------------------------------------------
# ---------------------------------------------------------------------------


def _query_professors(
    *,
    instructor_name: Optional[str] = None,
    department: Optional[str] = None,
    course_code: Optional[str] = None,
):  # type: ignore[override]
    """Return professor ratings filtered by name, department, and/or course code."""

    rmp_data = _load_rmp()
    course_map = _build_course_map()  # Currently unused but triggers cache for future features

    name_norm = _normalise_name(instructor_name) if instructor_name else None
    dept_norm = department.lower() if department else None

    # If course_code provided, narrow rmp_data to instructors teaching that course.
    if course_code:
        code_norm = course_code.strip().upper()
        # Step 1: Find all catalog instructor names for the given course.
        instructors_from_catalog = {
            name_norm
            for name_norm, codes in course_map.items()
            if code_norm in [c.upper() for c in codes]
        }

        if not instructors_from_catalog:
            raise ProfessorNotFoundError(f"No instructors found teaching {code_norm}")

        # Step 2: Convert catalog names (e.g., "supat w") to (last, initial) keys.
        instructor_keys = set()
        for name in instructors_from_catalog:
            parts = name.split()
            if len(parts) >= 2:
                instructor_keys.add((parts[0], parts[1][0]))  # ('supat', 'w')

        # Step 3: Filter RMP data by matching on the (last, initial) key.
        filtered_rmp = []
        for prof in rmp_data:
            prof_name_norm = _normalise_name(prof.get("name", ""))
            prof_parts = prof_name_norm.split()
            if len(prof_parts) >= 2:
                # RMP name is "first last", so key is (last, first_initial)
                rmp_key = (prof_parts[-1], prof_parts[0][0])
                if rmp_key in instructor_keys:
                    filtered_rmp.append(prof)
        rmp_data = filtered_rmp

        if not rmp_data:
            raise ProfessorNotFoundError(f"No rated instructors found teaching {code_norm}")

    matches: List[dict] = []

    for prof in rmp_data:
        # Department filter (if provided)
        if dept_norm and prof.get("department", "").lower() != dept_norm:
            continue

        # Name filter (if provided)
        if name_norm and name_norm not in _normalise_name(prof.get("name", "")):
            continue

        matches.append(prof)

    if not matches:
        raise ProfessorNotFoundError("No professors found for given parameters.")

    # Build structured output
    out_list: List[ProfessorOut] = []
    for prof in matches:
        metrics = prof.get("metrics", {})
        comments = prof.get("top_comments", [])[:5] if prof.get("top_comments") else []

        out_list.append(
            ProfessorOut(
                name=prof.get("name", ""),
                department=prof.get("department", ""),
                rating=float(metrics.get("rating", 0.0)),
                difficulty=float(metrics.get("difficulty", 0.0)),
                num_ratings=int(metrics.get("num_ratings", 0)),
                would_take_again_percent=float(metrics.get("would_take_again_percent", 0.0)),
                top_comments=comments,
            )
        )

    return PROut(professors=out_list).model_dump(mode="json")


# ---------------------------------------------------------------------------
# StructuredTool wrapper -----------------------------------------------------
# ---------------------------------------------------------------------------


ProfessorRatingTool: StructuredTool = StructuredTool.from_function(
    func=_query_professors,
    name="professor_rating",
    description=(
        "Given an instructor name, department, or course code, return rate-my-professor style metrics "
        "for Santa Monica College instructors including rating, difficulty, number of ratings, "
        "would-take-again percentage, and up to five top comments."
    ),
    args_schema=PRIn,
    return_schema=PROut,
)

# Public export --------------------------------------------------------------

__all__ = [
    "ProfessorRatingTool",
    "ProfessorNotFoundError",
]


if __name__ == "__main__":
    result = ProfessorRatingTool.invoke({"course_code": "CS 3"})
    print(result)