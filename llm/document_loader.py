"""
Document Loader Module for TransferAI

This module handles the loading and transformation of articulation data from JSON format
into LlamaIndex Document objects suitable for RAG. It's responsible for:

1. Loading JSON data from the articulation source file
2. Transforming nested articulation data into flat, searchable documents
3. Extracting and organizing metadata for retrieval and presentation
4. Creating LlamaIndex Document objects with appropriate text and metadata
5. Providing accurate course information through utility functions

The module provides functions to extract course information, flatten complex logic structures,
and prepare documents for vector indexing, as well as retrieve accurate course titles
and descriptions to ensure consistent course information throughout the application.
"""

import json
import os
import re
from typing import Dict, List, Set, Union, Optional, Any
from llama_index.core import Document

# Cache for course data to avoid repeated file reads
_course_cache: Dict[str, Dict[str, Any]] = {}
_json_data: Optional[Dict[str, Any]] = None


def _load_json_data(path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load and cache the articulation JSON data.
    
    Args:
        path: Optional path to the JSON data file. If None, defaults to "data/rag_data.json"
              relative to the current module.
              
    Returns:
        The parsed JSON data containing articulation information.
    """
    global _json_data
    
    if _json_data is not None:
        return _json_data
        
    if path is None:
        current_dir = os.path.dirname(__file__)
        path = os.path.join(current_dir, "data/rag_data.json")

    with open(path, "r") as f:
        _json_data = json.load(f)
        
    return _json_data


def _build_course_cache() -> None:
    """
    Build a cache of course data from the articulation data.
    
    This function extracts all course information from the articulation database and
    organizes it for quick lookup by course code.
    """
    global _course_cache
    
    if _course_cache:
        return  # Cache already built
        
    data = _load_json_data()
    
    try:
        # Extract all course information from the groups data
        for group in data.get('groups', []):
            for section in group.get('sections', []):
                for uc_course in section.get('uc_courses', []):
                    # Process UC course
                    uc_code = uc_course.get('uc_course_id', '')
                    if uc_code:
                        # Store with uppercase course code for consistent lookups
                        _course_cache[uc_code.upper()] = {
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
                                    _course_cache[course_code.upper()] = {
                                        'title': course.get('title', ''),
                                        'honors': course.get('honors', False),
                                        'name': course.get('name', ''),
                                        'type': 'CCC',
                                        'original_code': course_code  # Keep original code for display
                                    }
    except Exception as e:
        print(f"Error building course cache: {e}")
        # Initialize with empty data rather than failing
        _course_cache = {}


def get_course_title(course_code: str) -> str:
    """
    Get the official title for a course code.
    
    Args:
        course_code: The course code to look up (e.g., "CIS 21JB")
        
    Returns:
        The official course title or an empty string if not found
        
    Example:
        >>> get_course_title("CIS 21JB")
        "Advanced x86 Processor Assembly Programming"
    """
    if not _course_cache:
        _build_course_cache()
    
    # Normalize the course code by removing extra spaces and converting to uppercase
    normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
    
    # Try direct lookup first
    course_data = _course_cache.get(normalized_code, {})
    if course_data:
        return course_data.get('title', '')
    
    # If not found, try case-insensitive lookup
    for cached_code, cached_data in _course_cache.items():
        if cached_code.upper() == normalized_code:
            return cached_data.get('title', '')
    
    return ""


def get_course_description(course_code: str) -> str:
    """
    Get a formatted description with course code and title.
    
    Args:
        course_code: The course code to look up (e.g., "CIS 21JB")
        
    Returns:
        A formatted string with the course code and title, or just the code if not found
        
    Example:
        >>> get_course_description("CIS 21JB")
        "CIS 21JB: Advanced x86 Processor Assembly Programming"
    """
    if not _course_cache:
        _build_course_cache()
    
    # Normalize the course code by removing extra spaces and converting to uppercase
    normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
    fallback_code = course_code.strip()  # Use as fallback if not found
    
    # Try direct lookup first
    course_data = _course_cache.get(normalized_code, {})
    if not course_data:
        # If not found, try case-insensitive lookup (shouldn't be needed with uppercase keys)
        for cached_code, cached_data in _course_cache.items():
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


def get_course_data(course_code: str) -> Dict[str, Any]:
    """
    Get all available data for a course code.
    
    Args:
        course_code: The course code to look up (e.g., "CIS 21JB")
        
    Returns:
        A dictionary with all available course data
        
    Example:
        >>> get_course_data("CIS 21JB")
        {'title': 'Advanced x86 Processor Assembly Programming', 'honors': False, ...}
    """
    if not _course_cache:
        _build_course_cache()
    
    # Normalize the course code by removing extra spaces and converting to uppercase
    normalized_code = re.sub(r'\s+', ' ', course_code.strip()).upper()
    
    # Try direct lookup first
    course_data = _course_cache.get(normalized_code, {})
    if course_data:
        return course_data.copy()
    
    # If not found, try case-insensitive lookup
    for cached_code, cached_data in _course_cache.items():
        if cached_code.upper() == normalized_code:
            return cached_data.copy()
    
    return {}


def get_all_course_codes() -> List[str]:
    """
    Get a list of all available course codes.
    
    Returns:
        A list of all course codes in the database
        
    Example:
        >>> get_all_course_codes()
        ['CIS 21JA', 'CIS 21JB', 'CIS 22A', ...]
    """
    if not _course_cache:
        _build_course_cache()
    
    return list(_course_cache.keys())


def verify_course_description(course_code: str, expected_description: str) -> bool:
    """
    Verify if a course description matches the expected value.
    
    This function is useful for validating that course descriptions in 
    responses match the official data.
    
    Args:
        course_code: The course code to check
        expected_description: The description to verify
        
    Returns:
        True if the description matches, False otherwise
        
    Example:
        >>> verify_course_description("CIS 21JB", "Introduction to Database Systems")
        False
    """
    actual_title = get_course_title(course_code)
    return actual_title.lower() in expected_description.lower()


def extract_ccc_courses_from_logic(logic_block: Dict[str, Any]) -> List[str]:
    """
    Extract all CCC course codes from a logic block recursively.
    
    This function traverses the nested structure of a logic block to find all course codes
    mentioned in any part of the articulation logic, handling both AND and OR blocks.
    
    Args:
        logic_block: A dictionary containing the articulation logic structure with 
                    nested AND/OR blocks and course information.
    
    Returns:
        A sorted list of unique CCC course codes found in the logic block.
        
    Example:
        >>> logic = {"type": "OR", "courses": [{"type": "AND", "courses": [{"course_letters": "CIS 22A"}]}]}
        >>> extract_ccc_courses_from_logic(logic)
        ['CIS 22A']
    """
    course_codes = set()

    def recurse(node):
        if isinstance(node, list):
            for item in node:
                recurse(item)
        elif isinstance(node, dict):
            if "type" in node and "courses" in node:
                # This is an AND/OR logic wrapper
                recurse(node["courses"])
            else:
                # This is a course dict
                code = node.get("course_letters", "").strip()
                if code and code.upper() != "N/A":
                    course_codes.add(code)

    recurse(logic_block.get("courses", []))
    return sorted(course_codes)


def flatten_courses_from_json(json_data: Dict[str, Any]) -> List[Dict[str, Union[str, Dict]]]:
    """
    Convert nested articulation JSON into flat document objects for LLM ingestion.
    
    This function transforms the hierarchical ASSIST.org data structure into flat documents,
    each representing a single UC course with its articulation options. It extracts metadata
    and creates a text representation suitable for vector indexing.
    
    Args:
        json_data: The parsed JSON data containing articulation information, including
                  groups, sections, and UC courses with their logic blocks.
    
    Returns:
        A list of dictionaries, each containing 'text' and 'metadata' keys, ready to be
        converted to LlamaIndex Document objects.
        
    Note:
        The resulting documents preserve the hierarchical relationship through metadata
        while flattening the structure for easier retrieval.
    """
    flattened_docs = []

    def summarize_options(logic_block: Dict[str, Any]) -> str:
        """Create a human-readable summary of the options in a logic block."""
        summaries = []
        options = logic_block.get("courses", [])
        for i, option in enumerate(options):
            label = f"Option {chr(65 + i)}"
            if isinstance(option, dict) and option.get("type") == "AND":
                course_codes = [c.get("course_letters", "UNKNOWN") for c in option.get("courses", [])]
                summaries.append(f"{label}: " + " + ".join(course_codes))
            else:
                summaries.append(f"{label}: UNKNOWN FORMAT")
        return "; ".join(summaries)

    def get_course_count(logic_block: Dict[str, Any]) -> int:
        """Get the maximum number of courses required in any single option."""
        options = logic_block.get("courses", [])
        return max(
            len(opt.get("courses", [])) if isinstance(opt, dict) and opt.get("type") == "AND" else 1
            for opt in options
        ) if options else 0

    def has_multi_course_option(logic_block: Dict[str, Any]) -> bool:
        """Check if any option requires multiple courses (AND logic)."""
        for opt in logic_block.get("courses", []):
            if isinstance(opt, dict) and opt.get("type") == "AND" and len(opt.get("courses", [])) > 1:
                return True
        return False

    for group in json_data.get("groups", []):
        group_id = group.get("group_id")
        group_title = group.get("group_title")
        group_logic_type = group.get("group_logic_type")
        n_courses = group.get("n_courses")

        for section in group.get("sections", []):
            section_id = section.get("section_id")
            section_title = section.get("section_title")

            for course in section.get("uc_courses", []):
                logic_block = course.get("logic_block", {})
                no_articulation = logic_block.get("no_articulation", False)
                uc_id = course.get("uc_course_id", "").replace(":", "").strip()
                ccc_courses = extract_ccc_courses_from_logic(logic_block)

                enriched_metadata = {
                    "doc_type": "articulation",
                    "uc_course": uc_id,
                    "uc_title": course.get("uc_course_title"),
                    "units": course.get("units"),
                    "group": group_id,
                    "group_title": group_title,
                    "group_logic_type": group_logic_type,
                    "n_courses": n_courses,
                    "section": section_id,
                    "section_title": section_title,
                    "logic_block": logic_block,
                    "no_articulation": no_articulation,
                    "ccc_courses": ccc_courses,
                    "must_complete_at_uc": no_articulation,
                }

                # Enrich logic metadata if articulation exists
                if not no_articulation and isinstance(logic_block, dict):
                    enriched_metadata["logic_type"] = logic_block.get("type", "OR")
                    enriched_metadata["course_count"] = get_course_count(logic_block)
                    enriched_metadata["multi_course_option"] = has_multi_course_option(logic_block)
                    enriched_metadata["options_summary"] = summarize_options(logic_block)
                else:
                    enriched_metadata["logic_type"] = "OR"
                    enriched_metadata["course_count"] = 0
                    enriched_metadata["multi_course_option"] = False
                    enriched_metadata["options_summary"] = "No articulated course."

                flattened_docs.append({
                    "text": f"{uc_id} - {course.get('uc_course_title')}\n"
                            f"Group: {group_id} | Section: {section_id}\n"
                            f"Logic Type: {group_logic_type} | N Required: {n_courses or 'N/A'}\n"
                            f"Articulation Logic: {json.dumps(logic_block, indent=2)}",
                    "metadata": enriched_metadata
                })

    return flattened_docs


def load_documents(path: Optional[str] = None) -> List[Document]:
    """
    Load articulation data from JSON and convert to LlamaIndex Document objects.
    
    This is the main entry point for loading articulation data. It reads the JSON file,
    creates an overview document, and converts all articulation data into searchable
    Document objects with appropriate metadata.
    
    Args:
        path: Optional path to the JSON data file. If None, defaults to "data/rag_data.json"
              relative to the current module.
    
    Returns:
        A list of LlamaIndex Document objects, including an overview document and
        individual documents for each UC course articulation.
        
    Example:
        >>> docs = load_documents()
        >>> len(docs)  # Number of documents created
        95  # (varies based on data size)
    """
    json_data = _load_json_data(path)

    # Build the course cache while we're at it
    _build_course_cache()

    # Overview doc
    overview = {
        "text": f"Overview:\n{json_data.get('general_advice', '')}",
        "metadata": {
            "doc_type": "overview",
            "title": f"{json_data.get('major', '')} Transfer Overview",
            "source": json_data.get("from", "")
        }
    }

    flat_docs = flatten_courses_from_json(json_data)
    all_docs = [overview] + flat_docs

    return [Document(text=d["text"], metadata=d["metadata"]) for d in all_docs]