"""
TransferAI Articulation Package - Detectors

This module contains functions for detecting special cases and edge conditions
in articulation logic, such as honors requirements and redundant course selections.
These functions analyze patterns that require special handling or explanations.

Key Functions:
- is_honors_required: Detects when only honors courses will satisfy a requirement
- detect_redundant_courses: Identifies redundant course selections
- is_honors_pair_equivalent: Determines if courses are honors/non-honors equivalents
- validate_logic_block: Validates a course against specific logic requirements

The detectors focus on identifying special patterns that affect validation results
and user recommendations, enhancing the system's ability to provide nuanced and
helpful guidance.
"""

from typing import List, Dict, Union, Any, Tuple, Set, Optional
from .models import LogicBlock


def is_honors_required(
    logic_block: Union[LogicBlock, Dict[str, Any]]
) -> bool:
    """
    Determine if honors courses are required.
    
    Analyzes a logic block to determine if only honors courses will satisfy
    the requirement, by examining the structure and honors flags.
    
    Args:
        logic_block: A LogicBlock or dict representing articulation requirements
        
    Returns:
        True if only honors courses will satisfy the requirement, False otherwise
        
    Example:
        >>> logic_block = {"type": "OR", "courses": [
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1AH", "honors": True}]}
        ... ]}
        >>> is_honors_required(logic_block)
        True
        
        >>> logic_block = {"type": "OR", "courses": [
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1A", "honors": False}]},
        ...     {"type": "AND", "courses": [{"course_letters": "MATH 1AH", "honors": True}]}
        ... ]}
        >>> is_honors_required(logic_block)
        False
    """
    # Handle edge cases
    if not logic_block:
        return False
    
    # Check for no articulation flag
    if isinstance(logic_block, dict) and logic_block.get("no_articulation", False):
        return False
    elif isinstance(logic_block, LogicBlock) and logic_block.no_articulation:
        return False
        
    # Handle list input (multiple logic blocks)
    if isinstance(logic_block, list):
        # If ANY block requires honors, return True
        for block in logic_block:
            if is_honors_required(block):
                return True
        return False
        
    # Convert to dict if needed
    if isinstance(logic_block, dict):
        blocks = [logic_block]
    elif isinstance(logic_block, LogicBlock):
        blocks = [logic_block.dict()]
    else:
        blocks = []
        
    all_options_require_honors = True
    has_options = False
    
    # For each OR block
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "OR":
            continue
            
        # Check each option (usually AND blocks)
        for option in block.get("courses", []):
            has_options = True
            
            # If this is an AND block, check each course
            if isinstance(option, dict) and option.get("type") == "AND":
                # For each course in this AND group
                option_requires_honors = False
                for course in option.get("courses", []):
                    if course.get("honors", False):
                        option_requires_honors = True
                
                # If this option doesn't require honors, then honors aren't required
                if not option_requires_honors:
                    all_options_require_honors = False
                    break
            else:
                # Direct course option
                if not option.get("honors", False):
                    all_options_require_honors = False
                    break
                    
        # If we found a non-honors option, we can stop checking
        if not all_options_require_honors:
            break
    
    # Only return True if we actually found options and all required honors
    return has_options and all_options_require_honors


