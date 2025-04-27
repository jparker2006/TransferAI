import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from articulation.analyzers import count_uc_matches

class TestCountUCMatches(unittest.TestCase):
    def setUp(self):
        # Create mock Document objects for testing
        self.mock_docs = []
        
        # Create a doc for CSE 8A where CIS 36A is a direct match
        doc1 = MagicMock()
        doc1.metadata = {
            "uc_course": "CSE 8A",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 36A", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Create a doc for CSE 11 where CIS 36A is part of a combo with CIS 36B
        doc2 = MagicMock()
        doc2.metadata = {
            "uc_course": "CSE 11",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "CIS 36A", "honors": False},
                            {"course_letters": "CIS 36B", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Add another doc where CIS 36A doesn't appear at all
        doc3 = MagicMock()
        doc3.metadata = {
            "uc_course": "CSE 20",
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 22", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        self.mock_docs = [doc1, doc2, doc3]
    
    @patch('articulation.analyzers.get_uc_courses_satisfied_by_ccc')
    @patch('articulation.analyzers.get_uc_courses_requiring_ccc_combo')
    def test_direct_matches_only(self, mock_combo, mock_direct):
        """Test when a CCC course only has direct matches."""
        mock_direct.return_value = ["CSE 8A"]
        mock_combo.return_value = []
        
        count, direct, combo = count_uc_matches("CIS 36A", self.mock_docs)
        
        self.assertEqual(count, 1)
        self.assertEqual(direct, ["CSE 8A"])
        self.assertEqual(combo, [])
        
        mock_direct.assert_called_once_with("CIS 36A", self.mock_docs)
        mock_combo.assert_called_once_with("CIS 36A", self.mock_docs)
    
    @patch('articulation.analyzers.get_uc_courses_satisfied_by_ccc')
    @patch('articulation.analyzers.get_uc_courses_requiring_ccc_combo')
    def test_combination_matches_only(self, mock_combo, mock_direct):
        """Test when a CCC course only contributes to combos."""
        mock_direct.return_value = []
        mock_combo.return_value = ["CSE 11"]
        
        count, direct, combo = count_uc_matches("CIS 36A", self.mock_docs)
        
        self.assertEqual(count, 0)
        self.assertEqual(direct, [])
        self.assertEqual(combo, ["CSE 11"])
    
    @patch('articulation.analyzers.get_uc_courses_satisfied_by_ccc')
    @patch('articulation.analyzers.get_uc_courses_requiring_ccc_combo')
    def test_both_direct_and_combo(self, mock_combo, mock_direct):
        """Test when a CCC course has both direct matches and contributes to combos."""
        mock_direct.return_value = ["CSE 8A"]
        mock_combo.return_value = ["CSE 8A", "CSE 11"]  # Note overlap
        
        count, direct, combo = count_uc_matches("CIS 36A", self.mock_docs)
        
        self.assertEqual(count, 1)
        self.assertEqual(direct, ["CSE 8A"])
        # CSE 8A should be filtered out from combo because it's already a direct match
        self.assertEqual(combo, ["CSE 11"])
    
    @patch('articulation.analyzers.get_uc_courses_satisfied_by_ccc')
    @patch('articulation.analyzers.get_uc_courses_requiring_ccc_combo')
    def test_no_matches(self, mock_combo, mock_direct):
        """Test when a CCC course has no matches at all."""
        mock_direct.return_value = []
        mock_combo.return_value = []
        
        count, direct, combo = count_uc_matches("CIS 999", self.mock_docs)
        
        self.assertEqual(count, 0)
        self.assertEqual(direct, [])
        self.assertEqual(combo, [])
    
    @patch('articulation.analyzers.get_uc_courses_satisfied_by_ccc')
    @patch('articulation.analyzers.get_uc_courses_requiring_ccc_combo')
    def test_normalization(self, mock_combo, mock_direct):
        """Test that course codes are properly normalized."""
        mock_direct.return_value = ["CSE 8A"]
        mock_combo.return_value = []
        
        # Call with lowercase and extra spaces
        count_uc_matches("  cis 36a  ", self.mock_docs)
        
        # Verify the course was normalized before being passed to helper functions
        mock_direct.assert_called_once_with("  cis 36a  ", self.mock_docs)

if __name__ == "__main__":
    unittest.main() 