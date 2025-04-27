import unittest
import sys
import os
import warnings

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from articulation package instead of logic_formatter
from articulation import (
    is_honors_required,
    detect_redundant_courses,
    explain_if_satisfied,
)

# Display deprecation warning
warnings.warn(
    "This test file is deprecated and will be removed in a future version. "
    "Please use the module-specific test files instead:\n"
    "- test_articulation_detectors.py for is_honors_required and detect_redundant_courses\n"
    "- test_articulation_validators.py for explain_if_satisfied",
    DeprecationWarning,
    stacklevel=2
)


class TestHonorsRequired(unittest.TestCase):
    def test_empty_block(self):
        """Test is_honors_required with empty input."""
        self.assertFalse(is_honors_required(None))
        self.assertFalse(is_honors_required({}))
        
    def test_no_courses(self):
        """Test with an OR block that has no courses."""
        logic_block = {"type": "OR", "courses": []}
        self.assertFalse(is_honors_required(logic_block))
        
    def test_non_honors_option(self):
        """Test with a mix of honors and non-honors options."""
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 22H", "honors": True}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 22", "honors": False}
                    ]
                }
            ]
        }
        self.assertFalse(is_honors_required(logic_block))
        
    def test_only_honors_options(self):
        """Test with only honors options."""
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 22H", "honors": True}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 2BH", "honors": True}
                    ]
                }
            ]
        }
        self.assertTrue(is_honors_required(logic_block))
        
    def test_nested_blocks(self):
        """Test with nested logic blocks."""
        # A nested structure where all options ultimately require honors
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1AH", "honors": True},
                        {"course_letters": "MATH 1BH", "honors": True}
                    ]
                }
            ]
        }
        self.assertTrue(is_honors_required(logic_block))
        
        # Add a non-honors option and test again
        logic_block["courses"].append({
            "type": "AND",
            "courses": [
                {"course_letters": "MATH 1A", "honors": False}
            ]
        })
        self.assertFalse(is_honors_required(logic_block))
        
    def test_list_of_blocks(self):
        """Test with a list of logic blocks."""
        logic_blocks = [
            {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 22H", "honors": True}
                        ]
                    }
                ]
            }
        ]
        self.assertTrue(is_honors_required(logic_blocks))


