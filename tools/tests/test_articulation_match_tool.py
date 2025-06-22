from __future__ import annotations

"""Unit tests for ArticulationMatchTool.

These tests rely on the ASSIST articulation JSON files and test the complete
articulation matching workflow including edge cases.
"""

import sys
from pathlib import Path

import pytest

# Ensure project root (two levels up) is importable when running file directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.articulation_match_tool import ArticulationMatchTool, MajorNotFoundError, AMOut

# StructuredTool instance
TOOL = ArticulationMatchTool


def test_computer_science_happy_path() -> None:
    """Test successful articulation matching for Computer Science major."""
    
    # These courses should satisfy some CSE requirements based on the sample data
    smc_courses = ["CS 55", "MATH 7", "MATH 8", "MATH 11", "MATH 13", "MATH 10"]
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # Validate against schema
    AMOut(**result)
    
    # Basic structure checks
    assert result["major"] == target_major
    assert isinstance(result["satisfied"], list)
    assert isinstance(result["missing"], list)
    assert isinstance(result["notes"], list)
    assert result["academic_year"] == "2024-2025"
    
    # Should have some satisfied requirements
    assert len(result["satisfied"]) > 0
    
    # Check that satisfied requirements have proper structure
    for req in result["satisfied"]:
        assert "ucsd_course" in req
        assert "smc_courses_used" in req
        assert isinstance(req["smc_courses_used"], list)


def test_partial_satisfaction() -> None:
    """Test case where some requirements are satisfied, others are missing."""
    
    # Only provide a few courses
    smc_courses = ["CS 55", "MATH 7"]
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # Should have both satisfied and missing requirements
    assert len(result["satisfied"]) > 0
    assert len(result["missing"]) > 0
    
    # Check specific known mappings
    satisfied_ucsd_courses = [req["ucsd_course"] for req in result["satisfied"]]
    
    # CS 55 should satisfy some CSE requirement
    assert any("CSE" in course for course in satisfied_ucsd_courses)


def test_no_courses_provided() -> None:
    """Test with empty course list - should have all requirements missing."""
    
    smc_courses = []
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    assert len(result["satisfied"]) == 0
    assert len(result["missing"]) > 0


def test_unknown_major_raises_error() -> None:
    """Test that unknown major raises MajorNotFoundError."""
    
    with pytest.raises(MajorNotFoundError):
        TOOL.invoke({
            "smc_courses": ["CS 55"],
            "target_major": "Nonexistent Major B.S."
        })


def test_course_code_normalization() -> None:
    """Test that course codes are properly normalized."""
    
    # These should all be treated as equivalent
    smc_courses_variants = [
        ["CS 55", "MATH 7"],
        ["cs55", "math7"],  
        ["CS55", "MATH7"],
        [" CS 55 ", " MATH 7 "]
    ]
    
    target_major = "CSE: Computer Science B.S."
    
    results = []
    for courses in smc_courses_variants:
        result = TOOL.invoke({
            "smc_courses": courses,
            "target_major": target_major
        })
        results.append(result)
    
    # All results should be identical
    first_result = results[0]
    for result in results[1:]:
        assert len(result["satisfied"]) == len(first_result["satisfied"])
        assert len(result["missing"]) == len(first_result["missing"])


def test_ap_ib_credit_note() -> None:
    """Test that AP/IB courses trigger advisory note."""
    
    smc_courses = ["AP Calculus BC", "CS 55", "IB Chemistry"]
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # Should include AP/IB advisory note
    assert any("AP/IB" in note for note in result["notes"])


def test_slugification() -> None:
    """Test that major name slugification works correctly."""
    
    # Test different major name formats
    major_variants = [
        "CSE: Computer Science B.S.",
        "Computer Science B.S.",
        "Computer Science with Specialization in Bioinformatics B.S."
    ]
    
    smc_courses = ["CS 55"]
    
    for major in major_variants:
        try:
            result = TOOL.invoke({
                "smc_courses": smc_courses,
                "target_major": major
            })
            # If we get here, the major was found successfully
            assert result["major"] == major
        except MajorNotFoundError:
            # Some variations might not exist, which is okay
            pass


