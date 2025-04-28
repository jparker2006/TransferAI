"""
Unit tests for the CourseEquivalencyHandler class.

These tests verify that the handler correctly processes course equivalency queries
and produces appropriate responses about UC courses that can be satisfied.
"""

import unittest
from unittest.mock import MagicMock, patch

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.course_handler import CourseEquivalencyHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.articulation_facade import ArticulationFacade
from llm.services.matching_service import MatchingService


class TestCourseEquivalencyHandler(unittest.TestCase):
    """Test suite for the CourseEquivalencyHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {"verbosity": "STANDARD"}
        self.handler = CourseEquivalencyHandler(self.document_repository, self.config)
        self.handler.articulation_facade = MagicMock(spec=ArticulationFacade)
        self.handler.matching_service = MagicMock(spec=MatchingService)
        
        # Create mock documents for testing
        self.mock_doc_cse = MagicMock()
        self.mock_doc_cse.metadata = {
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
        
        self.mock_doc_math = MagicMock()
        self.mock_doc_math.metadata = {
            "uc_course": "MATH 20A",
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
        # Should handle explicit COURSE_EQUIVALENCY query type
        query = Query(
            text="What UC courses does CIS 22A satisfy?",
            filters={"ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_EQUIVALENCY
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle query with CCC courses and no UC courses
        query = Query(
            text="What UC courses does CIS 22A satisfy?",
            filters={"ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Should handle various forms of equivalency questions
        equivalency_variations = [
            "What can I satisfy with CIS 22A?",
            "What does MATH 1A transfer to?",
            "What requirements does CIS 22A meet?",
            "What UC courses are equivalent to CIS 22A?"
        ]
        
        for text in equivalency_variations:
            query = Query(
                text=text,
                filters={"ccc_courses": ["CIS 22A"]},
                config=self.config,
                query_type=QueryType.UNKNOWN
            )
            self.assertTrue(self.handler.can_handle(query))
        
        # Should not handle query with both UC and CCC courses
        query = Query(
            text="Does CIS 22A satisfy CSE 8A?",
            filters={"uc_course": ["CSE 8A"], "ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
        # Should not handle query with no CCC courses
        query = Query(
            text="What are the requirements for CSE 8A?",
            filters={"uc_course": ["CSE 8A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        self.assertFalse(self.handler.can_handle(query))
        
    def test_handle_single_course_single_match(self):
        """Test handle method with a single CCC course matching a single UC course."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [self.mock_doc_cse]
        self.handler.matching_service.match_reverse.return_value = [self.mock_doc_cse]
        self.handler.articulation_facade.count_uc_matches.return_value = (
            1, ["CSE 8A"], []
        )
        
        # Create query
        query = Query(
            text="What UC courses does CIS 22A satisfy?",
            filters={"ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_EQUIVALENCY
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("✅ CIS 22A can satisfy CSE 8A", result.formatted_response)
        self.assertEqual(result.matched_docs, [self.mock_doc_cse])
        
        # Verify mock calls
        self.document_repository.get_all_documents.assert_called_once()
        self.handler.matching_service.match_reverse.assert_called_once_with(
            documents=self.document_repository.get_all_documents.return_value,
            ccc_courses=["CIS 22A"],
            query_text="What UC courses does CIS 22A satisfy?"
        )
        self.handler.articulation_facade.count_uc_matches.assert_called_once_with(
            "CIS 22A", self.document_repository.get_all_documents.return_value
        )
        
    def test_handle_single_course_multiple_matches(self):
        """Test handle method with a single CCC course matching multiple UC courses."""
        # Set up mocks
        all_docs = [self.mock_doc_cse, self.mock_doc_math]
        self.document_repository.get_all_documents.return_value = all_docs
        self.handler.matching_service.match_reverse.return_value = all_docs
        self.handler.articulation_facade.count_uc_matches.return_value = (
            2, ["CSE 8A", "MATH 20A"], []
        )
        
        # Create query
        query = Query(
            text="What can I satisfy with CIS 22A?",
            filters={"ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_EQUIVALENCY
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("✅ CIS 22A can satisfy multiple UC courses", result.formatted_response)
        self.assertIn("CSE 8A", result.formatted_response)
        self.assertIn("MATH 20A", result.formatted_response)
        
    def test_handle_single_course_with_contributions(self):
        """Test handle method with a course that contributes to satisfying other requirements."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = [self.mock_doc_cse]
        self.handler.matching_service.match_reverse.return_value = [self.mock_doc_cse]
        self.handler.articulation_facade.count_uc_matches.return_value = (
            1, ["CSE 8A"], ["CSE 8B", "CSE 11"]
        )
        
        # Create query
        query = Query(
            text="What UC courses does CIS 22A satisfy?",
            filters={"ccc_courses": ["CIS 22A"]},
            config=self.config,
            query_type=QueryType.COURSE_EQUIVALENCY
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("✅ CIS 22A can satisfy CSE 8A", result.formatted_response)
        self.assertIn("contribute to satisfying CSE 8B, CSE 11", result.formatted_response)
        
    def test_handle_single_course_no_matches(self):
        """Test handle method with a course that doesn't satisfy any UC courses."""
        # Set up mocks
        self.document_repository.get_all_documents.return_value = []
        self.handler.matching_service.match_reverse.return_value = []
        self.handler.articulation_facade.count_uc_matches.return_value = (
            0, [], []
        )
        
        # Create query
        query = Query(
            text="What does CIS 999 satisfy?",
            filters={"ccc_courses": ["CIS 999"]},
            config=self.config,
            query_type=QueryType.COURSE_EQUIVALENCY
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("I couldn't find any UC courses", result.formatted_response)
        
    def test_handle_multiple_courses(self):
        """Test handle method with multiple CCC courses."""
        # Set up mocks
        all_docs = [self.mock_doc_cse, self.mock_doc_math]
        self.document_repository.get_all_documents.return_value = all_docs
        self.handler.matching_service.match_reverse.return_value = all_docs
        
        # Set up validation results with complete dictionaries
        cse_result = {
            "is_satisfied": True,
            "match_percentage": 100,
            "explanation": "Satisfied",
            "satisfied_options": [0],
            "missing_courses": {}
        }
        
        math_result = {
            "is_satisfied": False,
            "match_percentage": 50,
            "explanation": "Partially satisfied",
            "satisfied_options": [],
            "missing_courses": {"0": ["MATH 1B"]}
        }
        
        # Set up the side effect to return appropriate results for each document
        def validate_side_effect(logic_block, courses):
            # Get the uc_course this logic block belongs to
            for doc in all_docs:
                if doc.metadata.get("logic_block", {}) == logic_block:
                    uc_course = doc.metadata.get("uc_course", "")
                    if "CSE" in uc_course:
                        return cse_result
                    else:
                        return math_result
            
            # If we couldn't match the logic block to a document, use string matching as fallback
            if "CIS 22A" in str(logic_block):
                return cse_result
            else:
                return math_result
                
        self.handler.articulation_facade.validate_courses.side_effect = validate_side_effect
        
        # Create query
        query = Query(
            text="What can I satisfy with CIS 22A and MATH 1A?",
            filters={"ccc_courses": ["CIS 22A", "MATH 1A"]},
            config=self.config,
            query_type=QueryType.COURSE_EQUIVALENCY
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual(result.metadata["fully_satisfied"], ["CSE 8A"])
        self.assertEqual(result.metadata["partially_satisfied"], ["MATH 20A"])
        self.assertIn("fully satisfy: CSE 8A", result.formatted_response)
        self.assertIn("partially satisfy: MATH 20A", result.formatted_response)
        

if __name__ == "__main__":
    unittest.main() 