import json
import sys
from pathlib import Path

import pytest

# Ensure root importability
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.professor_rating_tool import ProfessorRatingTool, ProfessorNotFoundError

RMP_PATH = ROOT / "data" / "Professor_Ratings" / "santa_monica_college_professors_rag.json"

# Helper to fetch exemplar professor names and departments from RMP JSON for assertions
with open(RMP_PATH, "r", encoding="utf-8") as _fh:
    _RMP_DATA = json.load(_fh)["professors"]


@pytest.fixture(scope="module")
def rex_perez_entry():
    return next(p for p in _RMP_DATA if p["name"] == "Rex Perez")


def test_lookup_by_exact_name(rex_perez_entry):
    result = ProfessorRatingTool.invoke({"instructor_name": "Rex Perez"})
    assert result["professors"][0]["name"] == "Rex Perez"
    assert pytest.approx(result["professors"][0]["rating"], rel=1e-3) == rex_perez_entry["metrics"]["rating"]


def test_lookup_by_partial_name():
    # "Perez" should match at least Rex Perez plus potentially others
    result = ProfessorRatingTool.invoke({"instructor_name": "Perez"})
    names = {prof["name"] for prof in result["professors"]}
    assert any("Perez" in n for n in names)


def test_lookup_by_department():
    result = ProfessorRatingTool.invoke({"department": "Mathematics"})
    # Expect multiple entries
    assert len(result["professors"]) >= 3
    for prof in result["professors"]:
        assert prof["department"].lower() == "mathematics"


def test_not_found_raises():
    with pytest.raises(ProfessorNotFoundError):
        ProfessorRatingTool.invoke({"instructor_name": "Nonexistent Professor Xyz"})


# ---------------------------------------------------------------------------
# Course-code lookup tests ---------------------------------------------------
# ---------------------------------------------------------------------------


def test_lookup_by_course_code():
    """Course CS 3 should return at least instructor with last name Supat."""

    result = ProfessorRatingTool.invoke({"course_code": "CS 3"})
    names = {p["name"].lower() for p in result["professors"]}
    assert any("supat" in n for n in names)


def test_invalid_course_code():
    with pytest.raises(ProfessorNotFoundError):
        ProfessorRatingTool.invoke({"course_code": "ZZZ 999"})
