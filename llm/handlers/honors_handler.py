"""
TransferAI Honors Query Handler

This module implements the handler for honors-related queries. These queries
ask about whether honors courses are required or optional for satisfying
UC course requirements.
"""

from typing import Optional, Dict, Any, List
import re

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.matching_service import MatchingService
from llm.services.articulation_facade import ArticulationFacade
from llm.services.query_service import QueryService


class HonorsQueryHandler(QueryHandler):
    """
    Handler for honors requirement queries.
    
    These are queries that ask about whether honors courses are required
    for specific UC courses, such as:
    - "Does MATH 20A require honors courses?"
    - "Can I satisfy CSE 8A with a non-honors course?"
    - "Which UC courses require honors versions?"
    - "Are any honors courses required for the CS transfer path?"
    """
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the honors query handler.
        
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
        1. Have an explicit HONORS_REQUIREMENT query type
        2. Contain honors-related keywords and UC course references
        3. Ask about honors requirements for a transfer path or major
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        # Check if query type has been explicitly set
        if query.query_type == QueryType.HONORS_REQUIREMENT:
            return True
            
        # Check for honors keywords
        honors_keywords = [
            "honors", "honor", "h course", "h version", "h credit",
            "1h", "2h", "3h", "4h", "5h", "8h", "10h", "11h", "20h", "21h",
            "require honors", "honors required", "need honors", "with honors"
        ]
        
        # Also check for course code with H suffix like "MATH 20AH"
        text_lower = query.text.lower()
        
        # Either match one of the explicit keywords, or a course code ending with H
        has_honors_keyword = any(keyword in text_lower for keyword in honors_keywords)
        
        # Use regex to find course codes ending with H
        has_honors_course_code = bool(re.search(r'\d+[a-z]*h\b', text_lower))
        
        # Check for transfer path or major references
        transfer_keywords = ["transfer", "pathway", "path", "major", "cs major", "computer science"]
        has_transfer_keyword = any(keyword in text_lower for keyword in transfer_keywords)
        
        # Handle general honors requirements for transfer paths
        if has_honors_keyword and has_transfer_keyword:
            return True
            
        # Must have a UC course for specific course queries
        if (has_honors_keyword or has_honors_course_code) and query.uc_courses:
            return True
            
        return False
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process an honors requirement query and return results.
        
        This handler determines if honors courses are required for specific UC courses
        or across a transfer path by analyzing the logic blocks in the articulation documents.
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing honors requirement information
        """
        # Get all documents for analysis
        all_documents = self.document_repository.get_all_documents()
        
        # Check if this is a general query about honors courses in a transfer path
        text_lower = query.text.lower()
        transfer_keywords = ["transfer", "pathway", "path", "major", "cs major", "computer science"]
        is_transfer_path_query = any(keyword in text_lower for keyword in transfer_keywords)
        
        # Handle transfer path honors requirement queries
        if is_transfer_path_query or not query.uc_courses:
            # Extract major information if available (currently assuming CS if mentioned)
            major = "Computer Science"
            if "cs" in text_lower or "computer science" in text_lower:
                major = "Computer Science"
                
            # Get honors requirements for all courses
            honors_requirements = self._get_all_honors_requirements(all_documents)
            
            # If no honors requirements found at all
            if not honors_requirements:
                return QueryResult(
                    raw_response="No honors requirement information available.",
                    formatted_response="I couldn't find any information about honors requirements in the articulation data."
                )
                
            # Check if any courses require honors
            honors_required_courses = [uc for uc, required in honors_requirements.items() if required]
            
            # Format response
            if honors_required_courses:
                formatted_response = (
                    f"# Honors Requirements for {major} Transfer\n\n"
                    f"Based on the articulation data, the following courses **require** honors versions:\n\n"
                )
                for uc in sorted(honors_required_courses):
                    formatted_response += f"- {uc}\n"
                    
                formatted_response += "\n\nFor all other courses, both honors and non-honors versions are accepted if available."
                
                return QueryResult(
                    raw_response=f"Honors required for: {', '.join(honors_required_courses)}",
                    formatted_response=formatted_response,
                    metadata={
                        "honors_required_courses": honors_required_courses,
                        "major": major
                    }
                )
            else:
                formatted_response = (
                    f"# Honors Requirements for {major} Transfer\n\n"
                    f"Based on the articulation data, **no courses require honors versions**. "
                    f"While honors courses are accepted, you can satisfy all requirements with non-honors courses.\n\n"
                    f"Taking honors courses may still provide other benefits, but they are not required for articulation."
                )
                
                return QueryResult(
                    raw_response="No courses require honors versions",
                    formatted_response=formatted_response,
                    metadata={
                        "honors_required_courses": [],
                        "major": major
                    }
                )
        
        # Handle specific UC course query
        uc_course = query.uc_courses[0]  # Process the first UC course mentioned
        
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
        if isinstance(logic_block, dict) and logic_block.get("no_articulation", False):
            return QueryResult(
                raw_response=f"{uc_course} has no articulation.",
                formatted_response=f"❌ {uc_course} must be completed at the UC campus. There are no community college courses that articulate to this requirement."
            )
        
        # Check if honors courses are required
        honors_required = self.articulation_facade.is_honors_required(logic_block)
        
        # Extract honors information (which courses require honors)
        honors_info = self.articulation_facade.extract_honors_info(logic_block)
        honors_courses = honors_info.get("honors_courses", [])
        non_honors_courses = honors_info.get("non_honors_courses", [])
        
        # Generate the response based on honors requirements
        if honors_required:
            options_text = ""
            if honors_courses:
                options_text = f"The following courses must be taken for honors credit: {', '.join(honors_courses)}."
            
            return QueryResult(
                raw_response=f"{uc_course} requires honors courses.",
                formatted_response=(
                    f"# ✅ Yes, {uc_course} requires honors courses.\n\n"
                    f"Based on the official articulation data, only honors courses will satisfy {uc_course}. "
                    f"Non-honors options are not available. {options_text}"
                ),
                metadata={
                    "uc_course": uc_course,
                    "honors_required": True,
                    "honors_courses": honors_courses,
                    "non_honors_courses": non_honors_courses
                }
            )
        else:
            options_text = ""
            if non_honors_courses and honors_courses:
                options_text = (
                    f"You can satisfy this requirement with either the standard courses "
                    f"({', '.join(non_honors_courses)}) or their honors equivalents "
                    f"({', '.join(honors_courses)})."
                )
            elif non_honors_courses:
                options_text = f"You can satisfy this requirement with: {', '.join(non_honors_courses)}."
            
            return QueryResult(
                raw_response=f"{uc_course} does not require honors courses.",
                formatted_response=(
                    f"# ❌ No, {uc_course} does not require honors courses.\n\n"
                    f"Based on the official articulation data, you can satisfy {uc_course} "
                    f"with either honors or non-honors courses. {options_text}"
                ),
                metadata={
                    "uc_course": uc_course,
                    "honors_required": False,
                    "honors_courses": honors_courses,
                    "non_honors_courses": non_honors_courses
                }
            )
            
    def _get_all_honors_requirements(self, all_documents: List[Any]) -> Dict[str, bool]:
        """
        Analyze all documents to determine honors requirements for each UC course.
        
        This is used when answering general questions about which courses require honors.
        
        Args:
            all_documents: List of articulation documents to analyze
            
        Returns:
            Dictionary mapping UC course codes to boolean indicating if honors is required
        """
        honors_requirements = {}
        
        for doc in all_documents:
            uc_course = doc.metadata.get("uc_course", "")
            if not uc_course:
                continue
                
            logic_block = doc.metadata.get("logic_block", {})
            if isinstance(logic_block, dict) and logic_block.get("no_articulation", False):
                # Skip courses with no articulation
                continue
                
            honors_required = self.articulation_facade.is_honors_required(logic_block)
            honors_requirements[uc_course] = honors_required
            
        return honors_requirements
