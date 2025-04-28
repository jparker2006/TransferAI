"""
TransferAI Course Lookup Query Handler

This module implements the handler for course lookup queries. These queries
ask which CCC courses satisfy a specific UC course requirement.
"""

from typing import Optional, Dict, Any, List

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade
from llm.services.query_service import QueryService


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
            return QueryResult(
                raw_response="Could not process lookup query - no UC course specified.",
                formatted_response="Please specify which UC course you want to look up. For example, 'Which courses satisfy CSE 8A?'"
            )
        
        uc_course = query.uc_courses[0]  # Process the first UC course mentioned
        all_documents = self.document_repository.get_all_documents()
        
        # Find the document for this UC course
        matching_docs = []
        for doc in all_documents:
            doc_uc_course = doc.metadata.get("uc_course", "")
            if self.query_service.normalize_course_code(doc_uc_course) == self.query_service.normalize_course_code(uc_course):
                matching_docs.append(doc)
        
        if not matching_docs:
            return QueryResult(
                raw_response=f"No information found for {uc_course}.",
                formatted_response=f"I couldn't find any articulation information for {uc_course}."
            )
        
        doc = matching_docs[0]  # Use the first matching document
        
        # Check if the course has no articulation
        logic_block = doc.metadata.get("logic_block", {})
        if not logic_block or logic_block.get("no_articulation", False):
            return QueryResult(
                raw_response=f"No articulation for {uc_course}.",
                formatted_response=f"# No articulation for {uc_course}\n\nAccording to the articulation agreement, there are no De Anza courses that satisfy {uc_course}."
            )
        
        # Extract and format the articulation options
        options = logic_block.get("options", [])
        
        # Convert the logic block to a more readable format
        option_descriptions = []
        for i, option in enumerate(options):
            courses = option.get("courses", [])
            
            # Format courses based on whether they're an AND group or single course
            course_descriptions = []
            for course in courses:
                if isinstance(course, list):  # AND group
                    course_names = [c.get("name").split(" ", 1)[0] for c in course]
                    course_descriptions.append(", ".join(course_names))
                elif isinstance(course, dict):  # Single course
                    course_name = course.get("name").split(" ", 1)[0]  # Extract just the course code
                    course_descriptions.append(course_name)
            
            # If this is an AND group, join with "AND", otherwise list them as separate options
            if len(course_descriptions) > 1:
                option_descriptions.append(f"Option {chr(65+i)}: {' AND '.join(course_descriptions)}")
            else:
                option_descriptions.append(f"Option {chr(65+i)}: {course_descriptions[0]}")
        
        # Check if any courses satisfy the UC course
        if not option_descriptions:
            return QueryResult(
                raw_response=f"No articulation for {uc_course}.",
                formatted_response=f"# No articulation for {uc_course}\n\nAccording to the articulation agreement, there are no De Anza courses that satisfy {uc_course}."
            )
        
        # Format the response
        if len(option_descriptions) == 1:
            formatted_response = f"# {uc_course} can be satisfied by:\n\n{option_descriptions[0]}"
        else:
            options_text = "\n".join(option_descriptions)
            formatted_response = f"# {uc_course} can be satisfied by any of these options:\n\n{options_text}"
            
        return QueryResult(
            raw_response=f"Courses that satisfy {uc_course}: {', '.join(option_descriptions)}",
            formatted_response=formatted_response,
            matched_docs=matching_docs
        ) 