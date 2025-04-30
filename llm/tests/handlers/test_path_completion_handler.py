"""
Tests for the PathCompletionHandler class.

These tests verify that the PathCompletionHandler correctly identifies
and responds to queries about whether course combinations complete requirement paths.
"""

import unittest
from unittest.mock import MagicMock, patch

from llm.handlers.path_completion_handler import PathCompletionHandler
from llm.models.query import Query, QueryType
from llm.repositories.document_repository import DocumentRepository


class TestPathCompletionHandler(unittest.TestCase):
    """Test suite for the PathCompletionHandler class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.document_repository = MagicMock(spec=DocumentRepository)
        self.config = {'verbosity': 'STANDARD'}
        self.handler = PathCompletionHandler(self.document_repository, self.config)
        
        # Mock the group data to avoid document repository dependencies
        self.handler._group_data = {
            '1': {
                'id': '1',
                'type': 'complete_one_section',
                'description': 'Complete A or B',
                'sections': {
                    'A': {
                        'courses': ['CSE 8A', 'CSE 8B'],
                        'description': 'Introduction to Programming sequence'
                    },
                    'B': {
                        'courses': ['CSE 11'],
                        'description': 'Accelerated Introduction to Programming'
                    }
                }
            },
            '2': {
                'id': '2',
                'type': 'complete_all',
                'description': 'All of the following UC courses are required',
                'sections': {
                    'A': {
                        'courses': [
                            'CSE 12', 'CSE 15L', 'CSE 20', 'CSE 21', 'CSE 30',
                            'MATH 18', 'MATH 20A', 'MATH 20B', 'MATH 20C'
                        ],
                        'description': 'Core CS and Math courses'
                    }
                }
            }
        }
    
    def test_can_handle_path_completion_keywords(self):
        """Test that the handler detects queries with path completion keywords."""
        # Test with a query containing a path completion keyword
        query = Query(
            text="Is CSE 8A and 8B a full path?",
            filters={'uc_course': ['CSE 8A', 'CSE 8B']},
            config=self.config
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Test with another path keyword
        query = Query(
            text="Does CSE 11 complete a requirement section?",
            filters={'uc_course': ['CSE 11']},
            config=self.config
        )
        self.assertTrue(self.handler.can_handle(query))
        
        # Test with a question pattern
        query = Query(
            text="Are MATH 20A and MATH 20B enough to satisfy the math requirement?",
            filters={'uc_course': ['MATH 20A', 'MATH 20B']},
            config=self.config
        )
        self.assertTrue(self.handler.can_handle(query))
    
    def test_cannot_handle_non_path_queries(self):
        """Test that the handler rejects queries not related to path completion."""
        # Test with a query that doesn't contain path keywords
        query = Query(
            text="What courses satisfy CSE 8A?",
            filters={'uc_course': ['CSE 8A']},
            config=self.config
        )
        self.assertFalse(self.handler.can_handle(query))
        
        # Test with a query without UC courses
        query = Query(
            text="Is this a complete path?",
            filters={'uc_course': []},
            config=self.config
        )
        self.assertFalse(self.handler.can_handle(query))
    
    def test_exact_path_match_section_a(self):
        """Test handling of a query about courses that exactly match section A."""
        query = Query(
            text="If I complete CSE 8A and 8B, is that one full path?",
            filters={'uc_course': ['CSE 8A', 'CSE 8B']},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIn("Yes", result.formatted_response)
        self.assertIn("Group 1 Section A", result.formatted_response)
        self.assertTrue(result.metadata.get('completes_path', False))
        self.assertEqual(result.metadata.get('path_description'), "Group 1 Section A")
    
    def test_exact_path_match_section_b(self):
        """Test handling of a query about courses that exactly match section B."""
        query = Query(
            text="Does CSE 11 alone complete one path?",
            filters={'uc_course': ['CSE 11']},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIn("Yes", result.formatted_response)
        self.assertIn("Group 1 Section B", result.formatted_response)
        self.assertTrue(result.metadata.get('completes_path', False))
        self.assertEqual(result.metadata.get('path_description'), "Group 1 Section B")
    
    def test_partial_path_match(self):
        """Test handling of a query about courses that partially match a section."""
        query = Query(
            text="Is CSE 8A alone a full path?",
            filters={'uc_course': ['CSE 8A']},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIn("Not quite", result.formatted_response)
        self.assertIn("partially", result.formatted_response)
        self.assertIn("CSE 8B", result.formatted_response)  # Should mention the missing course
        self.assertFalse(result.metadata.get('completes_path', True))
        self.assertEqual(result.metadata.get('missing_courses'), ['CSE 8B'])
    
    def test_over_complete_path_match(self):
        """Test handling of a query about courses that over-complete a section."""
        query = Query(
            text="Are CSE 8A, CSE 8B, and MATH 20A a full path?",
            filters={'uc_course': ['CSE 8A', 'CSE 8B', 'MATH 20A']},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIn("Yes", result.formatted_response)
        self.assertIn("additional courses", result.formatted_response)
        self.assertIn("MATH 20A", result.formatted_response)  # Should mention the extra course
        self.assertTrue(result.metadata.get('completes_path', False))
        self.assertEqual(result.metadata.get('extra_courses'), ['MATH 20A'])
    
    def test_partial_path_match_group2(self):
        """Test handling of a query about courses that partially match Group 2 Section A."""
        query = Query(
            text="Do MATH 20A and CSE 12 complete a path?",
            filters={'uc_course': ['MATH 20A', 'CSE 12']},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIn("Not quite", result.formatted_response)
        self.assertIn("partially completes", result.formatted_response)
        self.assertIn("Group 2 Section A", result.formatted_response) 
        self.assertFalse(result.metadata.get('completes_path', True))
        self.assertTrue(len(result.metadata.get('missing_courses', [])) > 0)
    
    def test_no_path_match(self):
        """Test handling of a query about courses that don't match any path."""
        query = Query(
            text="Do CSE 12 and BILD 1 complete a path?",
            filters={'uc_course': ['CSE 12', 'BILD 1']},
            config=self.config
        )
        
        # Add BILD 1 to the group data so the test can detect no path match
        # (courses from different groups don't form a path)
        self.handler._group_data['3'] = {
            'id': '3',
            'type': 'select_n',
            'n': 2,
            'description': 'Select 2 courses from the following',
            'sections': {
                'A': {
                    'courses': ['BILD 1', 'BILD 2', 'BILD 3'],
                    'description': 'Science courses'
                }
            }
        }
        
        result = self.handler.handle(query)
        
        # Verify the result
        self.assertIn("No", result.formatted_response)
        self.assertIn("does not complete", result.formatted_response)
        self.assertFalse(result.metadata.get('completes_path', True))
    
    def test_no_courses_specified(self):
        """Test handling of a query with no UC courses specified."""
        query = Query(
            text="Is this a complete path?",
            filters={'uc_course': []},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result is an error message
        self.assertIn("Please specify which UC courses", result.formatted_response)
    
    @patch('llm.handlers.path_completion_handler.PathCompletionHandler._get_group_data')
    def test_no_group_data_available(self, mock_get_group_data):
        """Test handling when group data is not available."""
        # Make _get_group_data return None
        mock_get_group_data.return_value = None
        
        query = Query(
            text="Is CSE 8A and 8B a full path?",
            filters={'uc_course': ['CSE 8A', 'CSE 8B']},
            config=self.config
        )
        
        result = self.handler.handle(query)
        
        # Verify the result is an error message
        self.assertIn("unable to analyze path completion", result.formatted_response.lower())


if __name__ == '__main__':
    unittest.main() 