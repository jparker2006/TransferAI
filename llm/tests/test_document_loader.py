"""
Test suite for the document_loader module.

This module tests the document loading and course description utility functions
to ensure they provide accurate course information.
"""

import unittest
import sys
import os
from typing import Dict, List, Any

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from document_loader import (
    get_course_title,
    get_course_description,
    get_course_data,
    load_documents
)


class TestCourseDescriptions(unittest.TestCase):
    """Test the course description utility functions."""
    
    def test_get_course_title(self):
        """Test that get_course_title returns the correct title for a course code."""
        self.assertEqual(
            get_course_title("CIS 21JB"),
            "Advanced x86 Processor Assembly Programming"
        )
        
        self.assertEqual(
            get_course_title("CIS 21JA"),
            "Introduction to x86 Processor Assembly Language and Computer Architecture"
        )
        
        self.assertEqual(
            get_course_title("MATH 1A"),
            "Calculus I"
        )
        
        # Test with honors course
        self.assertEqual(
            get_course_title("MATH 1AH"),
            "Calculus I - HONORS"
        )
        
        # Test with non-existent course
        self.assertEqual(
            get_course_title("FAKE 101"),
            ""
        )
    
    def test_get_course_description(self):
        """Test that get_course_description returns the formatted description."""
        self.assertEqual(
            get_course_description("CIS 21JB"),
            "CIS 21JB: Advanced x86 Processor Assembly Programming"
        )
        
        # Test with honors course (should include Honors in the output)
        self.assertEqual(
            get_course_description("MATH 1AH"),
            "MATH 1AH (Honors): Calculus I - HONORS"
        )
    
    def test_get_course_data(self):
        """Test that get_course_data returns complete course data."""
        cis21jb_data = get_course_data("CIS 21JB")
        
        self.assertEqual(cis21jb_data.get("title"), "Advanced x86 Processor Assembly Programming")
        self.assertEqual(cis21jb_data.get("type"), "CCC")
        self.assertFalse(cis21jb_data.get("honors", True))
        
        # Test with honors course
        math1ah_data = get_course_data("MATH 1AH")
        
        self.assertEqual(math1ah_data.get("title"), "Calculus I - HONORS")
        self.assertEqual(math1ah_data.get("type"), "CCC")
        self.assertTrue(math1ah_data.get("honors", False))
    
    def test_course_normalization(self):
        """Test that course codes are normalized properly."""
        # Test with extra spaces
        self.assertEqual(
            get_course_title("CIS  21JB"),
            "Advanced x86 Processor Assembly Programming"
        )
        
        # Test with different case (though course codes are usually uppercase)
        self.assertEqual(
            get_course_title("cis 21jb"),
            "Advanced x86 Processor Assembly Programming"
        )
    
    def test_specific_problem_courses(self):
        """Test specific courses that were problematic in the past."""
        # Test CIS 21JB which was incorrectly described as "Introduction to Database Systems"
        self.assertEqual(
            get_course_title("CIS 21JB"),
            "Advanced x86 Processor Assembly Programming"
        )
        
        # Verify it's not described as database systems
        self.assertNotIn(
            "database",
            get_course_title("CIS 21JB").lower()
        )


class TestDocumentLoading(unittest.TestCase):
    """Test the document loading functionality."""
    
    def test_load_documents(self):
        """Test that documents are loaded with correct metadata."""
        docs = load_documents()
        
        # Verify we have documents
        self.assertTrue(len(docs) > 0)
        
        # Find a document for CSE 30
        cse30_doc = None
        for doc in docs:
            if doc.metadata.get("uc_course") == "CSE 30":
                cse30_doc = doc
                break
        
        # Verify CSE 30 document exists and has correct metadata
        self.assertIsNotNone(cse30_doc)
        self.assertEqual(cse30_doc.metadata.get("uc_title"), "Computer Organization and Systems Programming")
        
        # Verify CIS 21JB is in the list of CCC courses for CSE 30
        self.assertIn("CIS 21JB", cse30_doc.metadata.get("ccc_courses", []))


if __name__ == "__main__":
    unittest.main() 