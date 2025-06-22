from __future__ import annotations

"""Comprehensive tests for PrereqGraphTool using real SMC catalog data.

These tests use real prerequisite chains from Santa Monica College catalog to
verify the tool handles complex scenarios including:
- MATH 20 edge case (referenced but not defined in catalog)
- Deep chains: PHYSCS 22 → MATH 8 → MATH 7 → MATH 2 → MATH 20 + MATH 32
- Complex branching: MATH 2 prerequisites with AND logic
- Chemistry sequences with multiple prerequisites
- OR logic in prerequisites
- Corequisites vs prerequisites
- Advisory relationships
"""

from typing import Dict
from pathlib import Path
import sys

import pytest

# Ensure project root importable when running file directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.prereq_graph_tool import (
    PrereqGraphTool,
    PrereqGraph,
    RequirementEdge,
)

from tools import prereq_graph_tool as _pg_mod  # for internal helpers

# ---------------------------------------------------------------------------
# Real SMC catalog data - comprehensive prerequisite chains
# ---------------------------------------------------------------------------

_REAL_SMC_CATALOG: Dict[str, Dict[str, str]] = {
    # MATH 20 edge case - referenced but not defined (developmental math)
    "MATH 20": {
        "course_code": "MATH 20",
        # No prerequisites - this is a foundational course
    },
    
    # MATH 32 - also foundational (likely geometry/trigonometry)
    "MATH 32": {
        "course_code": "MATH 32",
        # No prerequisites - foundational course
    },
    
    # Real deep chain: MATH 2 requires MATH 20 AND MATH 32
    "MATH 2": {
        "course_code": "MATH 2",
        "course_title": "PRECALCULUS",
        "prerequisites": "MATH 20 and MATH 32",
        "advisory": "Eligibility for English 1",
    },
    
    # Alternative path: MATH 3 and MATH 4 also require MATH 20 + MATH 32
    "MATH 3": {
        "course_code": "MATH 3", 
        "course_title": "TRIGONOMETRY WITH APPLICATIONS",
        "prerequisites": "MATH 20 and MATH 32",
        "advisory": "MATH 4 and eligibility for English 1",
    },
    
    "MATH 4": {
        "course_code": "MATH 4",
        "course_title": "COLLEGE ALGEBRA FOR STEM MAJORS", 
        "prerequisites": "MATH 20",
        "advisory": "Eligibility for English 1",
    },
    
    # MATH 7 has OR logic: MATH 2 OR (MATH 3 AND MATH 4)
    "MATH 7": {
        "course_code": "MATH 7",
        "course_title": "CALCULUS 1",
        "prerequisites": "MATH 2 or (MATH 3 and MATH 4)",
    },
    
    # MATH 8 requires MATH 7 - continues the chain
    "MATH 8": {
        "course_code": "MATH 8", 
        "course_title": "CALCULUS 2",
        "prerequisites": "MATH 7",
    },
    
    # Advanced math requiring MATH 8
    "MATH 10": {
        "course_code": "MATH 10",
        "course_title": "DISCRETE STRUCTURES", 
        "prerequisites": "MATH 8",
    },
    
    "MATH 11": {
        "course_code": "MATH 11",
        "course_title": "MULTIVARIABLE CALCULUS",
        "prerequisites": "MATH 8", 
    },
    
    "MATH 13": {
        "course_code": "MATH 13",
        "course_title": "LINEAR ALGEBRA",
        "prerequisites": "MATH 8",
        "advisory": "Eligibility for English 1",
    },
    
    "MATH 15": {
        "course_code": "MATH 15",
        "course_title": "ORDINARY DIFFERENTIAL EQUATIONS",
        "prerequisites": "MATH 8",
    },
    
    # Physics chain: PHYSCS 21 requires MATH 7
    "PHYSCS 21": {
        "course_code": "PHYSCS 21",
        "course_title": "MECHANICS WITH LAB",
        "prerequisites": "MATH 7",
    },
    
    # PHYSCS 22 requires MATH 8 AND PHYSCS 21 - deep branching chain
    "PHYSCS 22": {
        "course_code": "PHYSCS 22", 
        "course_title": "ELECTRICITY AND MAGNETISM WITH LAB",
        "prerequisites": "MATH 8, PHYSCS 21",
    },
    
    "PHYSCS 23": {
        "course_code": "PHYSCS 23",
        "course_title": "FLUIDS, WAVES, THERMODYNAMICS, OPTICS WITH LAB", 
        "prerequisites": "MATH 8, PHYSCS 21",
    },
    
    # Chemistry sequences
    "CHEM 10": {
        "course_code": "CHEM 10",
        "course_title": "INTRODUCTORY GENERAL CHEMISTRY",
        "prerequisites": "MATH 31 or MATH 49",
    },
    
    "CHEM 11": {
        "course_code": "CHEM 11", 
        "course_title": "GENERAL CHEMISTRY I",
        "prerequisites": "CHEM 10",
        "corequisites": "MATH 2 or (MATH 3 and MATH 4)",
    },
    
    "CHEM 12": {
        "course_code": "CHEM 12",
        "course_title": "GENERAL CHEMISTRY II", 
        "prerequisites": "MATH 2 or (MATH 3 and MATH 4) and CHEM 11",
    },
    
    # Statistics with OR prerequisites 
    "STAT C1000": {
        "course_code": "STAT C1000",
        "course_title": "INTRODUCTION TO STATISTICS",
        "prerequisites": "MATH 18 or MATH 20 or MATH 49 or MATH 50",
    },
    
    "MATH 21": {
        "course_code": "MATH 21",
        "course_title": "FINITE MATHEMATICS",
        "prerequisites": "MATH 18 or MATH 20 or MATH 49 or MATH 50",
    },
    
    # Business calculus with different chain
    "MATH 26": {
        "course_code": "MATH 26",
        "course_title": "COLLEGE ALGEBRA FOR BUSINESS",
        "prerequisites": "MATH 18 or MATH 20 or MATH 49 or MATH 50",
    },
    
    "MATH 28": {
        "course_code": "MATH 28",
        "course_title": "CALCULUS 1 FOR BUSINESS AND SOCIAL SCIENCE",
        "prerequisites": "MATH 26",
    },
    
    # Foundational courses (no prerequisites)
    "MATH 18": {"course_code": "MATH 18"},
    "MATH 31": {"course_code": "MATH 31"}, 
    "MATH 49": {"course_code": "MATH 49"},
    "MATH 50": {"course_code": "MATH 50"},
}


