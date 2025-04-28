"""
TransferAI Group Query Handler

This module implements the handler for group requirement queries. These queries
ask about course requirements for UC articulation groups, including validating
if a set of CCC courses satisfies group requirements.
"""

from typing import Optional, Dict, Any, List
from collections import defaultdict
import json

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade
from llm.services.query_service import QueryService


class GroupQueryHandler(QueryHandler):
    """
    Handler for group requirement queries.
    
    These are queries that ask about group requirements or validate if a set of
    CCC courses satisfies a specific group's requirements, such as:
    - "What are the requirements for Group 1?"
    - "Do CIS 22A and MATH 1A satisfy Group 1?"
    """
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the group query handler.
        
        Args:
            document_repository: Repository for accessing articulation documents
            config: Configuration options for the handler
        """
        super().__init__(document_repository, config)
        self.matching_service = MatchingService()
        self.articulation_facade = ArticulationFacade()
        self.query_service = QueryService()
    
    def can_handle(self, query: Query) -> bool:
        """
        Determine if this handler can process the query.
        
        This handler can process queries that:
        1. Have an explicit GROUP_REQUIREMENT query type
        2. Mention group IDs or contain group-related keywords
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        # Check if query type has been explicitly set
        if query.query_type == QueryType.GROUP_REQUIREMENT:
            return True
            
        # Check for group mentions (e.g., "Group 1", "Group 2")
        if query.groups and len(query.groups) > 0:
            return True
            
        # Check for group-related keywords
        group_keywords = [
            "group requirements", "group", "requirement group", 
            "course requirements", "prerequisites"
        ]
        
        if any(keyword in query.text.lower() for keyword in group_keywords):
            # Only handle if not explicitly another type and no UC course mentioned
            # (those would likely be course-specific queries, not group-level)
            return not (query.query_type != QueryType.UNKNOWN or query.uc_courses)
            
        return False
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process a group requirement query and return results.
        
        This handler processes two types of queries:
        1. Queries about what courses are in a group
        2. Queries about whether specific CCC courses satisfy a group
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing group information or validation results
        """
        # Get all documents
        all_documents = self.document_repository.get_all_documents()
        
        # Find documents matching the group ID (from query or extracted)
        group_id = query.groups[0] if query.groups and len(query.groups) > 0 else None
        
        # If no explicit group ID, try to extract it from the query text
        if not group_id:
            # Look for patterns like "Group 1", "Group 2", etc.
            import re
            group_match = re.search(r"group\s+(\d+)", query.text.lower())
            if group_match:
                group_id = group_match.group(1)
        
        if not group_id:
            return QueryResult(
                raw_response="Could not process group query - no group specified.",
                formatted_response="Please specify which group you want to know about. For example, 'What are the requirements for Group 1?'"
            )
        
        # Find all documents for this group
        group_docs = [
            doc for doc in all_documents 
            if doc.metadata.get("group") == group_id
        ]
        
        if not group_docs:
            return QueryResult(
                raw_response=f"No information found for Group {group_id}.",
                formatted_response=f"I couldn't find any information about Group {group_id}."
            )
        
        # Get group metadata from the first document
        group_title = group_docs[0].metadata.get("group_title", f"Group {group_id}")
        group_type = group_docs[0].metadata.get("group_logic_type", "ALL_REQUIRED")
        n_courses = group_docs[0].metadata.get("n_courses")
        
        # Case 1: Validating CCC courses against group requirements
        if query.ccc_courses:
            return self._handle_group_validation(
                query, group_docs, group_id, group_title, group_type, n_courses
            )
        
        # Case 2: General information about the group
        return self._handle_group_info(
            query, group_docs, group_id, group_title, group_type, n_courses
        )
    
    def _handle_group_validation(
        self, 
        query: Query, 
        group_docs: List[Any],
        group_id: str,
        group_title: str,
        group_type: str,
        n_courses: Optional[int]
    ) -> QueryResult:
        """
        Handle validation of CCC courses against group requirements.
        
        Args:
            query: The original query
            group_docs: Documents for the specified group
            group_id: Group identifier
            group_title: Human-readable group title
            group_type: Logic type for the group (ALL_REQUIRED, SELECT_N_COURSES, etc.)
            n_courses: Number of courses required (for SELECT_N_COURSES type)
            
        Returns:
            QueryResult with validation information
        """
        # Group documents by section
        sections_by_id = defaultdict(list)
        for doc in group_docs:
            section_id = doc.metadata.get("section", "default")
            sections_by_id[section_id].append(doc)
        
        # Build group dictionary for validation
        group_dict = {
            "logic_type": group_type,
            "n_courses": n_courses,
            "sections": []
        }
        
        # Add each section to the group dictionary
        for section_id, docs_in_section in sections_by_id.items():
            section_dict = {
                "section_id": section_id,
                "section_title": docs_in_section[0].metadata.get("section_title", f"Section {section_id}"),
                "uc_courses": []
            }
            
            # Add each UC course in this section
            for doc in docs_in_section:
                logic_block = doc.metadata.get("logic_block", {})
                
                # Handle different formats of logic_block
                if isinstance(logic_block, str):
                    try:
                        logic_block = json.loads(logic_block)
                    except json.JSONDecodeError:
                        print(f"Could not parse logic_block for {doc.metadata.get('uc_course')}")
                        logic_block = {}
                
                # Add course to the section
                section_dict["uc_courses"].append({
                    "name": doc.metadata.get("uc_course"),
                    "logic_blocks": [logic_block] if isinstance(logic_block, dict) else logic_block
                })
            
            group_dict["sections"].append(section_dict)
        
        # Validate courses against the group
        validation_result = self.articulation_facade.validate_combo_against_group(
            query.ccc_courses, group_dict
        )
        
        # Format the response based on validation results
        if validation_result.get("is_fully_satisfied", False):
            formatted_response = (
                f"✅ Yes, your courses ({', '.join(query.ccc_courses)}) fully satisfy {group_title} (Group {group_id}).\n\n"
                f"Matched UC courses: {', '.join(validation_result.get('satisfied_uc_courses', []))}"
            )
        elif validation_result.get("partially_satisfied", False):
            missing = (
                validation_result.get("required_count", 0) - validation_result.get("satisfied_count", 0)
                if validation_result.get("required_count") is not None
                else "additional required courses"
            )
            
            formatted_response = (
                f"🔶 Your courses partially satisfy {group_title} (Group {group_id}).\n\n"
                f"You've matched: {', '.join(validation_result.get('satisfied_uc_courses', []))}, "
            )
            
            if isinstance(missing, int):
                formatted_response += f"but you still need {missing} more UC course(s)."
            else:
                formatted_response += (
                    "but they may span across multiple sections. "
                    f"For {group_title}, all UC courses must come from the same section."
                )
        else:
            formatted_response = (
                f"❌ No, your courses do not satisfy {group_title} (Group {group_id}).\n\n"
                "No UC course articulation paths were matched."
            )
        
        return QueryResult(
            raw_response=f"Validation of {', '.join(query.ccc_courses)} against Group {group_id}",
            formatted_response=formatted_response,
            matched_docs=group_docs,
            metadata={
                "group_id": group_id,
                "group_title": group_title,
                "group_type": group_type,
                "n_courses": n_courses,
                "is_satisfied": validation_result.get("is_fully_satisfied", False),
                "is_partially_satisfied": validation_result.get("partially_satisfied", False),
                "satisfied_uc_courses": validation_result.get("satisfied_uc_courses", []),
                "satisfied_count": validation_result.get("satisfied_count", 0),
                "required_count": validation_result.get("required_count", None)
            }
        )
    
    def _handle_group_info(
        self, 
        query: Query, 
        group_docs: List[Any],
        group_id: str,
        group_title: str,
        group_type: str,
        n_courses: Optional[int]
    ) -> QueryResult:
        """
        Handle general information queries about a group.
        
        Args:
            query: The original query
            group_docs: Documents for the specified group
            group_id: Group identifier
            group_title: Human-readable group title
            group_type: Logic type for the group (ALL_REQUIRED, SELECT_N_COURSES, etc.)
            n_courses: Number of courses required (for SELECT_N_COURSES type)
            
        Returns:
            QueryResult with group information
        """
        # Generate a summary of the group using the articulation facade
        group_summary = self.articulation_facade.render_group_summary(group_docs)
        
        # Add contextual information about the group type
        type_explanation = ""
        if group_type == "ALL_REQUIRED":
            type_explanation = "All courses in this group are required."
        elif group_type == "SELECT_N_COURSES" and n_courses is not None:
            type_explanation = f"You need to complete {n_courses} course(s) from this group."
        elif group_type == "CHOOSE_ONE_SECTION":
            type_explanation = "You need to complete all courses from one section in this group."
        
        # Build a complete response
        formatted_response = (
            f"# {group_title} (Group {group_id})\n\n"
            f"{type_explanation}\n\n"
            f"{group_summary}"
        )
        
        return QueryResult(
            raw_response=f"Information about Group {group_id}",
            formatted_response=formatted_response,
            matched_docs=group_docs,
            metadata={
                "group_id": group_id,
                "group_title": group_title,
                "group_type": group_type,
                "n_courses": n_courses
            }
        )