def detect_redundant_courses(
    selected_courses: List[str],
    logic_block: Union[LogicBlock, Dict[str, Any]]
) -> List[List[str]]:
    """
    Identify redundant course selections.
    
    Analyzes a list of selected courses to identify which ones are redundant
    for satisfying the given logic block. This helps users avoid taking
    unnecessary courses.
    
    Args:
        selected_courses: List of selected course codes
        logic_block: A LogicBlock or dict representing articulation requirements
        
    Returns:
        List of lists, where each inner list contains a group of redundant courses
        
    Example:
        >>> detect_redundant_courses(["MATH 1A", "MATH 1AH"], logic_block)
        [["MATH 1A", "MATH 1AH"]]  # If either course satisfies, one is redundant
    """
    # Guard clauses for invalid inputs
    if not logic_block or not isinstance(logic_block, (dict, LogicBlock)) or not selected_courses:
        return []
    
    # Ensure logic_block is a dict for consistent handling
    if isinstance(logic_block, LogicBlock):
        logic_block_dict = logic_block.dict()
    else:
        logic_block_dict = logic_block

    # Normalize the selected courses to uppercase for consistent comparison
    selected_courses = [c.upper().strip() for c in selected_courses]
    
    # Initialize redundant groups
    redundant_groups = []
    
    # First pass: Extract course options from logic block
    course_options = {}
    
    if logic_block_dict.get("type") == "OR":
        for i, option in enumerate(logic_block_dict.get("courses", [])):
            # Process AND blocks with single courses (direct equivalents)
            if isinstance(option, dict) and option.get("type") == "AND" and len(option.get("courses", [])) == 1:
                course = option["courses"][0].get("course_letters", "").upper().strip()
                if course:
                    course_options.setdefault(course, []).append(i)
    
    # Second pass: Find courses that satisfy the same options
    course_groups = {}
    for course, options in course_options.items():
        if course in selected_courses:
            option_key = tuple(sorted(options))
            course_groups.setdefault(option_key, []).append(course)
    
    # Add redundant courses from common option groups
    for courses in course_groups.values():
        if len(courses) > 1:
            redundant_groups.append(sorted(courses))
    
    # Third pass: Look for honors/non-honors pairs not caught by option matching
    # Create a set of courses we've already identified as redundant
    already_grouped = {course for group in redundant_groups for course in group}
    
    # Check each pair of selected courses
    for i, course1 in enumerate(selected_courses):
        if course1 in already_grouped:
            continue
            
        for j in range(i+1, len(selected_courses)):
            course2 = selected_courses[j]
            if course2 in already_grouped:
                continue
                
            # Check if this is an honors/non-honors pair
            if (course2 == course1 + "H") or (course1 == course2 + "H"):
                # One is the honors version of the other
                redundant_groups.append(sorted([course1, course2]))
                already_grouped.add(course1)
                already_grouped.add(course2)
                break
    
    return redundant_groups


def is_honors_pair_equivalent(
    or_block: Union[LogicBlock, Dict[str, Any]],
    course1: str,
    course2: str
) -> bool:
    """
    Determine if two courses are honors/non-honors equivalents.
    
    Checks if two courses represent the honors and non-honors versions
    of the same course, by analyzing their codes and the logic structure.
    
    Args:
        or_block: An OR logic block containing course options
        course1: First course code to check
        course2: Second course code to check
        
    Returns:
        True if the courses are honors/non-honors equivalents, False otherwise
        
    Example:
        >>> is_honors_pair_equivalent(logic_block, "MATH 1A", "MATH 1AH")
        True
    """
    # Handle invalid input type
    if not isinstance(or_block, (dict, LogicBlock)) or not or_block:
        return False
    
    # Convert LogicBlock to dict if needed
    if isinstance(or_block, LogicBlock):
        or_block_dict = or_block.dict()
    else:
        or_block_dict = or_block
        
    # Check if the block has a courses list
    if not or_block_dict.get("courses"):
        return False
        
    def normalize(c):
        """Normalize course code and separate honors suffix"""
        c = c.upper().strip()
        is_honors = c.endswith("H")
        base = c[:-1] if is_honors else c
        return base, is_honors
        
    base1, is_honors1 = normalize(course1)
    base2, is_honors2 = normalize(course2)
    
    # Must be different (one honors, one not)
    if is_honors1 == is_honors2:
        return False
        
    # Must have the same base name
    if base1 != base2:
        return False
        
    # Check if both appear in the OR block
    courses_in_block = []
    for option in or_block_dict.get("courses", []):
        if isinstance(option, dict) and option.get("type") == "AND" and len(option.get("courses", [])) == 1:
            course = option["courses"][0].get("course_letters", "").upper().strip()
            courses_in_block.append(course)
            
    return course1.upper() in courses_in_block and course2.upper() in courses_in_block


def explain_honors_equivalence(
    course1: str,
    course2: str
) -> str:
    """
    Generate explanation of honors equivalence.
    
    Creates a clear explanation of why two courses are considered
    honors/non-honors equivalents of each other.
    
    Args:
        course1: First course code
        course2: Second course code
        
    Returns:
        A formatted string explaining the honors equivalence
        
    Example:
        >>> explain_honors_equivalence("MATH 1A", "MATH 1AH")
        'MATH 1A and MATH 1AH are equivalent courses, with MATH 1AH being the honors version.'
    """
    def normalize(course):
        """Normalize course code to uppercase for consistent comparison"""
        return course.upper().strip()
        
    def is_honors(course):
        """Determine if a course is an honors course based on the 'H' suffix"""
        return course.upper().strip().endswith("H")
        
    c1 = normalize(course1)
    c2 = normalize(course2)
    
    # Identify which course is the honors version and which is the non-honors version
    honors = c1 if is_honors(c1) else c2
    non_honors = c2 if is_honors(c1) else c1
    
    # Return a formatted explanation of the equivalence
    return f"{non_honors} and {honors} are equivalent (non-honors and honors versions of the same course)"


