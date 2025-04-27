"""
TransferAI Articulation Package - Models

This module defines the data models for the articulation package using Pydantic.
It provides type-safe data structures for representing articulation logic, course options,
and validation results.

Key Classes:
- CourseOption: Represents a specific course option in articulation logic
- LogicBlock: Represents a logical structure (AND/OR) with nested courses or blocks
- ValidationResult: Stores the result of validating selected courses against requirements

These models enable type validation, serialization/deserialization, and structured
data manipulation throughout the articulation package.

This is part of the v1.5 refactoring from the monolithic logic_formatter.py
into a modular architecture with clearly defined responsibilities.
"""

from pydantic import BaseModel, Field, root_validator
from typing import List, Dict, Optional, Union, Literal, Set, Any
from enum import Enum


class CourseOption(BaseModel):
    """
    Represents a single course option within articulation logic.
    
    This model represents a specific course that can be used to satisfy
    a requirement, including metadata about the course.
    
    Attributes:
        course_letters: The course code (e.g., "CIS 22A")
        title: Optional course title
        honors: Whether this is an honors course
        course_id: Optional unique identifier for the course
    """
    course_letters: str
    title: Optional[str] = None
    honors: bool = False
    course_id: Optional[str] = None


class LogicBlock(BaseModel):
    """
    Represents a nested logic structure with AND/OR combinations.
    
    This model represents the core articulation logic structure, which can
    be nested to represent complex requirements. For example:
    - OR block: Take MATH 1A OR MATH 1AH
    - AND block: Take BOTH MATH 1A AND MATH 1B
    - Nested: Take (MATH 1A AND MATH 1B) OR (MATH 1AH AND MATH 1BH)
    
    Attributes:
        type: The logic type, either "AND" or "OR"
        courses: List of nested LogicBlocks or CourseOptions
        no_articulation: Flag indicating if no articulation is available
    """
    type: Literal["AND", "OR"]
    courses: List[Union["LogicBlock", CourseOption, Dict[str, Any]]]
    no_articulation: bool = False
    
    class Config:
        arbitrary_types_allowed = True


class ValidationResult(BaseModel):
    """
    Result of articulation validation with explanation.
    
    This model encapsulates the result of validating whether a set of
    selected courses satisfies an articulation requirement, including
    a detailed explanation of the result.
    
    Attributes:
        satisfied: Whether the requirement is satisfied
        explanation: Human-readable explanation of the result
        satisfied_by: Set of courses that contribute to satisfying the requirement
        missing_requirements: List of requirements that are not satisfied
    """
    satisfied: bool
    explanation: str
    satisfied_by: Set[str] = Field(default_factory=set)
    missing_requirements: List[str] = Field(default_factory=list)


class GroupLogicType(str, Enum):
    """
    Enumeration of group logic types from ASSIST articulation data.
    
    These represent the different ways that courses can be combined
    to satisfy group-level requirements.
    """
    CHOOSE_ONE_SECTION = "choose_one_section"
    ALL_REQUIRED = "all_required"
    SELECT_N_COURSES = "select_n_courses"


class GroupSection(BaseModel):
    """
    Represents a section within a group of requirements.
    
    Sections are used to organize related courses within a group,
    such as different science disciplines within a science requirement.
    
    Attributes:
        section_id: Identifier for the section (e.g., "A", "B")
        section_title: Human-readable title for the section
        uc_courses: List of UC courses in this section
    """
    section_id: str
    section_title: Optional[str] = None
    uc_courses: List[Dict[str, Any]] = Field(default_factory=list)


class ArticulationGroup(BaseModel):
    """
    Represents a group of related articulation requirements.
    
    Groups are the highest level of organization in articulation requirements,
    containing sections which in turn contain courses.
    
    Attributes:
        group_id: Identifier for the group (e.g., "1", "2")
        group_title: Human-readable title for the group
        group_logic_type: Logic type for the group
        sections: List of sections within the group
        n_courses: For SELECT_N_COURSES type, the number of courses to select
    """
    group_id: str
    group_title: Optional[str] = None
    group_logic_type: GroupLogicType
    sections: List[GroupSection] = Field(default_factory=list)
    n_courses: Optional[int] = None
    
    @root_validator(skip_on_failure=True)
    def validate_n_courses(cls, values):
        """Ensure n_courses is set for SELECT_N_COURSES type."""
        if (values.get('group_logic_type') == GroupLogicType.SELECT_N_COURSES and 
            values.get('n_courses') is None):
            raise ValueError("n_courses must be set for SELECT_N_COURSES type")
        return values