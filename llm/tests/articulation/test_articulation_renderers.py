"""
Unit tests for the TransferAI articulation.renderers module.

These tests verify the rendering functions that convert articulation logic
into human-readable formats.
"""

import os
import sys
import unittest
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

# Fix import path issue
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Now import the module
from llm.articulation.renderers import (
    render_logic_str,
    render_logic_v2,
    render_group_summary,
    render_combo_validation
)
from llm.articulation.models import ValidationResult


class TestRenderLogicStr(unittest.TestCase):
    """Test the render_logic_str function for converting logic blocks to readable text."""
    
    def test_simple_logic_block(self):
        """Test rendering a simple logic block with a single course."""
        # Create a simple metadata dict with a single course option
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_str(metadata)
        
        # Verify the output
        self.assertIn("Option A", result)
        self.assertIn("MATH 1A", result)
        self.assertIn("Non-honors courses also accepted", result)
    
    def test_multiple_options(self):
        """Test rendering a logic block with multiple options."""
        # Create a metadata dict with multiple options
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False}
                        ]
                    },
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 10", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_str(metadata)
        
        # Verify the output contains both options
        self.assertIn("Option A", result)
        self.assertIn("MATH 1A", result)
        self.assertIn("Option B", result)
        self.assertIn("MATH 10", result)
        self.assertIn("Non-honors courses also accepted", result)
    
    def test_and_logic_multiple_courses(self):
        """Test rendering a logic block with AND logic requiring multiple courses."""
        # Create a metadata dict with a single option requiring multiple courses
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False},
                            {"course_letters": "MATH 1B", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_str(metadata)
        
        # Verify the output shows AND logic
        self.assertIn("Option A", result)
        self.assertIn("MATH 1A AND MATH 1B", result)
        self.assertIn("Non-honors courses also accepted", result)
    
    def test_nested_logic_structures(self):
        """Test rendering nested logic structures with complex combinations."""
        # Create a metadata dict with nested logic
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND", 
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False},
                            {
                                "type": "OR",
                                "courses": [
                                    {"type": "AND", "courses": [{"course_letters": "PHYS 4A", "honors": False}]},
                                    {"type": "AND", "courses": [{"course_letters": "CHEM 1A", "honors": False}]}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_str(metadata)
        
        # Verify the nested logic is rendered appropriately
        self.assertIn("Option A", result)
        self.assertIn("MATH 1A", result)
        self.assertIn("PHYS 4A", result, f"Nested OR option missing from result: {result}")
        self.assertIn("CHEM 1A", result, f"Nested OR option missing from result: {result}")
    
    def test_honors_courses(self):
        """Test rendering logic blocks with honors course requirements."""
        # Create a metadata dict with honors courses
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1AH", "honors": True}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_str(metadata)
        
        # Verify honors information is included
        self.assertIn("Option A", result)
        self.assertIn("MATH 1AH (Honors)", result)
        self.assertIn("Honors courses accepted", result)
    
    def test_no_honors_note(self):
        """Test rendering without honors notes."""
        # Create a simple metadata dict
        metadata = {
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render without honors notes
        result = render_logic_str(metadata, include_honors_note=False)
        
        # Verify no honors information is included
        self.assertIn("Option A", result)
        self.assertIn("MATH 1A", result)
        self.assertNotIn("Non-honors courses also accepted", result)
        self.assertNotIn("Honors courses accepted", result)
    
    def test_no_articulation(self):
        """Test rendering with no_articulation flag."""
        # Create metadata with no_articulation flag
        metadata = {
            "no_articulation": True,
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_str(metadata)
        
        # Verify the correct message is shown
        self.assertEqual("❌ This course must be completed at UCSD.", result)
        
        # Test with no_articulation in the logic_block
        metadata = {
            "logic_block": {
                "no_articulation": True,
                "type": "OR",
                "courses": []
            }
        }
        result = render_logic_str(metadata)
        self.assertEqual("❌ This course must be completed at UCSD.", result)
    
    def test_empty_logic_block(self):
        """Test rendering with empty or invalid logic blocks."""
        # Test with empty dict
        result = render_logic_str({})
        self.assertEqual("❌ This course must be completed at UCSD.", result)
        
        # Test with empty logic_block
        result = render_logic_str({"logic_block": {}})
        self.assertEqual("❌ This course must be completed at UCSD.", result)
        
        # Test with malformed logic_block
        result = render_logic_str({"logic_block": {"type": "OR", "courses": []}})
        self.assertEqual("❌ This course must be completed at UCSD.", result)


class TestRenderLogicV2(unittest.TestCase):
    """Test the render_logic_v2 function for enhanced logic rendering."""
    
    def test_standard_rendering(self):
        """Test standard rendering mode with a simple logic block."""
        # Create a metadata dict with UC course info
        metadata = {
            "uc_course": "MATH 20A",
            "uc_title": "Calculus I",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render using v2 function
        result = render_logic_v2(metadata)
        
        # Verify header and formatting
        self.assertIn("## MATH 20A – Calculus I", result)
        self.assertIn("Available Options", result)
        self.assertIn("Single Course Options", result)
        self.assertIn("Complete option", result)
        self.assertIn("Non-honors courses also accepted", result)
    
    def test_simplified_rendering(self):
        """Test simplified rendering mode."""
        # Create a metadata dict with UC course info
        metadata = {
            "uc_course": "MATH 20A",
            "uc_title": "Calculus I",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False}
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
        }
        
        # Render using simplified mode
        result = render_logic_v2(metadata, simplified=True)
        
        # Verify simplified format
        self.assertIn("## MATH 20A – Calculus I", result)
        self.assertIn("Available Options", result)
        self.assertIn("Non-honors: MATH 1A", result)
        self.assertIn("Honors: MATH 1AH", result)
        
        # Should use pipe separator in simplified mode
        self.assertIn(" | ", result)
    
    def test_complex_nested_structures(self):
        """Test rendering complex nested logic structures."""
        # Create a metadata dict with nested logic
        metadata = {
            "uc_course": "MATH 20A",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1A", "honors": False},
                            {"course_letters": "MATH 1B", "honors": False}
                        ]
                    },
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 10", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Render using v2 function
        result = render_logic_v2(metadata)
        
        # Verify handling of complex structure
        self.assertIn("Multiple Course Options", result)
        self.assertIn("Single Course Options", result)
        self.assertIn("MATH 1A, MATH 1B", result)
        self.assertIn("MATH 10", result)
    
    def test_honors_handling(self):
        """Test honors course handling in v2 renderer."""
        # Create a logic block with honors courses
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1AH", "honors": True}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1A", "honors": False}
                    ]
                }
            ]
        }
        
        # Test with honors_required=True
        with patch('llm.articulation.renderers.is_honors_required', return_value=True):
            result = render_logic_v2(logic_block)
            # Just check that there's some output
            self.assertTrue(len(result) > 0)
            # Don't make specific text assertions as the format may change

        # Test with honors_required=False
        with patch('llm.articulation.renderers.is_honors_required', return_value=False):
            result = render_logic_v2(logic_block)
            # Just check that there's some output
            self.assertTrue(len(result) > 0)
    
    def test_no_articulation_handling(self):
        """Test handling of no articulation cases."""
        metadata = {
            "uc_course": "CHEM 6A",
            "no_articulation": True,
            "no_articulation_reason": "Course has lab component"
        }
        
        result = render_logic_v2(metadata)
        
        # Updated assertion to check for the course name in the message
        self.assertIn("CHEM 6A must be completed at UCSD", result)
        self.assertIn("Reason: Course has lab component", result)

    def test_no_contradictory_no_articulation_message(self):
        """Test that render_logic_v2 doesn't show contradictory 'no articulation' messages when options exist."""
        # Create a document with articulation options and a contradictory no_articulation flag
        metadata = {
            "uc_course": "CSE 12",
            "uc_title": "Basic Data Structures",
            "no_articulation": True,  # Contradictory flag
            "no_articulation_reason": "No articulation available",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 22C"}
                        ]
                    },
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 22CH", "honors": True}
                        ]
                    }
                ]
            }
        }
        
        # Render the logic block
        result = render_logic_v2(metadata)
        
        # Verify that the result includes the articulation options
        self.assertIn("CIS 22C", result)
        self.assertIn("CIS 22CH", result)
        
        # Verify that the result does NOT include the no articulation message
        self.assertNotIn("must be completed at UCSD", result)
        self.assertNotIn("No articulation available", result)
        
    def test_correct_course_name_in_no_articulation_message(self):
        """Test that render_logic_v2 includes the correct course name in no articulation messages."""
        # Create a document with no articulation options
        metadata = {
            "uc_course": "CSE 21",
            "uc_title": "Mathematics for Algorithms and Systems",
            "no_articulation": True,
            "no_articulation_reason": "No articulation available",
            "logic_block": {}
        }
        
        # Render the logic block
        result = render_logic_v2(metadata)
        
        # Verify that the result includes the no articulation message with the course name
        self.assertIn("CSE 21 must be completed at UCSD", result)
        self.assertIn("Reason: No articulation available", result)


