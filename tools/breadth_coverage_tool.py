from __future__ import annotations

"""TransferAI – Breadth Coverage Tool

This module provides :pydata:`BreadthCoverageTool`, a lightweight LangChain
StructuredTool that maps Santa Monica College course codes to IGETC / CSU
breadth areas using the JSON mappings bundled under
``data/assist_igetc_departments`` and ``data/assist_igetc_areas``.

The tool answers the question: *"Given the courses I have already completed,
which breadth areas do I still need?"*

Only the Python standard-library plus ``pydantic`` is required – no external
network or heavyweight dependencies.

NOTE: Some IGETC courses can be for multiple areas, but must only be counted once.
"""

from pathlib import Path
import json
from functools import lru_cache
from collections import defaultdict
from typing import Dict, List, Set, DefaultDict
import re

from pydantic import BaseModel, Field

# Fallback if LangChain is unavailable in minimal CI environments -----------------
try:
    from langchain_core.tools import StructuredTool  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – local stub for CI

    class StructuredTool:  # type: ignore
        """Very small subset shim – enough for .invoke() used in tests."""

        def __init__(self, *, func, name: str, description: str, args_schema, return_schema):  # noqa: D401,E501
            self._func = func
            self.name = name
            self.description = description
            self.args_schema = args_schema
            self.return_schema = return_schema

        def invoke(self, inputs):  # noqa: D401
            return self._func(**inputs)

        @classmethod
        def from_function(cls, func, *, name: str, description: str, args_schema, return_schema):  # noqa: D401,E501
            return cls(func=func, name=name, description=description, args_schema=args_schema, return_schema=return_schema)

# ---------------------------------------------------------------------------
# Constants & Paths ---------------------------------------------------------
# ---------------------------------------------------------------------------

IGETC_DIRS: List[Path] = [
    Path(__file__).resolve().parents[1]
    / "data"
    / "assist_igetc_departments",
    Path(__file__).resolve().parents[1]
    / "data"
    / "assist_igetc_areas",
]

# ---------------------------------------------------------------------------
# Pydantic Schemas ----------------------------------------------------------
# ---------------------------------------------------------------------------


class BreadthCoverageResult(BaseModel):
    """Output container returned by the tool."""

    matched: Dict[str, List[str]] = Field(default_factory=dict)
    missing: List[str] = Field(default_factory=list)
    unmatched_courses: List[str] = Field(default_factory=list)


class _BCIn(BaseModel):  # noqa: D401
    """Input schema for BreadthCoverageTool."""

    student_courses: List[str] = Field(
        ..., description="List of completed SMC course codes (e.g. ['ENGL 1', 'MATH 7'])"
    )


# ---------------------------------------------------------------------------
# Helper Functions ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _normalise_code(code: str) -> str:  # noqa: D401
    """Return canonical course-code representation (uppercase, single space)."""

    cleaned = " ".join(code.strip().upper().split())

    # Insert single space between alpha prefix and numeric part if missing.
    match = re.match(r"^([A-Z]+)\s*(\d+)([A-Z]?)$", cleaned)
    if match:
        prefix, number, suffix = match.groups()
        return f"{prefix} {number}{suffix}"

    return cleaned


def _extract_course_records(obj):  # noqa: D401, ANN001 – object type varies
    """Yield course record dicts from arbitrary JSON structure."""

    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, (dict, list)):
                yield from _extract_course_records(item)
        return

    if not isinstance(obj, dict):
        return

    # Heuristic: if dict has course_code or smc_course => treat as course record
    if any(k in obj for k in ("course_code", "smc_course", "course")):
        yield obj

    # Recurse into potential containers
    for key in ("courses", "data", "records"):
        if key in obj and isinstance(obj[key], (list, dict)):
            yield from _extract_course_records(obj[key])