# ---------------------------------------------------------------------------
# Fixtures & monkey-patching helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def monkeypatch_course_detail(monkeypatch):
    """Replace _fetch_course_detail with synthetic SMC catalog data.
    
    This fixture simulates the real catalog behavior where some foundational
    courses like MATH 20, MATH 32 are referenced but not defined.
    """
    missing_forced = {
        "MATH 18",
        "MATH 20",
        "MATH 31",
        "MATH 32",
        "MATH 49",
        "MATH 50",
    }

    def mock_fetch_course_detail(code: str):
        norm = code
        if norm in missing_forced:
            raise ValueError(f"Course '{norm}' not found in catalog (forced missing)")
        if norm in _REAL_SMC_CATALOG:
            return _REAL_SMC_CATALOG[norm]
        raise ValueError(f"Course '{norm}' not found in catalog")
    
    # Clear any existing cache before patching
    import tools.prereq_graph_tool as pg_mod
    if hasattr(pg_mod._fetch_course_detail, 'cache_clear'):
        pg_mod._fetch_course_detail.cache_clear()
    
    monkeypatch.setattr("tools.prereq_graph_tool._fetch_course_detail", mock_fetch_course_detail)
    return mock_fetch_course_detail


# ---------------------------------------------------------------------------
# Tests - real SMC prerequisite scenarios
# ---------------------------------------------------------------------------


def test_math_20_edge_case(monkeypatch_course_detail):
    """Test MATH 20 edge case - referenced but not defined in catalog."""
    result_dict = PrereqGraphTool.invoke({"course_code": "MATH 20"})
    graph = PrereqGraph(**result_dict)
    
    assert graph.root == "MATH 20"
    # MATH 20 has no prerequisites, so it won't appear in edges dict
    assert len(graph.edges) == 0
    # MATH 20 should appear in missing courses since it doesn't exist
    assert graph.missing_courses == ["MATH 20"]