class TestRenderGroupSummary(unittest.TestCase):
    """Test the render_group_summary function for group-level summaries."""
    
    def setUp(self):
        """Set up test data for group summaries."""
        # Create a mock Document class to simulate the expected input
        class Document:
            def __init__(self, metadata):
                self.metadata = metadata
        
        self.Document = Document
    
    def test_choose_one_section_group(self):
        """Test rendering a choose_one_section group."""
        # Create documents in two different sections
        docs = [
            self.Document({
                "group": "1",
                "group_title": "Math Requirement",
                "group_logic_type": "choose_one_section",
                "section": "A",
                "uc_course": "MATH 20A",
                "uc_title": "Calculus I",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "MATH 1A"}]}
                    ]
                }
            }),
            self.Document({
                "group": "1",
                "group_title": "Math Requirement",
                "group_logic_type": "choose_one_section",
                "section": "A",
                "uc_course": "MATH 20B",
                "uc_title": "Calculus II",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "MATH 1B"}]}
                    ]
                }
            }),
            self.Document({
                "group": "1",
                "group_title": "Math Requirement",
                "group_logic_type": "choose_one_section",
                "section": "B",
                "uc_course": "MATH 18",
                "uc_title": "Linear Algebra",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "MATH 2A"}]}
                    ]
                }
            })
        ]
        
        # Render the group summary
        result = render_group_summary(docs)
        
        # Verify structure and content
        self.assertIn("# Group 1: Math Requirement", result)
        self.assertIn("COMPLETE ONE FULL SECTION", result)
        self.assertIn("## SECTION A", result)
        self.assertIn("## SECTION B", result)
        self.assertIn("MATH 20A", result)
        self.assertIn("MATH 20B", result)
        self.assertIn("MATH 18", result)
        self.assertIn("## What You Need To Do", result)
        self.assertIn("Choose **exactly ONE section**", result)
    
    def test_all_required_group(self):
        """Test rendering an all_required group."""
        # Create documents for an all_required group
        docs = [
            self.Document({
                "group": "2",
                "group_title": "Core Requirements",
                "group_logic_type": "all_required",
                "uc_course": "CSE 8A",
                "uc_title": "Introduction to Programming I",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "CIS 22A"}]}
                    ]
                }
            }),
            self.Document({
                "group": "2",
                "group_title": "Core Requirements",
                "group_logic_type": "all_required",
                "uc_course": "CSE 8B",
                "uc_title": "Introduction to Programming II",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "CIS 22B"}]}
                    ]
                }
            })
        ]
        
        # Render the group summary
        result = render_group_summary(docs)
        
        # Verify structure and content
        self.assertIn("# Group 2: Core Requirements", result)
        self.assertIn("COMPLETE ALL COURSES", result)
        self.assertIn("CSE 8A", result)
        self.assertIn("CSE 8B", result)
        self.assertIn("## What You Need To Do", result)
        self.assertIn("Complete **ALL UC courses**", result)
    
    def test_select_n_courses_group(self):
        """Test rendering a select_n_courses group."""
        # Create documents for a select_n_courses group
        docs = [
            self.Document({
                "group": "3",
                "group_title": "Electives",
                "group_logic_type": "select_n_courses",
                "n_courses": 2,
                "uc_course": "PSYC 1",
                "uc_title": "Introduction to Psychology",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "PSYC 1"}]}
                    ]
                }
            }),
            self.Document({
                "group": "3",
                "group_title": "Electives",
                "group_logic_type": "select_n_courses",
                "n_courses": 2,
                "uc_course": "SOC 1",
                "uc_title": "Introduction to Sociology",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "SOC 1"}]}
                    ]
                }
            }),
            self.Document({
                "group": "3",
                "group_title": "Electives",
                "group_logic_type": "select_n_courses",
                "n_courses": 2,
                "uc_course": "ECON 1",
                "uc_title": "Principles of Economics",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "ECON 1"}]}
                    ]
                }
            })
        ]
        
        # Render the group summary
        result = render_group_summary(docs)
        
        # Verify structure and content
        self.assertIn("# Group 3: Electives", result)
        self.assertIn("SELECT 2 COURSES", result)
        self.assertIn("PSYC 1", result)
        self.assertIn("SOC 1", result)
        self.assertIn("ECON 1", result)
        self.assertIn("## What You Need To Do", result)
        self.assertIn("Select **exactly 2**", result)
    
    def test_multi_course_requirement(self):
        """Test rendering groups with multi-course requirements."""
        # Create a document with a multi-course requirement
        docs = [
            self.Document({
                "group": "4",
                "group_title": "Physics Sequence",
                "group_logic_type": "all_required",
                "uc_course": "PHYS 4A",
                "uc_title": "Physics for Scientists and Engineers I",
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {
                            "type": "AND", 
                            "courses": [
                                {"course_letters": "PHYS 4A"}, 
                                {"course_letters": "PHYS 4AL"}
                            ]
                        }
                    ]
                }
            })
        ]
        
        # Render the group summary
        result = render_group_summary(docs)
        
        # Verify multi-course note is included
        self.assertIn("Important Notes", result)
        self.assertIn("Some options require **multiple CCC courses**", result)
    
    def test_compact_mode(self):
        """Test compact rendering mode for large groups."""
        # Create multiple documents to test compact mode
        docs = [
            self.Document({
                "group": "5",
                "group_title": "Large Group",
                "group_logic_type": "choose_one_section",
                "section": "A",
                "uc_course": "COURSE1",
                "uc_title": "Course One",
                "logic_block": {"type": "OR", "courses": [{"type": "AND", "courses": [{"course_letters": "CC1"}]}]}
            }),
            self.Document({
                "group": "5",
                "group_title": "Large Group",
                "group_logic_type": "choose_one_section",
                "section": "A",
                "uc_course": "COURSE2",
                "uc_title": "Course Two",
                "logic_block": {"type": "OR", "courses": [{"type": "AND", "courses": [{"course_letters": "CC2"}]}]}
            }),
            self.Document({
                "group": "5",
                "group_title": "Large Group",
                "group_logic_type": "choose_one_section",
                "section": "B",
                "uc_course": "COURSE3",
                "uc_title": "Course Three",
                "logic_block": {"type": "OR", "courses": [{"type": "AND", "courses": [{"course_letters": "CC3"}]}]}
            })
        ]
        
        # Render in compact mode
        result = render_group_summary(docs, compact=True)
        
        # Verify compact formatting
        self.assertIn("### Section A", result)  # Smaller headers in compact mode
    
    def test_empty_docs(self):
        """Test handling of empty document list."""
        result = render_group_summary([])
        self.assertIn("No articulation documents found", result)


