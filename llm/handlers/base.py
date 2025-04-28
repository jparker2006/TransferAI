"""
TransferAI Handler Base Module

This module defines the base classes and interfaces for all query handlers in the
TransferAI system, implementing the Strategy Pattern for query processing.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Type

from llm.models.query import Query, QueryResult
from llm.repositories.document_repository import DocumentRepository


class QueryHandler(ABC):
    """
    Base class for all query handlers.
    
    Implements the Strategy Pattern, where each concrete handler implements
    a specific strategy for handling a particular type of query.
    """
    
    def __init__(self, document_repository: DocumentRepository, config: Dict[str, Any]):
        """
        Initialize the query handler.
        
        Args:
            document_repository: Repository for accessing articulation documents
            config: Configuration options for the handler
        """
        self.document_repository = document_repository
        self.config = config
    
    @abstractmethod
    def can_handle(self, query: Query) -> bool:
        """
        Determine if this handler can process the query.
        
        Args:
            query: The query to check
            
        Returns:
            True if this handler can process the query, False otherwise
        """
        pass
    
    @abstractmethod
    def handle(self, query: Query) -> Optional[QueryResult]:
        """
        Process the query and return results.
        
        Args:
            query: The query to process
            
        Returns:
            QueryResult containing the processed results, or None if processing failed
        """
        pass


class HandlerRegistry:
    """
    Registry of available query handlers.
    
    Maintains a list of registered handlers and provides methods for finding
    the appropriate handler for a given query.
    """
    
    def __init__(self):
        """Initialize an empty handler registry."""
        self.handlers: List[QueryHandler] = []
    
    def register(self, handler: QueryHandler) -> None:
        """
        Register a handler with the registry.
        
        Args:
            handler: The handler to register
        """
        self.handlers.append(handler)
    
    def register_all(self, handlers: List[QueryHandler]) -> None:
        """
        Register multiple handlers with the registry.
        
        Args:
            handlers: The handlers to register
        """
        self.handlers.extend(handlers)
    
    def find_handler(self, query: Query) -> Optional[QueryHandler]:
        """
        Find an appropriate handler for the query.
        
        Args:
            query: The query to find a handler for
            
        Returns:
            The first handler that can handle the query, or None if no handler can handle it
        """
        for handler in self.handlers:
            if handler.can_handle(query):
                return handler
        return None
