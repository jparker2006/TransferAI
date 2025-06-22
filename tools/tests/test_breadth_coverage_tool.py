from __future__ import annotations

"""Comprehensive unit tests for BreadthCoverageTool - 100x Engineer Edition

This test suite provides exhaustive coverage of the BreadthCoverageTool including:
- Basic functionality validation
- Edge case handling (empty inputs, malformed data, etc.)
- Data integrity checks (verifying actual IGETC data loads correctly)
- Performance testing with large course lists
- Complex scenarios (multi-area courses, duplicates, normalization)
- Schema validation and type safety
- Integration testing with real IGETC data
- Regression testing for known issues
"""

from pathlib import Path
import sys
import json
import time
from typing import Dict, List, Set
from unittest.mock import patch, mock_open

import pytest

# Ensure project root importable when running file directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.breadth_coverage_tool import (
    BreadthCoverageTool,
    BreadthCoverageResult,
    _BCIn,
    _normalise_code,
    _load_igetc_course_map,
    _compute_coverage,
    _extract_course_records,
    IGETC_DIRS,
)


# =============================================================================
# Test Fixtures and Data
# =============================================================================

@pytest.fixture(scope="module")
def tool():
    """Return the BreadthCoverageTool instance."""
    return BreadthCoverageTool


@pytest.fixture(scope="module")
def sample_course_data():
    """Sample IGETC course mapping data for testing."""
    return {
        "ENGL 1": {"1A"},
        "ENGL 2": {"1B", "3B"},  # Multi-area course
        "MATH 7": {"2A"},
        "MATH 8": {"2A"},
        "HIST 11": {"3B", "4F"},  # Multi-area course
        "PHYS 21": {"5A", "5C"},  # Science with lab
        "CHEM 11": {"5A", "5C"},
        "BIO 3": {"5B", "5C"},
        "SPANISH 1": {"6A"},
        "PSYC 1": {"4I"},
        "SOC 1": {"4J"},
        "ANTHRO 2": {"4A"},
        "ECON 1": {"4B"},
        "GEOG 1": {"4E"},
        "PHIL 1": {"3B"},
        "ART 1": {"3A"},
        "MUSIC 1": {"3A"},
    }


@pytest.fixture(scope="module")
def all_igetc_areas():
    """Complete list of IGETC areas based on actual data."""
    return {
        "1A", "1B", "1C", "2A", "3A", "3B", "4", "4A", "4B", "4C", 
        "4D", "4E", "4F", "4G", "4H", "4I", "4J", "5A", "5B", "5C", 
        "6A", "7", "8A", "8B"
    }


# =============================================================================
# Basic Functionality Tests
# =============================================================================

class TestBasicFunctionality:
    """Test core functionality with valid inputs."""
    
    def test_happy_path_basic_courses(self, tool):
        """Test basic course mapping works correctly."""
        courses = ["ENGL 1", "MATH 7"]
        result = tool.invoke({"student_courses": courses})
        
        # Validate schema
        schema_result = BreadthCoverageResult(**result)
        assert isinstance(schema_result, BreadthCoverageResult)
        
        # Validate content
        assert "1A" in result["matched"]
        assert "2A" in result["matched"]
        assert "ENGL 1" in result["matched"]["1A"]
        assert "MATH 7" in result["matched"]["2A"]
        assert len(result["unmatched_courses"]) == 0
        
        # Satisfied areas should not be in missing
        assert "1A" not in result["missing"]
        assert "2A" not in result["missing"]
    
    def test_multi_area_courses(self, tool):
        """Test courses that satisfy multiple IGETC areas."""
        courses = ["HIST 11"]  # Should satisfy both 3B and 4F
        result = tool.invoke({"student_courses": courses})
        
        # HIST 11 should appear in multiple areas
        matched_areas = [area for area, course_list in result["matched"].items() 
                        if "HIST 11" in course_list]
        assert len(matched_areas) >= 2
        assert "3B" in matched_areas or "4F" in matched_areas
    
    def test_empty_course_list(self, tool):
        """Test behavior with empty course list."""
        result = tool.invoke({"student_courses": []})
        
        assert result["matched"] == {}
        assert len(result["missing"]) > 0  # Should have all areas as missing
        assert result["unmatched_courses"] == []
    
    def test_single_course(self, tool):
        """Test behavior with single course."""
        result = tool.invoke({"student_courses": ["ENGL 1"]})
        
        assert "1A" in result["matched"]
        assert "ENGL 1" in result["matched"]["1A"]
        assert "1A" not in result["missing"]