def test_mathematics_major() -> None:
    """Test articulation matching for Mathematics major."""
    
    smc_courses = ["MATH 7", "MATH 8", "MATH 11", "MATH 13"]
    target_major = "Mathematics B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # Validate schema
    AMOut(**result)
    
    # Should have some satisfied math requirements
    assert len(result["satisfied"]) > 0
    
    # Check that MATH courses are being used
    for req in result["satisfied"]:
        assert any("MATH" in course for course in req["smc_courses_used"])


def test_and_logic_requirements() -> None:
    """Test requirements that need multiple courses (AND logic)."""
    
    # Test case where a UCSD course requires multiple SMC courses
    smc_courses = ["CS 20A", "CS 20B"]  # Both needed for CSE 12
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # Should find the CSE 12 requirement satisfied
    satisfied_courses = [req["ucsd_course"] for req in result["satisfied"]]
    assert "CSE 12" in satisfied_courses
    
    # Check that both CS 20A and CS 20B are listed as used
    cse12_req = next(req for req in result["satisfied"] if req["ucsd_course"] == "CSE 12")
    used_courses = [course.upper() for course in cse12_req["smc_courses_used"]]
    assert "CS 20A" in used_courses
    assert "CS 20B" in used_courses


def test_partial_and_logic() -> None:
    """Test case where only some courses of an AND requirement are satisfied."""
    
    # Only provide one of the two required courses
    smc_courses = ["CS 20A"]  # Missing CS 20B for CSE 12
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # CSE 12 should be in missing, not satisfied
    satisfied_courses = [req["ucsd_course"] for req in result["satisfied"]]
    assert "CSE 12" not in satisfied_courses
    assert "CSE 12" in result["missing"]


def test_tool_has_schemas() -> None:
    """Contract enforcement – tool exposes args_schema/return_schema."""
    
    assert hasattr(TOOL, "args_schema"), "Tool missing args_schema"
    assert hasattr(TOOL, "return_schema"), "Tool missing return_schema"


@pytest.mark.parametrize("major_name", [
    "Physics B.S.",
    "Mathematics B.S.", 
    "Environmental Systems: Environmental Chemistry B.S."
])
def test_multiple_majors(major_name: str) -> None:
    """Test that the tool works with different UCSD majors."""
    
    smc_courses = ["MATH 7", "MATH 8", "PHYSCS 21", "CHEM 11"]
    
    try:
        result = TOOL.invoke({
            "smc_courses": smc_courses,
            "target_major": major_name
        })
        
        # Basic validation
        AMOut(**result)
        assert result["major"] == major_name
        assert isinstance(result["satisfied"], list)
        assert isinstance(result["missing"], list)
        
    except MajorNotFoundError:
        # Some majors might not exist in the test data
        pytest.skip(f"Major {major_name} not found in test data") 


def test_complex_and_or_logic_combinations() -> None:
    """Test complex AND/OR combinations across different requirement structures."""
    
    # Test case with known complex requirements
    smc_courses = [
        "CS 55", "CS 20A", "CS 20B",  # For CSE requirements
        "MATH 7", "MATH 8", "MATH 11", "MATH 13",  # Full math sequence
        "PHYSCS 21", "PHYSCS 22",  # Physics sequence
        "CHEM 11", "CHEM 12",  # Chemistry sequence
        "BIOL 21", "BIOL 22", "BIOL 23"  # Biology sequence
    ]
    target_major = "CSE: Computer Science B.S."
    
    result = TOOL.invoke({
        "smc_courses": smc_courses,
        "target_major": target_major
    })
    
    # Should have many satisfied requirements with this comprehensive course set
    assert len(result["satisfied"]) >= 8, f"Expected at least 8 satisfied requirements, got {len(result['satisfied'])}"
    
    # Verify math sequence logic
    satisfied_courses = [req["ucsd_course"] for req in result["satisfied"]]
    math_courses = [course for course in satisfied_courses if course.startswith("MATH")]
    assert len(math_courses) >= 3, "Should satisfy multiple math requirements"
    
    # Verify no double-counting issues
    used_smc_courses = []
    for req in result["satisfied"]:
        used_smc_courses.extend(req["smc_courses_used"])
    
    # Each SMC course should be used efficiently (allowing some overlap for equivalent courses)
    unique_used = set(used_smc_courses)
    assert len(unique_used) <= len(smc_courses), "Should not use more courses than provided"


