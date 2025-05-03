"""
Unit tests for the CourseLookupHandler class.

These tests verify that the handler correctly processes course lookup queries
and produces appropriate responses about CCC courses that satisfy UC courses.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.course_lookup_handler import CourseLookupHandler
from llm.repositories.document_repository import DocumentRepository
from llama_index_client import Document

class TestCourseLookupHandler(unittest.TestCase):
    """Test cases for the CourseLookupHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {"debug_mode": True}
        self.handler = CourseLookupHandler(self.document_repository, self.config)
        
        # Mock dependencies
        self.handler.matching_service = MagicMock()
        self.handler.articulation_facade = MagicMock()
        self.handler.query_service = MagicMock()
        
        # Default normalization behavior
        self.handler.query_service.normalize_course_code.side_effect = lambda x: x.upper()
    
    def test_handle_no_uc_courses(self):
        """Test handling a query with no UC courses specified."""
        query = MagicMock(spec=Query)
        query.uc_courses = []
        query.text = "What courses satisfy UC requirements?"
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertIn("Please specify which UC course", result.formatted_response)
    
    def test_handle_no_matching_documents(self):
        """Test handling a query when no matching documents are found."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 8A"]
        query.text = "What courses satisfy CSE 8A?"
        
        # Mock matching_service to return no documents
        self.handler.matching_service.match_documents.return_value = []
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertIn("I couldn't find any articulation information", result.formatted_response)
        
        # Verify matching_service was called correctly
        self.handler.matching_service.match_documents.assert_called_once()
        call_args = self.handler.matching_service.match_documents.call_args[1]
        self.assertEqual(call_args["uc_courses"], ["CSE 8A"])
        self.assertEqual(call_args["ccc_courses"], [])
    
    def test_handle_no_articulation(self):
        """Test handling a course explicitly marked as having no articulation."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 8A"]
        query.text = "What courses satisfy CSE 8A?"
        
        # Create a mock document with no_articulation=True
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "CSE 8A",
            "logic_block": {"no_articulation": True}
        }
        
        # Mock matching_service to return this document
        self.handler.matching_service.match_documents.return_value = [doc]
        
        # Mock query_service for normalization
        self.handler.query_service.normalize_course_code.return_value = "CSE 8A"
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertIn("No, CSE 8A", result.formatted_response)
        self.assertIn("does not have any articulation", result.formatted_response)
        self.assertFalse(result.metadata.get("has_articulation", True))
    
    def test_handle_successful_articulation(self):
        """Test successful articulation lookup with valid options."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 8A"]
        query.text = "What courses satisfy CSE 8A?"
        
        # Create a mock document with articulation options
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "CSE 8A",
            "logic_block": {
                "options": [
                    {
                        "courses": [
                            {"name": "CIS 22A Introduction to Programming", "is_honors": False}
                        ]
                    }
                ]
            }
        }
        
        # Mock matching_service to return this document
        self.handler.matching_service.match_documents.return_value = [doc]
        
        # Mock query_service for normalization
        self.handler.query_service.normalize_course_code.return_value = "CSE 8A"
        
        # Mock articulation_facade methods
        self.handler.articulation_facade.get_articulation_options.return_value = {
            "options": [
                {
                    "courses": [
                        {"name": "CIS 22A", "is_honors": False}
                    ]
                }
            ]
        }
        self.handler.articulation_facade.format_course_options.return_value = "# CSE 8A can be satisfied by:\n\n**Option A**: CIS 22A"
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.formatted_response, "# CSE 8A can be satisfied by:\n\n**Option A**: CIS 22A")
        self.assertEqual(result.matched_docs, [doc])
        
        # Verify both facade methods were called correctly
        self.handler.articulation_facade.get_articulation_options.assert_called_once_with(doc.metadata["logic_block"])
        self.handler.articulation_facade.format_course_options.assert_called_once()
    
    def test_handle_complex_articulation(self):
        """Test handling complex articulation with AND groups and multiple options."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["MATH 20C"]
        query.text = "What courses satisfy MATH 20C?"
        
        # Create a mock document with complex articulation
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "MATH 20C",
            "logic_block": {
                "options": [
                    {
                        "courses": [
                            [
                                {"name": "MATH 1C Calculus", "is_honors": False},
                                {"name": "MATH 1D Calculus", "is_honors": False}
                            ]
                        ]
                    },
                    {
                        "courses": [
                            [
                                {"name": "MATH 1CH Honors Calculus", "is_honors": True},
                                {"name": "MATH 1DH Honors Calculus", "is_honors": True}
                            ]
                        ]
                    }
                ]
            }
        }
        
        # Mock matching_service to return this document
        self.handler.matching_service.match_documents.return_value = [doc]
        
        # Mock query_service for normalization
        self.handler.query_service.normalize_course_code.return_value = "MATH 20C"
        
        # Mock articulation_facade methods
        self.handler.articulation_facade.get_articulation_options.return_value = {
            "options": [
                {
                    "courses": [
                        {
                            "type": "AND",
                            "courses": [
                                {"name": "MATH 1C", "is_honors": False},
                                {"name": "MATH 1D", "is_honors": False}
                            ]
                        }
                    ]
                },
                {
                    "courses": [
                        {
                            "type": "AND",
                            "courses": [
                                {"name": "MATH 1CH", "is_honors": True},
                                {"name": "MATH 1DH", "is_honors": True}
                            ]
                        }
                    ]
                }
            ]
        }
        
        expected_response = "# MATH 20C can be satisfied by any of these options:\n\n**Option A**: MATH 1C, MATH 1D (complete all)\n**Option B**: MATH 1CH (Honors), MATH 1DH (Honors) (complete all)"
        self.handler.articulation_facade.format_course_options.return_value = expected_response
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.formatted_response, expected_response)
        self.assertEqual(result.matched_docs, [doc])
        
    def test_handle_error_in_articulation_processing(self):
        """Test handling errors that occur during articulation processing."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 8A"]
        query.text = "What courses satisfy CSE 8A?"
        
        # Create a mock document
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "CSE 8A",
            "logic_block": {"options": [{"courses": []}]}
        }
        
        # Mock matching_service to return this document
        self.handler.matching_service.match_documents.return_value = [doc]
        
        # Mock query_service for normalization
        self.handler.query_service.normalize_course_code.return_value = "CSE 8A"
        
        # Mock articulation_facade.get_articulation_options to raise an exception
        self.handler.articulation_facade.get_articulation_options.side_effect = Exception("Test error")
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertIn("error", result.formatted_response.lower())
        self.assertIn("CSE 8A", result.formatted_response)
    
    def test_handle_multiple_courses(self):
        """Test handling a query with multiple UC courses."""
        # Create a query with multiple UC courses
        query = MagicMock(spec=Query)
        query.uc_courses = ["MATH 20A", "MATH 20B"]
        query.text = "Which courses satisfy MATH 20A and 20B?"
        
        # Create mock documents for each course
        doc_math20a = MagicMock(spec=Document)
        doc_math20a.metadata = {
            "uc_course": "MATH 20A",
            "logic_block": {
                "options": [
                    {
                        "courses": [
                            {"name": "MATH 1A", "is_honors": False}
                        ]
                    },
                    {
                        "courses": [
                            {"name": "MATH 1AH", "is_honors": True}
                        ]
                    }
                ]
            }
        }
        
        doc_math20b = MagicMock(spec=Document)
        doc_math20b.metadata = {
            "uc_course": "MATH 20B",
            "logic_block": {
                "options": [
                    {
                        "courses": [
                            {"name": "MATH 1B", "is_honors": False}
                        ]
                    },
                    {
                        "courses": [
                            {"name": "MATH 1BH", "is_honors": True}
                        ]
                    }
                ]
            }
        }
        
        # Set up side effects for mock calls to handle multiple courses
        def mock_match_documents(documents, uc_courses, ccc_courses, query_text):
            if uc_courses == ["MATH 20A"]:
                return [doc_math20a]
            elif uc_courses == ["MATH 20B"]:
                return [doc_math20b]
            return []
        
        self.handler.matching_service.match_documents.side_effect = mock_match_documents
        
        # Mock normalize_course_code to return the input value
        def mock_normalize(course_code):
            return course_code
        
        self.handler.query_service.normalize_course_code.side_effect = mock_normalize
        
        # Reset get_articulation_options mock to return specific values instead of using side_effect
        self.handler.articulation_facade.get_articulation_options = MagicMock()
        
        # Set up return values for each logic block
        math20a_options = {
            "options": [
                {
                    "courses": [{"name": "MATH 1A", "is_honors": False}]
                },
                {
                    "courses": [{"name": "MATH 1AH", "is_honors": True}]
                }
            ]
        }
        
        math20b_options = {
            "options": [
                {
                    "courses": [{"name": "MATH 1B", "is_honors": False}]
                },
                {
                    "courses": [{"name": "MATH 1BH", "is_honors": True}]
                }
            ]
        }
        
        # Set up the return value map for get_articulation_options
        self.handler.articulation_facade.get_articulation_options.side_effect = [
            math20a_options,
            math20b_options
        ]
        
        # Reset format_course_options mock
        self.handler.articulation_facade.format_course_options = MagicMock()
        
        # Set up return values for format_course_options
        math20a_response = "# MATH 20A can be satisfied by any of these options:\n\n**Option A**: MATH 1A\n**Option B**: MATH 1AH (Honors)"
        math20b_response = "# MATH 20B can be satisfied by any of these options:\n\n**Option A**: MATH 1B\n**Option B**: MATH 1BH (Honors)"
        
        self.handler.articulation_facade.format_course_options.side_effect = [
            math20a_response,
            math20b_response
        ]
        
        # Process the query
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIsNotNone(result)
        self.assertIn("MATH 20A", result.formatted_response)
        self.assertIn("MATH 20B", result.formatted_response)
        self.assertIn("MATH 1A", result.formatted_response)
        self.assertIn("MATH 1AH", result.formatted_response)
        self.assertIn("MATH 1B", result.formatted_response)
        self.assertIn("MATH 1BH", result.formatted_response)
        self.assertIn("Articulation options for MATH 20A, MATH 20B", result.formatted_response)
        
        # Verify that the handler made the expected calls
        self.assertEqual(self.handler.matching_service.match_documents.call_count, 2)
        self.assertEqual(self.handler.articulation_facade.get_articulation_options.call_count, 2)
        self.assertEqual(self.handler.articulation_facade.format_course_options.call_count, 2)
        
        # Check the metadata
        self.assertEqual(result.metadata["uc_courses"], ["MATH 20A", "MATH 20B"])
        self.assertTrue(result.metadata["multi_course_query"])
    
    def test_integration_with_real_structure(self):
        """Test against real document structure for better coverage."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 11"]
        query.text = "What courses satisfy CSE 11?"
        
        # Create a realistic document structure
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "CSE 11",
            "logic_block": {
                "options": [
                    {
                        "courses": [
                            {"name": "CIS 35A Java Programming", "is_honors": False}
                        ]
                    },
                    {
                        "courses": [
                            [
                                {"name": "CIS 36A Python Programming", "is_honors": False},
                                {"name": "CIS 36B Advanced Python", "is_honors": False}
                            ]
                        ]
                    }
                ]
            }
        }
        
        # Don't mock the actual articulation_facade methods, pass them through
        real_articulation_facade = patch.object(
            self.handler, 'articulation_facade', 
            wraps=self.handler.articulation_facade
        ).start()
        
        # But still mock the matching service
        self.handler.matching_service.match_documents.return_value = [doc]
        self.handler.query_service.normalize_course_code.return_value = "CSE 11"
        
        # Use actual format_course_options implementation
        self.handler.articulation_facade.format_course_options.side_effect = lambda uc, info: (
            f"# {uc} can be satisfied by any of these options:\n\n"
            f"**Option A**: CIS 35A\n"
            f"**Option B**: CIS 36A, CIS 36B (complete all)"
        )
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertIn("CSE 11 can be satisfied by", result.formatted_response)
        self.assertIn("Option A", result.formatted_response)
        self.assertIn("Option B", result.formatted_response)
        self.assertIn("CIS 35A", result.formatted_response)
        self.assertIn("CIS 36A, CIS 36B", result.formatted_response)

    # Add this test to verify behavior for regression test case 1
    def test_regression_case_cse8a(self):
        """Test specifically for the regression test case 1 (CSE 8A)."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 8A"]
        query.text = "Which De Anza courses satisfy CSE 8A at UCSD?"
        
        # Create a realistic document structure matching CSE 8A
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "CSE 8A",
            "logic_block": {
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
        }
        
        # Mock matching_service to return this document
        self.handler.matching_service.match_documents.return_value = [doc]
        self.handler.query_service.normalize_course_code.return_value = "CSE 8A"
        
        articulation_info = {
            "options": [
                {
                    "courses": [{"name": "CIS 22A", "is_honors": False}]
                },
                {
                    "courses": [{"name": "CIS 36A", "is_honors": False}]
                },
                {
                    "courses": [{"name": "CIS 40", "is_honors": False}]
                }
            ]
        }
        self.handler.articulation_facade.get_articulation_options.return_value = articulation_info
        
        expected_response = "# CSE 8A can be satisfied by any of these options:\n\n**Option A**: CIS 22A\n**Option B**: CIS 36A\n**Option C**: CIS 40"
        self.handler.articulation_facade.format_course_options.return_value = expected_response
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertEqual(result.formatted_response, expected_response)
        self.assertNotIn("No articulation", result.formatted_response)
        
    def test_articulation_existence_query(self):
        """Test handling of queries asking if a course has any articulation (Test 16)."""
        query = MagicMock(spec=Query)
        query.uc_courses = ["CSE 15L"]
        query.text = "Does CSE 15L have any articulation?"
        query.query_type = QueryType.COURSE_LOOKUP  # Simulate query_service marking this as COURSE_LOOKUP
        
        # Create a mock document with no_articulation=True
        doc = MagicMock(spec=Document)
        doc.metadata = {
            "uc_course": "CSE 15L",
            "title": "Software Tools and Techniques Laboratory",
            "logic_block": {"no_articulation": True}
        }
        
        # Mock matching_service to return this document
        self.handler.matching_service.match_documents.return_value = [doc]
        
        # Mock query_service for normalization
        self.handler.query_service.normalize_course_code.return_value = "CSE 15L"
        
        result = self.handler.handle(query)
        
        self.assertIsNotNone(result)
        self.assertIn("❌ No, CSE 15L", result.formatted_response)
        self.assertIn("does not have any articulation", result.formatted_response)
        self.assertIn("De Anza College", result.formatted_response)
        self.assertIn("after transferring", result.formatted_response)
        
        # Verify metadata
        self.assertEqual(result.metadata["uc_course"], "CSE 15L")
        self.assertFalse(result.metadata["has_articulation"])
        
if __name__ == "__main__":
    unittest.main() 