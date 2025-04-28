"""
Prompt Service for TransferAI

This service handles the selection, preparation, and rendering of prompt templates for
different types of queries in the TransferAI system.

It provides:
- Template selection based on query type
- Context preparation for template rendering
- Rendering of templates with appropriate data
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, Union, List

from ..models.query import Query, QueryType
from ..templates import (
    COURSE_TEMPLATES,
    NO_ARTICULATION_TEMPLATES,
    GROUP_TEMPLATES,
    LOGIC_TYPE_EXPLANATIONS,
    prepare_course_context,
    prepare_group_context,
    enrich_with_descriptions
)

class VerbosityLevel(Enum):
    """
    Enumeration of verbosity levels for controlling response length and detail.
    
    MINIMAL: Brief, direct responses with minimal explanation
    STANDARD: Balanced responses with moderate explanation
    DETAILED: Thorough responses with extensive explanation
    """
    MINIMAL = auto()
    STANDARD = auto()
    DETAILED = auto()


class PromptType(Enum):
    """
    Enumeration of prompt types supported by the prompt builder.
    
    COURSE_EQUIVALENCY: For queries about specific UC courses and their equivalents
    GROUP_LOGIC: For queries about groups of courses and their requirements
    """
    COURSE_EQUIVALENCY = "course_equivalency"
    GROUP_LOGIC = "group_logic"


class PromptService:
    """
    Service for building and rendering prompt templates based on query type and context.
    
    This service handles template selection, context preparation, and rendering for
    different types of TransferAI queries.
    """
    
    def __init__(self, verbosity: Union[VerbosityLevel, str] = VerbosityLevel.STANDARD):
        """
        Initialize the prompt service.
        
        Args:
            verbosity: The verbosity level for prompt responses.
        """
        self.verbosity = self._normalize_verbosity(verbosity)
    
    def _normalize_verbosity(self, verbosity: Union[VerbosityLevel, str]) -> VerbosityLevel:
        """
        Convert string verbosity to enum if needed and validate.
        
        Args:
            verbosity: The verbosity level as an enum or string.
            
        Returns:
            Normalized VerbosityLevel enum.
        """
        if isinstance(verbosity, str):
            try:
                return VerbosityLevel[verbosity.upper()]
            except KeyError:
                return VerbosityLevel.STANDARD
        elif isinstance(verbosity, VerbosityLevel):
            return verbosity
        else:
            return VerbosityLevel.STANDARD
    
    def set_verbosity(self, verbosity: Union[VerbosityLevel, str]) -> None:
        """
        Update the verbosity level.
        
        Args:
            verbosity: The new verbosity level.
        """
        self.verbosity = self._normalize_verbosity(verbosity)
    
    def get_verbosity_key(self) -> str:
        """
        Get the verbosity key for template selection.
        
        Returns:
            The verbosity key as a string.
        """
        return self.verbosity.name
    
    def build_prompt(
        self,
        prompt_type: Union[PromptType, str],
        user_question: str,
        rendered_logic: str,
        **kwargs
    ) -> str:
        """
        Build a prompt based on the prompt type and context.
        
        Args:
            prompt_type: The type of prompt to build.
            user_question: The user's question.
            rendered_logic: The rendered articulation logic.
            **kwargs: Additional context variables.
            
        Returns:
            The rendered prompt template.
        """
        # Normalize prompt type
        if isinstance(prompt_type, str):
            try:
                prompt_type = PromptType(prompt_type.lower())
            except ValueError:
                prompt_type = PromptType.COURSE_EQUIVALENCY
        
        # Get the appropriate template and prepare context
        if prompt_type == PromptType.GROUP_LOGIC:
            return self._build_group_prompt(user_question, rendered_logic, **kwargs)
        else:
            return self._build_course_prompt(user_question, rendered_logic, **kwargs)
    
    def _build_course_prompt(
        self,
        user_question: str,
        rendered_logic: str,
        uc_course: str = "Unknown",
        uc_course_title: str = "",
        is_no_articulation: bool = False,
        **kwargs
    ) -> str:
        """
        Build a course-specific prompt.
        
        Args:
            user_question: The user's question.
            rendered_logic: The rendered articulation logic.
            uc_course: The UC course code.
            uc_course_title: The UC course title.
            is_no_articulation: Whether the course has no articulation.
            **kwargs: Additional context variables.
            
        Returns:
            The rendered course prompt.
        """
        # Select template based on articulation status
        template_dict = NO_ARTICULATION_TEMPLATES if is_no_articulation else COURSE_TEMPLATES
        
        # Prepare context
        context = prepare_course_context(
            rendered_logic=rendered_logic,
            user_question=user_question,
            uc_course=uc_course,
            uc_course_title=uc_course_title,
            is_no_articulation=is_no_articulation,
            **kwargs
        )
        
        # Get template based on verbosity
        template = template_dict.get(self.get_verbosity_key(), template_dict["STANDARD"])
        
        # Render template
        return template.format(**context)
    
    def _build_group_prompt(
        self,
        user_question: str,
        rendered_logic: str,
        group_id: str = "Unknown",
        group_title: str = "",
        group_logic_type: str = "",
        n_courses: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Build a group-specific prompt.
        
        Args:
            user_question: The user's question.
            rendered_logic: The rendered articulation logic.
            group_id: The group ID.
            group_title: The group title.
            group_logic_type: The group logic type.
            n_courses: The number of courses required (for select_n_courses).
            **kwargs: Additional context variables.
            
        Returns:
            The rendered group prompt.
        """
        # Prepare context
        context = prepare_group_context(
            rendered_logic=rendered_logic,
            user_question=user_question,
            group_id=group_id,
            group_title=group_title,
            group_logic_type=group_logic_type,
            n_courses=n_courses,
            **kwargs
        )
        
        # Get template based on verbosity
        template = GROUP_TEMPLATES.get(self.get_verbosity_key(), GROUP_TEMPLATES["STANDARD"])
        
        # Render template
        return template.format(**context)


