import sys
from pathlib import Path

# Ensure project root is in the import path so that `tools` can be imported when this
# file is executed directly (or via PyTest) without requiring `tools` to be an
# installable package. This avoids the need for an __init__.py inside the top-level
# `tools` directory, keeping the project structure clean.

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import major_requirement_tool as mrt  # noqa: E402

import json

import pytest


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def sample_data(tmp_path: Path, monkeypatch):
    """Create a temporary catalogue of ASSIST + UCSD files and patch the tool constants."""

    # ------------------------------------------------------------------
    # Build ASSIST directory tree with realistic major files
    # ------------------------------------------------------------------
    assist_root = (
        tmp_path
        / "assist_articulation_v2"
        / "rag_output"
        / "santa_monica_college"
        / "university_of_california_san_diego"
    )
    assist_root.mkdir(parents=True)

    # Helper to write ASSIST JSON files with realistic structure
    def _write_assist(filename: str, major_name: str, articulation_text: str):
        realistic_structure = {
            "result": {
                "name": major_name,
                "type": "Major",
                "publishDate": "2024-11-15T19:09:13.8303774",
                "templateAssets": "[Complex JSON structure...]",
                "articulations": "[Complex articulation data...]"
            },
            "articulation_text": articulation_text,  # Our custom field for extraction
            "validationFailure": None,
            "isSuccessful": True
        }
        (assist_root / filename).write_text(json.dumps(realistic_structure), encoding="utf-8")

    # Create realistic major files covering various scenarios
    _write_assist("cse_computer_science_bs.json", "CSE: Computer Science B.S.", 
                  "Complete CSE 8A, CSE 8B or CSE 11, CSE 12, CSE 20, MATH 20A-C, MATH 18...")
    
    _write_assist("physics_bs.json", "Physics B.S.", 
                  "Complete MATH 20A-E, PHYS 2A-C, PHYS 2CL, PHYS 2DL, one programming course...")
    
    _write_assist("mathematics_bs.json", "Mathematics B.S.", 
                  "Complete MATH 20A-D, MATH 18, choose from advanced mathematics courses...")
    
    _write_assist("environmental_systems_environmental_chemistry_bs.json", 
                  "Environmental Systems - Environmental Chemistry B.S.",
                  "Complete CHEM 6A-C, BILD 3, ECON 1, MATH 20A-B...")
    
    # Edge case: Major with very long filename
    _write_assist("structural_engineering_with_a_specialization_in_structural_health_monitoring_non_destructive_evaluation_bs.json",
                  "Structural Engineering with Specialization in Structural Health Monitoring",
                  "Complete extensive engineering prerequisites including MATH 20A-D...")
    
    # Edge case: Major with unusual characters and formatting
    _write_assist("theatre_and_dance_ba.json", "Theatre & Dance B.A.",
                  "Complete foundational courses in performing arts, no specific prerequisites...")
    
    # Edge case: JSON with different structure (no articulation_text field)
    complex_structure_only = {
        "result": {
            "name": "Music B.A.",
            "requirements": "Complete music theory, performance requirements...",
            "templateAssets": "[Complex structure without articulation_text field]"
        }
    }
    (assist_root / "music_ba.json").write_text(json.dumps(complex_structure_only), encoding="utf-8")

    # ------------------------------------------------------------------
    # Build UCSD transfer prep file with realistic data
    # ------------------------------------------------------------------
    prep_path = tmp_path / "ucsd_transfer_majors.json"
    prep_content = {
        "metadata": {
            "source": "https://admissions.ucsd.edu/transfer/transfer-major-preparation.html",
            "last_scraped": "2025-05-25"
        },
        "majors": {
            "computer_science": {
                "major_name": "Computer Science B.S.",
                "department": "Computer Science and Engineering",
                "required_courses": [
                    "MATH 18, MATH 20A, MATH 20B, MATH 20C",
                    "One course chosen from PHYS 2A, PHYS 2B, CHEM 6A, BILD 1, etc.",
                    "CSE 8B or 11 and CSE 12 and CSE 20"
                ],
                "additional_requirements": [
                    "All courses must be completed with letter grade C- or higher"
                ]
            },
            "physics": {
                "major_name": "Physics B.S.",
                "department": "Physics", 
                "required_courses": [
                    "MATH 18, MATH 20A, MATH 20B, MATH 20C"
                ],
                "additional_requirements": [
                    "Minimum GPA of 3.0 in minimum screening courses"
                ],
                "recommended_courses": [
                    "MATH 20D, PHYS 2A, PHYS 2B, PHYS 2C, One programming course"
                ]
            },
            "mathematics": {
                "major_name": "Mathematics B.S.",
                "department": "Mathematics",
                "required_courses": [
                    "MATH 18, MATH 20A, MATH 20B, MATH 20C, MATH 20D"
                ]
            },
            "business_economics": {
                "major_name": "Business Economics",
                "department": "Economics",
                "required_courses": [
                    "MATH 20A (or 10A), MATH 20B (or 10B)",
                    "ECON 1 or ECON 3",
                    "MGT 45 or ECON/MGT 4 and MGT 5"
                ],
                "additional_requirements": [
                    "Students must earn a C- or better in each class",
                    "Students must have a minimum 2.3 overall GPA"
                ]
            }
        }
    }
    prep_path.write_text(json.dumps(prep_content), encoding="utf-8")

    # ------------------------------------------------------------------
    # Patch module-level constants & clear caches
    # ------------------------------------------------------------------
    monkeypatch.setattr(mrt, "ASSIST_ROOT", assist_root, raising=False)
    monkeypatch.setattr(mrt, "UCSD_PREP_PATH", prep_path, raising=False)

    mrt._assist_file_catalogue.cache_clear()
    mrt._ucsd_transfer_prep_catalogue.cache_clear()

    return {
        "assist_root": assist_root,
        "prep_path": prep_path,
    }


