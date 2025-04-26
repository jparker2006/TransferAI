"""
TransferAI Articulation Data Models

This module defines the core data models used throughout the TransferAI articulation system.
All models use Pydantic for validation and serialization.
"""

from typing import List, Dict, Optional, Union, Set, Any, Tuple
from pydantic import BaseModel, Field, validator
from enum import Enum


class LogicType(str, Enum):
    """Logic types for articulation blocks"""
    AND = "AND"
    OR = "OR"


class Course(BaseModel):
    """
    Represents a single course in the articulation system.
    
    Attributes:
        code: The course code (e.g., "CIS 22A")
        title: Optional course title
        is_honors: Whether this is an honors course
        units: Optional number of credit units
    """
    code: str
    title: Optional[str] = None
    is_honors: bool = False
    units: Optional[float] = None
    
    @validator('code')
    def validate_code(cls, v):
        """Ensure course code is properly formatted"""
        if not v or not isinstance(v, str):
            raise ValueError('Course code must be a non-empty string')
        return v.strip().upper()


class CourseOption(BaseModel):
    """
    Represents a single course or course component in a logic block.
    
    Attributes:
        course_letters: The course code letters
        honors: Whether this is an honors course
    """
    course_letters: str
    honors: bool = False


class LogicBlock(BaseModel):
    """
    Represents an articulation logic block, which can be a single course
    or a combination of courses with AND/OR logic.
    
    Attributes:
        type: The logic type (AND or OR)
        courses: List of courses or nested logic blocks
        no_articulation: Whether this block has no articulation
    """
    type: LogicType = LogicType.OR
    courses: List[Union['LogicBlock', CourseOption, Dict[str, Any]]] = []
    no_articulation: bool = False
    
    class Config:
        """Pydantic config"""
        arbitrary_types_allowed = True


class ArticulationLogic(BaseModel):
    """
    Top-level articulation logic definition.
    
    Attributes:
        uc_course: The UC course code
        logic_block: The logic block representing articulation requirements
        no_articulation: Whether this course has no articulation
    """
    uc_course: str
    logic_block: LogicBlock
    no_articulation: bool = False


class ValidationResult(BaseModel):
    """
    Result of validating selected courses against an articulation logic block.
    
    Attributes:
        satisfied: Whether the requirements are satisfied
        missing_courses: List of missing courses (if not satisfied)
        satisfied_paths: List of paths that were satisfied
        partial_match: Whether there's a partial match
        match_percentage: Percentage of requirements satisfied (0.0 to 1.0)
        honors_required: Whether honors courses are required
        redundant_courses: List of redundant courses in the selection
    """
    satisfied: bool = False
    missing_courses: List[str] = []
    satisfied_paths: List[List[str]] = []
    partial_match: bool = False
    match_percentage: float = 0.0
    honors_required: bool = False
    redundant_courses: List[str] = []
    
    @validator('match_percentage')
    def validate_percentage(cls, v):
        """Ensure percentage is between 0 and 1"""
        if v < 0 or v > 1:
            raise ValueError('Match percentage must be between 0 and 1')
        return v


class GroupValidationResult(BaseModel):
    """
    Result of validating selected courses against a group of requirements.
    
    Attributes:
        is_fully_satisfied: Whether all requirements are satisfied
        satisfied_section_id: ID of the satisfied section (if any)
        missing_uc_courses: List of missing UC courses
        validated_courses: Dict mapping UC courses to their validation results
    """
    is_fully_satisfied: bool = False
    satisfied_section_id: Optional[str] = None
    missing_uc_courses: List[str] = []
    validated_courses: Dict[str, ValidationResult] = {}