# Backward compatibility function to support existing code
def build_prompt(
    logic: str,
    user_question: str,
    uc_course: str = "Unknown",
    prompt_type: Union[PromptType, str] = PromptType.COURSE_EQUIVALENCY,
    uc_course_title: str = "",
    group_id: str = "",
    group_title: str = "",
    group_logic_type: str = "",
    section_title: str = "",
    n_courses: Optional[int] = None,
    rendered_logic: str = "",
    verbosity: Union[VerbosityLevel, str] = VerbosityLevel.STANDARD,
) -> str:
    """
    Backward compatibility function for building prompts.
    
    Args:
        logic: String representation of the articulation logic.
        user_question: The original user query.
        uc_course: UC course code.
        prompt_type: Type of prompt to build.
        uc_course_title: Title of the UC course.
        group_id: Group identifier if applicable.
        group_title: Group title if applicable.
        group_logic_type: Type of logic for the group.
        section_title: Section title if applicable.
        n_courses: Number of courses required (for select_n_courses type).
        rendered_logic: Alternative rendered logic string (used for group prompts).
        verbosity: The desired level of detail in responses.
        
    Returns:
        A formatted prompt string for the LLM.
    """
    # Create a prompt service instance with the specified verbosity
    service = PromptService(verbosity=verbosity)
    
    # Use the rendered_logic if provided, otherwise fall back to logic
    logic_text = rendered_logic if rendered_logic else logic
    
    # Build the prompt using the service
    return service.build_prompt(
        prompt_type=prompt_type,
        user_question=user_question,
        rendered_logic=logic_text,
        uc_course=uc_course,
        uc_course_title=uc_course_title,
        group_id=group_id,
        group_title=group_title,
        group_logic_type=group_logic_type,
        section_title=section_title,
        n_courses=n_courses,
        is_no_articulation=("This course must be completed at UCSD" in logic_text)
    )
