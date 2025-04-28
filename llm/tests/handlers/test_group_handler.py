"""
Unit tests for the GroupQueryHandler class.

These tests verify that the handler correctly processes group requirement queries
and produces appropriate responses for group information and validation.
"""

import unittest
from unittest.mock import MagicMock, patch

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.group_handler import GroupQueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.articulation_facade import ArticulationFacade
from llm.services.matching_service import MatchingService


class TestGroupQueryHandler(unittest.TestCase):
    """Test suite for the GroupQueryHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {"verbosity": "STANDARD"}
        self.handler = GroupQueryHandler(self.document_repository, self.config)
        self.handler.articulation_facade = MagicMock(spec=ArticulationFacade)
        self.handler.matching_service = MagicMock(spec=MatchingService)
        
        # Create mock group documents for testing
        self.mock_doc_group1_sectionA_course1 = MagicMock()
        self.mock_doc_group1_sectionA_course1.metadata = {
            "group": "1",
            "group_title": "Mathematics Requirements",
            "group_logic_type": "CHOOSE_ONE_SECTION",
            "section": "A",
            "section_title": "Calculus",
            "uc_course": "MATH 20A",
            "uc_title": "Calculus I",
            "ccc_courses": ["MATH 1A"],
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
        
        self.mock_doc_group1_sectionA_course2 = MagicMock()
        self.mock_doc_group1_sectionA_course2.metadata = {
            "group": "1",
            "group_title": "Mathematics Requirements",
            "group_logic_type": "CHOOSE_ONE_SECTION",
            "section": "A",
            "section_title": "Calculus",
            "uc_course": "MATH 20B",
            "uc_title": "Calculus II",
            "ccc_courses": ["MATH 1B"],
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 1B", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        self.mock_doc_group1_sectionB_course1 = MagicMock()
        self.mock_doc_group1_sectionB_course1.metadata = {
            "group": "1",
            "group_title": "Mathematics Requirements",
            "group_logic_type": "CHOOSE_ONE_SECTION",
            "section": "B",
            "section_title": "Statistics",
            "uc_course": "MATH 11",
            "uc_title": "Statistics",
            "ccc_courses": ["MATH 10"],
            "logic_block": {
                "type": "OR",
                "courses": [
                    {
                        "type": "AND",
                        "courses": [
                            {"course_letters": "MATH 10", "honors": False}
                        ]
                    }
                ]
            }
        }
        
        self.mock_doc_group2_course1 = MagicMock()
        self.mock_doc_group2_course1.metadata = {
            "group": "2",
            "group_title": "Computer Science Requirements",
            "group_logic_type": "SELECT_N_COURSES",
            "n_courses": 2,
            "section": "A",
            "uc_course": "CSE 8A",
            "ccc_courses": ["CIS 22A"],
            "logic_block": {
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
        }
        
        # Create sample validation results
        self.full_satisfaction_result = {
            "is_fully_satisfied": True,
            "partially_satisfied": False,
            "satisfied_uc_courses": ["MATH 20A", "MATH 20B"],
            "satisfied_count": 2,
            "required_count": 2
        }
        
        self.partial_satisfaction_result = {
            "is_fully_satisfied": False,
            "partially_satisfied": True,
            "satisfied_uc_courses": ["MATH 20A"],
            "satisfied_count": 1,
            "required_count": 2
        }
        
        self.no_satisfaction_result = {
            "is_fully_satisfied": False,
            "partially_satisfied": False,
            "satisfied_uc_courses": [],
            "satisfied_count": 0,
            "required_count": 2
        }
        
    def test_can_handle(self):
        """Test can_handle method."""
        # Should handle explicit GROUP_REQUIREMENT query type
        query = Query(
            text="What are the requirements for Group 1?",
            filters={},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle query with explicit group
        query = Query(
            text="What are the requirements for Group 1?",
            filters={"group": ["1"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle query with group-related keywords
        query = Query(
            text="Tell me about the prerequisites in Group 1",
            filters={},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should not handle query with UC courses (likely a course-specific query)
        query = Query(
            text="What are the group requirements for MATH 20A?",
            filters={"uc_course": ["MATH 20A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
        # Should not handle query with explicit non-GROUP_REQUIREMENT type
        query = Query(
            text="Does CIS 22A satisfy CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        self.assertFalse(self.handler.can_handle(query))
        
    def test_handle_no_group_specified(self):
        """Test handle method with no group specified."""
        # Set up mock
        self.document_repository.get_all_documents.return_value = []
        
        # Create query
        query = Query(
            text="What are the group requirements?",
            filters={},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("Please specify which group", result.formatted_response)
        
    def test_handle_group_info(self):
        """Test handle method with a request for group information."""
        # Set up mocks
        group1_docs = [
            self.mock_doc_group1_sectionA_course1,
            self.mock_doc_group1_sectionA_course2,
            self.mock_doc_group1_sectionB_course1
        ]
        self.document_repository.get_all_documents.return_value = group1_docs
        self.handler.articulation_facade.render_group_summary.return_value = (
            "Section A (Calculus):\n- MATH 20A (Calculus I): MATH 1A\n- MATH 20B (Calculus II): MATH 1B\n\n"
            "Section B (Statistics):\n- MATH 11 (Statistics): MATH 10"
        )
        
        # Create query
        query = Query(
            text="What are the requirements for Group 1?",
            filters={"group": ["1"]},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata["group_id"], "1")
        self.assertEqual(result.metadata["group_title"], "Mathematics Requirements")
        self.assertEqual(result.metadata["group_type"], "CHOOSE_ONE_SECTION")
        self.assertIn("Mathematics Requirements (Group 1)", result.formatted_response)
        self.assertIn("You need to complete all courses from one section", result.formatted_response)
        self.assertIn("Section A (Calculus)", result.formatted_response)
        self.assertIn("Section B (Statistics)", result.formatted_response)
        
        # Verify mock calls
        self.document_repository.get_all_documents.assert_called_once()
        self.handler.articulation_facade.render_group_summary.assert_called_once_with(group1_docs)
        
    def test_handle_group_validation_full_satisfaction(self):
        """Test handle method with a request to validate courses against a group (full satisfaction)."""
        # Set up mocks
        group1_docs = [
            self.mock_doc_group1_sectionA_course1,
            self.mock_doc_group1_sectionA_course2
        ]
        self.document_repository.get_all_documents.return_value = group1_docs
        self.handler.articulation_facade.validate_combo_against_group.return_value = self.full_satisfaction_result
        
        # Create query
        query = Query(
            text="Do MATH 1A and MATH 1B satisfy Group 1?",
            filters={"group": ["1"], "ccc_courses": ["MATH 1A", "MATH 1B"]},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertTrue(result.metadata["is_satisfied"])
        self.assertFalse(result.metadata["is_partially_satisfied"])
        self.assertEqual(result.metadata["satisfied_uc_courses"], ["MATH 20A", "MATH 20B"])
        self.assertIn("✅ Yes, your courses (MATH 1A, MATH 1B) fully satisfy", result.formatted_response)
        self.assertIn("MATH 20A, MATH 20B", result.formatted_response)
        
    def test_handle_group_validation_partial_satisfaction(self):
        """Test handle method with a request to validate courses against a group (partial satisfaction)."""
        # Set up mocks
        group1_docs = [
            self.mock_doc_group1_sectionA_course1,
            self.mock_doc_group1_sectionA_course2
        ]
        self.document_repository.get_all_documents.return_value = group1_docs
        self.handler.articulation_facade.validate_combo_against_group.return_value = self.partial_satisfaction_result
        
        # Create query
        query = Query(
            text="Does MATH 1A satisfy Group 1?",
            filters={"group": ["1"], "ccc_courses": ["MATH 1A"]},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertFalse(result.metadata["is_satisfied"])
        self.assertTrue(result.metadata["is_partially_satisfied"])
        self.assertEqual(result.metadata["satisfied_uc_courses"], ["MATH 20A"])
        self.assertIn("🔶 Your courses partially satisfy", result.formatted_response)
        self.assertIn("MATH 20A", result.formatted_response)
        self.assertIn("you still need 1 more UC course(s)", result.formatted_response)
        
    def test_handle_group_validation_no_satisfaction(self):
        """Test handle method with a request to validate courses against a group (no satisfaction)."""
        # Set up mocks
        group1_docs = [
            self.mock_doc_group1_sectionA_course1,
            self.mock_doc_group1_sectionA_course2
        ]
        self.document_repository.get_all_documents.return_value = group1_docs
        self.handler.articulation_facade.validate_combo_against_group.return_value = self.no_satisfaction_result
        
        # Create query
        query = Query(
            text="Do CIS 22A and CIS 22B satisfy Group 1?",
            filters={"group": ["1"], "ccc_courses": ["CIS 22A", "CIS 22B"]},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertFalse(result.metadata["is_satisfied"])
        self.assertFalse(result.metadata["is_partially_satisfied"])
        self.assertEqual(result.metadata["satisfied_uc_courses"], [])
        self.assertIn("❌ No, your courses do not satisfy", result.formatted_response)
        self.assertIn("No UC course articulation paths were matched", result.formatted_response)
        
    def test_handle_group_not_found(self):
        """Test handle method with a group ID that doesn't exist."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [
            self.mock_doc_group1_sectionA_course1,
            self.mock_doc_group1_sectionA_course2
        ]
        
        # Create query
        query = Query(
            text="What are the requirements for Group 99?",
            filters={"group": ["99"]},
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("I couldn't find any information about Group 99", result.formatted_response)
        
    def test_extract_group_id_from_text(self):
        """Test extraction of group ID from query text."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [
            self.mock_doc_group1_sectionA_course1,
            self.mock_doc_group1_sectionA_course2
        ]
        self.handler.articulation_facade.render_group_summary.return_value = "Group 1 summary"
        
        # Create query without explicit group_id
        query = Query(
            text="What are the requirements for Group 1?",
            filters={},  # No group filter
            config=self.config,
            query_type=QueryType.GROUP_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("Mathematics Requirements (Group 1)", result.formatted_response)


if __name__ == "__main__":
    unittest.main() 