def test_deep_math_chain(monkeypatch_course_detail):
    """Test deep prerequisite chain: PHYSCS 22 → MATH 8 → MATH 7 → MATH 2 → MATH 20 + MATH 32."""
    result_dict = PrereqGraphTool.invoke({"course_code": "PHYSCS 22"})
    graph = PrereqGraph(**result_dict)
    
    # Should include courses that have prerequisites (not foundational courses)
    expected_courses = {
        "PHYSCS 22", "MATH 8", "PHYSCS 21", "MATH 7", "MATH 2", "MATH 3", "MATH 4"
    }
    assert set(graph.edges.keys()).issuperset(expected_courses)
    
    # MATH 20 and MATH 32 should be in missing courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 32" in graph.missing_courses
    
    # Verify PHYSCS 22 has two prerequisites
    physcs22_edges = graph.edges["PHYSCS 22"]
    assert len(physcs22_edges) == 1  # Should be combined into one edge with AND logic
    edge = physcs22_edges[0]
    assert edge.type == "prereq"
    assert set(edge.courses) == {"MATH 8", "PHYSCS 21"}
    assert edge.logic == "AND"
    
    # Verify MATH 7 has OR logic properly parsed
    math7_edges = graph.edges["MATH 7"]
    # There should be two alternative prerequisite sets (OR logic)
    assert len(math7_edges) == 2
    sets = [set(e.courses) for e in math7_edges]
    assert {"MATH 2"} in sets
    assert {"MATH 3", "MATH 4"} in sets
    for e in math7_edges:
        assert e.logic == "AND"


def test_complex_and_or_logic(monkeypatch_course_detail):
    """Test MATH 7 with complex OR logic: MATH 2 or (MATH 3 and MATH 4).""" 
    result_dict = PrereqGraphTool.invoke({"course_code": "MATH 7"})
    graph = PrereqGraph(**result_dict)
    
    # Should traverse courses with prerequisites (not foundational courses)
    expected_courses = {"MATH 7", "MATH 2", "MATH 3", "MATH 4"}
    assert set(graph.edges.keys()).issuperset(expected_courses)
    
    # Foundational courses should be in missing courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 32" in graph.missing_courses
    
    # MATH 2 requires MATH 20 AND MATH 32
    math2_edges = [e for e in graph.edges["MATH 2"] if e.type == "prereq"]
    assert len(math2_edges) == 1
    edge = math2_edges[0]
    assert edge.type == "prereq"
    assert set(edge.courses) == {"MATH 20", "MATH 32"}
    assert edge.logic == "AND"


def test_chemistry_sequence(monkeypatch_course_detail):
    """Test chemistry sequence with corequisites: CHEM 12 → CHEM 11 → CHEM 10."""
    result_dict = PrereqGraphTool.invoke({"course_code": "CHEM 12"})
    graph = PrereqGraph(**result_dict)
    
    # Should include chemistry and math chains (courses with prerequisites)
    expected_courses = {
        "CHEM 12", "CHEM 11", "CHEM 10", "MATH 2", "MATH 3", "MATH 4"
    }
    assert set(graph.edges.keys()).issuperset(expected_courses)
    
    # Foundational courses should be in missing courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 32" in graph.missing_courses
    assert "MATH 31" in graph.missing_courses
    assert "MATH 49" in graph.missing_courses
    
    # CHEM 11 should have both prerequisites and corequisites
    chem11_edges = graph.edges["CHEM 11"]
    edge_types = {e.type for e in chem11_edges}
    assert "prereq" in edge_types
    assert "coreq" in edge_types


def test_statistics_or_prerequisites(monkeypatch_course_detail):
    """Test STAT C1000 with OR prerequisites: MATH 18 or MATH 20 or MATH 49 or MATH 50."""
    result_dict = PrereqGraphTool.invoke({"course_code": "STAT C1000"})
    graph = PrereqGraph(**result_dict)
    
    # Should include only the root course since prerequisites are foundational
    assert set(graph.edges.keys()) == {"STAT C1000"}
    
    # Foundational courses should be in missing courses
    assert "MATH 18" in graph.missing_courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 49" in graph.missing_courses
    assert "MATH 50" in graph.missing_courses
    
    # Should have one edge with OR logic
    stat_edges = graph.edges["STAT C1000"]
    assert len(stat_edges) == 4  # Four alternative prerequisite options
    for e in stat_edges:
        assert e.type == "prereq"
        assert e.logic == "AND"
    sets = [tuple(e.courses) for e in stat_edges]
    expected_singletons = [("MATH 18",), ("MATH 20",), ("MATH 49",), ("MATH 50",)]
    for singleton in expected_singletons:
        assert singleton in sets


