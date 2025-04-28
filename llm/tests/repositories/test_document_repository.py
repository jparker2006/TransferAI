"""
Tests for the DocumentRepository implementation.

These tests verify the functionality of the DocumentRepository class, including:
- Document loading and caching
- Search methods (by UC course, CCC course, group, section)
- Reverse matching
- Course catalog building
- Cache invalidation
"""

import unittest
from unittest.mock import patch, MagicMock, call
import os
import time
from typing import Dict, List, Any, Set

# Import the DocumentRepository class
from llm.repositories.document_repository import DocumentRepository, cached_result

# Create a MockDocument class for testing
class MockDocument:
    def __init__(self, metadata: Dict[str, Any], text: str = "Test document"):
        self.metadata = metadata
        self.text = text

class TestCachedResultDecorator(unittest.TestCase):
    """Tests for the cached_result decorator."""

    def test_caching_behavior(self):
        """Test that the cached_result decorator properly caches results."""
        call_count = 0
        
        @cached_result(ttl_seconds=1)
        def test_function(self, arg1, arg2=None):
            nonlocal call_count
            call_count += 1
            return f"{arg1}-{arg2}-{call_count}"
        
        # First call should execute the function
        result1 = test_function(self, "a", arg2="b")
        self.assertEqual(result1, "a-b-1")
        self.assertEqual(call_count, 1)
        
        # Second call with same args should use cached result
        result2 = test_function(self, "a", arg2="b")
        self.assertEqual(result2, "a-b-1")  # Note: count still 1
        self.assertEqual(call_count, 1)  # Function not called again
        
        # Call with different args should execute the function
        result3 = test_function(self, "c", arg2="d")
        self.assertEqual(result3, "c-d-2")
        self.assertEqual(call_count, 2)
        
        # Test cache expiration
        time.sleep(1.1)  # Wait for cache to expire (ttl=1)
        result4 = test_function(self, "a", arg2="b")
        self.assertEqual(result4, "a-b-3")
        self.assertEqual(call_count, 3)  # Function called again after expiration
        
        # Test cache clearing
        test_function.clear_cache()
        result5 = test_function(self, "a", arg2="b")
        self.assertEqual(result5, "a-b-4")
        self.assertEqual(call_count, 4)  # Function called again after clearing

