"""
Tests for the ArticulationFacade service.

This module contains tests for the ArticulationFacade, which provides
a unified interface to the articulation package functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import os
from typing import Dict, List, Any

from llm.services.articulation_facade import ArticulationFacade


class TestArticulationFacade(unittest.TestCase):
    """Test cases for the ArticulationFacade."""

    def setUp(self):
        """Set up test fixtures."""
        self.facade = ArticulationFacade()
        
        # Sample logic blocks for testing
        self.simple_logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1A"}
                    ]
                }
            ]
        }
        
        self.honors_logic_block = {
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
                        {"course_letters": "MATH 1A"}
                    ]
                }
            ]
        }
        
        self.complex_logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 1A"},
                        {"course_letters": "MATH 1B"}
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "MATH 10"}
                    ]
                }
            ]
        }
        
        # Sample metadata
        self.sample_metadata = {
            "uc_course": "MATH 20A",
            "uc_title": "Calculus",
            "logic_block": self.simple_logic_block
        }
        
        # Sample docs
        self.doc1 = MagicMock()
        self.doc1.metadata = {
            "uc_course": "MATH 20A",
            "logic_block": self.simple_logic_block
        }
        
        self.doc2 = MagicMock()
        self.doc2.metadata = {
            "uc_course": "MATH 20B",
            "logic_block": self.complex_logic_block
        }
        
        self.docs = [self.doc1, self.doc2]
        
        # Sample group dict
        self.group_dict = {
            "logic_type": "OR",
            "n_courses": 1,
            "sections": [
                {
                    "section_id": "A",
                    "uc_courses": [
                        {
                            "name": "MATH 20A",
                            "logic_blocks": [self.simple_logic_block]
                        }
                    ]
                }
            ]
        }
        
        # Direct format from rag_data.json for CSE 8A (for articulation options tests)
        self.cse8a_logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {
                            "name": "CIS 22A Beginning Programming Methodologies in C++",
                            "honors": False,
                            "course_id": "a6d419c5",
                            "course_letters": "CIS 22A",
                            "title": "Beginning Programming Methodologies in C++"
                        }
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {
                            "name": "CIS 36A Introduction to Computer Programming Using Java",
                            "honors": False,
                            "course_id": "a1733a15",
                            "course_letters": "CIS 36A",
                            "title": "Introduction to Computer Programming Using Java"
                        }
                    ]
                },
                {
                    "type": "AND",
                    "courses": [
                        {
                            "name": "CIS 40 Introduction to Programming in Python",
                            "honors": False,
                            "course_id": "a1f64eec",
                            "course_letters": "CIS 40",
                            "title": "Introduction to Programming in Python"
                        }
                    ]
                }
            ]
        }
        
        # Format used in test_course_lookup_handler.py (for articulation options tests)
        self.test_cse8a_logic_block = {
            "options": [
                {
                    "courses": [
                        {"name": "CIS 22A Introduction to Programming", "is_honors": False}
                    ]
                },
                {
                    "courses": [
                        {"name": "CIS 36A Python Programming", "is_honors": False}
                    ]
                },
                {
                    "courses": [
                        {"name": "CIS 40 C++ Programming", "is_honors": False}
                    ]
                }
            ]
        }

    @patch('llm.articulation.validators.is_articulation_satisfied')
    def test_validate_courses(self, mock_is_articulation_satisfied):
        """Test that validate_courses correctly delegates to validators module."""
        # Setup
        mock_result = {"is_satisfied": True, "explanation": "Test explanation"}
        mock_is_articulation_satisfied.return_value = mock_result
        courses = ["MATH 1A"]
        
        # Execute
        result = self.facade.validate_courses(self.simple_logic_block, courses)
        
        # Verify
        mock_is_articulation_satisfied.assert_called_once_with(self.simple_logic_block, courses)
        self.assertEqual(result, mock_result)

    @patch('llm.articulation.renderers.render_logic_str')
    def test_render_articulation_logic(self, mock_render_logic_str):
        """Test that render_articulation_logic correctly delegates to renderers module."""
        # Setup
        mock_render_logic_str.return_value = "Rendered logic string"
        
        # Execute
        result = self.facade.render_articulation_logic(self.sample_metadata)
        
        # Verify
        mock_render_logic_str.assert_called_once_with(self.sample_metadata, "STANDARD")
        self.assertEqual(result, "Rendered logic string")
        
        # Test with different verbosity
        result = self.facade.render_articulation_logic(self.sample_metadata, "DETAILED")
        mock_render_logic_str.assert_called_with(self.sample_metadata, "DETAILED")

    @patch('llm.articulation.formatters.render_binary_response')
    def test_format_binary_response(self, mock_render_binary_response):
        """Test that format_binary_response correctly delegates to formatters module."""
        # Setup
        mock_render_binary_response.return_value = "Formatted response"
        
        # Execute
        result = self.facade.format_binary_response(True, "Test explanation", "MATH 20A")
        
        # Verify
        mock_render_binary_response.assert_called_once_with(True, "Test explanation", "MATH 20A")
        self.assertEqual(result, "Formatted response")

    @patch('llm.articulation.analyzers.count_uc_matches')
    def test_count_uc_matches(self, mock_count_uc_matches):
        """Test that count_uc_matches correctly delegates to analyzers module."""
        # Setup
        mock_count_uc_matches.return_value = (1, ["MATH 20A"], ["MATH 21A"])
        
        # Execute
        result = self.facade.count_uc_matches("MATH 1A", self.docs)
        
        # Verify
        mock_count_uc_matches.assert_called_once_with("MATH 1A", self.docs)
        self.assertEqual(result, (1, ["MATH 20A"], ["MATH 21A"]))

    @patch('llm.articulation.analyzers.extract_honors_info_from_logic')
    def test_extract_honors_info(self, mock_extract_honors_info):
        """Test that extract_honors_info correctly delegates to analyzers module."""
        # Setup
        mock_result = {
            "honors_courses": ["MATH 1AH"],
            "non_honors_courses": ["MATH 1A"]
        }
        mock_extract_honors_info.return_value = mock_result
        
        # Execute
        result = self.facade.extract_honors_info(self.honors_logic_block)
        
        # Verify
        mock_extract_honors_info.assert_called_once_with(self.honors_logic_block)
        self.assertEqual(result, mock_result)

    @patch('llm.articulation.detectors.is_honors_required')
    def test_is_honors_required(self, mock_is_honors_required):
        """Test that is_honors_required correctly delegates to detectors module."""
        # Setup
        mock_is_honors_required.return_value = True
        
        # Execute
        result = self.facade.is_honors_required(self.honors_logic_block)
        
        # Verify
        mock_is_honors_required.assert_called_once_with(self.honors_logic_block)
        self.assertEqual(result, True)
        
    @patch('llm.articulation.render_group_summary')
    def test_render_group_summary(self, mock_render_group_summary):
        """Test that render_group_summary correctly delegates to the articulation module."""
        # Setup
        mock_render_group_summary.return_value = "Group summary text"
        
        # Execute
        result = self.facade.render_group_summary(self.docs)
        
        # Verify
        mock_render_group_summary.assert_called_once_with(self.docs)
        self.assertEqual(result, "Group summary text")
        
    @patch('llm.articulation.validate_combo_against_group')
    def test_validate_combo_against_group(self, mock_validate_combo_against_group):
        """Test that validate_combo_against_group correctly delegates to the articulation module."""
        # Setup
        mock_result = {
            "is_fully_satisfied": True,
            "satisfied_uc_courses": ["MATH 20A"],
            "partially_satisfied": False,
            "satisfied_count": 1,
            "required_count": 1
        }
        mock_validate_combo_against_group.return_value = mock_result
        courses = ["MATH 1A"]
        
        # Execute
        result = self.facade.validate_combo_against_group(courses, self.group_dict)
        
        # Verify
        mock_validate_combo_against_group.assert_called_once_with(courses, self.group_dict)
        self.assertEqual(result, mock_result)
        
    @patch('llm.articulation.is_honors_pair_equivalent')
    def test_is_honors_pair_equivalent(self, mock_is_honors_pair_equivalent):
        """Test that is_honors_pair_equivalent correctly delegates to the articulation module."""
        # Setup
        mock_is_honors_pair_equivalent.return_value = True
        
        # Execute
        result = self.facade.is_honors_pair_equivalent(self.honors_logic_block, "MATH 1A", "MATH 1AH")
        
        # Verify
        mock_is_honors_pair_equivalent.assert_called_once_with(self.honors_logic_block, "MATH 1A", "MATH 1AH")
        self.assertEqual(result, True)
        
    @patch('llm.articulation.explain_honors_equivalence')
    def test_explain_honors_equivalence(self, mock_explain_honors_equivalence):
        """Test that explain_honors_equivalence correctly delegates to the articulation module."""
        # Setup
        mock_explanation = "MATH 1A and MATH 1AH are equivalent"
        mock_explain_honors_equivalence.return_value = mock_explanation
        
        # Execute
        result = self.facade.explain_honors_equivalence("MATH 1A", "MATH 1AH")
        
        # Verify
        mock_explain_honors_equivalence.assert_called_once_with("MATH 1A", "MATH 1AH")
        self.assertEqual(result, mock_explanation)
    
    # Tests from test_articulation_options.py
    
    def test_get_articulation_options_with_standard_format(self):
        """Test get_articulation_options with the standard OR/AND nested format."""
        options = self.facade.get_articulation_options(self.cse8a_logic_block)
        
        # Assert the result has options
        self.assertIn("options", options)
        self.assertTrue(len(options["options"]) > 0)
        
        # Print for debugging
        print(f"Standard format result: {json.dumps(options, indent=2)}")
        
        # Verify structure
        for option in options["options"]:
            self.assertIn("courses", option)
            self.assertTrue(len(option["courses"]) > 0)

    def test_get_articulation_options_with_test_format(self):
        """Test get_articulation_options with the format used in tests."""
        options = self.facade.get_articulation_options(self.test_cse8a_logic_block)
        
        # Assert the result has options
        self.assertIn("options", options)
        self.assertTrue(len(options["options"]) > 0)
        
        # Print for debugging
        print(f"Test format result: {json.dumps(options, indent=2)}")
        
        # Verify structure
        for option in options["options"]:
            self.assertIn("courses", option)
            self.assertTrue(len(option["courses"]) > 0)
            
    def test_get_articulation_options_with_real_data(self):
        """Test get_articulation_options with real data from the rag_data.json file."""
        # Load the actual data from rag_data.json
        rag_data_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'rag_data.json')
        
        if not os.path.exists(rag_data_path):
            self.skipTest(f"Skipping test because {rag_data_path} not found")
            
        with open(rag_data_path, 'r') as f:
            data = json.load(f)
            
        # Find CSE 8A logic block
        cse8a_block = None
        for group in data.get('groups', []):
            for section in group.get('sections', []):
                for uc_course in section.get('uc_courses', []):
                    if uc_course.get('uc_course_id') == 'CSE 8A':
                        cse8a_block = uc_course.get('logic_block')
                        break
                if cse8a_block:
                    break
            if cse8a_block:
                break
                
        if not cse8a_block:
            self.skipTest("Skipping test because CSE 8A not found in rag_data.json")
            
        # Test with the real data
        options = self.facade.get_articulation_options(cse8a_block)
        
        # Print for debugging
        print(f"Real data result: {json.dumps(options, indent=2)}")
        print(f"Original data: {json.dumps(cse8a_block, indent=2)}")
        
        # Assert the result has options
        self.assertIn("options", options)
        self.assertTrue(len(options["options"]) > 0)


if __name__ == '__main__':
    unittest.main() 