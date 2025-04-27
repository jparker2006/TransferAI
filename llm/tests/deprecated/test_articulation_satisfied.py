import unittest
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from articulation import (
    is_articulation_satisfied,
    is_honors_required
)


class TestArticulationSatisfied(unittest.TestCase):
    def test_empty_logic_block(self):
        """Test is_articulation_satisfied with empty input."""
        result = is_articulation_satisfied(None, ["CIS 22A"])
        self.assertFalse(result["is_satisfied"])
        self.assertEqual(result["explanation"], "❌ This course must be completed at UCSD.")
        self.assertEqual(result["missing_courses"], {})
        
    def test_no_articulation(self):
        """Test with a logic block that has no articulation."""
        logic_block = {"no_articulation": True}
        result = is_articulation_satisfied(logic_block, ["CIS 22A"])
        self.assertFalse(result["is_satisfied"])
        self.assertEqual(result["explanation"], "❌ This course must be completed at UCSD.")
        
    def test_satisfied_articulation(self):
        """Test with a satisfied articulation path."""
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22A", "honors": False}
                    ]
                }
            ]
        }
        result = is_articulation_satisfied(logic_block, ["CIS 22A"])
        self.assertTrue(result["is_satisfied"])
        self.assertIn("CIS 22A", result["explanation"])
        self.assertEqual(result["missing_courses"], {})
        self.assertTrue("satisfied_options" in result)
        
    def test_unsatisfied_articulation(self):
        """Test with an unsatisfied articulation path."""
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22A", "honors": False},
                        {"course_letters": "CIS 22B", "honors": False}
                    ]
                }
            ]
        }
        result = is_articulation_satisfied(logic_block, ["CIS 22A"])
        self.assertFalse(result["is_satisfied"])
        self.assertTrue(len(result["missing_courses"]) > 0)
        
    def test_honors_required_not_provided(self):
        """Test honors requirement detection when honors not provided."""
        logic_block = {
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
        result = is_articulation_satisfied(logic_block, ["MATH 22"])
        self.assertFalse(result["is_satisfied"])
        self.assertTrue(len(result["missing_courses"]) > 0)
        
    def test_honors_required_and_provided(self):
        """Test honors requirement when honors is provided."""
        logic_block = {
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
        result = is_articulation_satisfied(logic_block, ["MATH 22H"])
        self.assertTrue(result["is_satisfied"])
        
    def test_multiple_options(self):
        """Test with multiple articulation options."""
        logic_block = {
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
        result = is_articulation_satisfied(logic_block, ["CIS 36A"])
        self.assertTrue(result["is_satisfied"])
        self.assertIn("CIS 36A", result["explanation"])


if __name__ == "__main__":
    unittest.main() 