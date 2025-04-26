import unittest
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_formatter import render_binary_response

class TestBinaryResponse(unittest.TestCase):
    def test_positive_response(self):
        """Test that positive responses are formatted correctly."""
        result = render_binary_response(True, "Your courses satisfy the requirements.")
        expected = "✅ Yes, based on official articulation.\n\nYour courses satisfy the requirements."
        self.assertEqual(result, expected)
    
    def test_negative_response(self):
        """Test that negative responses are formatted correctly."""
        result = render_binary_response(False, "Missing required courses: MATH 1A.")
        expected = "❌ No, based on verified articulation logic.\n\nMissing required courses: MATH 1A."
        self.assertEqual(result, expected)
    
    def test_with_course_parameter(self):
        """Test that the course parameter is correctly included when provided."""
        result = render_binary_response(True, "CIS 22C satisfies this requirement.", "CSE 12")
        expected = "✅ Yes, based on official articulation. CSE 12\n\nCIS 22C satisfies this requirement."
        self.assertEqual(result, expected)
    
    def test_multiline_explanation(self):
        """Test that multiline explanations are preserved."""
        explanation = "Your course combination works.\n\nYou've completed all requirements."
        result = render_binary_response(True, explanation)
        expected = f"✅ Yes, based on official articulation.\n\n{explanation}"
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main() 