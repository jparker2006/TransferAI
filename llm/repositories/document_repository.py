"""
TransferAI Document Repository

This module provides access to the document storage layer for articulation documents.
It follows the Repository pattern to abstract the data access logic and provide
efficient caching for improved performance.
"""

from typing import List, Dict, Any, Optional, Set, Union, Tuple, Callable
import os
from pathlib import Path
import json
import re
import functools
import time
from datetime import datetime, timedelta

# Import our wrapped Document class instead of llama_index
from llm.models.document import Document

# Define cache decorator for method results
def cached_result(ttl_seconds: int = 3600):
    """
    Method decorator that caches results with a time-to-live (TTL).
    
    Args:
        ttl_seconds: Cache expiration time in seconds (default: 1 hour)
    """
    def decorator(func):
        cache = {}
        
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Create a cache key from the function arguments
            key = str(args) + str(sorted(kwargs.items()))
            
            # Check if result is in cache and not expired
            if key in cache:
                result, timestamp = cache[key]
                if timestamp + ttl_seconds > time.time():
                    return result
            
            # Call the original function and cache the result
            result = func(self, *args, **kwargs)
            cache[key] = (result, time.time())
            return result
            
        # Add a method to clear the cache that can be called both as an instance method
        # and as a direct function
        def clear_cache(self=None):
            cache.clear()
            
        wrapper.clear_cache = clear_cache
        wrapper._is_cached_method = True
            
        return wrapper
    return decorator


