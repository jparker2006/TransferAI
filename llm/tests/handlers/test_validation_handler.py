"""
Unit tests for the ValidationQueryHandler class.

These tests verify that the handler correctly processes course validation queries
and produces appropriate validation results.
"""

import unittest
from unittest.mock import MagicMock, patch

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.validation_handler import ValidationQueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.articulation_facade import ArticulationFacade
from llm.services.matching_service import MatchingService


class TestValidationQueryHandler(unittest.TestCase):
    """Test suite for the ValidationQueryHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {"verbosity": "STANDARD"}
        self.handler = ValidationQueryHandler(self.document_repository, self.config)
        self.handler.articulation_facade = MagicMock(spec=ArticulationFacade)
        self.handler.matching_service = MagicMock(spec=MatchingService)
        
        # Create mock document for testing
        self.mock_doc = MagicMock()
        self.mock_doc.metadata = {
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
        
        # Create mock document with no articulation
        self.no_articulation_doc = MagicMock()
        self.no_articulation_doc.metadata = {
            "uc_course": "CHEM 40A",
            "ccc_courses": [],
            "logic_block": {
                "no_articulation": True
            }
        }
        
    def test_can_handle(self):
        """Test can_handle method."""
        # Should handle explicit COURSE_VALIDATION query type
        query = Query(
            text="Does CIS 22A satisfy CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle query with UC and CCC courses and validation keywords
        query = Query(
            text="Does CIS 22A satisfy CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle query with other validation keywords
        query = Query(
            text="Is CIS 22A equivalent to CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should not handle query missing UC courses
        query = Query(
            text="What does CIS 22A satisfy?",
            filters={"ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
        # Should not handle query missing CCC courses
        query = Query(
            text="What satisfies CSE 8A?",
            filters={"uc_course": ["CSE 8A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
    def test_handle_success(self):
        """Test handle method with successful validation."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [self.mock_doc]
        self.handler.matching_service.match_documents.return_value = [self.mock_doc]
        self.handler.matching_service.validate_same_section.return_value = [self.mock_doc]
        self.handler.articulation_facade.validate_courses.return_value = {
            "is_satisfied": True,
            "explanation": "Course requirements are satisfied.",
            "satisfied_options": [0],
            "missing_courses": {},
            "match_percentage": 100
        }
        self.handler.articulation_facade.format_binary_response.return_value = (
            "✅ Yes, CIS 22A satisfies CSE 8A requirements."
        )
        
        # Create query
        query = Query(
            text="Does CIS 22A satisfy CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.satisfied, True)
        self.assertEqual(result.formatted_response, "✅ Yes, CIS 22A satisfies CSE 8A requirements.")
        self.assertEqual(result.matched_docs, [self.mock_doc])
        self.assertEqual(result.metadata["uc_course"], "CSE 8A")
        self.assertEqual(result.metadata["ccc_courses"], ["CIS 22A"])
        
        # Verify mock calls
        self.document_repository.get_all_documents.assert_called_once()
        self.handler.matching_service.match_documents.assert_called_once_with(
            documents=self.document_repository.get_all_documents.return_value,
            uc_courses=["CSE 8A"],
            ccc_courses=["CIS 22A"],
            query_text="Does CIS 22A satisfy CSE 8A?"
        )
        self.handler.matching_service.validate_same_section.assert_called_once_with([self.mock_doc])
        self.handler.articulation_facade.validate_courses.assert_called_once_with(
            self.mock_doc.metadata["logic_block"], ["CIS 22A"]
        )
        self.handler.articulation_facade.format_binary_response.assert_called_once_with(
            True, "Course requirements are satisfied.", "CSE 8A"
        )
        
    def test_handle_failure(self):
        """Test handle method with unsuccessful validation."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [self.mock_doc]
        self.handler.matching_service.match_documents.return_value = [self.mock_doc]
        self.handler.matching_service.validate_same_section.return_value = [self.mock_doc]
        self.handler.articulation_facade.validate_courses.return_value = {
            "is_satisfied": False,
            "explanation": "Course requirements are not satisfied.",
            "satisfied_options": [],
            "missing_courses": {"0": ["CIS 22B"]},
            "match_percentage": 0
        }
        self.handler.articulation_facade.format_binary_response.return_value = (
            "❌ No, CIS 35A does not satisfy CSE 8A requirements."
        )
        
        # Create query
        query = Query(
            text="Does CIS 35A satisfy CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 35A"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.satisfied, False)
        self.assertEqual(result.formatted_response, "❌ No, CIS 35A does not satisfy CSE 8A requirements.")
        
    def test_handle_no_articulation(self):
        """Test handle method with no_articulation flag."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [self.no_articulation_doc]
        self.handler.matching_service.match_documents.return_value = [self.no_articulation_doc]
        self.handler.matching_service.validate_same_section.return_value = [self.no_articulation_doc]
        
        # Create query
        query = Query(
            text="Does CIS 35A satisfy CHEM 40A?",
            filters={"uc_course": ["CHEM 40A"], "ccc_courses": ["CIS 35A"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.satisfied, False)
        self.assertIn("No, CHEM 40A has no articulation", result.formatted_response)
        
    def test_handle_honors_pair_equivalence(self):
        """Test handle method with honors pair equivalence."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [self.mock_doc]
        self.handler.matching_service.match_documents.return_value = [self.mock_doc]
        self.handler.matching_service.validate_same_section.return_value = [self.mock_doc]
        self.handler.articulation_facade.is_honors_pair_equivalent.return_value = True
        self.handler.articulation_facade.explain_honors_equivalence.return_value = (
            "MATH 1A and MATH 1AH together satisfy MATH 20A."
        )
        
        # Create query
        query = Query(
            text="Do MATH 1A and MATH 1AH satisfy MATH 20A?",
            filters={"uc_course": ["MATH 20A"], "ccc_courses": ["MATH 1A", "MATH 1AH"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.satisfied, True)
        self.assertIn("Yes, MATH 1A and MATH 1AH together satisfy MATH 20A", result.formatted_response)
        
    def test_handle_no_matching_document(self):
        """Test handle method with no matching document."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = []
        self.handler.matching_service.match_documents.return_value = []
        self.handler.matching_service.validate_same_section.return_value = []
        
        # Create query
        query = Query(
            text="Does CIS 22A satisfy NONEXISTENT?",
            filters={"uc_course": ["NONEXISTENT"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_VALIDATION
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("I couldn't find any articulation information", result.formatted_response)
        

if __name__ == "__main__":
    unittest.main() 