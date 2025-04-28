"""
Tests for the MatchingService class.

These tests verify the various matching strategies implemented in the MatchingService,
ensuring it correctly finds, filters, and ranks documents based on different criteria.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Set

from llm.services.matching_service import MatchingService
from llm.services.query_service import QueryService


class TestMatchingService(unittest.TestCase):
    """Test suite for the MatchingService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.matching_service = MatchingService()
        
        # Create mock Document class
        class MockDocument:
            def __init__(self, **kwargs):
                self.metadata = kwargs
                self.node = self  # For compatibility with semantic search results
                
        # Sample documents for testing
        self.sample_docs = [
            MockDocument(
                uc_course="CSE 8A",
                ccc_courses=["CIS 22A"],
                group="1",
                section="A",
                logic_block={
                    "options": [
                        {"courses": ["CIS 22A"]}
                    ]
                }
            ),
            MockDocument(
                uc_course="MATH 20A",
                ccc_courses=["MATH 1A"],
                group="2",
                section="B",
                logic_block={
                    "options": [
                        {"courses": ["MATH 1A"]}
                    ]
                }
            ),
            MockDocument(
                uc_course="BILD 1",
                ccc_courses=["BIO 11"],
                group="3",
                section="C",
                logic_block={
                    "options": [
                        {"courses": [["BIO 11", "CHEM 1A"]]}  # AND group
                    ]
                }
            ),
            MockDocument(
                uc_course="CHEM 6A",
                ccc_courses=["CHEM 1A", "CHEM 1B"],
                group="3",
                section="C",
                logic_block={
                    "options": [
                        {"courses": ["CHEM 1A", "CHEM 1B"]}
                    ]
                }
            ),
            MockDocument(
                uc_course="PHYS 2A",
                ccc_courses=["PHYS 4A"],
                group="4",
                section="D",
                logic_block={
                    "options": [
                        {"courses": ["PHYS 4A"]}
                    ]
                }
            )
        ]
        
        # Mock QueryService for testing
        self.matching_service.query_service = MagicMock(spec=QueryService)
        self.matching_service.query_service.normalize_course_code.side_effect = lambda code: code.upper()
        
    def test_match_by_courses(self):
        """Test matching by UC and CCC courses."""
        # Test match by UC course
        matches = self.matching_service.match_by_courses(
            self.sample_docs, 
            uc_courses=["CSE 8A"]
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "CSE 8A")
        
        # Test match by CCC course
        matches = self.matching_service.match_by_courses(
            self.sample_docs, 
            ccc_courses=["MATH 1A"]
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "MATH 20A")
        
        # Test match by both UC and CCC courses
        matches = self.matching_service.match_by_courses(
            self.sample_docs, 
            uc_courses=["CHEM 6A"],
            ccc_courses=["CHEM 1A"]
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "CHEM 6A")
        
        # Test no matches
        matches = self.matching_service.match_by_courses(
            self.sample_docs, 
            uc_courses=["NONEXISTENT"]
        )
        self.assertEqual(len(matches), 0)
        
    def test_match_by_group(self):
        """Test matching by group ID."""
        # Test valid group
        matches = self.matching_service.match_by_group(self.sample_docs, "3")
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].metadata["uc_course"], "BILD 1")
        self.assertEqual(matches[1].metadata["uc_course"], "CHEM 6A")
        
        # Test non-existent group
        matches = self.matching_service.match_by_group(self.sample_docs, "99")
        self.assertEqual(len(matches), 0)
        
    def test_match_by_section(self):
        """Test matching by section within a group."""
        # Test valid section
        matches = self.matching_service.match_by_section(self.sample_docs, "3", "C")
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].metadata["uc_course"], "BILD 1")
        self.assertEqual(matches[1].metadata["uc_course"], "CHEM 6A")
        
        # Test non-existent section
        matches = self.matching_service.match_by_section(self.sample_docs, "3", "Z")
        self.assertEqual(len(matches), 0)
        
    def test_match_reverse(self):
        """Test reverse matching (CCC to UC)."""
        # Set up mock responses for query service methods
        self.matching_service.query_service.extract_reverse_matches.return_value = [self.sample_docs[0]]
        self.matching_service.query_service.find_uc_courses_satisfied_by.return_value = [self.sample_docs[1]]
        
        # Test reverse matching
        matches = self.matching_service.match_reverse(
            self.sample_docs,
            ["CIS 22A", "MATH 1A"],
            "What can CIS 22A and MATH 1A satisfy?"
        )
        
        # Should call both reverse match methods
        self.matching_service.query_service.extract_reverse_matches.assert_called_once()
        self.assertEqual(self.matching_service.query_service.find_uc_courses_satisfied_by.call_count, 2)
        
        # We're calling find_uc_courses_satisfied_by twice (once for each CCC course)
        # and it's returning the same document both times, plus extract_reverse_matches
        # returns one document, so we get 3 total (with duplicates)
        self.assertEqual(len(matches), 3)
        
    def test_match_semantic(self):
        """Test semantic matching via vector search."""
        # Mock the index and query engine
        mock_index = MagicMock()
        mock_query_engine = MagicMock()
        mock_response = MagicMock()
        
        # Set up the mock response
        mock_node1 = MagicMock()
        mock_node1.node = self.sample_docs[0]
        mock_node2 = MagicMock()
        mock_node2.node = self.sample_docs[1]
        mock_response.source_nodes = [mock_node1, mock_node2]
        
        # Chain the mocks
        mock_index.as_query_engine.return_value = mock_query_engine
        mock_query_engine.query.return_value = mock_response
        
        # Set the index on the matching service
        self.matching_service.index = mock_index
        
        # Test semantic matching
        matches = self.matching_service.match_semantic("What courses satisfy CSE requirements?")
        
        # Verify the correct calls were made
        mock_index.as_query_engine.assert_called_once_with(similarity_top_k=10)
        mock_query_engine.query.assert_called_once_with("What courses satisfy CSE requirements?")
        
        # Check results
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0], self.sample_docs[0])
        self.assertEqual(matches[1], self.sample_docs[1])
        
    def test_validate_same_section(self):
        """Test filtering documents to the same section."""
        # Get documents from group 3
        group3_docs = self.matching_service.match_by_group(self.sample_docs, "3")
        self.assertEqual(len(group3_docs), 2)
        
        # Add a document from another section
        mixed_docs = group3_docs + [self.sample_docs[0]]  # Add a doc from section A
        self.assertEqual(len(mixed_docs), 3)
        
        # Filter to same section
        same_section_docs = self.matching_service.validate_same_section(mixed_docs)
        self.assertEqual(len(same_section_docs), 2)
        self.assertEqual(same_section_docs[0].metadata["section"], "C")
        self.assertEqual(same_section_docs[1].metadata["section"], "C")
        
    def test_filter_relevant_uc_courses(self):
        """Test filtering documents to those with UC courses mentioned in query."""
        # Mock the normalize_course_code to return uppercase
        self.matching_service.query_service.normalize_course_code.side_effect = lambda x: x.upper()
        
        # Test with query mentioning CSE 8A
        query = "Does CIS 22A satisfy CSE 8A?"
        filtered = self.matching_service.filter_relevant_uc_courses(self.sample_docs, query)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].metadata["uc_course"], "CSE 8A")
        
        # Test with query mentioning multiple courses
        query = "Can I use these courses for MATH 20A or BILD 1?"
        filtered = self.matching_service.filter_relevant_uc_courses(self.sample_docs, query)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0].metadata["uc_course"], "MATH 20A")
        self.assertEqual(filtered[1].metadata["uc_course"], "BILD 1")
        
    def test_filter_and_rank(self):
        """Test filtering and ranking documents."""
        # Create duplicates
        duplicate_docs = self.sample_docs + [self.sample_docs[0]]
        self.assertEqual(len(duplicate_docs), 6)
        
        # Filter and rank
        filtered = self.matching_service._filter_and_rank(duplicate_docs, limit=3)
        
        # Should remove duplicates and limit to 3
        self.assertEqual(len(filtered), 3)
        
        # Check first three docs maintained order
        self.assertEqual(filtered[0].metadata["uc_course"], "CSE 8A")
        self.assertEqual(filtered[1].metadata["uc_course"], "MATH 20A")
        self.assertEqual(filtered[2].metadata["uc_course"], "BILD 1")
        
    def test_match_documents_integration(self):
        """Integration test for the main match_documents method."""
        # Set up mock for reverse matches
        self.matching_service.query_service.extract_reverse_matches.return_value = []
        self.matching_service.query_service.find_uc_courses_satisfied_by.return_value = []
        
        # Test group/section matching (highest priority)
        matches = self.matching_service.match_documents(
            self.sample_docs,
            group_id="3",
            section_id="C"
        )
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].metadata["group"], "3")
        self.assertEqual(matches[0].metadata["section"], "C")
        
        # Test course matching (second priority)
        matches = self.matching_service.match_documents(
            self.sample_docs,
            uc_courses=["CSE 8A"],
            ccc_courses=["CIS 22A"]
        )
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "CSE 8A")
        
        # Test combined strategies with limit
        matches = self.matching_service.match_documents(
            self.sample_docs,
            uc_courses=["CSE 8A", "MATH 20A", "BILD 1"],
            limit=2
        )
        self.assertEqual(len(matches), 2)  # Limited to 2 results
        

if __name__ == "__main__":
    unittest.main() 