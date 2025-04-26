import unittest
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_formatter import render_combo_validation


class TestRenderComboValidation(unittest.TestCase):
    def test_empty_validations(self):
        """Test render_combo_validation with empty input."""
        result = render_combo_validation({})
        self.assertEqual(result, "No validation results to display.")
        
    def test_all_satisfied(self):
        """Test with all courses satisfied."""
        validations = {
            "CSE 8A": {
                "is_satisfied": True,
                "explanation": "✅ Satisfies Option A with: CIS 22A",
                "missing": [],
                "satisfied_options": ["CIS 22A"]
            },
            "CSE 8B": {
                "is_satisfied": True,
                "explanation": "✅ Satisfies Option A with: CIS 36B",
                "missing": [],
                "satisfied_options": ["CIS 36B"]
            }
        }
        result = render_combo_validation(validations)
        self.assertIn("All UC course requirements are satisfied", result)
        self.assertIn("CSE 8A", result)
        self.assertIn("CSE 8B", result)
        self.assertIn("✅", result)
        
    def test_some_unsatisfied(self):
        """Test with some courses unsatisfied."""
        validations = {
            "CSE 8A": {
                "is_satisfied": True,
                "explanation": "✅ Satisfies Option A with: CIS 22A",
                "missing": [],
                "satisfied_options": ["CIS 22A"]
            },
            "CSE 8B": {
                "is_satisfied": False,
                "explanation": "❌ No complete option satisfied.\nYou are missing: CIS 36B",
                "missing": ["CIS 36B"],
                "satisfied_options": []
            }
        }
        result = render_combo_validation(validations)
        self.assertIn("Some UC course requirements are not satisfied", result)
        self.assertIn("CSE 8A", result)
        self.assertIn("CSE 8B", result)
        self.assertIn("✅", result)
        self.assertIn("❌", result)
        self.assertIn("CIS 36B", result)
        
    def test_with_satisfying_courses_map(self):
        """Test with the satisfying_courses map provided."""
        validations = {
            "CSE 8A": {
                "is_satisfied": True,
                "explanation": "✅ Satisfies Option A with: CIS 22A",
                "missing": [],
                "satisfied_options": ["CIS 22A"]
            }
        }
        satisfying_courses = {
            "CSE 8A": ["CIS 22A", "CIS 40"]  # Including multiple courses
        }
        result = render_combo_validation(validations, satisfying_courses)
        self.assertIn("CSE 8A", result)
        self.assertIn("CIS 22A", result)
        self.assertIn("CIS 40", result)  # Should include both courses
        
    def test_formatting(self):
        """Test the formatting of the output table."""
        validations = {
            "CSE 8A": {
                "is_satisfied": True,
                "explanation": "✅ Satisfies Option A with: CIS 22A",
                "missing": [],
                "satisfied_options": ["CIS 22A"]
            }
        }
        result = render_combo_validation(validations)
        # Check table format
        self.assertIn("| UC Course | Status | Missing Courses | Satisfied By |", result)
        self.assertIn("|----------|--------|----------------|-------------|", result)
        self.assertIn("| CSE 8A | ✅ | None | CIS 22A |", result)


if __name__ == "__main__":
    unittest.main() 