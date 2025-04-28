"""
Tests for the DocumentService implementation.

These tests verify the functionality of the DocumentService class, including:
- Document loading and retrieval
- Course catalog and prefix generation
- Various document search methods
- Filter operations
"""

import unittest
from unittest.mock import patch, MagicMock, call, PropertyMock
from typing import Dict, List, Any, Set

# Import the classes to test
from llm.services.document_service import DocumentService
from llm.repositories.document_repository import DocumentRepository

# Create a MockDocument class for testing
class MockDocument:
    def __init__(self, metadata: Dict[str, Any], text: str = "Test document"):
        self.metadata = metadata
        self.text = text


class TestDocumentService(unittest.TestCase):
    """Tests for the DocumentService class."""
    
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
                    "courses": [{"type": "AND", "courses": [{"course_letters": "CIS 22A"}]}]
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
                    "courses": [{"type": "AND", "courses": [{"course_letters": "MATH 1A"}]}]
                }
            })
        ]
        
        # Create a mock DocumentRepository
        self.mock_repo = MagicMock(spec=DocumentRepository)
        self.mock_repo.get_all_documents.return_value = self.test_docs
        
        # Mock get_course_catalogs to return sample catalogs
        self.mock_repo.get_course_catalogs.return_value = (
            {"CSE 8A", "MATH 20A"},  # UC catalog
            {"CIS 22A", "CIS 36A", "MATH 1A"}  # CCC catalog
        )
        
        # Create a DocumentService with the mock repository
        self.service = DocumentService(repository=self.mock_repo)
    
    def test_load_documents(self):
        """Test loading documents."""
        # Setup mock for document loading
        mock_llama_docs = [MagicMock()]
        self.mock_repo.documents = []
        
        # Patch the internal _load_documents method to return our mock
        with patch.object(self.service, '_load_documents', return_value=mock_llama_docs):
            # Call the method
            count = self.service.load_documents()
            
            # Verify that documents were processed and stored
            self.assertEqual(count, len(mock_llama_docs))
            # Verify the repository was updated
            self.assertEqual(len(self.mock_repo.documents), len(mock_llama_docs))
            # Verify other repository methods were called
            self.mock_repo._build_course_catalogs.assert_called_once()
            self.mock_repo.clear_cache.assert_called_once()
    
    def test_get_uc_course_prefixes(self):
        """Test getting UC course prefixes."""
        # Call the method
        prefixes = self.service.get_uc_course_prefixes()
        
        # Verify the result
        self.assertEqual(prefixes, ["CSE", "MATH"])
        self.mock_repo.get_course_catalogs.assert_called_once()
    
    def test_get_ccc_course_prefixes(self):
        """Test getting CCC course prefixes."""
        # Call the method
        prefixes = self.service.get_ccc_course_prefixes()
        
        # Verify the result
        self.assertEqual(sorted(prefixes), ["CIS", "MATH"])
        self.mock_repo.get_course_catalogs.assert_called_once()
    
    def test_get_course_catalogs(self):
        """Test getting course catalogs."""
        # Call the method
        uc_catalog, ccc_catalog = self.service.get_course_catalogs()
        
        # Verify the result
        self.assertEqual(uc_catalog, {"CSE 8A", "MATH 20A"})
        self.assertEqual(ccc_catalog, {"CIS 22A", "CIS 36A", "MATH 1A"})
        self.mock_repo.get_course_catalogs.assert_called_once()
    
    def test_find_documents_by_uc_course(self):
        """Test finding documents by UC course."""
        # Mock the repository method
        self.mock_repo.find_by_uc_course.return_value = [self.test_docs[0]]
        
        # Call the method
        docs = self.service.find_documents_by_uc_course("CSE 8A")
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_uc_course.assert_called_once_with("CSE 8A")
    
    def test_find_documents_by_ccc_courses(self):
        """Test finding documents by CCC courses."""
        # Mock the repository method
        self.mock_repo.find_by_ccc_courses.return_value = [self.test_docs[0]]
        
        # Call the method
        docs = self.service.find_documents_by_ccc_courses(["CIS 22A"], require_all=True)
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_ccc_courses.assert_called_once_with(["CIS 22A"], True)
    
    def test_find_documents_by_group(self):
        """Test finding documents by group."""
        # Mock the repository method
        self.mock_repo.find_by_group.return_value = [self.test_docs[0]]
        
        # Call the method
        docs = self.service.find_documents_by_group("1")
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_group.assert_called_once_with("1")
    
    def test_find_documents_by_section(self):
        """Test finding documents by section."""
        # Mock the repository method
        self.mock_repo.find_by_section.return_value = [self.test_docs[0]]
        
        # Call the method
        docs = self.service.find_documents_by_section("A")
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_section.assert_called_once_with("A")
    
    def test_find_reverse_matches(self):
        """Test finding reverse matches."""
        # Mock the repository method
        self.mock_repo.find_reverse_matches.return_value = [self.test_docs[0]]
        
        # Call the method
        docs = self.service.find_reverse_matches("CIS 22A")
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_reverse_matches.assert_called_once_with("CIS 22A")
    
    def test_find_documents_by_filter_uc_course(self):
        """Test finding documents by UC course filter."""
        # Mock the repository methods
        self.mock_repo.find_by_uc_course.return_value = [self.test_docs[0]]
        
        # Call the method with UC course filter
        docs = self.service.find_documents_by_filter({"uc_course": "CSE 8A"})
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_uc_course.assert_called_once_with("CSE 8A")
    
    def test_find_documents_by_filter_ccc_courses(self):
        """Test finding documents by CCC courses filter."""
        # Mock the repository methods
        self.mock_repo.find_by_ccc_courses.return_value = [self.test_docs[0]]
        
        # Call the method with CCC courses filter
        docs = self.service.find_documents_by_filter({"ccc_courses": ["CIS 22A"]})
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_ccc_courses.assert_called_once_with(["CIS 22A"], True)
    
    def test_find_documents_by_filter_combined(self):
        """Test finding documents by combined filters."""
        # Mock the repository methods
        self.mock_repo.find_by_uc_course.return_value = [self.test_docs[0]]
        self.mock_repo.find_by_ccc_courses.return_value = [self.test_docs[0]]
        
        # Call the method with combined filters
        docs = self.service.find_documents_by_filter({
            "uc_course": "CSE 8A",
            "ccc_courses": ["CIS 22A"]
        })
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.find_by_uc_course.assert_called_once_with("CSE 8A")
        self.mock_repo.find_by_ccc_courses.assert_called_once_with(["CIS 22A"], True)
    
    def test_find_documents_by_filter_with_limit(self):
        """Test finding documents with a limit."""
        # Call the method with a limit
        docs = self.service.find_documents_by_filter({}, limit=1)
        
        # Verify the result
        self.assertEqual(docs, [self.test_docs[0]])
        self.mock_repo.get_all_documents.assert_called_once()
    
    def test_validate_documents_same_section(self):
        """Test validating documents from the same section."""
        # Create test documents from different sections
        test_docs = [
            MockDocument({"section": "A", "uc_course": "CSE 8A"}),
            MockDocument({"section": "A", "uc_course": "CSE 8B"}),
            MockDocument({"section": "B", "uc_course": "MATH 20A"})
        ]
        
        # Call the method
        filtered_docs = self.service.validate_documents_same_section(test_docs)
        
        # Verify that only documents from section A are returned
        self.assertEqual(len(filtered_docs), 2)
        self.assertEqual(filtered_docs[0].metadata["uc_course"], "CSE 8A")
        self.assertEqual(filtered_docs[1].metadata["uc_course"], "CSE 8B")
    
    def test_validate_documents_same_section_empty(self):
        """Test validating an empty document list."""
        # Call the method with an empty list
        filtered_docs = self.service.validate_documents_same_section([])
        
        # Verify that an empty list is returned
        self.assertEqual(filtered_docs, [])
    
    def test_get_reload_status(self):
        """Test getting reload status."""
        # Mock the repository method
        status = {"document_count": 2, "last_loaded": "2023-01-01T12:00:00"}
        self.mock_repo.get_reload_status.return_value = status
        
        # Call the method
        result = self.service.get_reload_status()
        
        # Verify the result
        self.assertEqual(result, status)
        self.mock_repo.get_reload_status.assert_called_once()
    
    def test_clear_cache(self):
        """Test clearing cache."""
        # Call the method
        self.service.clear_cache()
        
        # Verify that the repository method was called
        self.mock_repo.clear_cache.assert_called_once()


if __name__ == '__main__':
    unittest.main() 