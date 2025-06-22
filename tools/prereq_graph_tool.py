from __future__ import annotations

"""TransferAI – Prerequisite Graph Tool

This module exposes :data:`PrereqGraphTool`, a lightweight LangChain
`StructuredTool` that crawls prerequisite / corequisite / advisory chains for a
single course and returns a transitive dependency graph.

The design purposefully avoids any dependency on *CourseSearchTool* as
mandated.  Only :data:`tools.course_detail_tool.CourseDetailTool` is used for
course-existence validation.  All catalogue look-ups are wrapped with
``functools.lru_cache`` so repeated invocations are fast.
"""

from collections import defaultdict
from functools import lru_cache
from typing import DefaultDict, Dict, List, Literal, Set
import re

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Optional LangChain import – we embed a stub for minimal CI environments.
# ---------------------------------------------------------------------------
try:
    from langchain_core.tools import StructuredTool  # type: ignore
except ModuleNotFoundError:  # pragma: no cover

    class StructuredTool:  # type: ignore[too-few-public-methods]
        """Very small subset stub mirroring the API we consume (only .invoke)."""

        def __init__(self, *, func, name: str, description: str, args_schema, return_schema):
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
# Conditional import for CourseDetailTool - handle script execution
# ---------------------------------------------------------------------------

def _get_course_detail_tool():
    """Lazy import of CourseDetailTool to handle direct script execution."""
    try:
        from tools.course_detail_tool import CourseDetailTool, CourseNotFoundError
        return CourseDetailTool, CourseNotFoundError
    except ImportError:
        # If running as script, try adding project root to path
        import sys
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        from tools.course_detail_tool import CourseDetailTool, CourseNotFoundError
        return CourseDetailTool, CourseNotFoundError

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class RequirementEdge(BaseModel):
    """A logical relationship among *courses* leading into a target node."""

    type: Literal["prereq", "coreq", "advisory"]
    logic: Literal["AND", "OR"]
    courses: List[str]


class PrereqGraph(BaseModel):
    """Return object holding the full transitive prerequisite graph."""

    root: str  # Canonical root course code
    edges: Dict[str, List[RequirementEdge]] = Field(default_factory=dict)
    missing_courses: List[str] = Field(default_factory=list, description="Courses referenced in prerequisites but not found in catalog")


class _PGIn(BaseModel):  # noqa: D401
    """Input schema for PrereqGraphTool."""

    course_code: str = Field(..., description="Course code to inspect (e.g. 'MATH 7')")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


_CODE_RE = re.compile(r"([A-Z]{2,}\s*\d+[A-Z]?)", re.IGNORECASE)
_AND_RE = re.compile(r"\bAND\b|,|;", re.IGNORECASE)
_OR_RE = re.compile(r"\bOR\b|/", re.IGNORECASE)
_BRACKET_CONTENT_RE = re.compile(r"\([^)]*\)")


def _normalise_code(code: str) -> str:  # noqa: D401
    """Return canonical course-code representation (uppercase, single space)."""

    cleaned = " ".join(code.strip().upper().split())
    match = re.match(r"^([A-Z]+)\s*(\d+)([A-Z]?)$", cleaned)
    if match:
        prefix, number, suffix = match.groups()
        return f"{prefix} {number}{suffix}"
    return cleaned


def _strip_irrelevant_phrases(text: str) -> str:  # noqa: D401
    """Remove phrases unrelated to course codes (time-limits, etc.)."""

    # Drop content within parentheses that mentions phrases like 'same as', 'within'
    def _should_remove(segment: str) -> bool:
        lowered = segment.lower()
        return any(kw in lowered for kw in ["same as", "within", "placement", "permission", "department consent"])

    parts: List[str] = []
    last_end = 0
    for m in _BRACKET_CONTENT_RE.finditer(text):
        segment = m.group(0)
        if _should_remove(segment):
            parts.append(text[last_end : m.start()])
            last_end = m.end()
    parts.append(text[last_end:])
    return "".join(parts)


# ---------------------------------------------------------------------------
# Parsing helpers for nested logic (top-level OR handling)
# ---------------------------------------------------------------------------


def _split_by_top_level_or(text: str) -> List[str]:
    """Split *text* by top-level OR delimiters (word 'or', slash '/').

    Parentheses are respected so delimiters inside them do **not** cause a split.
    Returns a list of non-empty segment strings with surrounding whitespace trimmed.
    """

    segments: List[str] = []
    buf: List[str] = []
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ")":
            depth = max(depth - 1, 0)
            buf.append(ch)
            i += 1
            continue

        # Check for top-level OR delimiters ---------------------------------
        if depth == 0:
            # Slash treated as OR
            if ch == "/":
                segment = "".join(buf).strip()
                if segment:
                    segments.append(segment)
                buf.clear()
                i += 1
                continue

            # Keyword OR (case-insensitive, word-bounded)
            if text[i : i + 2].upper() == "OR":
                prev_char = text[i - 1] if i > 0 else " "
                next_char = text[i + 2] if i + 2 < len(text) else " "
                if not prev_char.isalpha() and not next_char.isalpha():
                    # word boundary – treat as delimiter
                    segment = "".join(buf).strip()
                    if segment:
                        segments.append(segment)
                    buf.clear()
                    i += 2
                    continue

        # Default – accumulate char
        buf.append(ch)
        i += 1

    # last buffer
    segment = "".join(buf).strip()
    if segment:
        segments.append(segment)
    return segments


