"""
TransferAI Course Equivalency Query Handler

This module implements the handler for course equivalency queries. These queries
ask what UC courses can be satisfied by specific CCC courses.
"""

from typing import Optional, Dict, Any, List

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade
from llm.services.query_service import QueryService


class CourseEquivalencyHandler(QueryHandler):
    """
    Handler for course equivalency queries.
    
    These are queries that ask what UC courses can be satisfied by specific CCC courses,
    such as "What UC courses does CIS 22A satisfy?" or "What can I satisfy with MATH 1A?".
    """
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the course equivalency handler.
        
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
        1. Have CCC courses specified but no UC courses
        2. Are asking what UC courses can be satisfied by CCC courses
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        # Check if query type has been explicitly set
        if query.query_type == QueryType.COURSE_EQUIVALENCY:
            return True
            
        # Must have CCC courses but no UC courses
        if not query.ccc_courses or query.uc_courses:
            return False
            
        # Check for equivalency keywords
        equivalency_keywords = [
            "satisfy", "transfer to", "fulfill", "equivalent", "what can",
            "what would", "what does", "what uc", "what requirements"
        ]
        if any(keyword in query.text.lower() for keyword in equivalency_keywords):
            return True
            
        return False
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process a course equivalency query and return results.
        
        This handler determines what UC courses can be satisfied by specific CCC courses by:
        1. Using the MatchingService to find reverse matches
        2. Analyzing the matched documents to determine satisfaction level
        3. Formatting a response listing satisfied UC courses
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing the list of satisfied UC courses
        """
        if not query.ccc_courses:
            return QueryResult(
                raw_response="Could not process equivalency query - no CCC courses specified.",
                formatted_response="Please specify which CCC courses you want to check. For example, 'What UC courses does CIS 22A satisfy?'"
            )
        
        ccc_courses = query.ccc_courses
        all_documents = self.document_repository.get_all_documents()
        
        # Use MatchingService to find reverse matches
        matched_docs = self.matching_service.match_reverse(
            documents=all_documents,
            ccc_courses=ccc_courses,
            query_text=query.text
        )
        
        if not matched_docs:
            return QueryResult(
                raw_response=f"No UC courses found that can be satisfied by {', '.join(ccc_courses)}.",
                formatted_response=f"I couldn't find any UC courses that can be satisfied by {', '.join(ccc_courses)}."
            )
        
        # Count the UC courses matched by the CCC courses
        if len(ccc_courses) == 1:
            # For a single CCC course, use the articulation facade to count matches
            ccc_course = ccc_courses[0]
            match_count, direct_matches, contribution_matches = self.articulation_facade.count_uc_matches(
                ccc_course, all_documents
            )
            
            if match_count == 0 and not contribution_matches:
                return QueryResult(
                    raw_response=f"No UC courses found that can be satisfied by {ccc_course}.",
                    formatted_response=f"❌ No, {ccc_course} does not satisfy any UC course requirements."
                )
            elif match_count == 1:
                formatted_response = f"✅ {ccc_course} can satisfy {direct_matches[0]}."
                if contribution_matches:
                    formatted_response += f"\n\nAdditionally, {ccc_course} can contribute to satisfying {', '.join(contribution_matches)} when combined with other courses."
                return QueryResult(
                    raw_response=f"{ccc_course} satisfies {direct_matches[0]}",
                    formatted_response=formatted_response,
                    matched_docs=matched_docs
                )
            elif match_count > 1:
                formatted_response = f"✅ {ccc_course} can satisfy multiple UC courses: {', '.join(direct_matches)}."
                if contribution_matches:
                    formatted_response += f"\n\nAdditionally, it can contribute to satisfying {', '.join(contribution_matches)} when combined with other courses."
                return QueryResult(
                    raw_response=f"{ccc_course} satisfies multiple UC courses",
                    formatted_response=formatted_response,
                    matched_docs=matched_docs
                )
        
        # For multiple CCC courses or fallback case, list all matched UC courses
        uc_courses = []
        for doc in matched_docs:
            uc_course = doc.metadata.get("uc_course")
            if uc_course and uc_course not in uc_courses:
                uc_courses.append(uc_course)
        
        if not uc_courses:
            return QueryResult(
                raw_response=f"No UC courses found that can be satisfied by {', '.join(ccc_courses)}.",
                formatted_response=f"I couldn't find any UC courses that can be satisfied by {', '.join(ccc_courses)}."
            )
        
        # Validate each matched UC course against the CCC courses
        fully_satisfied = []
        partially_satisfied = []
        
        for uc_course in uc_courses:
            uc_docs = [doc for doc in matched_docs if doc.metadata.get("uc_course") == uc_course]
            if not uc_docs:
                continue
                
            doc = uc_docs[0]
            logic_block = doc.metadata.get("logic_block", {})
            
            # Skip courses that have no articulation
            if logic_block.get("no_articulation", False):
                continue
                
            # Check if the CCC courses satisfy this UC course
            validation_result = self.articulation_facade.validate_courses(logic_block, ccc_courses)
            
            # Print debug information
            print(f"Validating {uc_course} with {ccc_courses}: {validation_result}")
            
            # Add to appropriate list based on validation result
            if validation_result.get("is_satisfied", False):
                fully_satisfied.append(uc_course)
            elif validation_result.get("match_percentage", 0) > 0:
                partially_satisfied.append(uc_course)
        
        # Format the response based on results
        if fully_satisfied and partially_satisfied:
            formatted_response = (
                f"With {', '.join(ccc_courses)}, you can fully satisfy: {', '.join(fully_satisfied)}\n\n"
                f"You can partially satisfy: {', '.join(partially_satisfied)}"
            )
        elif fully_satisfied:
            formatted_response = f"✅ {', '.join(ccc_courses)} can satisfy: {', '.join(fully_satisfied)}"
        elif partially_satisfied:
            formatted_response = (
                f"{', '.join(ccc_courses)} partially satisfies: {', '.join(partially_satisfied)}\n\n"
                f"You'll need additional courses to fully satisfy these requirements."
            )
        else:
            formatted_response = (
                f"While {', '.join(ccc_courses)} appears in some articulation paths, "
                f"it doesn't fully or partially satisfy any UC courses on its own. "
                f"You may need to combine it with other courses."
            )
        
        return QueryResult(
            raw_response=f"Courses satisfied by {', '.join(ccc_courses)}: {', '.join(uc_courses)}",
            formatted_response=formatted_response,
            matched_docs=matched_docs,
            metadata={
                "ccc_courses": ccc_courses,
                "fully_satisfied": fully_satisfied,
                "partially_satisfied": partially_satisfied
            }
        )
