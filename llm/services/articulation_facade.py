"""
TransferAI Articulation Facade

This module provides a unified interface to the articulation package functionality.
It implements the Facade pattern to simplify access to the various articulation components.
"""

from typing import Dict, List, Any, Optional, Union
from llama_index_client import Document


class ArticulationFacade:
    """
    Provides a unified interface to articulation functionality.
    
    This facade simplifies access to the articulation package by providing
    high-level methods that coordinate the various components.
    """
    
    def validate_courses(self, logic_block: Dict[str, Any], courses: List[str]) -> Dict[str, Any]:
        """
        Validate if courses satisfy articulation requirements.
        
        Args:
            logic_block: The articulation logic block to validate against
            courses: List of course codes to validate
            
        Returns:
            Dictionary containing validation results
        """
        from llm.articulation.validators import is_articulation_satisfied
        return is_articulation_satisfied(logic_block, courses)
    
    def render_articulation_logic(self, metadata: Dict[str, Any], verbosity: str = "STANDARD") -> str:
        """
        Render articulation logic in human-readable format.
        
        Args:
            metadata: Document metadata containing logic blocks
            verbosity: Verbosity level (CONCISE, STANDARD, DETAILED)
            
        Returns:
            Human-readable string representation of the articulation logic
        """
        from llm.articulation.renderers import render_logic_str
        return render_logic_str(metadata, verbosity)
    
    def format_binary_response(self, is_satisfied: bool, explanation: str, uc_course: str = "") -> str:
        """
        Format a binary (yes/no) response.
        
        Args:
            is_satisfied: Whether the requirement is satisfied
            explanation: Explanation of the result
            uc_course: Optional UC course code for context
            
        Returns:
            Formatted response string
        """
        from llm.articulation.formatters import render_binary_response
        return render_binary_response(is_satisfied, explanation, uc_course)
    
    def count_uc_matches(self, ccc_course: str, docs: List[Document]) -> tuple:
        """
        Count UC courses matched by a CCC course.
        
        Args:
            ccc_course: The CCC course code to analyze
            docs: List of articulation documents to search
            
        Returns:
            Tuple containing count of direct matches, list of direct matches,
            and list of contribution matches
        """
        from llm.articulation.analyzers import count_uc_matches
        return count_uc_matches(ccc_course, docs)
    
    def extract_honors_info(self, logic_block: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract honors course information from a logic block.
        
        Args:
            logic_block: Logic block to analyze
            
        Returns:
            Dictionary with honors and non-honors course lists
        """
        from llm.articulation.analyzers import extract_honors_info_from_logic
        return extract_honors_info_from_logic(logic_block)
    
    def is_honors_required(self, logic_block: Dict[str, Any]) -> bool:
        """
        Check if honors courses are required by the logic block.
        
        Args:
            logic_block: Logic block to check
            
        Returns:
            True if honors courses are required, False otherwise
        """
        from llm.articulation.detectors import is_honors_required
        return is_honors_required(logic_block)
        
    def render_group_summary(self, docs: List[Document]) -> str:
        """
        Render a summary of a group of articulation documents.
        
        Args:
            docs: List of articulation documents in the same group
            
        Returns:
            A rendered summary of the group requirements
        """
        from llm.articulation import render_group_summary
        return render_group_summary(docs)
        
    def validate_combo_against_group(self, courses: List[str], group_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a combination of courses against a group requirement.
        
        Args:
            courses: List of course codes to validate
            group_dict: Group requirement dictionary structure
            
        Returns:
            Validation results including whether requirements are satisfied
        """
        from llm.articulation import validate_combo_against_group
        return validate_combo_against_group(courses, group_dict)
        
    def is_honors_pair_equivalent(self, logic_block: Dict[str, Any], course1: str, course2: str) -> bool:
        """
        Check if two courses form an honors/non-honors equivalent pair.
        
        Args:
            logic_block: The articulation logic block to check against
            course1: First course code
            course2: Second course code
            
        Returns:
            True if the courses form an honors/non-honors pair, False otherwise
        """
        from llm.articulation import is_honors_pair_equivalent
        return is_honors_pair_equivalent(logic_block, course1, course2)
        
    def explain_honors_equivalence(self, course1: str, course2: str) -> str:
        """
        Generate explanation text for honors course equivalence.
        
        Args:
            course1: First course code
            course2: Second course code
            
        Returns:
            Formatted explanation of honors equivalence
        """
        from llm.articulation import explain_honors_equivalence
        return explain_honors_equivalence(course1, course2)

    def get_articulation_options(self, logic_block: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract articulation options from a logic block.
        
        Args:
            logic_block: The logic block containing articulation data
            
        Returns:
            Dictionary with articulation options information
        """
        if not logic_block or not isinstance(logic_block, dict):
            return {"options": []}
        
        # Check if the logic block is marked as having no articulation
        if logic_block.get("no_articulation", False):
            return {"options": []}
            
        result = {"options": []}
        
        # Handle two different format types:
        # 1. If logic_block has "options" key directly, use that format
        # 2. If logic_block has "type"/"courses" keys (standard OR/AND structure), convert it
        
        if "options" in logic_block:
            # Format 1: Direct options format
            options = logic_block.get("options", [])
            
            for option in options:
                option_data = {"courses": []}
                courses = option.get("courses", [])
                
                for course in courses:
                    if isinstance(course, list):  # AND group
                        and_group = []
                        for c in course:
                            # Get the full course name without description
                            full_name = c.get("name", "")
                            course_name = full_name.split(" ", 1)[0] if " " in full_name else full_name
                            is_honors = c.get("is_honors", False)
                            and_group.append({
                                "name": course_name,
                                "is_honors": is_honors
                            })
                        option_data["courses"].append({
                            "type": "AND",
                            "courses": and_group
                        })
                    elif isinstance(course, dict):  # Single course
                        # Get the full course name without description
                        full_name = course.get("name", "")
                        course_name = full_name.split(" ", 1)[0] if " " in full_name else full_name
                        is_honors = course.get("is_honors", False)
                        option_data["courses"].append({
                            "name": course_name,
                            "is_honors": is_honors
                        })
                
                result["options"].append(option_data)
                
        elif "type" in logic_block and logic_block["type"] == "OR":
            # Format 2: Standard OR/AND nested format
            
            # Each AND block in the OR block becomes an option
            for and_block in logic_block.get("courses", []):
                if isinstance(and_block, dict) and and_block.get("type") == "AND":
                    option_data = {"courses": []}
                    
                    # Process courses in the AND block
                    course_list = and_block.get("courses", [])
                    
                    if len(course_list) > 1:
                        # Multiple courses in AND relationship
                        and_group = []
                        for course in course_list:
                            # Extract course details
                            if isinstance(course, dict):
                                # First try to get the course_letters field (this is the correct code)
                                course_name = course.get("course_letters", "")
                                if not course_name:
                                    # If not available, fall back to the name field
                                    full_name = course.get("name", "")
                                    course_name = full_name.split(" ", 1)[0] if " " in full_name else full_name
                                
                                is_honors = course.get("honors", False)
                                and_group.append({
                                    "name": course_name,
                                    "is_honors": is_honors
                                })
                        
                        if and_group:
                            option_data["courses"].append({
                                "type": "AND",
                                "courses": and_group
                            })
                    else:
                        # Single course in AND block
                        for course in course_list:
                            if isinstance(course, dict):
                                # First try to get the course_letters field (this is the correct code)
                                course_name = course.get("course_letters", "")
                                if not course_name:
                                    # If not available, fall back to the name field
                                    full_name = course.get("name", "")
                                    course_name = full_name.split(" ", 1)[0] if " " in full_name else full_name
                                
                                is_honors = course.get("honors", False)
                                option_data["courses"].append({
                                    "name": course_name,
                                    "is_honors": is_honors
                                })
                    
                    # Add the option only if it has courses
                    if option_data["courses"]:
                        result["options"].append(option_data)
        
        return result

    def format_course_options(self, uc_course: str, articulation_info: Dict[str, Any]) -> str:
        """
        Format articulation options into a human-readable response.
        
        Args:
            uc_course: The UC course code
            articulation_info: Articulation information from get_articulation_options
            
        Returns:
            Formatted response string
        """
        options = articulation_info.get("options", [])
        
        if not options:
            return f"# No articulation for {uc_course}\n\nAccording to the articulation agreement, there are no courses that satisfy {uc_course}."
        
        # Format each option
        option_texts = []
        for i, option in enumerate(options):
            option_letter = chr(65 + i)  # A, B, C, etc.
            
            # Process the courses in this option
            course_descriptions = []
            courses = option.get("courses", [])
            
            for course_item in courses:
                if isinstance(course_item, dict) and course_item.get("type") == "AND":
                    # Handle AND group
                    and_courses = course_item.get("courses", [])
                    course_names = []
                    for course in and_courses:
                        name = course.get("name", "")
                        is_honors = course.get("is_honors", False)
                        if is_honors:
                            name += " (Honors)"
                        course_names.append(name)
                    course_descriptions.append(f"{', '.join(course_names)} (complete all)")
                else:
                    # Handle single course
                    name = course_item.get("name", "")
                    is_honors = course_item.get("is_honors", False)
                    if is_honors:
                        name += " (Honors)"
                    course_descriptions.append(name)
            
            if len(course_descriptions) == 1:
                option_texts.append(f"**Option {option_letter}**: {course_descriptions[0]}")
            else:
                option_texts.append(f"**Option {option_letter}**: {'; '.join(course_descriptions)}")
        
        options_text = "\n".join(option_texts)
        if len(options) == 1:
            return f"# {uc_course} can be satisfied by:\n\n{options_text}"
        else:
            return f"# {uc_course} can be satisfied by any of these options:\n\n{options_text}"