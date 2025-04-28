"""
Tests for the CourseRepository implementation.

These tests verify the functionality of the CourseRepository class, including:
- Course data loading and caching
- Course title and description retrieval
- Course catalog management
- Cache invalidation
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import time
from typing import Dict, Any

from llm.repositories.course_repository import CourseRepository, cached_result

# Sample course data for testing
SAMPLE_COURSE_DATA = {
    "groups": [
        {
            "group_id": "1",
            "sections": [
                {
                    "section_id": "A",
                    "uc_courses": [
                        {
                            "uc_course_id": "CSE 8A",
                            "uc_course_title": "Introduction to Programming",
                            "units": 4.0,
                            "logic_block": {
                                "type": "OR",
                                "courses": [
                                    {
                                        "type": "AND",
                                        "courses": [
                                            {
                                                "course_letters": "CIS 22A",
                                                "title": "Python Programming",
                                                "honors": False
                                            }
                                        ]
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
    ]
}


class TestCourseRepository(unittest.TestCase):
    """Tests for the CourseRepository class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.repo = CourseRepository()
        
    def test_init(self):
        """Test repository initialization."""
        self.assertEqual(self.repo._course_cache, {})
        self.assertIsNone(self.repo._last_loaded)
        
    def test_load_course_data(self):
        """Test loading course data from file."""
        # Mock the open function to return our sample data
        mock_file = mock_open(read_data=json.dumps(SAMPLE_COURSE_DATA))
        
        with patch('builtins.open', mock_file):
            # Load the data
            count = self.repo.load_course_data("fake_path.json")
            
            # Verify the data was loaded
            self.assertEqual(count, 2)  # CSE 8A and CIS 22A
            self.assertIsNotNone(self.repo._last_loaded)
            
            # Verify course cache contents
            self.assertIn("CSE 8A", self.repo._course_cache)
            self.assertIn("CIS 22A", self.repo._course_cache)
            
            # Verify UC course data
            uc_course = self.repo._course_cache["CSE 8A"]
            self.assertEqual(uc_course["title"], "Introduction to Programming")
            self.assertEqual(uc_course["units"], 4.0)
            self.assertEqual(uc_course["type"], "UC")
            
            # Verify CCC course data
            ccc_course = self.repo._course_cache["CIS 22A"]
            self.assertEqual(ccc_course["title"], "Python Programming")
            self.assertEqual(ccc_course["honors"], False)
            self.assertEqual(ccc_course["type"], "CCC")
            
    def test_get_course_title(self):
        """Test getting course titles."""
        # Setup test data
        self.repo._course_cache = {
            "CSE 8A": {"title": "Introduction to Programming", "type": "UC"},
            "CIS 22A": {"title": "Python Programming", "type": "CCC"}
        }
        
        # Test exact matches
        self.assertEqual(self.repo.get_course_title("CSE 8A"), "Introduction to Programming")
        self.assertEqual(self.repo.get_course_title("CIS 22A"), "Python Programming")
        
        # Test case insensitivity
        self.assertEqual(self.repo.get_course_title("cse 8a"), "Introduction to Programming")
        
        # Test non-existent course
        self.assertEqual(self.repo.get_course_title("CSE 999"), "")
        
    def test_get_course_description(self):
        """Test getting course descriptions."""
        # Setup test data
        self.repo._course_cache = {
            "CSE 8A": {
                "title": "Introduction to Programming",
                "type": "UC",
                "original_code": "CSE 8A"
            },
            "CIS 22A": {
                "title": "Python Programming",
                "type": "CCC",
                "honors": True,
                "original_code": "CIS 22A"
            }
        }
        
        # Test normal course
        self.assertEqual(
            self.repo.get_course_description("CSE 8A"),
            "CSE 8A: Introduction to Programming"
        )
        
        # Test honors course
        self.assertEqual(
            self.repo.get_course_description("CIS 22A"),
            "CIS 22A (Honors): Python Programming"
        )
        
        # Test non-existent course
        self.assertEqual(self.repo.get_course_description("CSE 999"), "CSE 999")
        
    def test_get_course_data(self):
        """Test getting complete course data."""
        # Setup test data
        test_data = {
            "title": "Introduction to Programming",
            "type": "UC",
            "units": 4.0
        }
        self.repo._course_cache = {"CSE 8A": test_data}
        
        # Test existing course
        data = self.repo.get_course_data("CSE 8A")
        self.assertEqual(data, test_data)
        self.assertIsNot(data, test_data)  # Should be a copy
        
        # Test non-existent course
        self.assertEqual(self.repo.get_course_data("CSE 999"), {})
        
    def test_get_all_course_codes(self):
        """Test getting all course codes."""
        # Setup test data
        self.repo._course_cache = {
            "CSE 8A": {},
            "CIS 22A": {},
            "MATH 1A": {}
        }
        
        # Get all codes
        codes = self.repo.get_all_course_codes()
        
        # Verify result
        self.assertEqual(codes, ["CIS 22A", "CSE 8A", "MATH 1A"])  # Should be sorted
        
    def test_get_course_catalogs(self):
        """Test getting course catalogs."""
        # Setup test data
        self.repo._course_cache = {
            "CSE 8A": {"type": "UC"},
            "CSE 8B": {"type": "UC"},
            "CIS 22A": {"type": "CCC"},
            "CIS 22B": {"type": "CCC"}
        }
        
        # Get catalogs
        uc_catalog, ccc_catalog = self.repo.get_course_catalogs()
        
        # Verify results
        self.assertEqual(uc_catalog, {"CSE 8A", "CSE 8B"})
        self.assertEqual(ccc_catalog, {"CIS 22A", "CIS 22B"})
        
    def test_get_reload_status(self):
        """Test getting reload status."""
        # Setup test data
        self.repo._course_cache = {
            "CSE 8A": {"type": "UC"},
            "CSE 8B": {"type": "UC"},
            "CIS 22A": {"type": "CCC"}
        }
        self.repo._last_loaded = time.time()
        
        # Get status
        status = self.repo.get_reload_status()
        
        # Verify status
        self.assertEqual(status["course_count"], 3)
        self.assertEqual(status["uc_course_count"], 2)
        self.assertEqual(status["ccc_course_count"], 1)
        self.assertIsNotNone(status["last_loaded"])
        
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Create test repository and methods with counters
        repo = CourseRepository()
        call_count = 0
        
        @cached_result(ttl_seconds=3600)
        def test_method(self, arg):
            nonlocal call_count
            call_count += 1
            return arg
            
        # Attach method to repository
        repo.test_method = test_method.__get__(repo, CourseRepository)
        
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