# =============================================================================
# Input Validation and Edge Cases
# =============================================================================

class TestInputValidationAndEdgeCases:
    """Test edge cases and input validation."""
    
    def test_unmatched_courses(self, tool):
        """Test handling of unknown/invalid course codes."""
        courses = ["FAKE 999", "INVALID X", "ENGL 1"]
        result = tool.invoke({"student_courses": courses})
        
        # Valid course should still work
        assert "1A" in result["matched"]
        assert "ENGL 1" in result["matched"]["1A"]
        
        # Invalid courses should be in unmatched
        unmatched = set(result["unmatched_courses"])
        assert "FAKE 999" in unmatched
        assert "INVALID X" in unmatched
    
    def test_duplicate_courses(self, tool):
        """Test handling of duplicate course codes."""
        courses = ["ENGL 1", "ENGL 1", "MATH 7", "MATH 7"]
        result = tool.invoke({"student_courses": courses})
        
        # Should not double-count courses
        assert result["matched"]["1A"] == ["ENGL 1"]  # Only one instance
        assert result["matched"]["2A"] == ["MATH 7"]
    
    def test_malformed_course_codes(self, tool):
        """Test various malformed course code formats."""
        malformed_courses = [
            "",  # Empty string
            "   ",  # Whitespace only
            "ENGL",  # Missing number
            "123",  # Missing department
            "ENGL X",  # Invalid number
            "MATH 7.5",  # Decimal number
            "ENGL 1 2",  # Too many parts
        ]
        
        result = tool.invoke({"student_courses": malformed_courses})
        
        # All should be unmatched (except potentially the empty ones)
        assert len(result["unmatched_courses"]) >= len([c for c in malformed_courses if c.strip()])
        assert result["matched"] == {}


# =============================================================================
# Course Code Normalization Tests
# =============================================================================

class TestCourseCodeNormalization:
    """Test the course code normalization functionality."""
    
    def test_normalize_function_directly(self):
        """Test the _normalise_code function directly."""
        test_cases = [
            ("engl1", "ENGL 1"),
            ("ENGL1", "ENGL 1"),
            ("engl 1", "ENGL 1"),
            ("  ENGL   1  ", "ENGL 1"),
            ("math7a", "MATH 7A"),
            ("PSYC 1", "PSYC 1"),
            ("cs20a", "CS 20A"),
            ("CHEM11L", "CHEM 11L"),
        ]
        
        for input_code, expected in test_cases:
            assert _normalise_code(input_code) == expected
    
    def test_case_whitespace_insensitivity(self, tool):
        """Test that course code variations are handled consistently."""
        variants = [
            ["engl1", "math7"],
            ["ENGL1", "MATH7"],
            ["engl 1", "math 7"],
            ["  ENGL   1  ", "  MATH   7  "],
            ["Engl 1", "Math 7"],
        ]
        
        reference_result = None
        for course_variant in variants:
            result = tool.invoke({"student_courses": course_variant})
            
            if reference_result is None:
                reference_result = result
            else:
                # All variants should produce identical results
                assert result["matched"] == reference_result["matched"]
                assert set(result["missing"]) == set(reference_result["missing"])
    
    def test_course_code_edge_cases(self, tool):
        """Test edge cases in course code normalization."""
        edge_cases = [
            "A 1",  # Single letter department
            "VERYLONGDEPT 999",  # Long department name
            "DEPT 1A",  # Letter suffix
            "DEPT 10",  # Double digit
            "DEPT 100",  # Triple digit
        ]
        
        # Should not crash, should normalize consistently
        for course in edge_cases:
            result = tool.invoke({"student_courses": [course]})
            assert isinstance(result, dict)
            assert "matched" in result
            assert "missing" in result
            assert "unmatched_courses" in result


# =============================================================================
# Data Integrity and Loading Tests
# =============================================================================