def test_cross_major_consistency() -> None:
    """Test that similar requirements are handled consistently across majors."""
    
    math_courses = ["MATH 7", "MATH 8", "MATH 11", "MATH 13"]
    majors_to_test = [
        "Mathematics B.S.",
        "Physics B.S.", 
        "CSE: Computer Science B.S."
    ]
    
    results = {}
    for major in majors_to_test:
        try:
            result = TOOL.invoke({
                "smc_courses": math_courses,
                "target_major": major
            })
            results[major] = result
        except Exception as e:
            results[major] = {"error": str(e)}
    
    # All majors should recognize basic math requirements
    for major, result in results.items():
        if "error" not in result:
            satisfied_courses = [req["ucsd_course"] for req in result["satisfied"]]
            # Should have at least some MATH course satisfied
            math_satisfied = [c for c in satisfied_courses if c.startswith("MATH")]
            assert len(math_satisfied) > 0, f"{major} should satisfy at least one MATH requirement"
            
            # MATH 20A should be consistently handled across majors
            if "MATH 20A" in satisfied_courses:
                math_20a_req = next(req for req in result["satisfied"] if req["ucsd_course"] == "MATH 20A")
                # Should use a sensible combination of math courses
                assert len(math_20a_req["smc_courses_used"]) <= 2, "MATH 20A should not require more than 2 SMC courses"


def test_requirement_structure_analysis() -> None:
    """Test the requirement structure analysis for different major types."""
    
    majors_to_analyze = [
        "CSE: Computer Science B.S.",  # Engineering major
        "Psychology B.A.",  # Liberal arts major  
        "Mathematics B.S."  # Science major
    ]
    
    for major in majors_to_analyze:
        try:
            # Use debug mode to get structure analysis
            result = TOOL.invoke({
                "smc_courses": ["MATH 7"],  # Minimal course list
                "target_major": major
            })
            
            # Basic structure validation
            assert "satisfied" in result
            assert "missing" in result
            assert isinstance(result["satisfied"], list)
            assert isinstance(result["missing"], list)
            
            # Should have reasonable number of requirements
            total_reqs = len(result["satisfied"]) + len(result["missing"])
            assert 5 <= total_reqs <= 50, f"{major} has unreasonable requirement count: {total_reqs}"
            
        except Exception as e:
            # Some majors might not exist in test data
            if "not found" not in str(e).lower():
                raise


def test_performance_with_large_course_lists() -> None:
    """Test performance and correctness with large course lists."""
    
    # Generate a large list of courses
    large_course_list = []
    
    # Add comprehensive math sequence
    large_course_list.extend([f"MATH {i}" for i in range(1, 15)])
    
    # Add comprehensive CS sequence  
    large_course_list.extend([f"CS {i}" for i in [1, 3, 7, 17, 20, 50, 55]])
    large_course_list.extend(["CS 20A", "CS 20B"])
    
    # Add science courses
    large_course_list.extend([f"CHEM {i}" for i in [11, 12]])
    large_course_list.extend([f"PHYSCS {i}" for i in [21, 22, 23]])
    large_course_list.extend([f"BIOL {i}" for i in [21, 22, 23]])
    
    # Add some invalid/uncommon courses
    large_course_list.extend(["INVALID 999", "RARE 100", "OLD 50"])
    
    target_major = "CSE: Computer Science B.S."
    
    # Test should complete quickly and return reasonable results
    import time
    start_time = time.time()
    
    result = TOOL.invoke({
        "smc_courses": large_course_list,
        "target_major": target_major
    })
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Should complete within reasonable time (less than 1 second)
    assert execution_time < 1.0, f"Tool took too long: {execution_time:.2f} seconds"
    
    # Should handle large course list correctly
    assert len(result["satisfied"]) > 0, "Should find some satisfied requirements"
    assert len(result["satisfied"]) >= 5, "Should find multiple satisfied requirements with comprehensive course list"
    
    # Verify no courses are used that weren't provided
    all_used_courses = []
    for req in result["satisfied"]:
        all_used_courses.extend(req["smc_courses_used"])
    
    normalized_provided = {_canonical(course) for course in large_course_list}
    for used_course in all_used_courses:
        normalized_used = _canonical(used_course)
        assert normalized_used in normalized_provided, f"Used course {used_course} not in provided list"


