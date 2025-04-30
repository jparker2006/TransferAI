"""
TransferAI Query Models

This module defines the data structures used for representing queries and query results
throughout the TransferAI system.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Any, Optional


class QueryType(Enum):
    """Enum defining the types of queries supported by the system."""
    COURSE_EQUIVALENCY = auto()  # What UC courses does CCC course X satisfy?
    COURSE_VALIDATION = auto()   # Does CCC course X satisfy UC course Y?
    GROUP_REQUIREMENT = auto()   # What courses satisfy requirement group Z?
    HONORS_REQUIREMENT = auto()  # Is an honors course required?
    COURSE_LOOKUP = auto()       # Which courses satisfy UC course Y?
    COURSE_COMPARISON = auto()   # Does course X require the same as course Y?
    PATH_COMPLETION = auto()     # Does X and Y complete a requirement path?
    UNKNOWN = auto()             # Fallback for unclassified queries


@dataclass
class Query:
    """
    Structured representation of a user query.
    
    Contains the original query text, extracted filters, configuration options,
    and the classified query type.
    """
    text: str
    filters: Dict[str, Any]
    config: Dict[str, Any]
    query_type: QueryType = QueryType.UNKNOWN
    
    @property
    def verbosity(self) -> str:
        """Get the verbosity level from config."""
        return self.config.get("verbosity", "STANDARD")
    
    @property
    def uc_courses(self) -> List[str]:
        """Get UC courses from filters."""
        return self.filters.get("uc_course", [])
    
    @property
    def ccc_courses(self) -> List[str]:
        """Get CCC courses from filters."""
        return self.filters.get("ccc_courses", [])
    
    @property
    def groups(self) -> List[str]:
        """Get groups from filters."""
        return self.filters.get("group", [])


@dataclass
class QueryResult:
    """
    Result of processing a query.
    
    Contains the raw and formatted responses, satisfaction status, matched documents,
    and additional metadata about the processing.
    """
    raw_response: str
    formatted_response: str
    satisfied: Optional[bool] = None
    matched_docs: List[Any] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