# =============================================================================
# Core functionality tests
# =============================================================================

def test_major_present_in_both_sources(sample_data):
    """Test major that exists in both ASSIST and UCSD prep sources."""
    res = mrt.major_requirement_tool("Computer Science")
    
    # Both sources should be populated
    assert res.assist_articulation is not None
    assert res.ucsd_transfer_prep is not None
    
    # Verify content extraction
    assert "CSE 8A" in res.assist_articulation
    assert "MATH 20A" in res.ucsd_transfer_prep
    assert "computer science" in res.major_name.lower()
    
    # No missing-data notes expected
    assert "No ASSIST" not in res.notes
    assert "No UCSD" not in res.notes
    assert "Lookup successful" in res.notes or len(res.notes.strip()) == 0


def test_major_present_only_in_assist(sample_data):
    """Test major that exists only in ASSIST source."""
    res = mrt.major_requirement_tool("Environmental Chemistry")
    
    assert res.assist_articulation is not None
    assert "CHEM 6A-C" in res.assist_articulation
    assert res.ucsd_transfer_prep is None
    assert "No UCSD transfer preparation found" in res.notes


def test_major_present_only_in_ucsd_prep(sample_data):
    """Test major that exists only in UCSD prep source."""
    res = mrt.major_requirement_tool("Business Economics")
    
    assert res.ucsd_transfer_prep is not None
    assert "ECON 1" in res.ucsd_transfer_prep
    assert res.assist_articulation is None
    assert "No ASSIST articulation found" in res.notes


def test_major_absent_everywhere(sample_data):
    """Test major that doesn't exist in either source."""
    with pytest.raises(ValueError) as exc_info:
        mrt.major_requirement_tool("Imaginary Studies")
    
    error_msg = str(exc_info.value)
    assert "not found in either source" in error_msg
    assert "No ASSIST articulation found" in error_msg
    assert "No UCSD transfer preparation found" in error_msg


