import unittest
import sys
import os

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logic_formatter import explain_honors_equivalence

class TestHonorsEquivalence(unittest.TestCase):
    def test_basic_equivalence_message(self):
        """Test that the basic honors equivalence message is correctly formatted."""
        result = explain_honors_equivalence("MATH 1AH", "MATH 1A")
        expected = "MATH 1AH and MATH 1A are equivalent for UC transfer credit. You may choose either."
        self.assertEqual(result, expected)
    
    def test_reversed_order(self):
        """Test that the honors course is always mentioned first regardless of parameter order."""
        result1 = explain_honors_equivalence("CIS 22CH", "CIS 22C")
        result2 = explain_honors_equivalence("CIS 22C", "CIS 22CH") 
        expected = "CIS 22CH and CIS 22C are equivalent for UC transfer credit. You may choose either."
        self.assertEqual(result1, expected)
        self.assertEqual(result2, expected)
    
    def test_normalize_course_codes(self):
        """Test that course codes are properly normalized."""
        result = explain_honors_equivalence("math 1ah", "MATH 1A")
        expected = "MATH 1AH and MATH 1A are equivalent for UC transfer credit. You may choose either."
        self.assertEqual(result, expected)
    
    def test_detects_which_is_honors(self):
        """Test that the function correctly identifies which course is the honors version."""
        # Test with the honors course having an 'H' suffix
        result = explain_honors_equivalence("PHYS 4A", "PHYS 4AH")
        expected = "PHYS 4AH and PHYS 4A are equivalent for UC transfer credit. You may choose either."
        self.assertEqual(result, expected)

if __name__ == "__main__":
    unittest.main() 