def _parse_requirement_text(text: str, req_type: str) -> List[RequirementEdge]:  # noqa: D401
    """Convert *text* into a list of :class:`RequirementEdge` respecting top-level OR."""

    if not text:
        return []

    # Pre-clean ----------------------------------------------------------------
    cleaned = _strip_irrelevant_phrases(text)

    # Split by top-level OR ----------------------------------------------------
    segments = _split_by_top_level_or(cleaned)

    edges: List[RequirementEdge] = []

    for seg in segments:
        # Remove wrapping parentheses
        if seg.startswith("(") and seg.endswith(")"):
            seg = seg[1:-1].strip()

        # Replace AND delimiters with space for regex capture
        seg_clean = _AND_RE.sub(" ", seg)
        # Extract course codes
        courses = {_normalise_code(c) for c in _CODE_RE.findall(seg_clean)}
        if not courses:
            continue

        logic: Literal["AND", "OR"] = "AND"  # inside segment it's AND by construction
        edge = RequirementEdge(type=req_type, logic=logic, courses=sorted(courses))
        edges.append(edge)

    return edges


# ---------------------------------------------------------------------------
# Data-fetching helper with memoisation
# ---------------------------------------------------------------------------


@lru_cache(maxsize=2048)
def _fetch_course_detail(code: str):  # noqa: D401
    """Wrapper around CourseDetailTool.invoke with LRU caching."""
    CourseDetailTool, _ = _get_course_detail_tool()
    return CourseDetailTool.invoke({"course_code": code})


# ---------------------------------------------------------------------------
# Core DFS traversal
# ---------------------------------------------------------------------------

graph: DefaultDict[str, List[RequirementEdge]]  # module-level placeholder (populated per call)
missing_courses: Set[str]  # module-level set to collect missing courses


def _dfs(code: str, seen: Set[str]) -> None:  # noqa: D401
    """Depth-first traversal populating *graph* from global context."""

    if code in seen:
        return
    seen.add(code)

    try:
        detail = _fetch_course_detail(code)
    except Exception:  # Catch any course lookup error
        # Course not found - add to missing courses and return
        missing_courses.add(code)
        return

    # Some catalogues use 'advisory', others 'advisories'
    column_mapping = [
        ("prerequisites", "prereq"),
        ("corequisites", "coreq"),
        ("advisories", "advisory"),
        ("advisory", "advisory"),
    ]

    for col, typ in column_mapping:
        text = (detail.get(col) or "").strip()
        if not text:
            continue
        edges = _parse_requirement_text(text, typ)  # type: ignore[arg-type]
        if not edges:
            continue
        graph[code].extend(edges)
        # recurse
        for edge in edges:
            for c in edge.courses:
                _dfs(c, seen)


# ---------------------------------------------------------------------------
# Public build function
# ---------------------------------------------------------------------------


def _build_prereq_graph(course_code: str) -> tuple[Dict[str, List[RequirementEdge]], List[str]]:  # noqa: D401
    global graph, missing_courses  # noqa: PLW0603 – reuse globals to avoid passing around
    graph = defaultdict(list)
    missing_courses = set()

    norm_root = _normalise_code(course_code)

    # Check if root course exists - if not, return empty graph with missing root
    try:
        _fetch_course_detail(norm_root)
    except Exception:  # Catch any course lookup error
        return {}, [norm_root]

    _dfs(norm_root, set())
    return graph, sorted(missing_courses)


# ---------------------------------------------------------------------------
# LangChain StructuredTool wrapper
# ---------------------------------------------------------------------------


def _prereq_func(course_code: str):  # type: ignore[override]
    """Entry point for LangChain."""
    norm_root = _normalise_code(course_code)
    edges_dict, missing_courses = _build_prereq_graph(norm_root)
    result = PrereqGraph(root=norm_root, edges=edges_dict, missing_courses=missing_courses)
    return result.model_dump(mode="json")


PrereqGraphTool: StructuredTool = StructuredTool.from_function(
    func=_prereq_func,
    name="prereq_graph",
    description=(
        "Return the full transitive prerequisite/corequisite/advisory graph for a given "
        "Santa Monica College course. Input: course_code."
    ),
    args_schema=_PGIn,
    return_schema=PrereqGraph,
)

# Public exports ------------------------------------------------------------

__all__ = [
    "PrereqGraphTool",
    "PrereqGraph",
    "RequirementEdge",
]

# ---------------------------------------------------------------------------
# CLI helper – run with `python -m tools.prereq_graph_tool --course "MATH 8"`
#              or `python tools/prereq_graph_tool.py --course "MATH 8"`
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json as _json
    import sys

    parser = argparse.ArgumentParser(description="CLI wrapper around PrereqGraphTool")
    parser.add_argument("--course", required=True, help="Course code to analyze, e.g. 'MATH 8'")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    try:
        result = PrereqGraphTool.invoke({"course_code": args.course})

        if args.pretty:
            print(_json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(_json.dumps(result, ensure_ascii=False))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
