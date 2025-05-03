"""
TransferAI Course Lookup Query Handler

This module implements the handler for course lookup queries. These queries
ask which CCC courses satisfy a specific UC course requirement.
"""

import logging
from typing import Optional, Dict, Any, List

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade
from llm.services.query_service import QueryService

# Set up logger
logger = logging.getLogger(__name__)

class CourseLookupHandler(QueryHandler):
    """
    Handler for course lookup queries.
    
    These are queries that ask which CCC courses satisfy a specific UC course,
    such as "Which De Anza courses satisfy CSE 8A at UCSD?" or "What satisfies CSE 11?".
    """
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the course lookup handler.
        
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
        1. Are explicitly marked as COURSE_LOOKUP type
        2. Have UC courses specified but no CCC courses
        3. Are asking what CCC courses satisfy a UC course
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        # Check if query type has been explicitly set
        if query.query_type == QueryType.COURSE_LOOKUP:
            return True
            
        # Must have UC courses but no CCC courses
        if not query.uc_courses:
            return False
            
        # Check for lookup keywords 
        lookup_keywords = [
            "which", "what", "courses satisfy", "courses that satisfy", 
            "what satisfies", "can satisfy", "courses for"
        ]
        
        if any(keyword in query.text.lower() for keyword in lookup_keywords):
            return True
            
        return False
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process a course lookup query and return results.
        
        This handler determines which CCC courses satisfy a specific UC course by:
        1. Finding the document for the requested UC course
        2. Extracting the articulation logic from the document
        3. Formatting a response listing all available options
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing the list of CCC courses that satisfy the UC course
        """
        if not query.uc_courses:
            logger.warning("Course lookup query missing UC course specification")
            return QueryResult(
                raw_response="Could not process lookup query - no UC course specified.",
                formatted_response="Please specify which UC course you want to look up. For example, 'Which courses satisfy CSE 8A?'"
            )
        
        # Check if we need to process multiple UC courses
        if len(query.uc_courses) == 1:
            # Single course case - use the original implementation
            return self._process_single_course(query.uc_courses[0], query.text)
        else:
            # Multiple courses case - process each course and combine results
            return self._process_multiple_courses(query.uc_courses, query.text)
    
    def _process_single_course(self, uc_course: str, query_text: str) -> QueryResult:
        """
        Process a single UC course lookup query.
        
        Args:
            uc_course: The UC course to look up
            query_text: The original query text
            
        Returns:
            QueryResult containing the articulation options for the UC course
        """
        logger.info(f"Processing course lookup query for UC course: {uc_course}")
        
        # Use MatchingService to find documents
        matching_docs = self.matching_service.match_documents(
            documents=self.document_repository.get_all_documents(),
            uc_courses=[uc_course],
            ccc_courses=[],  # No CCC courses for lookup queries
            query_text=query_text
        )
        
        # Filter to documents for this specific UC course
        matching_docs = [
            doc for doc in matching_docs
            if self.query_service.normalize_course_code(doc.metadata.get("uc_course", "")) == 
               self.query_service.normalize_course_code(uc_course)
        ]
        
        if not matching_docs:
            logger.warning(f"No documents found for UC course: {uc_course}")
            return QueryResult(
                raw_response=f"No information found for {uc_course}.",
                formatted_response=f"I couldn't find any articulation information for {uc_course}. This may mean the course isn't included in the current dataset."
            )
        
        # Get the primary document for this course
        doc = matching_docs[0]
        logger.debug(f"Found document for {uc_course}: {doc.metadata.get('id', 'unknown')}")
        
        # Extract the logic block
        logic_block = doc.metadata.get("logic_block", {})
        
        # Check if the course has been explicitly marked as having no articulation
        if isinstance(logic_block, dict) and logic_block.get("no_articulation", False):
            logger.info(f"Course {uc_course} explicitly marked as having no articulation")
            
            # Get course description if available
            course_title = doc.metadata.get("title", "")
            course_description = f" ({course_title})" if course_title else ""
            
            return QueryResult(
                raw_response=f"No articulation for {uc_course}.",
                formatted_response=(
                    f"# ❌ No, {uc_course}{course_description} does not have any articulation.\n\n"
                    f"According to the official articulation agreement, there are no courses at De Anza College "
                    f"that satisfy {uc_course}. This means you will need to complete this course at UCSD after transferring.\n\n"
                    f"You might want to check if this course is part of a sequence or if there are alternatives in your major requirements."
                ),
                metadata={
                    'uc_course': uc_course,
                    'has_articulation': False
                }
            )
        
        # Extract articulation options using the ArticulationFacade
        try:
            articulation_info = self.articulation_facade.get_articulation_options(logic_block)
            
            if not articulation_info or not articulation_info.get("options"):
                logger.warning(f"No valid articulation options found for {uc_course}")
                
                # Get course description if available
                course_title = doc.metadata.get("title", "")
                course_description = f" ({course_title})" if course_title else ""
                
                return QueryResult(
                    raw_response=f"No valid articulation options for {uc_course}.",
                    formatted_response=(
                        f"# ❌ No, {uc_course}{course_description} does not have any articulation.\n\n"
                        f"According to the official articulation agreement, there are no courses at De Anza College "
                        f"that satisfy {uc_course}. This means you will need to complete this course at UCSD after transferring.\n\n"
                        f"You might want to check if this course is part of a sequence or if there are alternatives in your major requirements."
                    ),
                    metadata={
                        'uc_course': uc_course,
                        'has_articulation': False
                    }
                )
            
            # Use the ArticulationFacade to format the response
            formatted_response = self.articulation_facade.format_course_options(
                uc_course, articulation_info
            )
            
            return QueryResult(
                raw_response=f"Found articulation options for {uc_course}",
                formatted_response=formatted_response,
                matched_docs=matching_docs,
                metadata={
                    "uc_course": uc_course,
                    "articulation_info": articulation_info,
                    "has_articulation": True
                }
            )
            
        except Exception as e:
            logger.error(f"Error processing articulation data for {uc_course}: {str(e)}")
            return QueryResult(
                raw_response=f"Error processing articulation data: {str(e)}",
                formatted_response=f"I encountered an error while processing the articulation information for {uc_course}. Please try again or contact support if the issue persists."
            ) 
    
    def _process_multiple_courses(self, uc_courses: List[str], query_text: str) -> QueryResult:
        """
        Process a lookup query with multiple UC courses.
        
        Args:
            uc_courses: List of UC courses to look up
            query_text: The original query text
            
        Returns:
            QueryResult containing articulation options for all requested UC courses
        """
        logger.info(f"Processing multi-course lookup query for UC courses: {', '.join(uc_courses)}")
        
        # Process each course individually and collect results
        course_results = []
        matched_docs = []
        
        for uc_course in uc_courses:
            result = self._process_single_course(uc_course, query_text)
            
            if result:
                course_results.append(result)
                if result.matched_docs:
                    matched_docs.extend(result.matched_docs)
        
        # If no results were found for any course, return a general message
        if not course_results:
            return QueryResult(
                raw_response=f"No information found for UC courses: {', '.join(uc_courses)}.",
                formatted_response=f"I couldn't find any articulation information for the requested UC courses. They may not be included in the current dataset."
            )
        
        # Combine the formatted responses
        combined_response = self._combine_formatted_responses(uc_courses, course_results)
        
        return QueryResult(
            raw_response=f"Found articulation options for multiple UC courses",
            formatted_response=combined_response,
            matched_docs=matched_docs,
            metadata={
                "uc_courses": uc_courses,
                "multi_course_query": True
            }
        )
    
    def _combine_formatted_responses(self, uc_courses: List[str], results: List[QueryResult]) -> str:
        """
        Combine multiple formatted responses into a single coherent response.
        
        Args:
            uc_courses: The UC courses in the query
            results: Individual QueryResults for each course
            
        Returns:
            A combined formatted response string
        """
        if not results:
            return f"No articulation information found for {', '.join(uc_courses)}."
        
        # Extract the formatted responses
        formatted_responses = [result.formatted_response for result in results if result.formatted_response]
        
        # Combine responses with separators
        combined = "\n\n---\n\n".join(formatted_responses)
        
        if len(uc_courses) > 1:
            intro = f"# Articulation options for {', '.join(uc_courses)}\n\n"
            return intro + combined
        else:
            return combined 