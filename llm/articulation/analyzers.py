"""
TransferAI Articulation Package - Analyzers

This module provides functions for analyzing articulation logic and extracting
useful information without modifying the underlying structures. These functions
support queries about articulation data beyond simple validation.

Key Functions:
- extract_honors_info_from_logic: Extracts honors course information
- count_uc_matches: Counts how many UC courses a community college course satisfies
- summarize_logic_blocks: Generates summaries of logic block requirements
- get_uc_courses_satisfied_by_ccc: Finds UC courses satisfied by community college courses

The analyzers focus on information extraction and pattern recognition within
articulation data, enabling richer query responses and insights about course
transferability.
"""

from typing import List, Dict, Any, Set, Union, Optional
from .models import LogicBlock
from llama_index_client import Document


def extract_honors_info_from_logic(
    logic_block: Union[LogicBlock, Dict[str, Any]]
) -> Dict[str, List[str]]:
    """
    Extract honors and non-honors courses from a logic block.
    
    Traverses the nested structure of a logic block to separate honors and non-honors
    courses into separate lists for easier processing and presentation.
    
    Args:
        logic_block: A LogicBlock or dict containing the articulation logic structure
                   with nested AND/OR blocks and course information
                   
    Returns:
        A dictionary with two keys:
        - 'honors_courses': A sorted list of honors course codes
        - 'non_honors_courses': A sorted list of non-honors course codes
        
    Example:
        >>> logic = {"type": "OR", "courses": [
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1AH", "honors": True}]},
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1A", "honors": False}]}
        ... ]}
        >>> extract_honors_info_from_logic(logic)
        {'honors_courses': ['MATH 1AH'], 'non_honors_courses': ['MATH 1A']}
    """
    # Ensure consistent handling by converting LogicBlock to dict if needed
    # We don't convert to dict here, to handle both dict and Pydantic models in recurse()
    
    # Initialize sets to track all courses, honors courses, and non-honors courses
    all_courses = set()
    honors_courses = set()
    non_honors_courses = set()

    def recurse(block):
        """Recursive helper function to traverse the nested logic structure"""
        # Handle Pydantic models
        if hasattr(block, 'dict') and callable(getattr(block, 'dict')):
            # For LogicBlock or CourseOption Pydantic models
            block_dict = block.dict()
            
            # If this is a CourseOption with course_letters, process it directly
            if 'course_letters' in block_dict:
                code = block_dict.get('course_letters', '').strip()
                if code:
                    all_courses.add(code)
                    if block_dict.get('honors', False):
                        honors_courses.add(code)
                    else:
                        non_honors_courses.add(code)
            # If this is a LogicBlock (AND/OR), recurse into its courses
            elif block_dict.get('type') in {'AND', 'OR'} and 'courses' in block_dict:
                for course in block.courses:
                    recurse(course)
            return
                
        # Handle dictionary
        if isinstance(block, dict):
            # If this is an AND/OR block with nested courses, recurse into each course
            if block.get("type") in {"AND", "OR"} and isinstance(block.get("courses"), list):
                for course in block["courses"]:
                    recurse(course)
            # If this is a course node, add it to the appropriate sets
            elif "course_letters" in block:
                code = block.get("course_letters", "").strip()
                if code:
                    all_courses.add(code)
                    if block.get("honors"):
                        honors_courses.add(code)
                    else:
                        non_honors_courses.add(code)
        # If this is a list of blocks, recurse into each item
        elif isinstance(block, list):
            for item in block:
                recurse(item)

    # Start the recursion from the top-level logic block
    recurse(logic_block)
    
    # Return sorted lists of honors and non-honors courses
    return {
        "honors_courses": sorted(honors_courses),
        "non_honors_courses": sorted(non_honors_courses),
    }


def count_uc_matches(
    ccc_course: str,
    docs: List[Document]
) -> tuple:
    """
    Count UC courses matched by a CCC course.
    
    Identifies both direct matches (where the CCC course alone satisfies a UC course)
    and contribution matches (where the CCC course is part of a combination).
    
    Args:
        ccc_course: The CCC course code to analyze
        docs: List of articulation documents to search
        
    Returns:
        Tuple containing:
        - Count of direct matches (int)
        - List of direct-match UC courses (list of strings)
        - List of combination-match UC courses (list of strings)
        
    Example:
        >>> count_uc_matches("CIS 36A", docs)
        (1, ['CSE 8A'], ['CSE 11'])  # Direct match for CSE 8A, contributes to CSE 11
    """
    # Find UC courses where this CCC course is a direct match
    direct_matches = get_uc_courses_satisfied_by_ccc(ccc_course, docs)
    
    # Find UC courses where this CCC course is part of a combination
    contributing_matches = get_uc_courses_requiring_ccc_combo(ccc_course, docs)
    
    # Remove any overlap (courses that are both direct matches and combo matches)
    # We only want to show unique contribution matches
    contributing_only = [uc for uc in contributing_matches if uc not in direct_matches]
    
    # Return the count of direct matches (not total matches), the direct matches list, and contributing matches list
    return (len(direct_matches), direct_matches, contributing_only)


