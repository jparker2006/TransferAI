from __future__ import annotations

"""TransferAI – Articulation Match Tool

StructuredTool that compares a student's completed SMC courses against UCSD 
lower-division requirements for a given major and reports satisfied/missing 
courses plus conditional notes.

This tool:
1. Takes a list of completed SMC course codes and a target UCSD major string
2. Loads the corresponding ASSIST articulation JSON file
3. Parses requirement groups and their articulation mappings
4. Determines which requirements are satisfied by the student's courses
5. Returns structured results with satisfied, missing, and notes

Dependencies: Only stdlib (json, re, pathlib, difflib)
"""

import difflib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Public Exceptions
# ---------------------------------------------------------------------------


class MajorNotFoundError(RuntimeError):
    """Raised when a major slug cannot be located in the articulation data."""


class UserCancellationError(RuntimeError):
    """Raised when user cancels the major selection process."""


# ---------------------------------------------------------------------------
# Pydantic I/O Schemas
# ---------------------------------------------------------------------------


class AMIn(BaseModel):
    """Input schema for ArticulationMatchTool."""
    
    smc_courses: List[str] = Field(
        ..., 
        description="List of completed SMC course codes (e.g., ['CS 55', 'MATH 7', 'MATH 8'])"
    )
    target_major: str = Field(
        ..., 
        description="Target UCSD major name (e.g., 'Computer Science B.S.')"
    )


class SatisfiedRequirement(BaseModel):
    """A UCSD requirement that has been satisfied."""
    
    ucsd_course: str
    smc_courses_used: List[str]


class AMOut(BaseModel):
    """Output schema for ArticulationMatchTool."""
    
    major: str
    academic_year: str
    satisfied: List[SatisfiedRequirement]
    missing: List[str]
    notes: List[str]


# ---------------------------------------------------------------------------
# Constants & Paths
# ---------------------------------------------------------------------------

_DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "assist_articulation_v2" / "json" / "santa_monica_college" / "university_of_california_san_diego"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _slugify(text: str) -> str:
    """Convert major name to filename slug."""
    slug = (
        text.lower()
        .replace('&', 'and')
        .replace('-', '')
        .replace('.', '')
        .replace(':', '')
        .strip()
        .replace('  ', ' ')
        .replace(' ', '_')
    )
    return slug


def _canonical(code: str) -> str:
    """Extract canonical course code from text."""
    # "CSE 21: Math for Algorithms (4.00 units)" → "CSE 21"
    # Also handles "cs55" → "CS 55"
    code_upper = code.strip().upper()
    match = re.search(r"([A-Z]{2,4})\s*(\d+)([A-Z]?)", code_upper)
    if match:
        prefix, number, suffix = match.groups()
        return f"{prefix} {number}{suffix}"
    return code_upper


def _parse_sending_courses(sending_articulation: Dict[str, Any]) -> List[List[str]]:
    """Parse SMC course requirements from sending articulation.
    
    Enhanced version that handles complex AND/OR logic, courseGroupConjunctions,
    and nested requirement structures.
    
    Returns list of course combinations where each inner list represents
    courses that must ALL be taken (AND logic), and the outer list represents
    alternatives (OR logic).
    """
    if not sending_articulation or "items" not in sending_articulation:
        return []
    
    combinations = []
    
    # Handle courseGroupConjunctions for complex logic between groups
    conjunctions = sending_articulation.get("courseGroupConjunctions", [])
    items = sending_articulation.get("items", [])
    
    # If no conjunctions, treat each group as alternatives (OR logic)
    if not conjunctions:
        for item in items:
            group_combinations = _parse_course_group(item)
            combinations.extend(group_combinations)
    else:
        # Handle complex conjunctions between groups
        # For now, we'll handle the most common case: AND between all groups
        # This could be expanded to handle more complex logical structures
        if len(items) > 1 and conjunctions:
            # Try to combine all groups with AND logic
            all_group_combinations = []
            for item in items:
                group_combinations = _parse_course_group(item)
                all_group_combinations.append(group_combinations)
            
            # Generate all possible combinations across groups
            import itertools
            for combo in itertools.product(*all_group_combinations):
                # Flatten and combine all courses from all groups
                combined_courses = []
                for group in combo:
                    combined_courses.extend(group)
                if combined_courses:
                    combinations.append(combined_courses)
        else:
            # Fallback to simple processing
            for item in items:
                group_combinations = _parse_course_group(item)
                combinations.extend(group_combinations)
    
    return combinations