class TestDocumentRepository(unittest.TestCase):
    """Tests for the DocumentRepository class."""
    
    def setUp(self):
        """Set up test data before each test."""
        # Create some mock documents for testing
        self.test_docs = [
            MockDocument({
                "uc_course": "CSE 8A",
                "uc_title": "Introduction to Programming",
                "group": "1",
                "section": "A",
                "ccc_courses": ["CIS 22A", "CIS 36A"],
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "CIS 22A"}]},
                        {"type": "AND", "courses": [{"course_letters": "CIS 36A"}]}
                    ]
                }
            }),
            MockDocument({
                "uc_course": "CSE 8B",
                "uc_title": "Programming in Java",
                "group": "1",
                "section": "A",
                "ccc_courses": ["CIS 22B", "CIS 36B"],
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "CIS 22B"}]},
                        {"type": "AND", "courses": [{"course_letters": "CIS 36B"}]}
                    ]
                }
            }),
            MockDocument({
                "uc_course": "MATH 20A",
                "uc_title": "Calculus I",
                "group": "2",
                "section": "B",
                "ccc_courses": ["MATH 1A"],
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "MATH 1A"}]}
                    ]
                }
            }),
            MockDocument({
                "uc_course": "MATH 20B",
                "uc_title": "Calculus II",
                "group": "2",
                "section": "B",
                "ccc_courses": ["MATH 1B"],
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {"type": "AND", "courses": [{"course_letters": "MATH 1B"}]}
                    ]
                }
            }),
            MockDocument({
                "uc_course": "CSE 11",
                "uc_title": "Accelerated Programming",
                "group": "1",
                "section": "A",
                "ccc_courses": ["CIS 22A", "CIS 22B"],
                "logic_block": {
                    "type": "OR",
                    "courses": [
                        {
                            "type": "AND", 
                            "courses": [
                                {"course_letters": "CIS 22A"},
                                {"course_letters": "CIS 22B"}
                            ]
                        }
                    ]
                }
            }),
            MockDocument({
                "uc_course": "CSE 15L",
                "uc_title": "Software Tools & Techniques",
                "group": "1",
                "section": "A",
                "ccc_courses": [],
                "logic_block": {
                    "no_articulation": True
                }
            })
        ]
        
        # Create a repository with test documents
        self.repo = DocumentRepository(self.test_docs)
        # Ensure course catalogs are built
        self.repo._build_course_catalogs()

    def test_init_with_documents(self):
        """Test initialization with pre-loaded documents."""
        self.assertEqual(len(self.repo.documents), 6)
        self.assertGreater(len(self.repo.uc_course_catalog), 0)
        self.assertGreater(len(self.repo.ccc_course_catalog), 0)
        
    def test_load_documents(self):
        """Test loading documents from file."""
        repo = DocumentRepository()
        count = repo.load_documents()
        
        # Just check that documents were loaded successfully
        self.assertGreater(count, 0, "Should load at least one document")
        self.assertEqual(count, len(repo.documents), "Document count should match loaded documents")
        self.assertIsNotNone(repo._last_loaded, "Last loaded timestamp should be set")
    
    def test_get_reload_status(self):
        """Test getting document loading status."""
        self.repo._last_loaded = time.time()
        status = self.repo.get_reload_status()
        self.assertEqual(status["document_count"], 6)
        self.assertIsNotNone(status["last_loaded"])
        self.assertEqual(status["uc_course_count"], len(self.repo.uc_course_catalog))
        
    def test_find_by_uc_course(self):
        """Test finding documents by UC course."""
        # Test exact match
        docs = self.repo.find_by_uc_course("CSE 8A")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].metadata["uc_course"], "CSE 8A")
        
        # Test case-insensitive match
        docs = self.repo.find_by_uc_course("cse 8a")
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].metadata["uc_course"], "CSE 8A")
        
        # Test non-existent course
        docs = self.repo.find_by_uc_course("CSE 999")
        self.assertEqual(len(docs), 0)
        
    def test_find_by_ccc_courses(self):
        """Test finding documents by CCC courses."""
        # Test single course match with require_all=True
        docs = self.repo.find_by_ccc_courses(["CIS 22A"])
        self.assertEqual(len(docs), 2)  # CSE 8A and CSE 11
        
        # Test multiple course match with require_all=True
        docs = self.repo.find_by_ccc_courses(["CIS 22A", "CIS 22B"])
        self.assertEqual(len(docs), 1)  # Only CSE 11
        
        # Test with require_all=False (any match)
        docs = self.repo.find_by_ccc_courses(["CIS 22A", "MATH 1A"], require_all=False)
        self.assertEqual(len(docs), 3)  # CSE 8A, CSE 11, MATH 20A
        
        # Test case insensitivity
        docs = self.repo.find_by_ccc_courses(["cis 22a"])
        self.assertEqual(len(docs), 2)  # CSE 8A and CSE 11
        
        # Test empty input
        docs = self.repo.find_by_ccc_courses([])
        self.assertEqual(len(docs), 0)
        
    def test_find_by_group(self):
        """Test finding documents by group."""
        # Test existing group
        docs = self.repo.find_by_group("1")
        self.assertEqual(len(docs), 4)  # CSE 8A, CSE 8B, CSE 11, CSE 15L
        
        # Test another group
        docs = self.repo.find_by_group("2")
        self.assertEqual(len(docs), 2)  # MATH 20A, MATH 20B
        
        # Test non-existent group
        docs = self.repo.find_by_group("999")
        self.assertEqual(len(docs), 0)
        
    def test_find_by_section(self):
        """Test finding documents by section."""
        # Test existing section
        docs = self.repo.find_by_section("A")
        self.assertEqual(len(docs), 4)  # CSE 8A, CSE 8B, CSE 11, CSE 15L
        
        # Test another section
        docs = self.repo.find_by_section("B")
        self.assertEqual(len(docs), 2)  # MATH 20A, MATH 20B
        
        # Test non-existent section
        docs = self.repo.find_by_section("Z")
        self.assertEqual(len(docs), 0)
        
    def test_find_reverse_matches(self):
        """Test finding reverse matches for a CCC course."""
        # Test direct match
        docs = self.repo.find_reverse_matches("CIS 22A")
        self.assertEqual(len(docs), 2)  # CSE 8A and CSE 11
        
        # Test case insensitivity
        docs = self.repo.find_reverse_matches("cis 22a")
        self.assertEqual(len(docs), 2)
        
        # Test non-existent course
        docs = self.repo.find_reverse_matches("CIS 999")
        self.assertEqual(len(docs), 0)
        
        # Test empty input
        docs = self.repo.find_reverse_matches("")
        self.assertEqual(len(docs), 0)
        
    def test_get_all_documents(self):
        """Test getting all documents."""
        docs = self.repo.get_all_documents()
        self.assertEqual(len(docs), 6)
        self.assertEqual(docs, self.test_docs)
        
    def test_get_documents_count(self):
        """Test getting document count."""
        count = self.repo.get_documents_count()
        self.assertEqual(count, 6)
        
    def test_get_course_catalogs(self):
        """Test getting course catalogs."""
        uc_catalog, ccc_catalog = self.repo.get_course_catalogs()
        self.assertIsInstance(uc_catalog, set)
        self.assertIsInstance(ccc_catalog, set)
        self.assertEqual(len(uc_catalog), 6)  # CSE 8A, CSE 8B, MATH 20A, MATH 20B, CSE 11, CSE 15L
        self.assertEqual(len(ccc_catalog), 6)  # CIS 22A, CIS 36A, CIS 22B, CIS 36B, MATH 1A, MATH 1B
        
    def test_filter_documents(self):
        """Test filtering documents with a custom predicate."""
        # Filter documents with "CSE" in the course code
        docs = self.repo.filter_documents(
            lambda doc: "CSE" in doc.metadata.get("uc_course", "")
        )
        self.assertEqual(len(docs), 4)  # CSE 8A, CSE 8B, CSE 11, CSE 15L
        
        # Filter documents with multiple CCC courses
        docs = self.repo.filter_documents(
            lambda doc: len(doc.metadata.get("ccc_courses", [])) > 1
        )
        self.assertEqual(len(docs), 3)  # CSE 8A, CSE 8B, CSE 11
        
    def test_find_documents_with_honors_requirements(self):
        """Test finding documents with honors requirements."""
        # Mock the is_honors_required function to return True for CSE 8A
        with patch('llm.articulation.detectors.is_honors_required', 
                  side_effect=lambda block: block.get("uc_course") == "CSE 8A"):
            docs = self.repo.find_documents_with_honors_requirements()
            self.assertEqual(len(docs), 0)  # None in our test data
            
    def test_find_documents_with_no_articulation(self):
        """Test finding documents with no articulation."""
        docs = self.repo.find_documents_with_no_articulation()
        self.assertEqual(len(docs), 1)  # CSE 15L
        self.assertEqual(docs[0].metadata["uc_course"], "CSE 15L")
        
    def test_normalize_course_code(self):
        """Test course code normalization."""
        # Test with various formats
        self.assertEqual(self.repo._normalize_course_code("CSE 8A"), "CSE 8A")
        self.assertEqual(self.repo._normalize_course_code("cse8a"), "CSE 8A")
        self.assertEqual(self.repo._normalize_course_code("CSE  8A "), "CSE 8A")
        self.assertEqual(self.repo._normalize_course_code(""), "")
        
        # Test with mock for fallback implementation
        with patch('llm.query_parser.normalize_course_code', side_effect=ImportError()):
            # This should use the fallback implementation
            self.assertEqual(self.repo._normalize_course_code("CSE  8A "), "CSE 8A")
            
    def test_logic_contains_course(self):
        """Test checking if a logic block contains a course."""
        # Create a test logic block
        logic_block = {
            "type": "OR",
            "courses": [
                {
                    "type": "AND",
                    "courses": [
                        {"course_letters": "CIS 22A"},
                        {"course_letters": "CIS 22B"}
                    ]
                },
                {"type": "AND", "courses": [{"course_letters": "CIS 36A"}]}
            ]
        }
        
        # Test with courses that are present
        self.assertTrue(self.repo._logic_contains_course(logic_block, "CIS 22A"))
        self.assertTrue(self.repo._logic_contains_course(logic_block, "CIS 22B"))
        self.assertTrue(self.repo._logic_contains_course(logic_block, "CIS 36A"))
        
        # Test with course that is not present
        self.assertFalse(self.repo._logic_contains_course(logic_block, "CIS 999"))
        
        # Test with empty logic block
        self.assertFalse(self.repo._logic_contains_course({}, "CIS 22A"))
        self.assertFalse(self.repo._logic_contains_course(None, "CIS 22A"))
        
    def test_cached_search_methods(self):
        """Test that search methods use the cache."""
        # Create a test repository with a spy on _normalize_course_code
        repo = DocumentRepository(self.test_docs)
        original_normalize = repo._normalize_course_code
        call_count = 0
        
        def counting_normalize(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return original_normalize(*args, **kwargs)
            
        repo._normalize_course_code = counting_normalize
        
        # First call should call normalize_course_code
        repo.find_by_uc_course("CSE 8A")
        self.assertGreater(call_count, 0)
        
        # Reset counter
        call_count = 0
        
        # Second call should use cached result
        repo.find_by_uc_course("CSE 8A")
        self.assertEqual(call_count, 0)  # No calls to normalize_course_code
        
        # Clear cache
        repo.clear_cache()
        
        # After clearing cache, should call normalize_course_code again
        repo.find_by_uc_course("CSE 8A")
        self.assertGreater(call_count, 0)
            
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Create test repository and methods with counters
        repo = DocumentRepository(self.test_docs)
        call_count = 0
        
        @cached_result(ttl_seconds=3600)
        def test_method(self, arg):
            nonlocal call_count
            call_count += 1
            return arg
            
        # Attach method to repository
        repo.test_method = test_method.__get__(repo, DocumentRepository)
        
        # First call
        repo.test_method("test")
        self.assertEqual(call_count, 1)
        
        # Second call (should use cache)
        repo.test_method("test")
        self.assertEqual(call_count, 1)  # Still 1
        
        # Clear cache
        repo.clear_cache()
        
        # Third call (should not use cache)
        repo.test_method("test")
        self.assertEqual(call_count, 2)


if __name__ == '__main__':
    unittest.main() 