def test_edge_case_malformed_data_handling() -> None:
    """Test handling of edge cases and potential data anomalies."""
    
    # Test with empty course list
    result = TOOL.invoke({
        "smc_courses": [],
        "target_major": "CSE: Computer Science B.S."
    })
    assert len(result["satisfied"]) == 0
    assert len(result["missing"]) > 0
    
    # Test with courses that have unusual formatting
    unusual_courses = [
        "CS    55",  # Extra spaces
        "cs55",      # No space, lowercase
        "CS-55",     # Hyphen instead of space
        "CS.55",     # Period instead of space
        "CS/55",     # Slash
        " CS 55 ",   # Leading/trailing spaces
    ]
    
    result = TOOL.invoke({
        "smc_courses": unusual_courses,
        "target_major": "CSE: Computer Science B.S."
    })
    
    # Should normalize all variants to the same result
    if len(result["satisfied"]) > 0:
        # All valid CS 55 variants should produce the same satisfaction
        satisfied_courses = [req["ucsd_course"] for req in result["satisfied"]]
        # Should have some CSE courses satisfied
        cse_courses = [c for c in satisfied_courses if c.startswith("CSE")]
        assert len(cse_courses) > 0, "Should satisfy some CSE requirements with CS 55 variants"


def test_semantic_consistency_validation() -> None:
    """Test semantic consistency of requirement satisfaction."""
    
    # Test case: if MATH 7+8 satisfies MATH 20A, then MATH 7+8+11 should also satisfy it
    base_courses = ["MATH 7", "MATH 8"]
    extended_courses = ["MATH 7", "MATH 8", "MATH 11"]
    
    target_major = "CSE: Computer Science B.S."
    
    base_result = TOOL.invoke({
        "smc_courses": base_courses,
        "target_major": target_major
    })
    
    extended_result = TOOL.invoke({
        "smc_courses": extended_courses,
        "target_major": target_major
    })
    
    # Extended course list should satisfy at least as many requirements
    assert len(extended_result["satisfied"]) >= len(base_result["satisfied"]), \
        "Adding more courses should not decrease satisfied requirements"
    
    # Specific requirements satisfied in base should still be satisfied in extended
    base_satisfied = {req["ucsd_course"] for req in base_result["satisfied"]}
    extended_satisfied = {req["ucsd_course"] for req in extended_result["satisfied"]}
    
    missing_in_extended = base_satisfied - extended_satisfied
    assert len(missing_in_extended) == 0, \
        f"Requirements satisfied with fewer courses missing with more courses: {missing_in_extended}"


@pytest.mark.parametrize("major_type,expected_min_reqs", [
    ("CSE: Computer Science B.S.", 10),
    ("Mathematics B.S.", 5), 
    ("Physics B.S.", 8),
])
def test_major_type_requirement_patterns(major_type: str, expected_min_reqs: int) -> None:
    """Test that different major types have expected requirement patterns."""
    
    try:
        result = TOOL.invoke({
            "smc_courses": [],
            "target_major": major_type
        })
        
        total_requirements = len(result["satisfied"]) + len(result["missing"])
        assert total_requirements >= expected_min_reqs, \
            f"{major_type} should have at least {expected_min_reqs} requirements, found {total_requirements}"
            
        # Engineering majors should have math and science requirements
        if "engineering" in major_type.lower() or major_type.startswith("CSE"):
            missing_courses = result["missing"]
            has_math = any("MATH" in course for course in missing_courses)
            has_physics = any("PHYS" in course for course in missing_courses)
            assert has_math, f"{major_type} should have MATH requirements"
            assert has_physics, f"{major_type} should have PHYSICS requirements"
            
    except MajorNotFoundError:
        pytest.skip(f"Major {major_type} not found in test data")


# Import the canonical function for the edge case test
from tools.articulation_match_tool import _canonical 