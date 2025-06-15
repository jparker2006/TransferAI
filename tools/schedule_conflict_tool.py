from __future__ import annotations

"""TransferAI – Schedule Conflict Detection Tool

Given multiple Santa Monica College course sections (as returned by
:pyattr:`tools.section_lookup_tool.SectionLookupTool` – specifically the
``section["schedule"]`` lists), determine whether any meeting-time conflicts
exist between the provided sections.

The tool ignores asynchronous or arranged components (those whose *days*
value is ``"N"`` or whose *time* string starts with ``"Arrange"``) because they
cannot clash with fixed meeting times.

Example
-------
>>> from tools.schedule_conflict_tool import ScheduleConflictTool
>>> ScheduleConflictTool.invoke({
...     "sections": [
...         [{"days": "MW", "time": "9:30a.m.-11:55a.m."}],
...         [{"days": "MW", "time": "10:45a.m.-12:10p.m."}],
...     ]
... })
{'has_conflict': True,
 'conflicting_pairs': [(0, 1)],
 'conflict_descriptions': ['Section 0 (MW 9:30a.m.-11:55a.m.) overlaps with Section 1 (MW 10:45a.m.-12:10p.m.)']}
"""

from datetime import time
from typing import Dict, List, Set, Tuple
import re
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

# ---------------------------------------------------------------------------
# Pydantic schemas -----------------------------------------------------------
# ---------------------------------------------------------------------------


class ScheduleConflictInput(BaseModel):  # noqa: D401
    """Input schema – list of section *schedule* arrays."""

    sections: List[List[Dict[str, str]]] = Field(
        ...,
        description="Each item represents a section's schedule list, i.e. the value of section['schedule'] from SectionLookupTool.",
    )


class ConflictReport(BaseModel):  # noqa: D401
    """Output schema describing any detected conflicts."""

    has_conflict: bool
    conflicting_pairs: List[Tuple[int, int]]
    conflict_descriptions: List[str]


# ---------------------------------------------------------------------------
# Helper utilities -----------------------------------------------------------
# ---------------------------------------------------------------------------


_DAY_TOKEN_RE = re.compile(r"Th|Su|Sa|M|T|W|F")

_DAY_TO_INDEX = {
    "M": 0,  # Monday
    "T": 1,  # Tuesday
    "W": 2,  # Wednesday
    "Th": 3,  # Thursday
    "F": 4,  # Friday
    "Sa": 5,  # Saturday
    "Su": 6,  # Sunday
}


def _parse_days(days_str: str) -> Set[int]:  # noqa: D401
    """Return a set of weekday indices represented by *days_str*.

    Handles compact notations like 'MW', 'TTh', 'WF', etc.  The special code
    'N' signifies an online/arranged component and therefore yields an empty
    set.
    """

    cleaned = days_str.strip()
    if cleaned.upper() == "N":
        return set()

    tokens = _DAY_TOKEN_RE.findall(cleaned)
    day_indices = {_DAY_TO_INDEX[tok] for tok in tokens if tok in _DAY_TO_INDEX}
    return day_indices


_TIME_RE = re.compile(r"^(?P<h>\d{1,2})(?::(?P<m>\d{2}))?(?P<ampm>[ap])m$")


def _parse_single_time(t_str: str) -> time | None:  # noqa: D401
    """Convert a single time like '8:30a.m.' to :pyclass:`datetime.time`.

    Return *None* if the string cannot be parsed.
    """

    clean = (
        t_str.strip()
        .lower()
        .replace(" ", "")
        .replace(".", "")  # '8:30a.m.' -> '8:30am'
    )
    match = _TIME_RE.match(clean)
    if not match:
        return None

    hour = int(match.group("h"))
    minute = int(match.group("m") or 0)
    ampm = match.group("ampm")

    if ampm == "p" and hour != 12:
        hour += 12
    elif ampm == "a" and hour == 12:
        hour = 0

    return time(hour=hour, minute=minute)


