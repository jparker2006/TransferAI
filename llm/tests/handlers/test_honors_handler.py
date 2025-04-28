"""
Unit tests for the HonorsQueryHandler class.

These tests verify that the handler correctly processes honors requirement queries
and produces appropriate responses about whether honors courses are required.
"""

import unittest
from unittest.mock import MagicMock, patch

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.honors_handler import HonorsQueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.articulation_facade import ArticulationFacade
from llm.services.matching_service import MatchingService
from llm.services.query_service import QueryService


class TestHonorsQueryHandler(unittest.TestCase):
    """Test suite for the HonorsQueryHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {"verbosity": "STANDARD"}
        self.handler = HonorsQueryHandler(self.document_repository, self.config)
        self.handler.articulation_facade = MagicMock(spec=ArticulationFacade)
        self.handler.matching_service = MagicMock(spec=MatchingService)
        self.handler.query_service = MagicMock(spec=QueryService)
        
        # Configure normalize_course_code to return the input unchanged for simplicity
        self.handler.query_service.normalize_course_code.side_effect = lambda x: x
        
        # Create mock documents for testing
        self.mock_doc_honors_required = MagicMock()
        self.mock_doc_honors_required.metadata = {
            "uc_course": "MATH 20A",
            "uc_title": "Calculus for Science and Engineering I",
            "ccc_courses": ["MATH 1AH"],
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
        
        self.mock_doc_honors_optional = MagicMock()
        self.mock_doc_honors_optional.metadata = {
            "uc_course": "CSE 8A",
            "uc_title": "Introduction to Programming",
            "ccc_courses": ["CIS 22A", "CIS 22AH"],
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
                            {"course_letters": "CIS 22AH", "honors": True}
                        ]
                    }
                ]
            }
        }
        
        self.mock_doc_no_articulation = MagicMock()
        self.mock_doc_no_articulation.metadata = {
            "uc_course": "CHEM 40A",
            "uc_title": "Organic Chemistry",
            "ccc_courses": [],
            "logic_block": {
                "no_articulation": True
            }
        }
        
        # Mock honors info responses
        self.honors_required_info = {
            "honors_courses": ["MATH 1AH"],
            "non_honors_courses": []
        }
        
        self.honors_optional_info = {
            "honors_courses": ["CIS 22AH"],
            "non_honors_courses": ["CIS 22A"]
        }
        
    def test_can_handle(self):
        """Test can_handle method."""
        # Should handle explicit HONORS_REQUIREMENT query type
        query = Query(
            text="Does MATH 20A require honors courses?",
            filters={},
            config=self.config,
            query_type=QueryType.HONORS_REQUIREMENT
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle query with UC course and honors-related keywords
        query = Query(
            text="Does MATH 20A require honors courses?",
            filters={"uc_course": ["MATH 20A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle various forms of honors questions
        honors_variations = [
            "Does CSE 8A need honors?",
            "Is an honors version required for MATH 20A?",
            "Can I satisfy CHEM 1A without honors?",
            "Do I need to take MATH 20AH?"
        ]
        
        for text in honors_variations:
            query = Query(
                text=text,
                filters={"uc_course": ["MATH 20A"]},
                config=self.config,
                query_type=QueryType.UNKNOWN
            )
            self.assertTrue(self.handler.can_handle(query))
        
        # Should not handle query with no UC course
        query = Query(
            text="Which classes require honors courses?",
            filters={},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
        # Should not handle query with UC course but no honors keywords
        query = Query(
            text="What are the requirements for MATH 20A?",
            filters={"uc_course": ["MATH 20A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
    def test_handle_no_uc_course_specified(self):
        """Test handle method with no UC course specified."""
        # Create query
        query = Query(
            text="Do I need honors courses?",
            filters={},
            config=self.config,
            query_type=QueryType.HONORS_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("Please specify which UC course", result.formatted_response)
        
    def test_handle_course_not_found(self):
        """Test handle method with a UC course that doesn't exist."""
        # Set up mock
        self.document_repository.get_all_documents.return_value = []
        
        # Create query
        query = Query(
            text="Does NONEXISTENT 101 require honors courses?",
            filters={"uc_course": ["NONEXISTENT 101"]},
            config=self.config,
            query_type=QueryType.HONORS_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("I couldn't find any articulation information", result.formatted_response)
        
    def test_handle_no_articulation(self):
        """Test handle method with a course that has no articulation."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [
            self.mock_doc_no_articulation
        ]
        
        # Create query
        query = Query(
            text="Does CHEM 40A require honors courses?",
            filters={"uc_course": ["CHEM 40A"]},
            config=self.config,
            query_type=QueryType.HONORS_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("must be completed at the UC campus", result.formatted_response)
        self.assertIn("no community college courses", result.formatted_response)
        
    def test_handle_honors_required(self):
        """Test handle method with a course that requires honors."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [
            self.mock_doc_honors_required
        ]
        self.handler.articulation_facade.is_honors_required.return_value = True
        self.handler.articulation_facade.extract_honors_info.return_value = self.honors_required_info
        
        # Create query
        query = Query(
            text="Does MATH 20A require honors courses?",
            filters={"uc_course": ["MATH 20A"]},
            config=self.config,
            query_type=QueryType.HONORS_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata["uc_course"], "MATH 20A")
        self.assertTrue(result.metadata["honors_required"])
        self.assertEqual(result.metadata["honors_courses"], ["MATH 1AH"])
        self.assertEqual(result.metadata["non_honors_courses"], [])
        self.assertIn("✅ Yes, MATH 20A requires honors courses", result.formatted_response)
        self.assertIn("only honors courses will satisfy", result.formatted_response)
        self.assertIn("MATH 1AH", result.formatted_response)
        
        # Verify mock calls
        self.document_repository.get_all_documents.assert_called_once()
        self.handler.articulation_facade.is_honors_required.assert_called_once_with(
            self.mock_doc_honors_required.metadata["logic_block"]
        )
        self.handler.articulation_facade.extract_honors_info.assert_called_once_with(
            self.mock_doc_honors_required.metadata["logic_block"]
        )
        
    def test_handle_honors_optional(self):
        """Test handle method with a course that has optional honors."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [
            self.mock_doc_honors_optional
        ]
        self.handler.articulation_facade.is_honors_required.return_value = False
        self.handler.articulation_facade.extract_honors_info.return_value = self.honors_optional_info
        
        # Create query
        query = Query(
            text="Does CSE 8A require honors courses?",
            filters={"uc_course": ["CSE 8A"]},
            config=self.config,
            query_type=QueryType.HONORS_REQUIREMENT
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata["uc_course"], "CSE 8A")
        self.assertFalse(result.metadata["honors_required"])
        self.assertEqual(result.metadata["honors_courses"], ["CIS 22AH"])
        self.assertEqual(result.metadata["non_honors_courses"], ["CIS 22A"])
        self.assertIn("❌ No, CSE 8A does not require honors courses", result.formatted_response)
        self.assertIn("either honors or non-honors courses", result.formatted_response)
        self.assertIn("standard courses (CIS 22A) or their honors equivalents (CIS 22AH)", result.formatted_response)
        
        # Verify mock calls
        self.document_repository.get_all_documents.assert_called_once()
        self.handler.articulation_facade.is_honors_required.assert_called_once_with(
            self.mock_doc_honors_optional.metadata["logic_block"]
        )
        self.handler.articulation_facade.extract_honors_info.assert_called_once_with(
            self.mock_doc_honors_optional.metadata["logic_block"]
        )


if __name__ == "__main__":
    unittest.main() 