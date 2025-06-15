import json
import sys
from pathlib import Path

import pytest

# Ensure project root on sys.path so that `tools` package resolves when running
# tests directly via `pytest tools/tests/...` from repo root.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.schedule_conflict_tool import ScheduleConflictTool, ScheduleConflictInput

# ---------------------------------------------------------------------------
# Helper to extract schedule blocks from parsed_program JSON -----------------
# ---------------------------------------------------------------------------


CATALOG_ROOT = Path(__file__).resolve().parents[2] / "data" / "SMC_catalog" / "parsed_programs"


def load_schedules(filename: str, course_code: str, section_numbers: list[str]):  # noqa: D401
    """Return a list of *schedule* lists for the requested section numbers.

    Parameters
    ----------
    filename : str
        The JSON catalogue file (e.g., ``"accounting.json"``).
    course_code : str
        Canonical course code (e.g., ``"ACCTG 1"``).
    section_numbers : List[str]
        Specific section_number strings to retrieve.
    """

    file_path = CATALOG_ROOT / filename
    data = json.loads(file_path.read_text(encoding="utf-8"))

    for course in data["courses"]:
        if course["course_code"] == course_code:
            return [
                sec["schedule"]
                for sec in course["sections"]
                if sec["section_number"] in section_numbers
            ]

    raise ValueError(f"{course_code} not found in {filename}")


# ---------------------------------------------------------------------------
# Conflict test cases --------------------------------------------------------
# ---------------------------------------------------------------------------


def test_conflict_case_1():
    """ACCTG 1-1003 vs ACCTG 2-1021 should conflict (same MW window)."""

    schedules = load_schedules("accounting.json", "ACCTG 1", ["1003"]) + load_schedules(
        "accounting.json", "ACCTG 2", ["1021"]
    )

    result = ScheduleConflictTool.invoke({"sections": schedules})

    assert result["has_conflict"] is True
    assert [0, 1] in result["conflicting_pairs"]


def test_conflict_case_2():
    """CS 3-1716 (MW 11–2:05) overlaps with PSYC C1000-2976 (MW 11:15–12:35)."""

    schedules = load_schedules("computer_science.json", "CS 3", ["1716"]) + load_schedules(
        "psychology.json", "PSYC C1000", ["2976"]
    )

    result = ScheduleConflictTool.invoke({"sections": schedules})

    assert result["has_conflict"] is True
    assert [0, 1] in result["conflicting_pairs"]


# ---------------------------------------------------------------------------
# No-conflict test cases -----------------------------------------------------
# ---------------------------------------------------------------------------


def test_no_conflict_case_1():
    """ACCTG 1 sections on different days should not conflict."""

    schedules = load_schedules("accounting.json", "ACCTG 1", ["1001"]) + load_schedules(
        "accounting.json", "ACCTG 1", ["1003"]
    )

    result = ScheduleConflictTool.invoke({"sections": schedules})

    assert result["has_conflict"] is False
    assert result["conflicting_pairs"] == []


def test_no_conflict_case_2():
    """Back-to-back TTh blocks (CS 3-1715 vs PSYC C1000-2975) should not overlap."""

    schedules = load_schedules("computer_science.json", "CS 3", ["1715"]) + load_schedules(
        "psychology.json", "PSYC C1000", ["2975"]
    )

    result = ScheduleConflictTool.invoke({"sections": schedules})

    assert result["has_conflict"] is False
    assert result["conflicting_pairs"] == []