class TestRedundantCourses(unittest.TestCase):
    def test_empty_inputs(self):
        """Test detect_redundant_courses with empty inputs."""
        self.assertEqual(detect_redundant_courses([], {}), [])
        self.assertEqual(detect_redundant_courses(["CIS 22A"], {}), [])
        
    def test_no_redundancy(self):
        """Test with courses that aren't redundant."""
        selected_courses = ["CIS 22A", "CIS 36A"]
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22A"}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 36A"}
                    ]
                }
            ]
        }
        self.assertEqual(detect_redundant_courses(selected_courses, logic_block), [])
        
    def test_redundant_honors_pair(self):
        """Test with a redundant honors/non-honors pair."""
        # Test with MATH courses
        selected_courses = ["MATH 1A", "MATH 1AH"]
        logic_block = {
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
        result = detect_redundant_courses(selected_courses, logic_block)
        self.assertEqual(len(result), 1)
        self.assertEqual(sorted(result[0]), ["MATH 1A", "MATH 1AH"])
        
        # Test with CIS courses
        selected_courses = ["CIS 22C", "CIS 22CH"]
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22C", "honors": False}
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
        result = detect_redundant_courses(selected_courses, logic_block)
        self.assertEqual(len(result), 1)
        self.assertEqual(sorted(result[0]), ["CIS 22C", "CIS 22CH"])
        
    def test_multiple_redundant_groups(self):
        """Test with multiple redundant groups."""
        selected_courses = ["MATH 1A", "MATH 1AH", "MATH 1B", "MATH 1BH"]
        logic_block = {
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
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1B", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1BH", "honors": True}
                    ]
                }
            ]
        }
        result = detect_redundant_courses(selected_courses, logic_block)
        self.assertEqual(len(result), 2)  # Two redundant groups
        
        # Test with mixed course types
        selected_courses = ["CHEM 1A", "CHEM 1AH", "BIOL 6A", "BIOL 6AH"]
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CHEM 1A", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CHEM 1AH", "honors": True}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "BIOL 6A", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "BIOL 6AH", "honors": True}
                    ]
                }
            ]
        }
        result = detect_redundant_courses(selected_courses, logic_block)
        self.assertEqual(len(result), 2)  # Two redundant groups
        pairs = [sorted(group) for group in result]
        self.assertIn(["BIOL 6A", "BIOL 6AH"], pairs)
        self.assertIn(["CHEM 1A", "CHEM 1AH"], pairs)
        
    def test_case_insensitivity(self):
        """Test that course code matching is case-insensitive."""
        selected_courses = ["chem 1a", "CHEM 1AH"]
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CHEM 1A", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CHEM 1AH", "honors": True}
                    ]
                }
            ]
        }
        result = detect_redundant_courses(selected_courses, logic_block)
        self.assertEqual(len(result), 1)
        self.assertEqual(sorted(result[0]), ["CHEM 1A", "CHEM 1AH"])
        
    def test_honors_inference_without_logic_block(self):
        """Test that we can infer honors pairs even without logic block info."""
        # Should detect honors pair based on course names alone
        selected_courses = ["PHYS 4A", "PHYS 4AH"]
        logic_block = {"type": "OR", "courses": []}  # Empty courses
        result = detect_redundant_courses(selected_courses, logic_block)
        self.assertEqual(len(result), 1)
        self.assertEqual(sorted(result[0]), ["PHYS 4A", "PHYS 4AH"])
        
    def test_generalized_pattern_matching(self):
        """Test that the regex-based pattern matcher works for various course prefixes and formats."""
        # Test various course prefixes and spacing formats
        test_cases = [
            # Various subject prefixes with consistent format
            (["CHEM 1A", "CHEM 1AH"], [["CHEM 1A", "CHEM 1AH"]]),
            (["PHYS 4A", "PHYS 4AH"], [["PHYS 4A", "PHYS 4AH"]]),
            (["BIOL 6A", "BIOL 6AH"], [["BIOL 6A", "BIOL 6AH"]]),
            (["ENGR 37", "ENGR 37H"], [["ENGR 37", "ENGR 37H"]]),
            
            # Different spacing formats
            (["MATH1A", "MATH1AH"], [["MATH1A", "MATH1AH"]]),
            (["CS 101", "CS 101H"], [["CS 101", "CS 101H"]]),
            (["PSYCH22", "PSYCH22H"], [["PSYCH22", "PSYCH22H"]]),
            
            # Mixed course prefixes in one input
            (
                ["CHEM 1A", "CHEM 1AH", "PHYS 4A", "PHYS 4AH", "BIOL 6A", "BIOL 6AH"],
                [["BIOL 6A", "BIOL 6AH"], ["CHEM 1A", "CHEM 1AH"], ["PHYS 4A", "PHYS 4AH"]]
            ),
            
            # Course numbers with letters in the middle
            (["MATH 2B1", "MATH 2B1H"], [["MATH 2B1", "MATH 2B1H"]]),
            (["CS 61A", "CS 61AH"], [["CS 61A", "CS 61AH"]])
        ]
        
        # Basic logic block for testing with empty courses
        logic_block = {"type": "OR", "courses": []}
        
        for selected_courses, expected_groups in test_cases:
            result = detect_redundant_courses(selected_courses, logic_block)
            
            # Check for correct number of groups
            self.assertEqual(len(result), len(expected_groups), 
                             f"Expected {len(expected_groups)} redundant groups for {selected_courses}, got {len(result)}")
            
            # Check if each expected group was detected
            for expected_group in expected_groups:
                self.assertIn(sorted(expected_group), [sorted(g) for g in result],
                             f"Expected group {sorted(expected_group)} not found in results for {selected_courses}")


class TestExplainIfSatisfied(unittest.TestCase):
    def test_redundancy_reporting_when_satisfied(self):
        """Test that redundant courses are reported when a path is satisfied."""
        selected_courses = ["CIS 22C", "CIS 22CH"]
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22C", "honors": False}
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
        is_satisfied, explanation = explain_if_satisfied(logic_block, selected_courses, detect_all_redundant=True)
        self.assertTrue(is_satisfied)
        self.assertIn("Redundant courses detected", explanation)
        self.assertIn("CIS 22C", explanation)
        self.assertIn("CIS 22CH", explanation)
        
    def test_redundancy_reporting_when_not_satisfied(self):
        """Test that redundant courses are reported even when no path is satisfied."""
        selected_courses = ["CIS 22C", "CIS 22CH"]  # Missing CIS 21JA
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22C", "honors": False},
                        {"course_letters": "CIS 21JA", "honors": False}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22CH", "honors": True},
                        {"course_letters": "CIS 21JA", "honors": False}
                    ]
                }
            ]
        }
        is_satisfied, explanation = explain_if_satisfied(logic_block, selected_courses, detect_all_redundant=True)
        self.assertFalse(is_satisfied)
        self.assertIn("Redundant courses detected", explanation)
        self.assertIn("CIS 22C", explanation)
        self.assertIn("CIS 22CH", explanation)
        
    def test_multiple_redundant_groups_reporting(self):
        """Test that multiple redundant course groups are reported correctly."""
        selected_courses = ["PHYS 4A", "PHYS 4AH", "CHEM 1A", "CHEM 1AH"]
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "PHYS 4A", "honors": False}
                    ]
                }
            ]
        }
        is_satisfied, explanation = explain_if_satisfied(logic_block, selected_courses, detect_all_redundant=True)
        self.assertTrue(is_satisfied)
        self.assertIn("Redundant courses detected", explanation)
        self.assertIn("PHYS 4A", explanation)
        self.assertIn("PHYS 4AH", explanation)
        self.assertIn("CHEM 1A", explanation)
        self.assertIn("CHEM 1AH", explanation)


if __name__ == "__main__":
    unittest.main() 