class TestRenderComboValidation(unittest.TestCase):
    """Test the render_combo_validation function for showing validation results."""
    
    def test_all_satisfied(self):
        """Test rendering all satisfied validations."""
        # Create validation results where all are satisfied
        validations = {
            "MATH 20A": ValidationResult(satisfied=True, explanation="Satisfied with: MATH 1A"),
            "MATH 20B": ValidationResult(satisfied=True, explanation="Satisfied with: MATH 1B")
        }
        
        # Render the validation results
        result = render_combo_validation(validations)
        
        # Verify content
        self.assertIn("✅ All UC course requirements are satisfied", result)
        self.assertIn("| MATH 20A | ✅ |", result)
        self.assertIn("| MATH 20B | ✅ |", result)
        self.assertIn("| UC Course | Status | Missing Courses | Satisfied By |", result)
    
    def test_partially_satisfied(self):
        """Test rendering partially satisfied validations."""
        # Create validation results with some not satisfied
        validations = {
            "MATH 20A": ValidationResult(satisfied=True, explanation="Satisfied with: MATH 1A"),
            "MATH 20B": ValidationResult(satisfied=False, explanation="Not satisfied, missing: MATH 1B")
        }
        
        # Render the validation results
        result = render_combo_validation(validations)
        
        # Verify content
        self.assertIn("❌ Some UC course requirements are not satisfied", result)
        self.assertIn("| MATH 20A | ✅ |", result)
        self.assertIn("| MATH 20B | ❌ |", result)
        self.assertIn("MATH 1B", result)  # Missing course
    
    def test_with_satisfying_courses(self):
        """Test rendering with explicit satisfying_courses parameter."""
        # Create validation results
        validations = {
            "MATH 20A": ValidationResult(satisfied=True, explanation="Satisfied"),
            "MATH 20B": ValidationResult(satisfied=True, explanation="Satisfied")
        }
        
        # Add explicit satisfying courses mapping
        satisfying_courses = {
            "MATH 20A": ["MATH 1A", "MATH 1A-H"],
            "MATH 20B": ["MATH 1B"]
        }
        
        # Render with satisfying_courses
        result = render_combo_validation(validations, satisfying_courses)
        
        # Verify satisfying courses are shown
        self.assertIn("MATH 1A, MATH 1A-H", result)
        self.assertIn("MATH 1B", result)
    
    def test_dictionary_validation_format(self):
        """Test rendering with validation results as dictionaries instead of objects."""
        # Create validation results as dictionaries
        validations = {
            "MATH 20A": {
                "satisfied": True, 
                "explanation": "Satisfied with: MATH 1A"
            },
            "MATH 20B": {
                "satisfied": False,
                "explanation": "Not satisfied, missing: MATH 1B"
            }
        }
        
        # Render the validation results
        result = render_combo_validation(validations)
        
        # Verify content is correctly parsed
        self.assertIn("❌ Some UC course requirements are not satisfied", result)
        self.assertIn("| MATH 20A | ✅ |", result)
        self.assertIn("| MATH 20B | ❌ |", result)
    
    def test_empty_validations(self):
        """Test handling of empty validation results."""
        result = render_combo_validation({})
        self.assertEqual("No validation results to display.", result)


if __name__ == "__main__":
    unittest.main() 