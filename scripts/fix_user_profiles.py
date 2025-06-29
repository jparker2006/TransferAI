from __future__ import annotations
"""Update user profiles with correct units_completed and GPA.

This script scans ``evals/user_profiles/*.json`` and, for each profile:
1. Computes the total semester units using :pydata:`tools.unit_calculator_tool.UnitCalculatorTool`.
2. Builds a *planned course* list (units + expected letter grade) for every
   course entry in the profile.
3. Invokes :pydata:`tools.gpa_projection_tool.GPAProjectionTool` assuming the
   student has **0 completed units** and all listed courses are *planned* –
   effectively reproducing the current cumulative SMC GPA on the 4-point
   simple scale.
4. Writes the updated ``units_completed`` and ``gpa`` values back to the file.

Run with: ``python scripts/fix_user_profiles.py``
"""

# Ensure project root resolvable when run from within ``scripts`` -------------
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Third-party / project imports ---------------------------------------------
# ---------------------------------------------------------------------------

import json
from typing import Dict, List, Any

from tools.unit_calculator_tool import UnitCalculatorTool
from tools.gpa_projection_tool import GPAProjectionTool
from tools.course_detail_tool import CourseNotFoundError

# ---------------------------------------------------------------------------
# Helper functions ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _normalise(code: str) -> str:  # noqa: D401
    """Return catalogue-normalised representation (upper-case, single space)."""

    return " ".join(code.upper().split())


def _calc_units(course_codes: List[str]) -> Dict[str, float]:  # noqa: D401
    """Return *breakdown* mapping via UnitCalculatorTool (str→units).

    Any course not present in the local catalog is silently skipped (a warning
    is printed). This prevents the entire run from failing when a profile
    references a deprecated or placeholder course code.
    """

    breakdown: Dict[str, float] = {}

    for code in course_codes:
        try:
            # Query one course at a time to isolate missing-course errors
            out = UnitCalculatorTool.invoke({"course_codes": [code]})
            breakdown.update(out["breakdown"])
        except CourseNotFoundError:
            print(f"[WARN] {code} not found in catalog – skipped")
            continue

    return breakdown


# ---------------------------------------------------------------------------
# Main processing -----------------------------------------------------------
# ---------------------------------------------------------------------------

PROFILES_DIR = ROOT / "evals" / "user_profiles"


def _update_profile(path: Path) -> None:  # noqa: D401
    """Update *path* in-place with correct units_completed and gpa."""

    data: Dict[str, Any] = json.loads(path.read_text())
    courses: List[Dict[str, str]] = data.get("courses", [])
    course_codes = [_normalise(c["code"]) for c in courses]

    # 1. Unit calculation ---------------------------------------------------
    breakdown = _calc_units(course_codes)
    total_units = sum(breakdown.values())

    if not breakdown:
        print(f"[INFO] No valid course units found for {path.name}; skipping update.")
        return

    # 2. Build planned_courses payload -------------------------------------
    planned = []
    for entry in courses:
        code = _normalise(entry["code"])
        grade = entry["grade"].strip().upper()
        units_val = breakdown.get(code)
        if units_val is None:
            # Unknown course – skip from GPA calc but still counts units 0
            continue
        planned.append({
            "course_code": code,
            "units": units_val,
            "letter_grade": grade,
        })

    # 3. GPA projection -----------------------------------------------------
    gpa_out = GPAProjectionTool.invoke({
        "current_gpa": 0.0,
        "units_completed": 0.0001,  # minimal positive to satisfy validator
        "planned_courses": planned,
        "gpa_type": "smc",
    })
    projected_gpa = gpa_out["projected_gpa"]  # type: ignore[index]

    # 4. Persist updates ----------------------------------------------------
    data["units_completed"] = int(total_units) if total_units.is_integer() else total_units
    data["gpa"] = projected_gpa

    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Updated {path.name}: units={total_units}, GPA={projected_gpa}")


def main() -> None:  # noqa: D401
    for file_path in PROFILES_DIR.glob("U*.json"):
        # Run update, then normalise dash in schedule
        _update_profile(file_path)

        # reload, fix dashes, write back
        data = json.loads(file_path.read_text())
        sched = data.get("current_schedule", [])
        if isinstance(sched, list):
            for ent in sched:
                if isinstance(ent, dict):
                    _fix_schedule_dashes(ent)
            file_path.write_text(json.dumps(data, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Utility: replace unicode dashes with ASCII hyphen in schedule -------------
# ---------------------------------------------------------------------------


def _fix_schedule_dashes(entry: Dict[str, Any]) -> None:  # noqa: D401
    if "time" in entry and isinstance(entry["time"], str):
        entry["time"] = entry["time"].replace("\u2013", "-").replace("\u2014", "-")


if __name__ == "__main__":  # pragma: no cover
    main() 