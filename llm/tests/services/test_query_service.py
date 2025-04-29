"""
Tests for the QueryService class.

These tests verify the functionality of the QueryService, which is responsible for
extracting information from user queries and categorizing them.
"""

import unittest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Set

from llm.services.query_service import QueryService
from llm.models.query import Query, QueryType


class TestQueryService(unittest.TestCase):
    """Test suite for the QueryService class."""

    def setUp(self):
        """Set up test fixtures."""
        self.query_service = QueryService()
        
        # Create more detailed mock documents for testing
        class MockDoc:
            def __init__(self, **kwargs):
                self.metadata = kwargs
                
        # Sample course catalogs
        self.uc_courses = {
            "CSE 8A", "CSE 8B", "MATH 20A", "MATH 20B", "BILD 1", "CHEM 6A"
        }
        self.ccc_courses = {
            "CIS 22A", "CIS 22B", "MATH 1A", "MATH 1B", "BIO 11", "CHEM 1A" 
        }
        
        # Sample documents
        self.sample_docs = [
            MockDoc(
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
            MockDoc(
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
            MockDoc(
                uc_course="BILD 1",
                ccc_courses=["BIO 11"],
                group="3",
                section="C",
                logic_block={
                    "options": [
                        {"courses": [["BIO 11", "CHEM 1A"]]}  # AND group
                    ]
                }
            )
        ]

    def test_normalize_course_code(self):
        """Test course code normalization."""
        test_cases = [
            ("cis-21ja:", "CIS 21JA"),
            ("MATH2BH", "MATH 2BH"),
            ("CS 101", "CS 101"),
            ("Physics4A", "PHYSICS 4A"),
            ("chem1a", "CHEM 1A"),
            ("CSE8AL", "CSE 8AL")
        ]
        
        for input_code, expected in test_cases:
            result = self.query_service.normalize_course_code(input_code)
            self.assertEqual(result, expected)

    def test_extract_prefixes_from_docs(self):
        """Test extraction of course prefixes from documents."""
        # Test UC prefixes
        uc_prefixes = self.query_service.extract_prefixes_from_docs(self.sample_docs, "uc_course")
        self.assertEqual(set(uc_prefixes), {"CSE", "MATH", "BILD"})
        
        # Test CCC prefixes
        ccc_prefixes = self.query_service.extract_prefixes_from_docs(self.sample_docs, "ccc_courses")
        self.assertEqual(set(ccc_prefixes), {"CIS", "MATH", "BIO"})

    def test_extract_filters(self):
        """Test extraction of filters from a query string."""
        # Test with UC and CCC courses
        query = "Does CIS 22A satisfy CSE 8A?"
        filters = self.query_service.extract_filters(
            query, self.uc_courses, self.ccc_courses
        )
        self.assertEqual(filters["uc_course"], ["CSE 8A"])
        self.assertEqual(filters["ccc_courses"], ["CIS 22A"])
        
        # Test with sequence of courses
        query = "Do MATH 1A and 1B satisfy MATH 20A and 20B?"
        filters = self.query_service.extract_filters(
            query, self.uc_courses, self.ccc_courses
        )
        self.assertEqual(set(filters["uc_course"]), {"MATH 20A", "MATH 20B"})
        self.assertEqual(set(filters["ccc_courses"]), {"MATH 1A", "MATH 1B"})

    def test_extract_reverse_matches(self):
        """Test extraction of reverse matches from a query."""
        query = "What does CIS 22A satisfy?"
        matches = self.query_service.extract_reverse_matches(query, self.sample_docs)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "CSE 8A")

    def test_extract_group_matches(self):
        """Test extraction of group matches from a query."""
        # Test group match
        query = "What courses are in Group 2?"
        matches = self.query_service.extract_group_matches(query, self.sample_docs)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "MATH 20A")
        
        # Test no match
        query = "What courses are in Group 5?"
        matches = self.query_service.extract_group_matches(query, self.sample_docs)
        self.assertEqual(len(matches), 0)

    def test_extract_section_matches(self):
        """Test extraction of section matches from a query."""
        # Test section match - update query format to match implementation
        query = "Tell me about Group 3 Section C"
        matches = self.query_service.extract_section_matches(query, self.sample_docs)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].metadata["uc_course"], "BILD 1")
        
        # Test no match
        query = "Tell me about Group 3 Section D"
        matches = self.query_service.extract_section_matches(query, self.sample_docs)
        self.assertEqual(len(matches), 0)

    def test_split_multi_uc_query(self):
        """Test splitting a multi-course query."""
        query = "What satisfies CSE 8A and MATH 20A?"
        uc_courses = ["CSE 8A", "MATH 20A"]
        
        result = self.query_service.split_multi_uc_query(query, uc_courses)
        self.assertEqual(len(result), 2)
        self.assertEqual(
            result[0], 
            "What satisfies CSE 8A and MATH 20A? (focus on CSE 8A)"
        )
        self.assertEqual(
            result[1], 
            "What satisfies CSE 8A and MATH 20A? (focus on MATH 20A)"
        )

    def test_enrich_uc_courses_with_prefixes(self):
        """Test enriching course codes with prefixes."""
        matches = ["CSE 8A", "8B", "MATH 20A", "20B"]
        uc_prefixes = ["CSE", "MATH"]
        
        result = self.query_service.enrich_uc_courses_with_prefixes(matches, uc_prefixes)
        self.assertEqual(set(result), {"CSE 8A", "CSE 8B", "MATH 20A", "MATH 20B"})

    def test_find_uc_courses_satisfied_by(self):
        """Test finding UC courses satisfied by a CCC course."""
        results = self.query_service.find_uc_courses_satisfied_by("CIS 22A", self.sample_docs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata["uc_course"], "CSE 8A")
        
        # Test AND group
        results = self.query_service.find_uc_courses_satisfied_by("BIO 11", self.sample_docs)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].metadata["uc_course"], "BILD 1")

    def test_logic_block_contains_ccc_course(self):
        """Test checking if a logic block contains a CCC course."""
        logic_block = {
            "options": [
                {"courses": ["CIS 22A"]},
                {"courses": [["BIO 11", "CHEM 1A"]]}  # AND group
            ]
        }
        
        # Test direct match
        self.assertTrue(
            self.query_service._logic_block_contains_ccc_course(logic_block, "CIS 22A")
        )
        
        # Test AND group match
        self.assertTrue(
            self.query_service._logic_block_contains_ccc_course(logic_block, "BIO 11")
        )
        
        # Test no match
        self.assertFalse(
            self.query_service._logic_block_contains_ccc_course(logic_block, "PHYS 4A")
        )

    def test_determine_query_type(self):
        """Test determining the query type."""
        # Test course validation/lookup
        query = Query(
            text="Does CIS 22A satisfy CSE 8A?",
            filters={
                "uc_course": ["CSE 8A"],
                "ccc_courses": ["CIS 22A"]
            },
            config={}
        )
        # System now classifies this as COURSE_LOOKUP instead of COURSE_VALIDATION
        self.assertEqual(
            self.query_service.determine_query_type(query),
            QueryType.COURSE_LOOKUP
        )
        
        # Test course equivalency
        query = Query(
            text="What does CIS 22A satisfy?",
            filters={
                "ccc_courses": ["CIS 22A"]
            },
            config={}
        )
        self.assertEqual(
            self.query_service.determine_query_type(query),
            QueryType.COURSE_EQUIVALENCY
        )
        
        # Test group requirement
        query = Query(
            text="What courses are in Group 2?",
            filters={
                "group": ["2"]
            },
            config={}
        )
        self.assertEqual(
            self.query_service.determine_query_type(query),
            QueryType.GROUP_REQUIREMENT
        )
        
        # Test honors requirement
        query = Query(
            text="Does CSE 8A require honors?",
            filters={
                "uc_course": ["CSE 8A"]
            },
            config={}
        )
        self.assertEqual(
            self.query_service.determine_query_type(query),
            QueryType.HONORS_REQUIREMENT
        )
        
        # Test unknown
        query = Query(
            text="What is course articulation?",
            filters={},
            config={}
        )
        self.assertEqual(
            self.query_service.determine_query_type(query),
            QueryType.UNKNOWN
        )


if __name__ == "__main__":
    unittest.main() 