def test_advisory_relationships(monkeypatch_course_detail):
    """Test that advisory relationships are captured separately from prerequisites."""
    result_dict = PrereqGraphTool.invoke({"course_code": "MATH 2"})
    graph = PrereqGraph(**result_dict)
    
    # MATH 2 should have prerequisites but advisory should be ignored
    # (advisory is just text, not course codes)
    math2_edges = graph.edges["MATH 2"]
    prereq_edges = [e for e in math2_edges if e.type == "prereq"]
    assert len(prereq_edges) == 1
    assert set(prereq_edges[0].courses) == {"MATH 20", "MATH 32"}
    
    # Missing foundational courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 32" in graph.missing_courses


def test_business_math_separate_chain(monkeypatch_course_detail):
    """Test business math has separate chain: MATH 28 → MATH 26 → MATH 18/20/49/50."""
    result_dict = PrereqGraphTool.invoke({"course_code": "MATH 28"})
    graph = PrereqGraph(**result_dict)
    
    expected_courses = {"MATH 28", "MATH 26"}
    assert set(graph.edges.keys()).issuperset(expected_courses)
    
    # Foundational courses should be in missing courses
    assert "MATH 18" in graph.missing_courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 49" in graph.missing_courses
    assert "MATH 50" in graph.missing_courses
    
    # MATH 28 should require only MATH 26
    math28_edges = graph.edges["MATH 28"]
    assert len(math28_edges) == 1
    edge = math28_edges[0]
    assert edge.type == "prereq"
    assert edge.courses == ["MATH 26"]


def test_multiple_advanced_math_courses(monkeypatch_course_detail):
    """Test that multiple courses requiring MATH 8 are all captured."""
    result_dict = PrereqGraphTool.invoke({"course_code": "MATH 11"})
    graph = PrereqGraph(**result_dict)
    
    # Should include courses with prerequisites (not foundational courses)
    expected_courses = {
        "MATH 11", "MATH 8", "MATH 7", "MATH 2", "MATH 3", "MATH 4"
    }
    assert set(graph.edges.keys()).issuperset(expected_courses)
    
    # Foundational courses should be in missing courses
    assert "MATH 20" in graph.missing_courses
    assert "MATH 32" in graph.missing_courses
    
    # MATH 11 should require only MATH 8
    math11_edges = graph.edges["MATH 11"]
    assert len(math11_edges) == 1
    edge = math11_edges[0]
    assert edge.type == "prereq"
    assert edge.courses == ["MATH 8"]


def test_performance_deep_graph(monkeypatch_course_detail):
    """Test performance on deepest available graph (PHYSCS 22)."""
    import time
    start_time = time.time()
    
    result_dict = PrereqGraphTool.invoke({"course_code": "PHYSCS 22"})
    graph = PrereqGraph(**result_dict)
    
    end_time = time.time()
    runtime = end_time - start_time
    
    # Should complete well under 0.3 seconds
    assert runtime < 0.3
    
    # Should have reasonable number of courses (not infinite)
    assert len(graph.edges) < 20
    assert len(graph.edges) > 5  # Should have captured the chain
    
    # Should have some missing courses
    assert len(graph.missing_courses) > 0


def test_cycle_prevention(monkeypatch_course_detail):
    """Test that circular references don't cause infinite loops."""
    # Add a synthetic cycle to test cycle detection
    original_chem10 = _REAL_SMC_CATALOG["CHEM 10"].copy()
    try:
        # Create artificial cycle: CHEM 10 → CHEM 11 → CHEM 10
        _REAL_SMC_CATALOG["CHEM 10"]["prerequisites"] = "CHEM 11"
        
        result_dict = PrereqGraphTool.invoke({"course_code": "CHEM 11"})
        graph = PrereqGraph(**result_dict)
        
        # Should terminate without error
        assert "CHEM 10" in graph.edges
        assert "CHEM 11" in graph.edges
        
        # Should have the missing_courses field
        assert isinstance(graph.missing_courses, list)
        
    finally:
        # Restore original data
        _REAL_SMC_CATALOG["CHEM 10"] = original_chem10


def test_missing_courses_functionality(monkeypatch_course_detail):
    """Test that missing courses are properly tracked and reported."""
    result_dict = PrereqGraphTool.invoke({"course_code": "MATH 7"})
    graph = PrereqGraph(**result_dict)
    
    # Should have missing courses
    assert len(graph.missing_courses) > 0
    assert "MATH 20" in graph.missing_courses
    assert "MATH 32" in graph.missing_courses
    
    # Missing courses should be sorted
    assert graph.missing_courses == sorted(graph.missing_courses)
    
    # No duplicates in missing courses
    assert len(graph.missing_courses) == len(set(graph.missing_courses))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"]) 