def summarize_logic_blocks(
    logic_block: Union[LogicBlock, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate concise summary of logic structure.
    
    Creates a simplified representation of a complex logic structure,
    highlighting key patterns and requirements without the full detail.
    
    Args:
        logic_block: Logic block structure to summarize
        
    Returns:
        Dictionary containing summarized metadata about the articulation logic:
        - option_count: Number of distinct articulation options
        - multi_course_options: Count of options requiring multiple CCC courses
        - honors_required: Whether only honors courses satisfy the requirement
        - has_honors_options: Whether any honors courses are present in options
        - min_courses_required: Minimum number of CCC courses needed
        - no_articulation: Whether articulation is available at all
        
    Example:
        >>> summarize_logic_blocks(logic_block)
        {
            'option_count': 2, 
            'multi_course_options': 1,
            'honors_required': False,
            'has_honors_options': True,
            'min_courses_required': 1,
            'no_articulation': False
        }
    """
    # Ensure logic_block is a dict for consistent handling
    if isinstance(logic_block, LogicBlock):
        logic_block = logic_block.dict()
    
    # Handle invalid or empty logic blocks
    if not logic_block or not isinstance(logic_block, dict):
        return {
            "option_count": 0,
            "multi_course_options": 0,
            "honors_required": False,
            "has_honors_options": False,
            "min_courses_required": 0,
            "no_articulation": True
        }
    
    # Check if there's no articulation available
    if logic_block.get("no_articulation", False):
        return {
            "option_count": 0,
            "multi_course_options": 0,
            "honors_required": False,
            "has_honors_options": False,
            "min_courses_required": 0,
            "no_articulation": True
        }
    
    # Initialize counters and flags
    option_count = 0
    multi_course_options = 0
    min_course_count = float('inf')
    honors_courses_found = False
    
    # Process the logic block
    if logic_block.get("type") == "OR":
        for option in logic_block.get("courses", []):
            option_count += 1
            
            if isinstance(option, dict) and option.get("type") == "AND":
                courses = option.get("courses", [])
                course_count = len(courses)
                
                # Track multi-course options
                if course_count > 1:
                    multi_course_options += 1
                
                # Track minimum course count
                if course_count < min_course_count:
                    min_course_count = course_count
                
                # Check for honors courses
                for course in courses:
                    if isinstance(course, dict) and course.get("honors", False):
                        honors_courses_found = True
    
    # Get honors required status using imported function
    from .detectors import is_honors_required
    honors_required = is_honors_required(logic_block)
    
    # Adjust minimum course count for edge cases
    if min_course_count == float('inf'):
        min_course_count = 0
    
    return {
        "option_count": option_count,
        "multi_course_options": multi_course_options,
        "honors_required": honors_required,
        "has_honors_options": honors_courses_found,
        "min_courses_required": min_course_count,
        "no_articulation": False
    }


def get_uc_courses_satisfied_by_ccc(
    ccc_course: str,
    all_docs: List[Document]
) -> List[str]:
    """
    Find UC courses that can be directly satisfied by a single CCC course.
    
    Identifies UC courses where the specified CCC course alone can satisfy the
    articulation requirement without needing additional courses.
    
    Args:
        ccc_course: The CCC course code to check (e.g., "CIS 22A")
        all_docs: List of articulation documents to search through
        
    Returns:
        A sorted list of UC course codes that can be satisfied by the given CCC course
        
    Example:
        >>> get_uc_courses_satisfied_by_ccc("CIS 36A", docs)
        ['CSE 8A']
    """
    # Handle edge cases
    if not ccc_course or not all_docs:
        return []
        
    # Normalize the CCC course code to uppercase for consistent matching
    matched_uc_courses = set()
    ccc_course_normalized = ccc_course.strip().upper()

    # Check each document for a direct match
    for doc in all_docs:
        # Extract logic blocks from document metadata
        logic_blocks = doc.metadata.get("logic_block", [])
        
        # Ensure logic_blocks is a list
        if isinstance(logic_blocks, dict):
            logic_blocks = [logic_blocks]
        elif not isinstance(logic_blocks, list):
            continue

        # Check each logic block
        for block in logic_blocks:
            # Skip non-OR blocks
            if not isinstance(block, dict) or block.get("type") != "OR":
                continue

            # Check each AND option within the OR block
            for and_option in block.get("courses", []):
                # Skip non-AND blocks
                if not isinstance(and_option, dict) or and_option.get("type") != "AND":
                    continue

                # Get the course list for this AND option
                course_list = and_option.get("courses", [])
                
                # Check if this is a direct match (single course that matches our target)
                if (len(course_list) == 1 and
                    course_list[0].get("course_letters", "").strip().upper() == ccc_course_normalized):
                    # Add the matching UC course to our results
                    uc_course = doc.metadata.get("uc_course", "")
                    if uc_course:
                        matched_uc_courses.add(uc_course)

    # Return a sorted list of matched UC courses
    return sorted(matched_uc_courses)


def get_uc_courses_requiring_ccc_combo(
    ccc_course: str,
    all_docs: List[Document]
) -> List[str]:
    """
    Find UC courses where the given CCC course is part of a multi-course combination.
    
    Identifies UC courses where the specified CCC course contributes to satisfying
    the articulation requirement but must be combined with additional courses.
    
    Args:
        ccc_course: The CCC course code to check (e.g., "CIS 22A")
        all_docs: List of articulation documents to search through
        
    Returns:
        A sorted list of UC course codes where the given CCC course is part of a 
        multi-course combination requirement
        
    Example:
        >>> get_uc_courses_requiring_ccc_combo("CIS 36A", docs)
        ['CSE 11']  # If CSE 11 requires CIS 36A + CIS 36B
    """
    # Normalize the CCC course code to uppercase for consistent matching
    contributing_uc_courses = set()
    ccc_course_normalized = ccc_course.strip().upper()

    # Check each document
    for doc in all_docs:
        # Extract logic blocks from document metadata
        logic_blocks = doc.metadata.get("logic_block", [])
        
        # Ensure logic_blocks is a list
        if isinstance(logic_blocks, dict):
            logic_blocks = [logic_blocks]
        elif not isinstance(logic_blocks, list):
            continue

        # Check each logic block
        for block in logic_blocks:
            # Skip non-OR blocks
            if not isinstance(block, dict) or block.get("type") != "OR":
                continue

            # Check each AND option within the OR block
            for and_option in block.get("courses", []):
                # Skip non-AND blocks
                if not isinstance(and_option, dict) or and_option.get("type") != "AND":
                    continue

                # Get the course list for this AND option
                course_list = and_option.get("courses", [])
                
                # Check if this is a multi-course combination that includes our target course
                if (len(course_list) > 1 and
                    any(course.get("course_letters", "").strip().upper() == ccc_course_normalized
                        for course in course_list)):
                    # Add the matching UC course to our results
                    uc_course = doc.metadata.get("uc_course", "")
                    if uc_course:
                        contributing_uc_courses.add(uc_course)

    # Return a sorted list of contributing UC courses
    return sorted(contributing_uc_courses)


def find_uc_courses_satisfied_by(ccc_course: str, all_docs: List[Document]) -> List[Document]:
    """
    Reverse-match: Find all UC courses whose logic includes the given CCC course.
    
    Searches deeply inside all nested logic blocks for any occurrence of the specified
    CCC course, regardless of whether it's part of an AND or OR block. This is useful
    for identifying all UC courses that a particular CCC course can contribute toward.
    
    Args:
        ccc_course: The CCC course code to search for (e.g., "CIS 22A")
        all_docs: List of articulation documents to search through
        
    Returns:
        A list of Document objects containing UC courses whose articulation logic
        includes the specified CCC course
        
    Example:
        >>> result = find_uc_courses_satisfied_by("MATH 1A", all_docs)
        >>> [doc.metadata.get("uc_course") for doc in result]
        ['MATH 20A', 'MATH 21A']  # Found in both courses' logic
    """
    matches = []

    # Handle edge cases
    if not ccc_course or not all_docs:
        return matches

    # Normalize the CCC course code to uppercase for consistent matching
    ccc_norm = ccc_course.strip().upper()

    def logic_contains_course(block):
        """Recursively check if the logic block contains the specified course."""
        # Handle empty or invalid blocks
        if not block or not isinstance(block, dict):
            return False
            
        logic_type = block.get("type")
        courses = block.get("courses", [])

        if isinstance(courses, list):
            for entry in courses:
                if isinstance(entry, dict):
                    # Recursive check for nested logic blocks
                    if entry.get("type") in {"AND", "OR"}:
                        if logic_contains_course(entry):
                            return True
                    # Check for direct course match
                    elif entry.get("course_letters", "").strip().upper() == ccc_norm:
                        return True
        return False

    # Check each document for matches
    for doc in all_docs:
        logic = doc.metadata.get("logic_block", {})
        if logic_contains_course(logic):
            matches.append(doc)

    return matches 