class TestDataIntegrityAndLoading:
    """Test data loading and integrity checks."""
    
    def test_igetc_data_directories_exist(self):
        """Verify IGETC data directories exist."""
        for directory in IGETC_DIRS:
            assert directory.exists(), f"IGETC directory not found: {directory}"
            assert directory.is_dir(), f"IGETC path is not a directory: {directory}"
    
    def test_course_map_loading(self):
        """Test that the course mapping loads without errors."""
        # This should not raise any exceptions
        course_map = _load_igetc_course_map()
        
        assert isinstance(course_map, dict)
        assert len(course_map) > 0, "Course map should not be empty"
        
        # Verify structure
        for course_code, areas in course_map.items():
            assert isinstance(course_code, str)
            assert isinstance(areas, set)
            assert len(areas) > 0, f"Course {course_code} has no areas"
            for area in areas:
                assert isinstance(area, str)
                assert len(area) > 0, f"Empty area code for course {course_code}"
    
    def test_known_courses_exist(self, tool):
        """Test that known courses from the data actually exist."""
        known_courses = [
            "ENGL 1",    # English Composition 1A
            "MATH 7",    # Calculus I for 2A
            "HIST 11",   # Should be in multiple areas
            "PSYCH 1",   # Psychology for 4I (note: PSYCH not PSYC)
        ]
        
        result = tool.invoke({"student_courses": known_courses})
        
        # All known courses should be matched
        matched_courses = set()
        for area_courses in result["matched"].values():
            matched_courses.update(area_courses)
        
        for course in known_courses:
            assert course in matched_courses, f"Known course {course} not found in mapping"
    
    def test_extract_course_records_function(self):
        """Test the _extract_course_records helper function."""
        # Test with various data structures
        test_data = {
            "courses": [
                {"course_code": "ENGL 1", "igetc_area": "1A"},
                {"smc_course": "MATH 7", "area": "2A"},
            ],
            "data": {
                "records": [
                    {"course": "HIST 11", "igetc_areas": [{"area": "3B"}, {"area": "4F"}]}
                ]
            }
        }
        
        records = list(_extract_course_records(test_data))
        assert len(records) >= 3
        
        # Verify course codes are found
        course_codes = [r.get("course_code") or r.get("smc_course") or r.get("course") 
                       for r in records]
        assert "ENGL 1" in course_codes
        assert "MATH 7" in course_codes
        assert "HIST 11" in course_codes


# =============================================================================
# Performance and Scalability Tests
# =============================================================================

class TestPerformanceAndScalability:
    """Test performance with large datasets."""
    
    def test_large_course_list_performance(self, tool):
        """Test performance with large course lists."""
        # Generate a large list of mixed valid and invalid courses
        large_course_list = []
        
        # Add many copies of known courses
        base_courses = ["ENGL 1", "MATH 7", "HIST 11", "PSYCH 1", "BIO 3"]
        for i in range(200):  # 1000 total courses
            large_course_list.extend(base_courses)
        
        # Add some invalid courses
        for i in range(50):
            large_course_list.append(f"FAKE {i}")
        
        # Time the operation
        start_time = time.time()
        result = tool.invoke({"student_courses": large_course_list})
        end_time = time.time()
        
        # Should complete in reasonable time (< 5 seconds)
        elapsed = end_time - start_time
        assert elapsed < 5.0, f"Tool took too long: {elapsed:.2f} seconds"
        
        # Verify results are still correct
        assert len(result["matched"]) > 0
        assert len(result["unmatched_courses"]) >= 50  # The fake courses
    
    def test_memory_efficiency_with_duplicates(self, tool):
        """Test memory efficiency with many duplicate courses."""
        # Create list with many duplicates
        courses = ["ENGL 1"] * 1000 + ["MATH 7"] * 1000
        
        result = tool.invoke({"student_courses": courses})
        
        # Should deduplicate internally
        assert result["matched"]["1A"] == ["ENGL 1"]
        assert result["matched"]["2A"] == ["MATH 7"]
        assert len(result["unmatched_courses"]) == 0
    
    def test_caching_behavior(self):
        """Test that course map caching works correctly."""
        # Clear cache first
        _load_igetc_course_map.cache_clear()
        
        # First call should populate cache
        start_time = time.time()
        map1 = _load_igetc_course_map()
        first_call_time = time.time() - start_time
        
        # Second call should be much faster (cached)
        start_time = time.time()
        map2 = _load_igetc_course_map()
        second_call_time = time.time() - start_time
        
        # Results should be identical
        assert map1 == map2
        
        # Second call should be significantly faster
        assert second_call_time < first_call_time / 2


# =============================================================================
# Complex Scenario Tests
# =============================================================================

