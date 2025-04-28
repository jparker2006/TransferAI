"""
TransferAI Validation Query Handler

This module implements the handler for course validation queries. These queries
ask whether specific CCC courses satisfy requirements for specific UC courses.
"""

from typing import Optional, Dict, Any, List

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade
from llm.services.query_service import QueryService


class ValidationQueryHandler(QueryHandler):
    """
    Handler for course validation queries.
    
    These are queries that ask if specific CCC courses satisfy the requirements
    for specific UC courses, such as "Does CIS 22A satisfy CSE 8A?".
    """
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the validation query handler.
        
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
        1. Have both UC and CCC courses specified
        2. Are asking if CCC courses satisfy a UC course requirement
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        # Check if query type has been explicitly set
        if query.query_type == QueryType.COURSE_VALIDATION:
            return True
            
        # Fallback logic: check if we have both UC and CCC courses
        if not query.uc_courses or not query.ccc_courses:
            return False
            
        # Check for validation keywords
        validation_keywords = [
            "satisfy", "fulfill", "equivalent", "transfer", "articulate", 
            "count for", "substitute", "meet requirement"
        ]
        if any(keyword in query.text.lower() for keyword in validation_keywords):
            return True
            
        return False
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process a validation query and return results.
        
        This handler determines if specific CCC courses satisfy a UC course
        requirement by:
        1. Finding the relevant UC course document
        2. Extracting its articulation logic
        3. Validating the CCC courses against that logic
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing the validation results
        """
        if not query.uc_courses or not query.ccc_courses:
            return QueryResult(
                raw_response="Could not process validation query - missing courses.",
                formatted_response="I need both UC and CCC courses to validate. Please specify which UC course and which CCC courses you want to check."
            )
        
        # Focus on the first UC course mentioned
        uc_course = query.uc_courses[0]
        ccc_courses = query.ccc_courses
        
        # Use MatchingService to find documents instead of directly using DocumentRepository
        # This provides more sophisticated matching, filtering, and ranking
        matched_docs = self.matching_service.match_documents(
            documents=self.document_repository.get_all_documents(),
            uc_courses=[uc_course],
            ccc_courses=ccc_courses,
            query_text=query.text
        )
        
        # Filter to documents in the same section for consistency
        matched_docs = self.matching_service.validate_same_section(matched_docs)
        
        if not matched_docs:
            return QueryResult(
                raw_response=f"No articulation information found for {uc_course}.",
                formatted_response=f"I couldn't find any articulation information for {uc_course}. This may mean the course has no established articulation path or isn't part of the current dataset."
            )
        
        # Get the logic block from the first matching document
        doc = matched_docs[0]
        logic_block = doc.metadata.get("logic_block", {})
        
        # Check for no_articulation flag
        if logic_block.get("no_articulation", False):
            return QueryResult(
                raw_response=f"{uc_course} has no articulation.",
                formatted_response=f"❌ No, {uc_course} has no articulation at this community college. This course must be completed at the UC campus.",
                satisfied=False,
                matched_docs=matched_docs
            )
        
        # Special case: Check for honors pair equivalence
        if len(ccc_courses) == 2 and self.articulation_facade.is_honors_pair_equivalent(
            logic_block, ccc_courses[0], ccc_courses[1]
        ):
            explanation = self.articulation_facade.explain_honors_equivalence(ccc_courses[0], ccc_courses[1])
            return QueryResult(
                raw_response=f"Honors pair equivalence: {explanation}",
                formatted_response=f"✅ Yes, {explanation}",
                satisfied=True,
                matched_docs=matched_docs
            )
        
        # Perform validation against the logic block
        validation_result = self.articulation_facade.validate_courses(logic_block, ccc_courses)
        is_satisfied = validation_result["is_satisfied"]
        explanation = validation_result["explanation"]
        
        # Create the response
        formatted_response = self.articulation_facade.format_binary_response(
            is_satisfied, explanation, uc_course
        )
        
        return QueryResult(
            raw_response=explanation,
            formatted_response=formatted_response,
            satisfied=is_satisfied,
            matched_docs=matched_docs,
            metadata={
                "validation_details": validation_result,
                "uc_course": uc_course,
                "ccc_courses": ccc_courses
            }
        )
