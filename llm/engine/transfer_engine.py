"""
TransferAI Engine

This module contains the core engine for TransferAI, which coordinates
the various components of the system.
"""

from typing import Optional, Dict, Any, List, Type
import logging
import time
from pathlib import Path

from llm.models.query import Query, QueryResult, QueryType
from llm.repositories.document_repository import DocumentRepository
from llm.services.query_service import QueryService
from llm.services.prompt_service import PromptService, VerbosityLevel
from llm.services.matching_service import MatchingService
from llm.handlers.base import QueryHandler, HandlerRegistry
from llm.engine.config import Config, get_config
from llm.engine.utils import setup_logging, get_version, load_handler_classes, format_error

# Import LlamaIndex for setting LLM
from llama_index.core.settings import Settings
from llama_index.llms.ollama import Ollama


class TransferAIEngine:
    """
    Core engine for TransferAI.
    
    Coordinates the components of the system to process user queries and generate responses.
    Acts as the main entry point for the system.
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        document_repository: Optional[DocumentRepository] = None,
        query_service: Optional[QueryService] = None,
        matching_service: Optional[MatchingService] = None,
        prompt_service: Optional[PromptService] = None
    ):
        """
        Initialize the engine with dependencies.
        
        Args:
            config: Configuration object, or None to use default config
            document_repository: Document repository, or None to create a new one
            query_service: Query service, or None to create a new one
            matching_service: Matching service, or None to create a new one
            prompt_service: Prompt service, or None to create a new one
        """
        # Initialize configuration
        self.config = config or get_config()
        
        # Setup logging
        setup_logging(
            log_level=self.config.get("log_level", "INFO"),
            log_file=self.config.get("log_file")
        )
        
        # Create logger for this class
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initializing TransferAI Engine v{get_version()}")
        
        # Set up LLM if specified in config
        if self.config.get("llm_model"):
            self._setup_llm()
        
        # Initialize components
        self.document_repository = document_repository or DocumentRepository()
        
        self.query_service = query_service or QueryService()
        
        # Initialize matching service with document repository
        self.matching_service = matching_service or MatchingService()
        
        # Initialize prompt service with verbosity from config
        verbosity_str = self.config.get("verbosity", "STANDARD").upper()
        try:
            verbosity = VerbosityLevel[verbosity_str]
        except KeyError:
            # Fall back to default if invalid
            verbosity = VerbosityLevel.STANDARD
            
        self.prompt_service = prompt_service or PromptService(verbosity=verbosity)
        
        # Initialize handler registry
        self.handler_registry = HandlerRegistry()
        
        # Track initialization state
        self.initialized = False
        
    def _setup_llm(self):
        """Set up the LLM model based on configuration."""
        model_name = self.config.get("llm_model")
        if not model_name:
            return
            
        self.logger.info(f"Setting up LLM model: {model_name}")
        try:
            # Currently we only support Ollama models
            if ":" in model_name:  # Format like "deepseek-r1:1.5b"
                llm = Ollama(
                    model=model_name,
                    request_timeout=self.config.get("timeout", 30.0)
                )
                Settings.llm = llm
                self.logger.info(f"Set Ollama LLM to {model_name}")
            else:
                self.logger.warning(f"Unsupported LLM model format: {model_name}")
        except Exception as e:
            self.logger.error(f"Error setting up LLM model: {e}")
        
    def configure(self, **kwargs):
        """
        Configure the engine with custom settings.
        
        Args:
            **kwargs: Configuration options to set
        """
        # Update configuration
        self.config.update(**kwargs)
        
        # Update component configurations as needed
        if "verbosity" in kwargs:
            try:
                verbosity_str = kwargs["verbosity"].upper()
                verbosity = VerbosityLevel[verbosity_str]
                self.prompt_service.set_verbosity(verbosity)
            except KeyError:
                # Just log a warning and continue with current verbosity
                self.logger.warning(f"Invalid verbosity level: {kwargs['verbosity']}. Using current setting.")
        
        # Update LLM if model changed
        if "llm_model" in kwargs:
            self._setup_llm()
            
        if "log_level" in kwargs or "log_file" in kwargs:
            setup_logging(
                log_level=self.config.get("log_level", "INFO"),
                log_file=self.config.get("log_file")
            )
            
        self.logger.info("Engine configuration updated")
                
    def load(self):
        """
        Load data and initialize components.
        
        This method loads documents, initializes components, and registers handlers.
        Call this method before handling queries, or let the engine call it automatically
        on the first query.
        """
        if self.initialized:
            self.logger.debug("Engine already initialized, skipping load")
            return
            
        start_time = time.time()
        self.logger.info("Loading TransferAI Engine...")
        
        # Load documents
        self.logger.info("Loading documents...")
        self.document_repository.load_documents()
        
        # Set document repository in matching service
        if hasattr(self.matching_service, 'set_documents'):
            self.matching_service.set_documents(self.document_repository.documents)
        
        # Register handlers
        self.logger.info("Registering handlers...")
        self._register_handlers()
        
        # Mark as initialized
        self.initialized = True
        
        elapsed = time.time() - start_time
        self.logger.info(f"TransferAI Engine loaded in {elapsed:.2f} seconds")
        
    def handle_query(self, query_text: str) -> Optional[str]:
        """
        Process a user query and generate response.
        
        Args:
            query_text: The raw query text
            
        Returns:
            Formatted response string, or None if processing failed
        """
        if not self.initialized:
            self.logger.info("Engine not initialized, initializing now...")
            self.load()
            
        if not self.document_repository.documents:
            self.logger.warning("⚠️ No documents loaded.")
            return "No documents loaded. Unable to process query."
            
        start_time = time.time()
        self.logger.info(f"Processing query: {query_text}")
        
        try:
            # Extract filters from the query
            filters = self.query_service.extract_filters(
                query_text,
                uc_course_catalog=self.document_repository.uc_course_catalog,
                ccc_course_catalog=self.document_repository.ccc_course_catalog
            )
            
            self.logger.debug(f"Extracted filters: {filters}")
            
            # Create query object
            query = Query(
                text=query_text,
                filters=filters,
                config=self.config.as_dict()
            )
            
            # Determine query type
            query.query_type = self.query_service.determine_query_type(query)
            self.logger.debug(f"Determined query type: {query.query_type}")
            
            # Find handler
            handler = self.handler_registry.find_handler(query)
            if not handler:
                self.logger.warning("No handler found for query")
                return "I'm unable to process this query."
                
            self.logger.info(f"Using handler: {handler.__class__.__name__}")
            
            # Process query
            result = handler.handle(query)
            if not result:
                self.logger.warning("Handler returned no result")
                return "No relevant information found."
                
            elapsed = time.time() - start_time
            self.logger.info(f"Query processed in {elapsed:.2f} seconds")
            
            return result.formatted_response
                
        except Exception as e:
            self.logger.error(f"Error processing query: {e}", exc_info=True)
            if self.config.get("debug_mode", False):
                return format_error(e, include_traceback=True)
            else:
                return "An error occurred while processing your query."
    
    def _register_handlers(self):
        """
        Register query handlers with the registry.
        
        Creates instances of all available handlers and registers them with
        the handler registry in the correct order of precedence.
        """
        # Import handler implementations
        from llm.handlers.validation_handler import ValidationQueryHandler
        from llm.handlers.course_handler import CourseEquivalencyHandler
        from llm.handlers.course_lookup_handler import CourseLookupHandler
        from llm.handlers.group_handler import GroupQueryHandler
        from llm.handlers.honors_handler import HonorsQueryHandler
        from llm.handlers.fallback_handler import FallbackQueryHandler
        
        # Handler classes in order of precedence
        handler_classes = [
            ValidationQueryHandler,  # Most specific handler first
            CourseEquivalencyHandler,
            CourseLookupHandler,     # Add our new handler with appropriate precedence
            GroupQueryHandler,
            HonorsQueryHandler,
            FallbackQueryHandler,    # Fallback handler last
        ]
        
        # Create and register handlers in order
        handlers = []
        for handler_cls in handler_classes:
            try:
                self.logger.debug(f"Creating handler: {handler_cls.__name__}")
                handler = handler_cls(self.document_repository, self.config.as_dict())
                handlers.append(handler)
            except Exception as e:
                self.logger.error(f"Error creating handler {handler_cls.__name__}: {e}", exc_info=True)
        
        self.logger.info(f"Registering {len(handlers)} handlers")
        self.handler_registry.register_all(handlers)

    def _auto_register_handlers(self):
        """
        Automatically discover and register handlers.
        
        This is an alternative to explicitly registering handlers,
        which discovers handlers dynamically.
        """
        # Import the base class
        from llm.handlers.base import QueryHandler
        
        # Load handler classes
        handler_classes = load_handler_classes("llm.handlers", QueryHandler)
        
        # Sort handler classes by precedence - lower precedence gets registered first
        handler_classes.sort(key=lambda cls: getattr(cls, 'PRECEDENCE', 100))
        
        # Create and register handlers
        handlers = []
        for handler_cls in handler_classes:
            try:
                self.logger.debug(f"Creating auto-discovered handler: {handler_cls.__name__}")
                handler = handler_cls(self.document_repository, self.config.as_dict())
                handlers.append(handler)
            except Exception as e:
                self.logger.error(f"Error creating handler {handler_cls.__name__}: {e}", exc_info=True)
        
        self.logger.info(f"Auto-registering {len(handlers)} handlers")
        self.handler_registry.register_all(handlers)
        
    def __str__(self):
        return f"TransferAIEngine(version={get_version()}, handlers={len(self.handler_registry.handlers) if hasattr(self.handler_registry, 'handlers') else 0})"
        
    def __repr__(self):
        return self.__str__()
