"""
TransferAI Fallback Query Handler

This module implements the fallback query handler for queries that don't match
any of the specialized handlers.
"""

from typing import Optional, Dict, Any, List

from llm.models.query import Query, QueryResult, QueryType
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository


class FallbackQueryHandler(QueryHandler):
    """
    Handler for queries that don't match any specialized handler.
    
    Acts as a catch-all for unrecognized query types, providing generalized
    responses when a more specific handler isn't applicable.
    """
    
    def can_handle(self, query: Query) -> bool:
        """
        Determine if this handler can process the query.
        
        The fallback handler can handle any query, but should be registered
        last so more specialized handlers take precedence.
        
        Args:
            query: The query to check
            
        Returns:
            Always returns True
        """
        # This handler can handle any query, but should be registered last
        return True
    
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process the query and return results.
        
        For now, this provides a simple generic response. In the future,
        it might use the LLM to generate a more helpful response.
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing the processed results
        """
        try:
            # If we have CCC courses in the query, try to provide some information
            if query.ccc_courses and len(query.ccc_courses) > 0:
                ccc_course = query.ccc_courses[0]
                return QueryResult(
                    raw_response=f"You asked about {ccc_course}, but I couldn't determine specific articulation details.",
                    formatted_response=f"I see you're asking about {ccc_course}. To get specific information, try asking:\n"
                                    f"- Does {ccc_course} satisfy a specific UC course?\n"
                                    f"- What UC courses does {ccc_course} satisfy?\n"
                                    f"- Is {ccc_course} part of a specific requirement group?"
                )
            
            # Default generic response
            return QueryResult(
                raw_response="Unable to process query type.",
                formatted_response="I'm not sure how to answer that question. Try asking about specific course "
                                "articulations, like:\n"
                                "- Does [CCC Course] satisfy [UC Course]?\n"
                                "- What UC courses does [CCC Course] satisfy?\n"
                                "- What courses satisfy [Group]?"
            )
        except Exception as e:
            # Catch any unexpected errors and provide a graceful fallback
            return QueryResult(
                raw_response=f"Error processing query: {str(e)}",
                formatted_response="I encountered an issue while processing your question. Please try rephrasing or "
                                "ask a different question about course articulations."
            )
