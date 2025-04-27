"""
Migration Test Suite for TransferAI

This test suite validates that the articulation package produces identical results
to the original logic_formatter.py to ensure a safe migration.
"""

import unittest
import sys
import os
import warnings

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Suppress deprecation warnings from legacy module
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Import from both packages to compare output
import logic_formatter_adapter
from articulation import (
    is_articulation_satisfied,
    explain_if_satisfied,
    render_logic_str,
    render_logic_v2,
    render_group_summary,
    render_combo_validation,
    render_binary_response,
    include_binary_explanation,
    get_course_summary,
    is_honors_required,
    is_honors_pair_equivalent,
    explain_honors_equivalence,
    validate_combo_against_group,
    validate_uc_courses_against_group_sections
)

from articulation.analyzers import (
    extract_honors_info_from_logic,
    count_uc_matches,
    summarize_logic_blocks,
    get_uc_courses_satisfied_by_ccc,
    get_uc_courses_requiring_ccc_combo
)

from articulation.detectors import validate_logic_block

class TestMigrationEquivalence(unittest.TestCase):
    """Test that the articulation package produces identical output to logic_formatter."""

    def setUp(self):
        """Set up test fixtures."""
        # Sample logic block for testing
        self.logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22A", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 36A", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1AH", "honors": True}
                    ]
                }
            ]
        }
        
        # Sample metadata for testing rendering functions
        self.metadata = {
            "uc_course": "CSE 8A",
            "uc_course_title": "Introduction to Programming",
            "logic_block": self.logic_block,
            "no_articulation": False
        }
        
        # Sample courses for testing validation
        self.selected_courses = ["CIS 22A"]
        
        # Sample document list for testing
        self.docs = [
            type('Document', (), {
                'metadata': self.metadata,
                'text': 'Sample document text for CSE 8A'
            })
        ]
        
        # Sample validation results for testing render_combo_validation
        self.validations = {
            "CSE 8A": {
                "satisfied": True,
                "explanation": "Satisfied by CIS 22A"
            },
            "CSE 8B": {
                "satisfied": False,
                "explanation": "No matching courses"
            }
        }

    def test_is_articulation_satisfied(self):
        """Test that is_articulation_satisfied produces identical results."""
        legacy_result = logic_formatter_adapter.is_articulation_satisfied(self.logic_block, self.selected_courses)
        new_result = is_articulation_satisfied(self.logic_block, self.selected_courses)
        self.assertEqual(legacy_result, new_result)
    
    def test_render_logic_str(self):
        """Test that render_logic_str produces identical results."""
        legacy_result = logic_formatter_adapter.render_logic_str(self.metadata)
        new_result = render_logic_str(self.metadata)
        self.assertEqual(legacy_result, new_result)
    
    def test_render_logic_v2(self):
        """Test that render_logic_v2 produces identical results."""
        legacy_result = logic_formatter_adapter.render_logic_v2(self.metadata)
        new_result = render_logic_v2(self.metadata)
        self.assertEqual(legacy_result, new_result)
    
    def test_render_group_summary(self):
        """Test that render_group_summary produces identical results."""
        legacy_result = logic_formatter_adapter.render_group_summary(self.docs)
        new_result = render_group_summary(self.docs)
        self.assertEqual(legacy_result, new_result)
    
    def test_render_binary_response(self):
        """Test that render_binary_response produces identical results."""
        legacy_result = logic_formatter_adapter.render_binary_response(True, "This is satisfied", "CSE 8A")
        new_result = render_binary_response(True, "This is satisfied", "CSE 8A")
        self.assertEqual(legacy_result, new_result)
    
    def test_is_honors_required(self):
        """Test that is_honors_required produces identical results."""
        legacy_result = logic_formatter_adapter.is_honors_required(self.logic_block)
        new_result = is_honors_required(self.logic_block)
        self.assertEqual(legacy_result, new_result)
    
    def test_extract_honors_info(self):
        """Test that extract_honors_info_from_logic produces identical results."""
        legacy_result = logic_formatter_adapter.extract_honors_info_from_logic(self.logic_block)
        new_result = extract_honors_info_from_logic(self.logic_block)
        self.assertEqual(legacy_result, new_result)
    
    def test_summarize_logic_blocks(self):
        """Test that summarize_logic_blocks produces identical results."""
        legacy_result = logic_formatter_adapter.summarize_logic_blocks(self.logic_block)
        new_result = summarize_logic_blocks(self.logic_block)
        self.assertEqual(legacy_result, new_result)
    
    def test_render_combo_validation(self):
        """Test that render_combo_validation produces identical results."""
        legacy_result = logic_formatter_adapter.render_combo_validation(self.validations)
        new_result = render_combo_validation(self.validations)
        self.assertEqual(legacy_result, new_result)
        
    def test_validate_logic_block(self):
        """Test that validate_logic_block produces identical results."""
        course_code = "CIS 22A"
        legacy_result = logic_formatter_adapter.validate_logic_block(course_code, self.logic_block)
        new_result = validate_logic_block(course_code, self.logic_block)
        self.assertEqual(legacy_result, new_result)

if __name__ == "__main__":
    unittest.main() 