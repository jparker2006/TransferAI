"""
Test suite for the articulation.formatters module.

This module tests the formatting functions that generate structured responses
from validation results and other articulation data.

Tests focus on:
1. render_binary_response - Formatting yes/no responses with explanation
2. include_binary_explanation - Adding validation summaries to responses
3. get_course_summary - Generating concise course summaries
"""

import unittest
import sys
import os
from typing import Dict, List, Any

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from articulation.formatters import (
    render_binary_response,
    include_binary_explanation,
    get_course_summary
)
from articulation.models import CourseOption


class TestRenderBinaryResponse(unittest.TestCase):
    """Test the render_binary_response function for formatting yes/no responses.
    
    Note: Most basic tests for this function are in test_binary_response.py.
    This test class only adds integration tests and edge cases not covered there.
    """
    
    def test_integration_with_include_binary_explanation(self):
        """Test that render_binary_response output can be used with include_binary_explanation."""
        # First generate a binary response
        binary_response = render_binary_response(True, "Your course CIS 22A satisfies this requirement.", "CSE 8A")
        
        # Then use it with include_binary_explanation
        validation_summary = "CIS 22A is equivalent to CSE 8A according to the articulation agreement."
        result = include_binary_explanation(binary_response, True, validation_summary)
        
        # Verify that both original content and the validation summary are included
        self.assertIn("CSE 8A", result)
        self.assertIn("Your **course** CIS 22A **satisfies** this requirement", result)
        self.assertIn("CIS 22A is equivalent to CSE 8A according to", result)
    
    def test_key_term_highlighting(self):
        """Test that key terms get proper highlighting in the explanation."""
        explanation = "This course satisfies the requirements. The articulation is valid."
        result = render_binary_response(True, explanation)
        
        # Key terms should be highlighted with bold markdown
        self.assertIn("**satisfies**", result)
        self.assertIn("**articulation**", result)
    
    def test_compatibility_with_specialized_formatters(self):
        """Test compatibility with other specialized formatters in the system."""
        # Create a binary response that might be further processed
        binary_response = render_binary_response(True, "Requirement satisfied")
        
        # Verify structure is consistent for downstream processing
        self.assertTrue(binary_response.startswith("#"))  # Should start with markdown header
        self.assertIn("✅", binary_response)  # Should contain emoji indicator


class TestIncludeBinaryExplanation(unittest.TestCase):
    """Test the include_binary_explanation function for adding summaries to responses."""
    
    def test_adding_satisfied_summary(self):
        """Test adding summary to a satisfied response."""
        response_text = "Here are the details for CSE 8A."
        validation_summary = "Your course CIS 22A satisfies this requirement."
        result = include_binary_explanation(response_text, True, validation_summary)
        
        self.assertIn("✅ Yes", result)
        self.assertIn("Your course CIS 22A satisfies this requirement", result)
        self.assertIn("Here are the details for CSE 8A", result)
    
    def test_adding_unsatisfied_summary(self):
        """Test adding summary to an unsatisfied response."""
        response_text = "Here are the requirements for CSE 8A."
        validation_summary = "Your course CIS 21A does not satisfy the requirements."
        result = include_binary_explanation(response_text, False, validation_summary)
        
        self.assertIn("❌ No", result)
        self.assertIn("Your course CIS 21A does not satisfy", result)
        self.assertIn("Here are the requirements for CSE 8A", result)
    
    def test_with_different_validation_summary(self):
        """Test with various validation summary texts."""
        response_text = "Course information:"
        
        # Test with multiline summary
        multiline_summary = "Option 1: CIS 22A\nOption 2: CIS 22B"
        result = include_binary_explanation(response_text, True, multiline_summary)
        self.assertIn("Option 1:", result)
        self.assertIn("Option 2:", result)
        
        # Test with markdown formatting
        markdown_summary = "**Bold summary** with *emphasis* and `code`"
        result = include_binary_explanation(response_text, True, markdown_summary)
        self.assertIn("**Bold summary**", result)
        self.assertIn("*emphasis*", result)
        self.assertIn("`code`", result)
        
        # Test with empty summary
        empty_summary = ""
        result = include_binary_explanation(response_text, True, empty_summary)
        self.assertIn(response_text, result)
    
    def test_formatting_of_prepended_summary(self):
        """Test the formatting of the prepended summary."""
        response_text = "Course details:"
        validation_summary = "Your courses satisfy the requirements."
        
        result = include_binary_explanation(response_text, True, validation_summary)
        
        # Check that the result has the expected structure
        lines = result.strip().split("\n")
        self.assertTrue(any("✅ Yes" in line for line in lines[:2]))  # Header should be in first 2 lines
        self.assertTrue(any("satisfy" in line for line in lines[:4]))  # Summary should be near the top
        self.assertTrue(any("Course details:" in line for line in lines))  # Original text should be preserved
    
    def test_preserving_original_response(self):
        """Test that the original response text is preserved."""
        response_text = "This is a multi-line\nresponse with special chars: @#$%^&*"
        validation_summary = "Summary text"
        
        result = include_binary_explanation(response_text, True, validation_summary)
        
        # Verify all parts of the original response text are preserved
        for line in response_text.split("\n"):
            self.assertIn(line, result)
        
        self.assertIn("special chars: @#$%^&*", result)