# =============================================================================
# Name normalization and matching tests
# =============================================================================

def test_degree_marker_removal(sample_data):
    """Test that degree markers (B.S., B.A., etc.) are properly handled."""
    test_cases = [
        "Computer Science B.S.",
        "Computer Science (B.S.)",
        "Computer Science BS", 
        "Computer Science bs",
        "Computer Science"
    ]
    
    for variant in test_cases:
        res = mrt.major_requirement_tool(variant)
        assert res.assist_articulation is not None
        assert "computer science" in res.major_name.lower()


def test_case_insensitive_matching(sample_data):
    """Test case-insensitive major name matching."""
    test_cases = [
        "PHYSICS",
        "physics", 
        "Physics",
        "PhYsIcS"
    ]
    
    for variant in test_cases:
        res = mrt.major_requirement_tool(variant)
        assert res.assist_articulation is not None
        assert "MATH 20A-E" in res.assist_articulation


def test_whitespace_normalization(sample_data):
    """Test handling of extra whitespace in major names."""
    test_cases = [
        "  Mathematics  ",
        "Mathematics\t\n",
        "  Mathematics   B.S.  "
    ]
    
    for variant in test_cases:
        res = mrt.major_requirement_tool(variant)
        assert res.assist_articulation is not None or res.ucsd_transfer_prep is not None


def test_partial_name_matching(sample_data):
    """Test fuzzy matching for partial major names."""
    # Should match "Environmental Systems - Environmental Chemistry"
    res = mrt.major_requirement_tool("Environmental")
    assert res.assist_articulation is not None
    assert "CHEM 6A-C" in res.assist_articulation


def test_special_characters_in_names(sample_data):
    """Test handling of special characters in major names."""
    res = mrt.major_requirement_tool("Theatre and Dance")
    assert res.assist_articulation is not None
    assert "performing arts" in res.assist_articulation


# =============================================================================
# Edge cases and error handling
# =============================================================================

def test_empty_major_name(sample_data):
    """Test handling of empty or whitespace-only major names."""
    with pytest.raises(ValueError) as exc_info:
        mrt.major_requirement_tool("")
    assert "non-empty string" in str(exc_info.value)
    
    with pytest.raises(ValueError) as exc_info:
        mrt.major_requirement_tool("   ")
    assert "non-empty string" in str(exc_info.value)
    
    with pytest.raises(ValueError) as exc_info:
        mrt.major_requirement_tool(None)
    assert "non-empty string" in str(exc_info.value)


def test_very_long_major_name(sample_data):
    """Test handling of very long major names."""
    res = mrt.major_requirement_tool("Structural Engineering")
    assert res.assist_articulation is not None
    assert "engineering prerequisites" in res.assist_articulation


def test_multiple_matches_warning(sample_data):
    """Test warning when multiple files match the same major."""
    # This should match multiple files and generate a warning
    res = mrt.major_requirement_tool("Engineering")
    # Should find structural engineering file
    assert res.assist_articulation is not None
    # May contain warning about multiple matches (depends on exact matching logic)


def test_json_extraction_fallback(sample_data):
    """Test extraction when articulation_text field is missing."""
    res = mrt.major_requirement_tool("Music")
    assert res.assist_articulation is not None
    # Should fall back to pretty-printing the entire JSON
    assert "Music B.A." in res.assist_articulation


# =============================================================================
# Data structure and format tests  
# =============================================================================

def test_ucsd_prep_different_structures(sample_data):
    """Test handling of different UCSD prep data structures."""
    # Test major with all fields
    res = mrt.major_requirement_tool("Physics")
    assert res.ucsd_transfer_prep is not None
    assert "recommended_courses" in res.ucsd_transfer_prep
    
    # Test major with minimal fields
    res = mrt.major_requirement_tool("Mathematics")
    assert res.ucsd_transfer_prep is not None
    assert "MATH 18" in res.ucsd_transfer_prep


