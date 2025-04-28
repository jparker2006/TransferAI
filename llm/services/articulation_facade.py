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