def _parse_course_group(item: Dict[str, Any]) -> List[List[str]]:
    """Parse a single course group, handling internal AND/OR logic."""
    if item.get("type") != "CourseGroup":
        return []
    
    course_group = []
    group_items = item.get("items", [])
    course_conjunction = item.get("courseConjunction", "And")  # Default to AND
    
    # Extract all courses in this group
    courses_in_group = []
    for course_item in group_items:
        if course_item.get("type") == "Course":
            prefix = course_item.get("prefix", "")
            number = course_item.get("courseNumber", "")
            if prefix and number:
                courses_in_group.append(f"{prefix} {number}")
    
    if not courses_in_group:
        return []
    
    # Handle conjunction type
    if course_conjunction.lower() == "and":
        # All courses must be taken together
        return [courses_in_group]
    elif course_conjunction.lower() == "or":
        # Any single course satisfies the requirement
        return [[course] for course in courses_in_group]
    else:
        # Default to AND logic for unknown conjunctions
        return [courses_in_group]


def _extract_articulations(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract articulation mappings from ASSIST JSON data."""
    try:
        articulations_str = data["result"]["articulations"]
        return json.loads(articulations_str)
    except (KeyError, json.JSONDecodeError):
        return []


def _extract_receiving_course(articulation: Dict[str, Any]) -> Optional[str]:
    """Extract UCSD course code from articulation."""
    try:
        course_data = articulation["articulation"]["course"]
        prefix = course_data.get("prefix", "")
        number = course_data.get("courseNumber", "")
        if prefix and number:
            return f"{prefix} {number}"
    except (KeyError, TypeError):
        pass
    return None


def _extract_academic_year(data: Dict[str, Any]) -> str:
    """Extract academic year from ASSIST data."""
    try:
        academic_year_str = data["result"]["academicYear"]
        academic_year_data = json.loads(academic_year_str)
        return academic_year_data.get("code", "unknown")
    except (KeyError, json.JSONDecodeError):
        return "unknown"


def _has_no_articulation(sending_articulation: Dict[str, Any]) -> bool:
    """Check if there's no articulation (denied courses or no course articulated)."""
    if not sending_articulation:
        return True
    
    # Check for "No Course Articulated" cases
    if sending_articulation.get("noArticulationReason"):
        return True
    
    # Check for denied courses
    if sending_articulation.get("deniedCourses"):
        return True
    
    # Check if items is empty
    if not sending_articulation.get("items"):
        return True
    
    return False


def _analyze_requirement_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze the structure of requirements for debugging and validation."""
    try:
        articulations = _extract_articulations(data)
        structure_info = {
            "total_requirements": len(articulations),
            "requirements_with_articulation": 0,
            "requirements_without_articulation": 0,
            "complex_and_requirements": 0,
            "complex_or_requirements": 0,
            "multi_group_requirements": 0,
            "course_conjunctions": [],
            "group_conjunctions": []
        }
        
        for articulation in articulations:
            sending_articulation = articulation.get("articulation", {}).get("sendingArticulation", {})
            
            if _has_no_articulation(sending_articulation):
                structure_info["requirements_without_articulation"] += 1
                continue
            
            structure_info["requirements_with_articulation"] += 1
            
            items = sending_articulation.get("items", [])
            group_conjunctions = sending_articulation.get("courseGroupConjunctions", [])
            
            if len(items) > 1:
                structure_info["multi_group_requirements"] += 1
            
            if group_conjunctions:
                structure_info["group_conjunctions"].extend(group_conjunctions)
            
            for item in items:
                if item.get("type") == "CourseGroup":
                    course_conjunction = item.get("courseConjunction", "And")
                    structure_info["course_conjunctions"].append(course_conjunction)
                    
                    group_items = item.get("items", [])
                    if len(group_items) > 1:
                        if course_conjunction.lower() == "and":
                            structure_info["complex_and_requirements"] += 1
                        elif course_conjunction.lower() == "or":
                            structure_info["complex_or_requirements"] += 1
        
        return structure_info
    except Exception:
        return {"error": "Failed to analyze requirement structure"}


def _validate_result_consistency(result: Dict[str, Any], student_courses: set) -> List[str]:
    """Validate the logical consistency of articulation results."""
    warnings = []
    
    # Check for duplicate course usage
    used_courses = {}
    for req in result.get("satisfied", []):
        for course in req.get("smc_courses_used", []):
            canonical_course = _canonical(course)
            if canonical_course in used_courses:
                used_courses[canonical_course].append(req["ucsd_course"])
            else:
                used_courses[canonical_course] = [req["ucsd_course"]]
    
    # Report courses used for multiple requirements
    for course, requirements in used_courses.items():
        if len(requirements) > 1:
            warnings.append(f"Course {course} satisfies multiple requirements: {', '.join(requirements)}")
    
    # Check that all used courses are in student's course list
    for req in result.get("satisfied", []):
        for course in req.get("smc_courses_used", []):
            canonical_course = _canonical(course)
            if canonical_course not in student_courses:
                warnings.append(f"Result claims {course} was used but it's not in student's course list")
    
    # Basic sanity checks
    total_requirements = len(result.get("satisfied", [])) + len(result.get("missing", []))
    if total_requirements == 0:
        warnings.append("No requirements found - this might indicate a parsing error")
    
    return warnings


# ---------------------------------------------------------------------------
# Fuzzy Matching Functions
# ---------------------------------------------------------------------------


def _get_available_majors() -> List[Tuple[str, str]]:
    """Get all available major files and their human-readable names.
    
    Returns:
        List of (filename, human_readable_name) tuples
    """
    if not _DATA_ROOT.exists():
        return []
    
    majors = []
    for file_path in _DATA_ROOT.glob("*.json"):
        filename = file_path.stem  # Remove .json extension
        # Convert filename to human-readable format
        human_name = _filename_to_human_readable(filename)
        majors.append((filename, human_name))
    
    return sorted(majors, key=lambda x: x[1])


def _filename_to_human_readable(filename: str) -> str:
    """Convert filename to human-readable major name.
    
    Examples:
        'cse_computer_science_bs' -> 'CSE: Computer Science B.S.'
        'mathematics_bs' -> 'Mathematics B.S.'
        'physics_ba_secondary_education' -> 'Physics B.A. (Secondary Education)'
    """
    # Handle special prefixes
    parts = filename.split('_')
    
    # Check for department prefixes
    dept_prefixes = {
        'cse': 'CSE:',
        'ece': 'ECE:',
        'mae': 'MAE:',
        'cogs': 'COGS:',
    }
    
    if parts[0].lower() in dept_prefixes:
        prefix = dept_prefixes[parts[0].lower()]
        parts = parts[1:]  # Remove the prefix from parts
    else:
        prefix = ''
    
    # Process the remaining parts
    processed_parts = []
    degree_found = False
    
    for i, part in enumerate(parts):
        if part.lower() in ['bs', 'ba', 'minor']:
            # Handle degree types
            if part.lower() == 'bs':
                processed_parts.append('B.S.')
            elif part.lower() == 'ba':
                processed_parts.append('B.A.')
            elif part.lower() == 'minor':
                processed_parts.append('(Minor)')
            degree_found = True
        elif part.lower() == 'with' and i + 1 < len(parts) and parts[i + 1].lower() in ['a', 'concentration', 'specialization']:
            # Handle "with a specialization in..." or "with concentration in..."
            remaining = parts[i+1:]  # Skip 'with'
            if remaining and remaining[0].lower() == 'a':
                remaining = remaining[1:]  # Skip 'a'
            if remaining and remaining[0].lower() in ['specialization', 'concentration']:
                spec_type = remaining[0].capitalize()
                remaining = remaining[1:]  # Skip 'specialization'/'concentration'
            else:
                spec_type = 'Specialization'
            if remaining and remaining[0].lower() == 'in':
                remaining = remaining[1:]  # Skip 'in'
            specialization_text = ' '.join(word.capitalize() for word in remaining)
            processed_parts.append(f'({spec_type} in {specialization_text})')
            break
        elif part.lower() == 'secondary' and i + 1 < len(parts) and parts[i + 1].lower() == 'education':
            processed_parts.append('(Secondary Education)')
            break
        elif part.lower() in ['and', 'in', 'of', 'the']:
            # Keep common words lowercase
            processed_parts.append(part.lower())
        else:
            # Capitalize regular words
            processed_parts.append(part.capitalize())
    
    # Combine all parts
    human_name = ' '.join(processed_parts)
    
    # Add prefix if exists
    if prefix:
        human_name = f"{prefix} {human_name}"
    
    return human_name


def _find_fuzzy_matches(user_input: str, available_majors: List[Tuple[str, str]], threshold: float = 0.6) -> List[Tuple[str, str, float]]:
    """Find fuzzy matches for user input against available majors.
    
    Args:
        user_input: User's major input
        available_majors: List of (filename, human_readable_name) tuples
        threshold: Minimum similarity score (0-1)
        
    Returns:
        List of (filename, human_readable_name, similarity_score) tuples, sorted by score descending
    """
    matches = []
    user_input_lower = user_input.lower()
    
    for filename, human_name in available_majors:
        # Calculate similarity against both filename and human-readable name
        filename_similarity = difflib.SequenceMatcher(None, user_input_lower, filename.lower()).ratio()
        human_name_similarity = difflib.SequenceMatcher(None, user_input_lower, human_name.lower()).ratio()
        
        # Use the higher similarity score
        max_similarity = max(filename_similarity, human_name_similarity)
        
        # Also check for substring matches (boost score if user input is contained)
        if user_input_lower in filename.lower() or user_input_lower in human_name.lower():
            max_similarity = max(max_similarity, 0.8)
        
        # Check for keyword matches
        user_keywords = set(user_input_lower.replace('.', '').replace(':', '').split())
        name_keywords = set(human_name.lower().replace('.', '').replace(':', '').split())
        filename_keywords = set(filename.lower().replace('_', ' ').split())
        
        keyword_overlap_human = len(user_keywords.intersection(name_keywords)) / len(user_keywords) if user_keywords else 0
        keyword_overlap_filename = len(user_keywords.intersection(filename_keywords)) / len(user_keywords) if user_keywords else 0
        keyword_score = max(keyword_overlap_human, keyword_overlap_filename)
        
        # Combine similarity and keyword scores
        final_score = max(max_similarity, keyword_score * 0.9)
        
        if final_score >= threshold:
            matches.append((filename, human_name, final_score))
    
    # Sort by similarity score descending
    return sorted(matches, key=lambda x: x[2], reverse=True)


def _prompt_user_for_major_selection(matches: List[Tuple[str, str, float]], user_input: str) -> Optional[str]:
    """Prompt user to select from fuzzy matches.
    
    Args:
        matches: List of (filename, human_readable_name, similarity_score) tuples
        user_input: Original user input for context
        
    Returns:
        Selected filename or None if user cancels
    """
    print(f"\n🤔 Could not find exact match for '{user_input}'")
    print(f"📚 Found {len(matches)} similar majors. Please select one:")
    print()
    
    # Show top 10 matches max
    display_matches = matches[:10]
    
    for i, (filename, human_name, score) in enumerate(display_matches, 1):
        confidence = int(score * 100)
        print(f"  {i}. {human_name} ({confidence}% match)")
    
    print(f"  0. Cancel (none of these match)")
    print()
    
    while True:
        try:
            choice = input("👉 Enter your choice (0-{max_choice}): ".format(max_choice=len(display_matches)))
            choice_num = int(choice.strip())
            
            if choice_num == 0:
                print("❌ Operation cancelled by user")
                return None
            elif 1 <= choice_num <= len(display_matches):
                selected_filename, selected_human_name, _ = display_matches[choice_num - 1]
                print(f"✅ Selected: {selected_human_name}")
                return selected_filename
            else:
                print(f"❌ Please enter a number between 0 and {len(display_matches)}")
        except (ValueError, KeyboardInterrupt, EOFError):
            print("❌ Operation cancelled")
            return None


def _find_major_with_fuzzy_matching(target_major: str) -> str:
    """Find major file using fuzzy matching with user confirmation.
    
    Args:
        target_major: User's target major input
        
    Returns:
        Exact filename to use
        
    Raises:
        MajorNotFoundError: If no suitable major is found
        UserCancellationError: If user cancels the selection
    """
    # Step 1: Try exact slugification (original approach)
    slug = _slugify(target_major)
    exact_path = _DATA_ROOT / f"{slug}.json"
    
    if exact_path.exists():
        return slug
    
    # Step 2: Get all available majors
    available_majors = _get_available_majors()
    
    if not available_majors:
        raise MajorNotFoundError("No articulation data files found in the data directory")
    
    # Step 3: Find fuzzy matches
    matches = _find_fuzzy_matches(target_major, available_majors, threshold=0.4)
    
    if not matches:
        raise MajorNotFoundError(
            f"No similar majors found for '{target_major}'. "
            f"Available majors include: {', '.join([name for _, name in available_majors[:5]])}..."
        )
    
    # Step 4: If we have a very high confidence match (>0.95) that's clearly better than others, use it automatically
    if matches[0][2] > 0.95 and (len(matches) == 1 or matches[0][2] - matches[1][2] > 0.1):
        filename, human_name, score = matches[0]
        print(f"🎯 Auto-selected high-confidence match for '{target_major}': {human_name} ({int(score*100)}% match)")
        return filename
    
    # Step 5: Prompt user for selection
    selected_filename = _prompt_user_for_major_selection(matches, target_major)
    
    if selected_filename is None:
        raise UserCancellationError("User cancelled major selection")
    
    return selected_filename


# ---------------------------------------------------------------------------
# Main Tool Class
# ---------------------------------------------------------------------------


@dataclass
class ArticulationMatchTool:
    """
    StructuredTool – Compare a student's SMC courses against UCSD lower-division
    requirements for a given major and report satisfied / missing courses plus notes.
    """
    
    name: str = "articulation_match"
    description: str = (
        "Input: smc_courses (List[str]), target_major (str). "
        "Return JSON dict with keys: major, academic_year, satisfied, missing, notes."
    )

    def run(self, smc_courses: List[str], target_major: str) -> Dict[str, Any]:
        """Main entry point used by the agent."""
        
        # Load articulation data using fuzzy matching
        try:
            filename = _find_major_with_fuzzy_matching(target_major)
            file_path = _DATA_ROOT / f"{filename}.json"
        except UserCancellationError:
            raise MajorNotFoundError(f"User cancelled major selection for '{target_major}'")
        except MajorNotFoundError:
            # Re-raise with more context
            raise
        
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise MajorNotFoundError(f"Failed to load articulation data for '{target_major}': {e}")
        
        # Normalize student courses for fast lookup
        student_courses = {_canonical(course) for course in smc_courses}
        
        # Extract articulations and academic year
        articulations = _extract_articulations(data)
        academic_year = _extract_academic_year(data)
        
        satisfied = []
        missing = []
        notes = []
        
        # Process each articulation
        for articulation in articulations:
            ucsd_course = _extract_receiving_course(articulation)
            if not ucsd_course:
                continue
            
            sending_articulation = articulation.get("articulation", {}).get("sendingArticulation", {})
            
            # Check if there's no articulation available
            if _has_no_articulation(sending_articulation):
                missing.append(ucsd_course)
                continue
            
            # Parse required course combinations
            course_combinations = _parse_sending_courses(sending_articulation)
            
            if not course_combinations:
                missing.append(ucsd_course)
                continue
            
            # Check if any combination is satisfied
            requirement_satisfied = False
            satisfied_courses = []
            
            for combination in course_combinations:
                # Normalize combination courses
                normalized_combination = {_canonical(course) for course in combination}
                
                # Check if student has all courses in this combination
                if normalized_combination.issubset(student_courses):
                    requirement_satisfied = True
                    satisfied_courses = combination
                    break
            
            if requirement_satisfied:
                satisfied.append({
                    "ucsd_course": ucsd_course,
                    "smc_courses_used": satisfied_courses
                })
            else:
                missing.append(ucsd_course)
        
        # Handle special cases with AP/IB
        if any("AP" in course or "IB" in course for course in smc_courses):
            notes.append("AP/IB credit may satisfy additional requirements - consult with an advisor.")
        
        return {
            "major": target_major,
            "academic_year": academic_year,
            "satisfied": satisfied,
            "missing": missing,
            "notes": notes
        }


# ---------------------------------------------------------------------------
# LangChain Tool Registration
# ---------------------------------------------------------------------------


def _articulation_match_func(smc_courses: List[str], target_major: str, debug: bool = False) -> Dict[str, Any]:
    """Enhanced function wrapper for StructuredTool with improved logic and validation."""
    
    # Load articulation data using fuzzy matching
    try:
        filename = _find_major_with_fuzzy_matching(target_major)
        file_path = _DATA_ROOT / f"{filename}.json"
    except UserCancellationError:
        raise MajorNotFoundError(f"User cancelled major selection for '{target_major}'")
    except MajorNotFoundError:
        # Re-raise with more context
        raise
    
    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise MajorNotFoundError(f"Failed to load articulation data for '{target_major}': {e}")
    
    # Normalize student courses for fast lookup
    student_courses = {_canonical(course) for course in smc_courses}
    
    # Extract articulations and academic year
    articulations = _extract_articulations(data)
    academic_year = _extract_academic_year(data)
    
    satisfied = []
    missing = []
    notes = []
    debug_info = {}
    
    if debug:
        debug_info = _analyze_requirement_structure(data)
        debug_info["student_courses_normalized"] = list(student_courses)
        debug_info["processing_details"] = []
    
    # Process each articulation
    for articulation in articulations:
        ucsd_course = _extract_receiving_course(articulation)
        if not ucsd_course:
            continue
        
        sending_articulation = articulation.get("articulation", {}).get("sendingArticulation", {})
        
        # Debug tracking
        if debug:
            detail = {
                "ucsd_course": ucsd_course,
                "has_articulation": not _has_no_articulation(sending_articulation),
                "combinations_found": [],
                "satisfied": False
            }
        
        # Check if there's no articulation available
        if _has_no_articulation(sending_articulation):
            missing.append(ucsd_course)
            if debug:
                detail["reason"] = "No articulation available"
                debug_info["processing_details"].append(detail)
            continue
        
        # Parse required course combinations with enhanced logic
        course_combinations = _parse_sending_courses(sending_articulation)
        
        if debug:
            detail["combinations_found"] = course_combinations
        
        if not course_combinations:
            missing.append(ucsd_course)
            if debug:
                detail["reason"] = "No valid course combinations parsed"
                debug_info["processing_details"].append(detail)
            continue
        
        # Check if any combination is satisfied
        requirement_satisfied = False
        satisfied_courses = []
        best_match = None  # Track the best partial match for debugging
        
        for combination in course_combinations:
            # Normalize combination courses
            normalized_combination = {_canonical(course) for course in combination}
            
            # Check if student has all courses in this combination
            if normalized_combination.issubset(student_courses):
                requirement_satisfied = True
                satisfied_courses = combination
                break
            elif debug:
                # Track partial matches for debugging
                intersection = normalized_combination.intersection(student_courses)
                if len(intersection) > 0:
                    if best_match is None or len(intersection) > len(best_match["matched"]):
                        best_match = {
                            "combination": combination,
                            "matched": list(intersection),
                            "missing": list(normalized_combination - student_courses)
                        }
        
        if requirement_satisfied:
            satisfied.append({
                "ucsd_course": ucsd_course,
                "smc_courses_used": satisfied_courses
            })
            if debug:
                detail["satisfied"] = True
                detail["courses_used"] = satisfied_courses
        else:
            missing.append(ucsd_course)
            if debug:
                detail["reason"] = "No combination fully satisfied"
                if best_match:
                    detail["best_partial_match"] = best_match
        
        if debug:
            debug_info["processing_details"].append(detail)
    
    # Handle special cases with AP/IB
    if any("AP" in course or "IB" in course for course in smc_courses):
        notes.append("AP/IB credit may satisfy additional requirements - consult with an advisor.")
    
    # Validate result consistency
    if debug:
        consistency_warnings = _validate_result_consistency({
            "satisfied": satisfied,
            "missing": missing
        }, student_courses)
        if consistency_warnings:
            notes.extend([f"⚠️ {warning}" for warning in consistency_warnings])
    
    result = {
        "major": target_major,
        "academic_year": academic_year,
        "satisfied": satisfied,
        "missing": missing,
        "notes": notes
    }
    
    if debug:
        result["debug_info"] = debug_info
    
    return result


# Create the StructuredTool instance following the same pattern as other tools
ArticulationMatchTool = StructuredTool.from_function(
    func=_articulation_match_func,
    name="articulation_match",
    description=(
        "Compare completed SMC courses against UCSD major requirements. "
        "Input: smc_courses (list of course codes), target_major (major name). "
        "Returns satisfied requirements, missing requirements, and notes."
    ),
    args_schema=AMIn,
    return_schema=AMOut,
)

# Add return_schema attribute using the same approach as CourseDetailTool
object.__setattr__(ArticulationMatchTool, "return_schema", AMOut)


# ---------------------------------------------------------------------------
# Demo Main Function
# ---------------------------------------------------------------------------


def demo_main():
    """Demo function to showcase ArticulationMatchTool capabilities."""
    print("🚀 ArticulationMatchTool Demo")
    print("=" * 60)
    
    # Test scenarios
    scenarios = [
        {
            "name": "Beginning Student",
            "courses": ["CS 55", "MATH 7", "MATH 8"],
            "description": "Basic programming + calculus sequence"
        },
        {
            "name": "AND Logic Test",
            "courses": ["CS 20A", "CS 20B"],
            "description": "Should satisfy CSE 12 (requires BOTH courses)"
        },
        {
            "name": "Incomplete AND",
            "courses": ["CS 20A"],
            "description": "Should NOT satisfy CSE 12 (missing CS 20B)"
        },
        {
            "name": "Transfer Ready",
            "courses": [
                "CS 55", "CS 20A", "CS 20B", "CS 17",
                "MATH 7", "MATH 8", "MATH 11", "MATH 13", "MATH 10",
                "PHYSCS 21", "PHYSCS 22", "CHEM 11", "CHEM 12"
            ],
            "description": "Comprehensive coursework"
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print(f"   {scenario['description']}")
        print(f"   Courses: {', '.join(scenario['courses'])}")
        
        try:
            result = ArticulationMatchTool.invoke({
                "smc_courses": scenario["courses"],
                "target_major": "CSE: Computer Science B.S."
            })
            
            print(f"   ✅ Satisfied: {len(result['satisfied'])} requirements")
            if result['satisfied']:
                for req in result['satisfied'][:3]:  # Show first 3
                    courses_used = " + ".join(req['smc_courses_used'])
                    print(f"      • {req['ucsd_course']} ← {courses_used}")
                if len(result['satisfied']) > 3:
                    print(f"      ... and {len(result['satisfied']) - 3} more")
            
            print(f"   ❌ Missing: {len(result['missing'])} requirements")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Demo complete! Tool successfully handles AND/OR logic.")


if __name__ == "__main__":
    demo_main()