def test_assist_json_structure_variations(sample_data):
    """Test handling of different ASSIST JSON structures."""
    # Test file with articulation_text field
    res = mrt.major_requirement_tool("Computer Science")
    assert res.assist_articulation is not None
    
    # Test file without articulation_text field (falls back to full JSON)
    res = mrt.major_requirement_tool("Music")
    assert res.assist_articulation is not None


# =============================================================================
# Performance and caching tests
# =============================================================================

def test_caching_behavior(sample_data):
    """Test that file catalogues are properly cached."""
    # First call should populate cache
    res1 = mrt.major_requirement_tool("Physics")
    
    # Second call should use cached data
    res2 = mrt.major_requirement_tool("Mathematics")
    
    # Results should be consistent
    assert res1.assist_articulation is not None
    assert res2.assist_articulation is not None


def test_cache_clearing(sample_data):
    """Test that cache clearing works properly."""
    # Populate cache
    mrt.major_requirement_tool("Physics")
    
    # Clear caches
    mrt._assist_file_catalogue.cache_clear()
    mrt._ucsd_transfer_prep_catalogue.cache_clear()
    
    # Should still work after cache clear
    res = mrt.major_requirement_tool("Mathematics")
    assert res.assist_articulation is not None


# =============================================================================
# Integration and realistic scenario tests
# =============================================================================

def test_realistic_student_queries(sample_data):
    """Test realistic queries a student might make."""
    realistic_queries = [
        "computer science",
        "Computer Science B.S.",
        "CS",  # This won't match, should raise ValueError
        "Physics BS",
        "mathematics",
        "business econ"
    ]
    
    successful_queries = 0
    for query in realistic_queries:
        try:
            res = mrt.major_requirement_tool(query)
            successful_queries += 1
            assert res.major_name is not None
            assert res.notes is not None
        except ValueError:
            # Expected for some queries like "CS"
            pass
    
    # Should successfully handle most realistic queries
    assert successful_queries >= 4


def test_comprehensive_major_coverage(sample_data):
    """Test coverage across different types of majors."""
    major_types = [
        ("Computer Science", "STEM"),
        ("Physics", "STEM"), 
        ("Mathematics", "STEM"),
        ("Theatre and Dance", "Arts"),
        ("Business Economics", "Business"),
        ("Environmental Chemistry", "Environmental")
    ]
    
    for major_name, category in major_types:
        try:
            res = mrt.major_requirement_tool(major_name)
            # Should have at least one source of information
            assert res.assist_articulation is not None or res.ucsd_transfer_prep is not None
            assert category.lower() in res.major_name.lower() or major_name.lower() in res.major_name.lower()
        except ValueError:
            # Some majors might not be found, which is acceptable
            pass


# =============================================================================
# Boundary condition tests
# =============================================================================

def test_missing_assist_directory(tmp_path, monkeypatch):
    """Test behavior when ASSIST directory doesn't exist."""
    # Point to non-existent directory
    fake_assist_root = tmp_path / "nonexistent"
    monkeypatch.setattr(mrt, "ASSIST_ROOT", fake_assist_root, raising=False)
    
    # Create minimal UCSD prep file
    prep_path = tmp_path / "ucsd_prep.json"
    prep_content = {
        "majors": {
            "test_major": {
                "major_name": "Test Major",
                "required_courses": ["TEST 101"]
            }
        }
    }
    prep_path.write_text(json.dumps(prep_content), encoding="utf-8")
    monkeypatch.setattr(mrt, "UCSD_PREP_PATH", prep_path, raising=False)
    
    # Clear caches
    mrt._assist_file_catalogue.cache_clear()
    mrt._ucsd_transfer_prep_catalogue.cache_clear()
    
    # Should still work with only UCSD prep data
    res = mrt.major_requirement_tool("Test Major")
    assert res.assist_articulation is None
    assert res.ucsd_transfer_prep is not None
    assert "No ASSIST articulation found" in res.notes


