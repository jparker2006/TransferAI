"""
TransferAI Course Repository

This module provides a repository for managing course information, including course
metadata, titles, and relationships. It maintains a cache of course data and provides
methods for querying and retrieving course information.
"""

from typing import Dict, Any, List, Optional, Set, Tuple
import re
import json
import os
from pathlib import Path
import functools
import time
from datetime import datetime

# Cache decorator for method results
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
            
        # Add a method to clear the cache
        def clear_cache(self=None):
            cache.clear()
            
        wrapper.clear_cache = clear_cache
        wrapper._is_cached_method = True
            
        return wrapper
    return decorator


class CourseRepository:
    """
    Repository for managing course information.
    
    This class provides methods for accessing and querying course data,
    including course titles, descriptions, and relationships between courses.
    It maintains a cache of course information for efficient access.
    
    Attributes:
        _course_cache: Dictionary mapping course codes to course data
        _last_loaded: Timestamp of when course data was last loaded
    """
    
    def __init__(self):
        """Initialize the course repository."""
        self._course_cache: Dict[str, Dict[str, Any]] = {}
        self._last_loaded: Optional[float] = None
        
    def load_course_data(self, path: Optional[str] = None) -> int:
        """
        Load course data from the data source.
        
        Args:
            path: Optional path to the course data file
            
        Returns:
            Number of courses loaded
        """
        if path is None:
            # Try to find the data file relative to current module
            current_dir = os.path.dirname(__file__)
            possible_paths = [
                os.path.join(current_dir, "..", "data", "rag_data.json"),
                os.path.join(current_dir, "..", "..", "data", "rag_data.json"),
                os.path.join(current_dir, "..", "llm", "data", "rag_data.json")
            ]
            
            for p in possible_paths:
                if os.path.exists(p):
                    path = p
                    break
            
            if path is None:
                raise FileNotFoundError("Could not find rag_data.json in any expected location")

        with open(path, "r") as f:
            data = json.load(f)
            
        self._build_course_cache(data)
        self._last_loaded = time.time()
        
        return len(self._course_cache)
        
    def _build_course_cache(self, data: Dict[str, Any]) -> None:
        """
        Build a cache of course data from the articulation data.
        
        Args:
            data: The parsed JSON data containing course information
        """
        self._course_cache = {}
        
        try:
            # Extract all course information from the groups data
            for group in data.get('groups', []):
                for section in group.get('sections', []):
                    for uc_course in section.get('uc_courses', []):
                        # Process UC course
                        uc_code = uc_course.get('uc_course_id', '')
                        if uc_code:
                            # Store with uppercase course code for consistent lookups
                            self._course_cache[uc_code.upper()] = {
                                'title': uc_course.get('uc_course_title', ''),
                                'units': uc_course.get('units', 0.0),
                                'type': 'UC',
                                'original_code': uc_code  # Keep original code for display
                            }
                        
                        # Process associated CCC courses
                        logic_block = uc_course.get('logic_block', {})
                        for option in logic_block.get('courses', []):
                            if option.get('type') == 'AND':
                                for course in option.get('courses', []):
                                    course_code = course.get('course_letters', '')
                                    if course_code and course_code != 'N/A':
                                        # Store with uppercase course code for consistent lookups
                                        self._course_cache[course_code.upper()] = {
                                            'title': course.get('title', ''),
                                            'honors': course.get('honors', False),
                                            'name': course.get('name', ''),
                                            'type': 'CCC',
                                            'original_code': course_code  # Keep original code for display
                                        }
        except Exception as e:
            self.logger.error(f"Error building course cache: {e}")
            self._course_cache = {}
            
    @cached_result(ttl_seconds=3600)
    def get_course_title(self, course_code: str) -> str:
        """
        Get the official title for a course code.
        
        Args:
            course_code: The course code to look up (e.g., "CIS 21JB")
            
        Returns:
            The official course title or an empty string if not found
        """
        # Normalize the course code by removing extra spaces and converting to uppercase
        normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
        
        # Try direct lookup first
        course_data = self._course_cache.get(normalized_code, {})
        if course_data:
            return course_data.get('title', '')
        
        # If not found, try case-insensitive lookup
        for cached_code, cached_data in self._course_cache.items():
            if cached_code.upper() == normalized_code:
                return cached_data.get('title', '')
        
        return ""
        
    @cached_result(ttl_seconds=3600)
    def get_course_description(self, course_code: str) -> str:
        """
        Get a formatted description with course code and title.
        
        Args:
            course_code: The course code to look up (e.g., "CIS 21JB")
            
        Returns:
            A formatted string with the course code and title, or just the code if not found
        """
        # Normalize the course code by removing extra spaces and converting to uppercase
        normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
        fallback_code = course_code.strip()  # Use as fallback if not found
        
        # Try direct lookup first
        course_data = self._course_cache.get(normalized_code, {})
        if not course_data:
            # If not found, try case-insensitive lookup
            for cached_code, cached_data in self._course_cache.items():
                if cached_code.upper() == normalized_code:
                    course_data = cached_data
                    break
        
        title = course_data.get('title', '')
        
        if title:
            is_honors = course_data.get('honors', False)
            honors_suffix = " (Honors)" if is_honors else ""
            # Use original code from cache if available, otherwise use the provided code
            display_code = course_data.get('original_code', fallback_code)
            return f"{display_code}{honors_suffix}: {title}"
        
        return fallback_code
        
    def get_course_data(self, course_code: str) -> Dict[str, Any]:
        """
        Get all available data for a course code.
        
        Args:
            course_code: The course code to look up (e.g., "CIS 21JB")
            
        Returns:
            Dictionary containing all available course data
        """
        # Normalize the course code by removing extra spaces and converting to uppercase
        normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
        
        # Try direct lookup first
        course_data = self._course_cache.get(normalized_code, {})
        if course_data:
            return course_data.copy()
        
        # If not found, try case-insensitive lookup
        for cached_code, cached_data in self._course_cache.items():
            if cached_code.upper() == normalized_code:
                return cached_data.copy()
        
        return {}
        
    def get_all_course_codes(self) -> List[str]:
        """
        Get a list of all available course codes.
        
        Returns:
            List of all course codes in the database
        """
        return sorted(self._course_cache.keys())
        
    def get_course_catalogs(self) -> Tuple[Set[str], Set[str]]:
        """
        Get the UC and CCC course catalogs.
        
        Returns:
            Tuple containing (uc_course_catalog, ccc_course_catalog)
        """
        uc_catalog = set()
        ccc_catalog = set()
        
        for code, data in self._course_cache.items():
            if data.get('type') == 'UC':
                uc_catalog.add(code)
            elif data.get('type') == 'CCC':
                ccc_catalog.add(code)
                
        return uc_catalog, ccc_catalog
        
    def get_reload_status(self) -> Dict[str, Any]:
        """
        Get information about the course data loading status.
        
        Returns:
            Dictionary with course count and last load time
        """
        return {
            "course_count": len(self._course_cache),
            "last_loaded": datetime.fromtimestamp(self._last_loaded).isoformat() if self._last_loaded else None,
            "uc_course_count": len([c for c in self._course_cache.values() if c.get('type') == 'UC']),
            "ccc_course_count": len([c for c in self._course_cache.values() if c.get('type') == 'CCC'])
        }
        
    def clear_cache(self) -> None:
        """Clear all cached results."""
        # Clear method-specific caches
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_is_cached_method') and attr._is_cached_method:
                attr.clear_cache(self)