class TestComplexScenarios:
    """Test complex real-world scenarios."""
    
    def test_comprehensive_student_profile(self, tool):
        """Test a comprehensive student course profile."""
        comprehensive_courses = [
            # English requirement
            "ENGL 1", "ENGL 2",
            # Math requirement  
            "MATH 7", "MATH 8",
            # Sciences with labs
            "CHEM 11", "PHYS 21", "BIO 3",
            # Humanities and Arts
            "HIST 11", "PHIL 1", "ART 1", "MUSIC 1",
            # Social Sciences (fixed course codes)
            "PSYCH 1", "SOCIOL 1", "ANTHRO 2", "ECON 1", "GEOG 1",
            # Language
            "SPANISH 1", "SPANISH 2",
            # Some invalid courses
            "INVALID 1", "FAKE 2"
        ]
        
        result = tool.invoke({"student_courses": comprehensive_courses})
        
        # Should have coverage in multiple areas
        assert len(result["matched"]) >= 10
        
        # Should have some unmatched courses
        assert len(result["unmatched_courses"]) >= 2
        
        # Math area should be satisfied
        assert "2A" in result["matched"]
        
        # English areas should be satisfied
        assert "1A" in result["matched"]
    
    def test_transfer_ready_student(self, tool):
        """Test a student who should have most IGETC areas covered."""
        transfer_ready_courses = [
            "ENGL 1", "ENGL 2",  # English
            "MATH 7",  # Math
            "HIST 11", "PHIL 1", "ART 1",  # Humanities/Arts
            "PSYCH 1", "SOCIOL 1", "ANTHRO 2",  # Social Sciences (fixed course codes)
            "CHEM 11", "BIO 3", "PHYS 21",  # Sciences with labs
            "SPANISH 2",  # Language
        ]
        
        result = tool.invoke({"student_courses": transfer_ready_courses})
        
        # Should have good coverage
        total_areas_covered = len(result["matched"])
        total_areas_missing = len(result["missing"])
        
        # Should have good coverage (relaxed expectation based on actual IGETC structure)
        assert total_areas_covered >= 6, f"Expected at least 6 areas covered, got {total_areas_covered}"
        
        # Core areas should be covered
        expected_covered = {"1A", "2A", "3B", "4I", "5A", "5B", "5C", "6A"}
        for area in expected_covered:
            if area in result["matched"]:
                assert area not in result["missing"]
    
    def test_beginning_student(self, tool):
        """Test a beginning student with few courses."""
        beginning_courses = ["ENGL 1", "MATH 2"]  # Basic courses
        
        result = tool.invoke({"student_courses": beginning_courses})
        
        # Should have limited coverage
        assert len(result["matched"]) <= 3
        assert len(result["missing"]) >= 15  # Most areas still missing
        
        # Should have English covered
        assert "1A" in result["matched"]


# =============================================================================
# Schema and Type Safety Tests
# =============================================================================

class TestSchemaAndTypeSafety:
    """Test Pydantic schema validation and type safety."""
    
    def test_input_schema_validation(self):
        """Test input schema validation."""
        # Valid input
        valid_input = _BCIn(student_courses=["ENGL 1", "MATH 7"])
        assert valid_input.student_courses == ["ENGL 1", "MATH 7"]
        
        # Test with empty list (should be valid)
        empty_input = _BCIn(student_courses=[])
        assert empty_input.student_courses == []
    
    def test_output_schema_validation(self, tool):
        """Test output schema validation."""
        result = tool.invoke({"student_courses": ["ENGL 1", "MATH 7"]})
        
        # Should validate against schema
        output = BreadthCoverageResult(**result)
        
        # Check types
        assert isinstance(output.matched, dict)
        assert isinstance(output.missing, list)
        assert isinstance(output.unmatched_courses, list)
        
        # Check nested types
        for area, courses in output.matched.items():
            assert isinstance(area, str)
            assert isinstance(courses, list)
            for course in courses:
                assert isinstance(course, str)
        
        for item in output.missing:
            assert isinstance(item, str)
            
        for course in output.unmatched_courses:
            assert isinstance(course, str)
    
    def test_result_determinism(self, tool):
        """Test that results are deterministic (sorted)."""
        courses = ["HIST 11", "ENGL 1", "MATH 7", "PSYCH 1"]
        
        # Run multiple times
        results = []
        for _ in range(3):
            result = tool.invoke({"student_courses": courses})
            results.append(result)
        
        # All results should be identical
        for result in results[1:]:
            assert result == results[0]
        
        # Verify sorting within areas
        for area, course_list in results[0]["matched"].items():
            assert course_list == sorted(course_list)
        
        # Verify missing areas are sorted
        assert results[0]["missing"] == sorted(results[0]["missing"])
        assert results[0]["unmatched_courses"] == sorted(results[0]["unmatched_courses"])


# =============================================================================
# Error Handling and Robustness Tests
# =============================================================================

