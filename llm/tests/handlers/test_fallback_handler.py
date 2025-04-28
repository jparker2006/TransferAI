"""
Unit tests for the FallbackQueryHandler class.

These tests verify that the fallback handler correctly processes queries that don't match
any specialized handler and provides appropriate generic responses.
"""

import unittest
from unittest.mock import MagicMock, patch

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.fallback_handler import FallbackQueryHandler
from llm.repositories.document_repository import DocumentRepository


class TestFallbackQueryHandler(unittest.TestCase):
    """Test suite for the FallbackQueryHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {"verbosity": "STANDARD"}
        self.handler = FallbackQueryHandler(self.document_repository, self.config)
        
    def test_can_handle(self):
        """Test can_handle method always returns True."""
        # Create various types of queries
        queries = [
            Query(
                text="What courses are available?",
                filters={},
                config=self.config,
                query_type=QueryType.UNKNOWN
            ),
            Query(
                text="Does MATH 1A satisfy CSE 8A?",
                filters={"uc_course": ["CSE 8A"], "ccc_courses": ["MATH 1A"]},
                config=self.config,
                query_type=QueryType.COURSE_EQUIVALENCY
            ),
            Query(
                text="What are the requirements for Group 1?",
                filters={"group_id": "1"},
                config=self.config,
                query_type=QueryType.GROUP_REQUIREMENT
            ),
            Query(
                text="",  # Empty query
                filters={},
                config=self.config,
                query_type=QueryType.UNKNOWN
            )
        ]
        
        # The fallback handler should be able to handle all queries
        for query in queries:
            self.assertTrue(self.handler.can_handle(query))
    
    def test_handle_with_ccc_course(self):
        """Test handle method with a query containing CCC courses."""
        # Create query with CCC course
        query = Query(
            text="Tell me about MATH 1A",
            filters={"ccc_courses": ["MATH 1A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("MATH 1A", result.formatted_response)
        self.assertIn("try asking", result.formatted_response.lower())
        self.assertIn("satisfy a specific UC course", result.formatted_response)
        
    def test_handle_without_ccc_course(self):
        """Test handle method with a query not containing CCC courses."""
        # Create query without CCC course
        query = Query(
            text="How do I transfer credits?",
            filters={},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertIn("I'm not sure how to answer that question", result.formatted_response)
        self.assertIn("Try asking about specific course articulations", result.formatted_response)
        
    def test_handle_empty_query(self):
        """Test handle method with an empty query."""
        # Create empty query
        query = Query(
            text="",
            filters={},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result
        self.assertIsNotNone(result)
        self.assertEqual("Unable to process query type.", result.raw_response)
        self.assertIn("I'm not sure how to answer that question", result.formatted_response)
        
    def test_handle_multiple_ccc_courses(self):
        """Test handle method with multiple CCC courses."""
        # Create query with multiple CCC courses
        query = Query(
            text="Tell me about MATH 1A and PHYS 4A",
            filters={"ccc_courses": ["MATH 1A", "PHYS 4A"]},
            config=self.config,
            query_type=QueryType.UNKNOWN
        )
        
        # Process query
        result = self.handler.handle(query)
        
        # Verify result - should just reference the first CCC course
        self.assertIsNotNone(result)
        self.assertIn("MATH 1A", result.formatted_response)
        self.assertNotIn("PHYS 4A", result.formatted_response)
        

if __name__ == "__main__":
    unittest.main() 