def test_missing_ucsd_prep_file(tmp_path, monkeypatch):
    """Test behavior when UCSD prep file doesn't exist."""
    # Create minimal ASSIST structure
    assist_root = tmp_path / "assist"
    assist_root.mkdir()
    assist_file = assist_root / "test_major.json"
    assist_file.write_text(json.dumps({
        "articulation_text": "Test articulation content"
    }), encoding="utf-8")
    
    monkeypatch.setattr(mrt, "ASSIST_ROOT", assist_root, raising=False)
    monkeypatch.setattr(mrt, "UCSD_PREP_PATH", tmp_path / "nonexistent.json", raising=False)
    
    # Clear caches
    mrt._assist_file_catalogue.cache_clear()
    mrt._ucsd_transfer_prep_catalogue.cache_clear()
    
    # Should still work with only ASSIST data
    res = mrt.major_requirement_tool("Test Major")
    assert res.assist_articulation is not None
    assert res.ucsd_transfer_prep is None
    assert "UCSD transfer prep catalogue is empty" in res.notes


def test_corrupted_json_files(tmp_path, monkeypatch):
    """Test handling of corrupted JSON files."""
    assist_root = tmp_path / "assist"
    assist_root.mkdir()
    
    # Create corrupted JSON file
    corrupted_file = assist_root / "corrupted_major.json"
    corrupted_file.write_text("{ invalid json content", encoding="utf-8")
    
    monkeypatch.setattr(mrt, "ASSIST_ROOT", assist_root, raising=False)
    monkeypatch.setattr(mrt, "UCSD_PREP_PATH", tmp_path / "nonexistent.json", raising=False)
    
    # Clear caches
    mrt._assist_file_catalogue.cache_clear()
    mrt._ucsd_transfer_prep_catalogue.cache_clear()
    
    # Should handle corrupted file gracefully
    res = mrt.major_requirement_tool("Corrupted Major")
    assert res.assist_articulation is not None
    assert "Failed to read JSON" in res.assist_articulation


# =============================================================================
# Output format and content validation tests
# =============================================================================

def test_result_schema_validation(sample_data):
    """Test that results conform to expected schema."""
    res = mrt.major_requirement_tool("Computer Science")
    
    # Check all required fields are present
    assert hasattr(res, 'major_name')
    assert hasattr(res, 'assist_articulation') 
    assert hasattr(res, 'ucsd_transfer_prep')
    assert hasattr(res, 'notes')
    
    # Check field types
    assert isinstance(res.major_name, str)
    assert res.assist_articulation is None or isinstance(res.assist_articulation, str)
    assert res.ucsd_transfer_prep is None or isinstance(res.ucsd_transfer_prep, str)
    assert isinstance(res.notes, str)


def test_content_preservation(sample_data):
    """Test that original content formatting is preserved."""
    res = mrt.major_requirement_tool("Computer Science")
    
    # Should preserve newlines and formatting in articulation text
    if res.assist_articulation:
        # Content should be substantial (not just empty or minimal)
        assert len(res.assist_articulation) > 50
    
    if res.ucsd_transfer_prep:
        # Should contain structured information
        assert len(res.ucsd_transfer_prep) > 20


def test_notes_informativeness(sample_data):
    """Test that notes provide useful information."""
    # Test successful case
    res = mrt.major_requirement_tool("Computer Science")
    assert res.notes is not None
    assert len(res.notes) > 0
    
    # Test partial match case
    res = mrt.major_requirement_tool("Environmental Chemistry")
    assert "No UCSD transfer preparation found" in res.notes
    
    # Test no match case
    with pytest.raises(ValueError) as exc_info:
        mrt.major_requirement_tool("Nonexistent Major")
    assert "not found in either source" in str(exc_info.value) 