@lru_cache(maxsize=1)
def _load_igetc_course_map() -> Dict[str, Set[str]]:  # noqa: D401
    """Return mapping ``{course_code: {area_codes}}`` memoised for process lifetime."""

    mapping: Dict[str, Set[str]] = defaultdict(set)

    for folder in IGETC_DIRS:
        if not folder.exists():
            continue

        for json_file in folder.glob("*.json"):
            try:
                with json_file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception:  # pragma: no cover – skip unreadable files
                continue

            for record in _extract_course_records(data):
                # Skip inactive course at *record* level if present
                if not bool(record.get("is_active", True)):
                    continue

                # Determine course code -----------------------------------
                raw_code = (
                    record.get("course_code")
                    or record.get("smc_course")
                    or record.get("course")
                    or record.get("smcCourse")
                )
                if not raw_code or not isinstance(raw_code, str):
                    continue

                norm_code = _normalise_code(raw_code)

                # Determine breadth areas --------------------------------
                areas: Set[str] = set()

                if "igetc_area" in record and record["igetc_area"]:
                    areas.add(str(record["igetc_area"]).strip().upper())

                if "area" in record and record.get("igetc_area") is None:  # area fallback
                    # Some records may use "area" key directly
                    areas.add(str(record["area"]).strip().upper())

                if "igetc_areas" in record and isinstance(record["igetc_areas"], list):
                    for ar in record["igetc_areas"]:
                        if isinstance(ar, dict):
                            # Respect is_active on area sub-record if present
                            if not bool(ar.get("is_active", True)):
                                continue
                            area_code = ar.get("area") or ar.get("igetc_area")
                            if area_code:
                                areas.add(str(area_code).strip().upper())
                        elif isinstance(ar, str):
                            areas.add(str(ar).strip().upper())

                # No area codes found – skip
                if not areas:
                    continue

                mapping[norm_code].update(areas)

    return dict(mapping)  # Cast back to regular dict for immutability


# ---------------------------------------------------------------------------
# Core Coverage Computation -------------------------------------------------
# ---------------------------------------------------------------------------


def _compute_coverage(student_courses: List[str]) -> BreadthCoverageResult:  # noqa: D401
    """Return coverage result for *student_courses*."""

    mapping = _load_igetc_course_map()

    # Compute universe of areas once from mapping --------------------------------
    all_areas: Set[str] = set()
    for areas in mapping.values():
        all_areas.update(areas)

    matched_dict: DefaultDict[str, Set[str]] = defaultdict(set)
    unmatched: Set[str] = set()

    for course in student_courses:
        norm = _normalise_code(course)
        if norm in mapping:
            for area in mapping[norm]:
                matched_dict[area].add(norm)
        else:
            unmatched.add(norm)

    # Sort for deterministic output and convert sets to lists
    matched_sorted = {area: sorted(list(courses)) for area, courses in matched_dict.items()}
    missing_sorted = sorted(all_areas - set(matched_sorted))
    unmatched_sorted = sorted(list(unmatched))  # Convert set to sorted list

    return BreadthCoverageResult(
        matched=matched_sorted,
        missing=missing_sorted,
        unmatched_courses=unmatched_sorted,
    )


# ---------------------------------------------------------------------------
# LangChain StructuredTool wrapper -----------------------------------------
# ---------------------------------------------------------------------------


def _coverage_func(student_courses: List[str]):  # type: ignore[override]
    """Function exposed via LangChain StructuredTool."""

    return _compute_coverage(student_courses).model_dump(mode="json")


BreadthCoverageTool: StructuredTool = StructuredTool.from_function(
    func=_coverage_func,
    name="breadth_coverage",
    description=(
        "Given a list of Santa Monica College course codes, return which IGETC / "
        "CSU breadth areas are satisfied and which areas are still missing. "
        "Returns `matched`, `missing`, and `unmatched_courses` keys."
    ),
    args_schema=_BCIn,
    return_schema=BreadthCoverageResult,
)

# Exports ------------------------------------------------------------------

__all__ = [
    "BreadthCoverageTool",
    "BreadthCoverageResult",
]

# ---------------------------------------------------------------------------
# Manual demo ---------------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover – simple CLI demo
    sample = ["ENGL 1", "MATH 7", "HIST 11"]
    import json as _json

    output = BreadthCoverageTool.invoke({"student_courses": sample})
    print(_json.dumps(output, indent=2))