class DocumentRepository:
    """
    Repository for accessing and querying articulation documents.
    
    Provides a consistent interface for loading and retrieving documents,
    with methods for searching by various criteria and efficient caching
    for improved performance.
    
    Attributes:
        documents: List of articulation documents
        uc_course_catalog: Set of all UC courses in the repository
        ccc_course_catalog: Set of all CCC courses in the repository
        _cache: Dictionary for caching expensive operations
        _last_loaded: Timestamp of when documents were last loaded
    """
    
    def __init__(self, documents: Optional[List[Document]] = None):
        """
        Initialize the document repository.
        
        Args:
            documents: Optional list of pre-loaded documents
        """
        self.documents: List[Document] = documents or []
        self.uc_course_catalog: Set[str] = set()
        self.ccc_course_catalog: Set[str] = set()
        self._cache: Dict[str, Any] = {}
        self._last_loaded: Optional[float] = None
        
        # Initialize query service for course code normalization
        from llm.services.query_service import QueryService
        self._query_service = QueryService()
        
        if documents:
            self._build_course_catalogs()
        
    def load_documents(self, path: Optional[str] = None) -> int:
        """
        Load documents from the data source.
        
        Note: This method is now a thin wrapper around the DocumentService's load_documents
        method and is kept for backward compatibility. New code should use DocumentService
        directly.
        
        Args:
            path: Optional path to the document data file
            
        Returns:
            Number of documents loaded
        """
        from llm.services.document_service import DocumentService
        
        start_time = time.time()
        document_service = DocumentService(self)
        count = document_service.load_documents(path)
        
        # Document_service already updates these values but we track the load time here
        load_time = time.time() - start_time
        print(f"Loaded {count} documents in {load_time:.2f} seconds")
        return count
        
    def clear_cache(self) -> None:
        """Clear all cached results in the repository."""
        self._cache = {}
        
        # Clear method-specific caches
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_cached_method') and attr._is_cached_method:
                # Call the clear_cache method with self as the argument
                attr.clear_cache(self)
                
    def get_reload_status(self) -> Dict[str, Any]:
        """
        Get information about the document loading status.
        
        Returns:
            Dictionary with document count and last load time
        """
        return {
            "document_count": len(self.documents),
            "last_loaded": datetime.fromtimestamp(self._last_loaded).isoformat() if self._last_loaded else None,
            "uc_course_count": len(self.uc_course_catalog),
            "ccc_course_count": len(self.ccc_course_catalog)
        }
    
    @cached_result(ttl_seconds=3600)
    def find_by_uc_course(self, uc_course: str) -> List[Document]:
        """
        Find documents for a specific UC course.
        
        Args:
            uc_course: The UC course code to search for
            
        Returns:
            List of documents matching the UC course
        """
        # Normalize the course code for case-insensitive search
        normalized_course = self._normalize_course_code(uc_course)
        
        return [
            doc for doc in self.documents
            if self._normalize_course_code(doc.metadata.get("uc_course", "")) == normalized_course
        ]
    
    @cached_result(ttl_seconds=3600)
    def find_by_ccc_courses(self, ccc_courses: List[str], require_all: bool = True) -> List[Document]:
        """
        Find documents containing specific CCC courses.
        
        Args:
            ccc_courses: List of CCC course codes to search for
            require_all: If True, all specified courses must be present;
                        if False, matches documents containing any of the courses
            
        Returns:
            List of documents matching the criteria
        """
        if not ccc_courses:
            return []
            
        # Normalize the course codes for comparison
        normalized_courses = [self._normalize_course_code(course) for course in ccc_courses]
        
        result = []
        for doc in self.documents:
            doc_courses = [self._normalize_course_code(c) for c in doc.metadata.get("ccc_courses", [])]
            
            if require_all:
                # All specified courses must be present
                if all(nc in doc_courses for nc in normalized_courses):
                    result.append(doc)
            else:
                # Match if any of the courses are present
                if any(nc in doc_courses for nc in normalized_courses):
                    result.append(doc)
                    
        return result
        
    @cached_result(ttl_seconds=3600)
    def find_by_group(self, group_id: str) -> List[Document]:
        """
        Find documents for a specific group.
        
        Args:
            group_id: The group identifier to search for
            
        Returns:
            List of documents matching the group
        """
        return [
            doc for doc in self.documents
            if doc.metadata.get("group") == group_id
        ]
        
    @cached_result(ttl_seconds=3600)
    def find_by_section(self, section_id: str) -> List[Document]:
        """
        Find documents for a specific section.
        
        Args:
            section_id: The section identifier to search for
            
        Returns:
            List of documents matching the section
        """
        return [
            doc for doc in self.documents
            if doc.metadata.get("section") == section_id
        ]
        
    @cached_result(ttl_seconds=3600)
    def find_reverse_matches(self, ccc_course: str) -> List[Document]:
        """
        Find UC courses that can be satisfied by a specific CCC course.
        
        This implements the reverse match logic previously in analyzers.py
        to find all UC courses that a CCC course contributes to satisfying.
        
        Args:
            ccc_course: The CCC course code to search for
            
        Returns:
            List of UC course documents that can be satisfied by the CCC course
        """
        if not ccc_course:
            return []
            
        normalized_course = self._normalize_course_code(ccc_course)
        matches = []
        
        for doc in self.documents:
            if self._logic_contains_course(doc.metadata.get("logic_block", {}), normalized_course):
                matches.append(doc)
                
        return matches
        
    def get_all_documents(self) -> List[Document]:
        """
        Get all documents in the repository.
        
        Returns:
            List of all documents
        """
        return self.documents
    
    def get_documents_count(self) -> int:
        """
        Get the total number of documents in the repository.
        
        Returns:
            Number of documents
        """
        return len(self.documents)
    
    def get_course_catalogs(self) -> Tuple[Set[str], Set[str]]:
        """
        Get the UC and CCC course catalogs.
        
        Returns:
            Tuple containing (uc_course_catalog, ccc_course_catalog)
        """
        return (self.uc_course_catalog, self.ccc_course_catalog)
        
    def filter_documents(self, predicate: Callable[[Document], bool]) -> List[Document]:
        """
        Filter documents using a custom predicate function.
        
        Args:
            predicate: Function that takes a Document and returns a boolean
            
        Returns:
            List of documents for which the predicate returned True
        """
        return [doc for doc in self.documents if predicate(doc)]
        
    def find_documents_with_honors_requirements(self) -> List[Document]:
        """
        Find documents that have honors course requirements.
        
        Returns:
            List of documents with honors requirements
        """
        from llm.articulation.detectors import is_honors_required
        
        return [
            doc for doc in self.documents
            if is_honors_required(doc.metadata.get("logic_block", {}))
        ]
        
    def find_documents_with_no_articulation(self) -> List[Document]:
        """
        Find documents marked as having no articulation.
        
        Returns:
            List of documents with no_articulation=True
        """
        return [
            doc for doc in self.documents
            if doc.metadata.get("no_articulation", False) or 
               (isinstance(doc.metadata.get("logic_block", {}), dict) and 
                doc.metadata.get("logic_block", {}).get("no_articulation", False))
        ]
    
    def _build_course_catalogs(self) -> None:
        """
        Build the UC and CCC course catalogs from the loaded documents.
        
        This creates sets of all unique UC and CCC course codes for later reference.
        """
        self.uc_course_catalog = set()
        self.ccc_course_catalog = set()
        
        for doc in self.documents:
            uc = doc.metadata.get("uc_course")
            if uc:
                self.uc_course_catalog.add(self._normalize_course_code(uc))
                
            for ccc in doc.metadata.get("ccc_courses", []):
                if ccc:
                    self.ccc_course_catalog.add(self._normalize_course_code(ccc))
    
    def _normalize_course_code(self, course_code: str) -> str:
        """
        Normalize a course code for consistent comparison.
        
        Args:
            course_code: The course code to normalize
            
        Returns:
            Normalized course code (uppercase with standardized spacing)
        """
        return self._query_service.normalize_course_code(course_code)
    
    def _logic_contains_course(self, logic_block: Dict[str, Any], normalized_course: str) -> bool:
        """
        Recursively check if a logic block contains a specific course.
        
        Args:
            logic_block: The logic block to check
            normalized_course: The normalized course code to look for
            
        Returns:
            True if the course is found in the logic block, False otherwise
        """
        # Handle empty or invalid blocks
        if not logic_block or not isinstance(logic_block, dict):
            return False
            
        logic_type = logic_block.get("type")
        courses = logic_block.get("courses", [])

        if isinstance(courses, list):
            for entry in courses:
                if isinstance(entry, dict):
                    # Recursive check for nested logic blocks
                    if entry.get("type") in {"AND", "OR"}:
                        if self._logic_contains_course(entry, normalized_course):
                            return True
                    # Check for direct course match
                    elif self._normalize_course_code(entry.get("course_letters", "")) == normalized_course:
                        return True
        return False