def validate_logic_block(
    course_code: str,
    logic_block: Union[LogicBlock, Dict[str, Any]]
) -> Tuple[bool, List[str], List[str]]:
    """
    Validate a course against a logic block and extract match information.
    
    Recursively traverses a logic block to determine if a course code satisfies
    any part of the articulation requirements, handling AND/OR combinations.
    
    Args:
        course_code: Course code to validate
        logic_block: Logic block to check against
        
    Returns:
        Tuple containing:
        - Boolean indicating if the course satisfies any requirement
        - List of matched course codes
        - List of missing/required course codes
        
    Example:
        >>> validate_logic_block("MATH 1A", logic_block)
        (True, ["MATH 1A"], [])
        >>> validate_logic_block("CHEM 1A", logic_block)
        (False, [], ["MATH 1A"])
    """
    # Convert LogicBlock to dict if needed
    if isinstance(logic_block, LogicBlock):
        logic_block_dict = logic_block.dict()
    else:
        logic_block_dict = logic_block
    
    # Base case for empty logic
    if not logic_block_dict:
        return False, [], []
    
    # Handle list format specifically
    if isinstance(logic_block_dict, list):
        all_matches = []
        all_misses = []
        
        for item in logic_block_dict:
            is_valid, matches, misses = validate_logic_block(course_code, item)
            if is_valid:
                return True, matches, []
            
            all_matches.extend(matches)
            all_misses.extend(misses)
        
        # Extract course names if available
        course_names = []
        for item in logic_block_dict:
            if isinstance(item, dict) and "course_letters" in item:
                course_names.append(item.get("course_letters", ""))
        
        return False, all_matches, all_misses if all_misses else course_names
    
    # Check for nested courses in OR condition
    if logic_block_dict.get("type") == "OR":
        all_matches = []
        all_misses = []
        courses = logic_block_dict.get("courses", [])
        
        # OR logic means any match is sufficient
        for course in courses:
            is_valid, matches, misses = validate_logic_block(course_code, course)
            if is_valid:
                return True, matches, []
            
            all_matches.extend(matches)
            all_misses.extend(misses)
        
        # If no match found, return all courses that could have satisfied the requirement
        return False, all_matches, all_misses
    
    # Check for nested courses in AND condition
    elif logic_block_dict.get("type") == "AND":
        all_matches = []
        all_misses = []
        courses = logic_block_dict.get("courses", [])
        
        # AND logic means all must match
        for course in courses:
            is_valid, matches, misses = validate_logic_block(course_code, course)
            
            all_matches.extend(matches)
            
            if not is_valid:
                all_misses.extend(misses)
        
        # If there are misses, the requirement is not satisfied
        if all_misses:
            return False, all_matches, all_misses
        
        return True, all_matches, []
    
    # Check for a direct match with a course
    elif "course_letters" in logic_block_dict:
        target_course = logic_block_dict.get("course_letters", "").strip()
        is_honors = logic_block_dict.get("honors", False)
        normalized_course = course_code.lower().strip()
        normalized_target = target_course.lower().strip()
        
        # Strip the 'H' suffix for comparing with honors courses
        base_course = normalized_course[:-1] if normalized_course.endswith('h') else normalized_course
        base_target = normalized_target[:-1] if normalized_target.endswith('h') else normalized_target
        
        # Exact match found (case insensitive)
        if normalized_target == normalized_course:
            # If it's an honors course, return match
            if is_honors:
                return True, [f"{target_course} (Honors)"], []
            return True, [target_course], []
            
        # Handle honors course requirement when non-honors version is provided
        # e.g., MATH 3A won't match MATH 3AH (honors required)
        if is_honors and base_target == base_course and not normalized_course.endswith('h'):
            return False, [], [f"{target_course} (Honors)"]
        
        # No match found
        if is_honors:
            return False, [], [f"{target_course} (Honors)"]
        return False, [], [target_course]
    
    # Fallback for unrecognized format
    return False, [], [] 