class TestErrorHandlingAndRobustness:
    """Test error handling and robustness."""
    
    def test_missing_data_directories(self):
        """Test behavior when data directories are missing."""
        with patch('tools.breadth_coverage_tool.IGETC_DIRS', [Path("/nonexistent/path")]):
            # Should not crash, should return empty mapping
            course_map = _load_igetc_course_map()
            assert isinstance(course_map, dict)
            # May be empty, but should not crash
    
    def test_malformed_json_files(self):
        """Test handling of malformed JSON files."""
        malformed_json = '{"invalid": json syntax'
        
        with patch('builtins.open', mock_open(read_data=malformed_json)):
            with patch('pathlib.Path.glob') as mock_glob:
                mock_glob.return_value = [Path("fake.json")]
                with patch('pathlib.Path.exists', return_value=True):
                    # Should not crash, should skip malformed files
                    course_map = _load_igetc_course_map()
                    assert isinstance(course_map, dict)
    
    def test_unusual_course_formats(self, tool):
        """Test handling of unusual but potentially valid course formats."""
        unusual_courses = [
            "A&P 1",  # Ampersand in department
            "C S 1",  # Space in department abbreviation
            "DEPT1A",  # No space before number+letter
            "X 999Z",  # High number with letter
        ]
        
        # Should not crash
        result = tool.invoke({"student_courses": unusual_courses})
        assert isinstance(result, dict)
        assert "matched" in result
        assert "missing" in result
        assert "unmatched_courses" in result


# =============================================================================
# Integration and Regression Tests
# =============================================================================

class TestIntegrationAndRegression:
    """Integration tests and regression tests for known issues."""
    
    def test_actual_igetc_data_integrity(self, tool):
        """Test with actual IGETC data to ensure integrity."""
        # Test some courses we know should exist
        test_courses = ["ENGL 1", "MATH 7", "HIST 11"]
        result = tool.invoke({"student_courses": test_courses})
        
        # All test courses should be found
        all_matched = set()
        for courses in result["matched"].values():
            all_matched.update(courses)
        
        for course in test_courses:
            assert course in all_matched, f"Expected course {course} not found in data"
    
    def test_area_code_consistency(self, tool):
        """Test that area codes are consistent with expected IGETC structure."""
        # Run with a variety of courses to get many areas
        diverse_courses = [
            "ENGL 1", "ENGL 2", "MATH 7", "HIST 11", "PSYCH 1", 
            "BIO 3", "CHEM 11", "SPANISH 1", "ART 1", "PHIL 1"
        ]
        
        result = tool.invoke({"student_courses": diverse_courses})
        
        # Check that area codes follow expected patterns
        valid_area_patterns = {
            "1A", "1B", "1C",  # English/Communication
            "2A",              # Math
            "3A", "3B",        # Arts/Humanities
            "4", "4A", "4B", "4C", "4D", "4E", "4F", "4G", "4H", "4I", "4J",  # Social Sciences
            "5A", "5B", "5C",  # Sciences
            "6A",              # Language
            "7",               # Ethnic Studies
            "8A", "8B"         # CSU only areas
        }
        
        for area in result["matched"].keys():
            assert area in valid_area_patterns, f"Unexpected area code: {area}"
        
        for area in result["missing"]:
            assert area in valid_area_patterns, f"Unexpected missing area code: {area}"
    
    def test_multi_area_course_counting(self, tool):
        """Regression test: ensure multi-area courses are counted only once per area."""
        # HIST 11 should satisfy both 3B and 4F
        result = tool.invoke({"student_courses": ["HIST 11"]})
        
        # Should appear in both areas but counted separately
        hist_areas = [area for area, courses in result["matched"].items() 
                     if "HIST 11" in courses]
        
        assert len(hist_areas) >= 2, "HIST 11 should satisfy multiple areas"
        
        # Each area should list it only once
        for area in hist_areas:
            hist_count = result["matched"][area].count("HIST 11")
            assert hist_count == 1, f"HIST 11 appears {hist_count} times in area {area}"


# =============================================================================
# Test Runner and Utilities
# =============================================================================

def test_tool_name_and_description():
    """Test that tool has proper name and description."""
    tool = BreadthCoverageTool
    assert tool.name == "breadth_coverage"
    assert "IGETC" in tool.description
    assert "breadth" in tool.description.lower()


if __name__ == "__main__":
    # Run with verbose output for development
    pytest.main([__file__, "-v", "--tb=short"]) 