class TestGetCourseSummary(unittest.TestCase):
    """Test the get_course_summary function for generating course summaries."""
    
    def test_with_simple_metadata(self):
        """Test with simple course metadata."""
        metadata = {
            "uc_course": "CSE 8A",
            "uc_course_title": "Introduction to Programming",
            "ccc_courses": ["CIS 22A"]
        }
        
        summary = get_course_summary(metadata)
        
        self.assertIn("CSE 8A", summary)
        self.assertIn("CIS 22A", summary)
    
    def test_with_complex_metadata(self):
        """Test with complex metadata containing multiple options."""
        metadata = {
            "uc_course": "CSE 8A",
            "uc_course_title": "Introduction to Programming",
            "logic_block": {
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
                    }
                ]
            }
        }
        
        summary = get_course_summary(metadata)
        
        self.assertIn("CSE 8A", summary)
        self.assertIn("CIS 22A", summary)
        self.assertIn("CIS 36A", summary)
    
    def test_with_honors_course_options(self):
        """Test with honors course options in the metadata."""
        metadata = {
            "uc_course": "MATH 20A",
            "uc_course_title": "Calculus",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 2AH", "honors": True}
                        ]
                    }
                ]
            }
        }
        
        summary = get_course_summary(metadata)
        
        self.assertIn("MATH 20A", summary)
        self.assertIn("MATH 2AH", summary)
        self.assertIn("honors", summary.lower())
    
    def test_with_missing_metadata_fields(self):
        """Test behavior with missing metadata fields."""
        # Minimal metadata
        metadata = {
            "uc_course": "CSE 8A"
        }
        
        summary = get_course_summary(metadata)
        
        self.assertIn("CSE 8A", summary)
        self.assertIn("Equivalent", summary)
        
        # Missing uc_course
        metadata = {
            "ccc_courses": ["CIS 22A"]
        }
        
        summary = get_course_summary(metadata)
        
        self.assertIn("Unknown", summary)
        self.assertIn("CIS 22A", summary)
    
    def test_formatting_of_course_summary(self):
        """Test the formatting of the course summary output."""
        metadata = {
            "uc_course": "CSE 8A",
            "uc_course_title": "Introduction to Programming",
            "ccc_courses": ["CIS 22A", "CS 111"]
        }
        
        summary = get_course_summary(metadata)
        
        # Check for standard formatting elements
        self.assertIn("UC Course:", summary)
        self.assertIn("CCC Equivalent", summary)
        self.assertIn("Logic:", summary)
    
    def test_handling_of_missing_logic_block(self):
        """Test handling of metadata without a logic block."""
        metadata = {
            "uc_course": "CSE 8A",
            "uc_course_title": "Introduction to Programming",
            "ccc_courses": [
                {"course_letters": "CIS 22A", "title": "C++ Programming"},
                {"course_letters": "CS 111", "title": "Java Programming"}
            ]
        }
        
        summary = get_course_summary(metadata)
        
        self.assertIn("CSE 8A", summary)
        self.assertIn("CIS 22A", summary)
        self.assertIn("CS 111", summary)


if __name__ == "__main__":
    unittest.main() 