def _parse_time_range(range_str: str) -> Tuple[time, time] | None:  # noqa: D401
    """Parse *range_str* of the form '8:30a.m.-10:55a.m.'.

    Return (start_time, end_time).  If the string contains 'Arrange' or cannot
    be parsed, return *None*.
    """

    if "arrange" in range_str.lower():
        return None

    parts = [p.strip() for p in range_str.split("-", 1)]
    if len(parts) != 2:
        return None

    start_t = _parse_single_time(parts[0])
    end_t = _parse_single_time(parts[1])

    if start_t is None or end_t is None:
        return None

    return (start_t, end_t)


def _times_overlap(a_start: time, a_end: time, b_start: time, b_end: time) -> bool:  # noqa: D401
    """Return *True* if two time intervals overlap (exclusive of boundaries)."""

    return (a_start < b_end) and (b_start < a_end)


# ---------------------------------------------------------------------------
# Core computation -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _detect_conflicts(*, sections: List[List[Dict[str, str]]]):  # type: ignore[override]
    """Return a :class:`ConflictReport` for the provided *sections*."""

    # Build an intermediate representation: list[section_index] -> list of
    # tuples (days_set, start_time, end_time, original_days, original_time).
    parsed: List[List[Tuple[Set[int], time, time, str, str]]] = []

    for sched_list in sections:
        section_entries: List[Tuple[Set[int], time, time, str, str]] = []
        for entry in sched_list:
            days_raw: str | None = entry.get("days")  # type: ignore[assignment]
            time_raw: str | None = entry.get("time")  # type: ignore[assignment]
            if not days_raw or not time_raw:
                # Skip malformed entries silently
                continue

            day_set = _parse_days(days_raw)
            if not day_set:
                # No fixed meeting days (online/arranged) → skip
                continue

            time_tuple = _parse_time_range(time_raw)
            if time_tuple is None:
                continue

            start_t, end_t = time_tuple
            section_entries.append((day_set, start_t, end_t, days_raw, time_raw))

        parsed.append(section_entries)

    conflicting_pairs: List[Tuple[int, int]] = []
    conflict_descriptions: List[str] = []

    num_sections = len(parsed)
    for i in range(num_sections):
        for j in range(i + 1, num_sections):
            conflict_found = False
            for day_set_i, s_i, e_i, days_i_raw, time_i_raw in parsed[i]:
                for day_set_j, s_j, e_j, days_j_raw, time_j_raw in parsed[j]:
                    if day_set_i & day_set_j and _times_overlap(s_i, e_i, s_j, e_j):
                        # Record pair only once even if multiple overlapping components
                        if (i, j) not in conflicting_pairs:
                            conflicting_pairs.append((i, j))
                        if not conflict_found:
                            conflict_descriptions.append(
                                f"Section {i} ({days_i_raw} {time_i_raw}) overlaps with "
                                f"Section {j} ({days_j_raw} {time_j_raw})"
                            )
                            conflict_found = True
                        # We can break after first conflict between the two sections
                        break
                if conflict_found:
                    break

    has_conflict = bool(conflicting_pairs)

    return ConflictReport(
        has_conflict=has_conflict,
        conflicting_pairs=conflicting_pairs,
        conflict_descriptions=conflict_descriptions,
    ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# StructuredTool wrapper -----------------------------------------------------
# ---------------------------------------------------------------------------


ScheduleConflictTool: StructuredTool = StructuredTool.from_function(
    func=_detect_conflicts,
    name="schedule_conflict",
    description=(
        "Given a list of SMC section schedule blocks, determine whether any time "
        "conflicts exist between the sections. Days without fixed meeting times "
        "(code 'N' or 'Arrange') are ignored. The tool returns a boolean flag, "
        "conflicting section index pairs, and human-readable descriptions."
    ),
    args_schema=ScheduleConflictInput,
    return_schema=ConflictReport,
)

# Public export --------------------------------------------------------------

__all__ = ["ScheduleConflictTool"]

# ---------------------------------------------------------------------------
# Manual demo ----------------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import json

    demo_input = {
        "sections": [
            [{"days": "MW", "time": "9:30a.m.-11:55a.m."}],
            [{"days": "MW", "time": "10:45a.m.-12:10p.m."}],
            [{"days": "F", "time": "2:00p.m.-4:30p.m."}],
        ]
    }

    print(json.dumps(ScheduleConflictTool.invoke(demo_input), indent=2))
