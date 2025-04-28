"""
Unit tests for the TransferAIEngine class.

These tests verify that the engine properly initializes components,
routes queries to the appropriate handlers, and handles errors gracefully.
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from llm.engine.transfer_engine import TransferAIEngine
from llm.engine.config import Config, Environment
from llm.models.query import Query, QueryResult, QueryType
from llm.repositories.document_repository import DocumentRepository
from llm.services.query_service import QueryService
from llm.services.matching_service import MatchingService
from llm.services.prompt_service import PromptService
from llm.handlers.base import QueryHandler, HandlerRegistry


class TestTransferAIEngine(unittest.TestCase):
    """Test suite for the TransferAIEngine class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_config = MagicMock(spec=Config)
        self.mock_config.get.return_value = "STANDARD"
        self.mock_config.as_dict.return_value = {"verbosity": "STANDARD"}
        
        self.mock_doc_repo = MagicMock(spec=DocumentRepository)
        self.mock_doc_repo.documents = ["doc1", "doc2"]
        self.mock_doc_repo.uc_course_catalog = set(["CSE 8A", "CSE 8B"])
        self.mock_doc_repo.ccc_course_catalog = set(["MATH 1A", "MATH 1B"])
        
        self.mock_query_service = MagicMock(spec=QueryService)
        self.mock_matching_service = MagicMock(spec=MatchingService)
        self.mock_prompt_service = MagicMock(spec=PromptService)
        
        # Create a mock handler registry
        self.mock_handler_registry = MagicMock(spec=HandlerRegistry)
        
        # Create engine with mock dependencies
        with patch('llm.engine.transfer_engine.HandlerRegistry', return_value=self.mock_handler_registry):
            self.engine = TransferAIEngine(
                config=self.mock_config,
                document_repository=self.mock_doc_repo,
                query_service=self.mock_query_service,
                matching_service=self.mock_matching_service,
                prompt_service=self.mock_prompt_service
            )
        
        # Reset mocks to clear initialization calls
        self.mock_config.reset_mock()
        self.mock_doc_repo.reset_mock()
        self.mock_query_service.reset_mock()
        self.mock_matching_service.reset_mock()
        self.mock_prompt_service.reset_mock()
        self.mock_handler_registry.reset_mock()
    
    def test_init_with_defaults(self):
        """Test initialization with default dependencies."""
        with patch('llm.engine.transfer_engine.get_config') as mock_get_config, \
             patch('llm.engine.transfer_engine.DocumentRepository') as mock_doc_repo_cls, \
             patch('llm.engine.transfer_engine.QueryService') as mock_query_service_cls, \
             patch('llm.engine.transfer_engine.MatchingService') as mock_matching_service_cls, \
             patch('llm.engine.transfer_engine.PromptService') as mock_prompt_service_cls, \
             patch('llm.engine.transfer_engine.HandlerRegistry') as mock_registry_cls:
            
            # Create default mocks for dependency initialization
            mock_config = MagicMock(spec=Config)
            mock_config.get.return_value = "STANDARD"
            mock_get_config.return_value = mock_config
            
            # Create engine with default dependencies
            engine = TransferAIEngine()
            
            # Verify dependencies were created
            mock_get_config.assert_called_once()
            mock_doc_repo_cls.assert_called_once()
            mock_query_service_cls.assert_called_once()
            mock_matching_service_cls.assert_called_once()
            mock_prompt_service_cls.assert_called_once()
            mock_registry_cls.assert_called_once()
            
            # Verify engine is not initialized
            self.assertFalse(engine.initialized)
    
    def test_configure(self):
        """Test engine configuration."""
        # Configure engine
        self.engine.configure(
            verbosity="DETAILED",
            debug_mode=True,
            log_level="DEBUG"
        )
        
        # Verify config was updated
        self.mock_config.update.assert_called_once_with(
            verbosity="DETAILED",
            debug_mode=True,
            log_level="DEBUG"
        )
        
        # Verify prompt service verbosity was updated
        self.mock_prompt_service.set_verbosity.assert_called_once()
    
    @patch('llm.handlers.validation_handler.ValidationQueryHandler')
    @patch('llm.handlers.course_handler.CourseEquivalencyHandler')
    @patch('llm.handlers.group_handler.GroupQueryHandler') 
    @patch('llm.handlers.honors_handler.HonorsQueryHandler')
    @patch('llm.handlers.fallback_handler.FallbackQueryHandler')
    def test_register_handlers(self, mock_fallback, mock_honors, mock_group, 
                               mock_course, mock_validation):
        """Test handler registration."""
        # Setup mock handler instances
        handler_mocks = [
            MagicMock(spec=QueryHandler),
            MagicMock(spec=QueryHandler),
            MagicMock(spec=QueryHandler),
            MagicMock(spec=QueryHandler),
            MagicMock(spec=QueryHandler)
        ]
        
        # Setup __name__ attributes to prevent AttributeError
        mock_validation.__name__ = "ValidationQueryHandler"
        mock_course.__name__ = "CourseEquivalencyHandler"
        mock_group.__name__ = "GroupQueryHandler"
        mock_honors.__name__ = "HonorsQueryHandler"
        mock_fallback.__name__ = "FallbackQueryHandler"
        
        # Make each handler class return its mock instance
        mock_validation.return_value = handler_mocks[0]
        mock_course.return_value = handler_mocks[1]
        mock_group.return_value = handler_mocks[2]
        mock_honors.return_value = handler_mocks[3]
        mock_fallback.return_value = handler_mocks[4]
        
        # Call method under test - don't patch as we've already patched the actual handler classes
        self.engine._register_handlers()
            
        # Verify all handler classes were instantiated
        mock_validation.assert_called_once_with(self.mock_doc_repo, self.mock_config.as_dict())
        mock_course.assert_called_once_with(self.mock_doc_repo, self.mock_config.as_dict())
        mock_group.assert_called_once_with(self.mock_doc_repo, self.mock_config.as_dict())
        mock_honors.assert_called_once_with(self.mock_doc_repo, self.mock_config.as_dict())
        mock_fallback.assert_called_once_with(self.mock_doc_repo, self.mock_config.as_dict())
        
        # Verify handlers were registered
        self.mock_handler_registry.register_all.assert_called_once()
    
    def test_load(self):
        """Test engine loading."""
        # Setup mocks
        self.engine._register_handlers = MagicMock()
        
        # Call method under test
        self.engine.load()
        
        # Verify documents were loaded
        self.mock_doc_repo.load_documents.assert_called_once()
        
        # Verify handlers were registered
        self.engine._register_handlers.assert_called_once()
        
        # Verify engine is initialized
        self.assertTrue(self.engine.initialized)
        
        # Call load again
        self.mock_doc_repo.reset_mock()
        self.engine._register_handlers.reset_mock()
        self.engine.load()
        
        # Verify nothing happened on second load
        self.mock_doc_repo.load_documents.assert_not_called()
        self.engine._register_handlers.assert_not_called()
    
    def test_handle_query_successful(self):
        """Test successful query handling."""
        # Setup mocks
        self.engine.initialized = True
        self.mock_query_service.extract_filters.return_value = {"uc_course": ["CSE 8A"]}
        self.mock_query_service.determine_query_type.return_value = QueryType.COURSE_EQUIVALENCY
        
        mock_handler = MagicMock(spec=QueryHandler)
        mock_result = MagicMock(spec=QueryResult)
        mock_result.formatted_response = "Test response"
        mock_handler.handle.return_value = mock_result
        
        self.mock_handler_registry.find_handler.return_value = mock_handler
        
        # Call method under test
        result = self.engine.handle_query("What satisfies CSE 8A?")
        
        # Verify query was processed
        self.mock_query_service.extract_filters.assert_called_once()
        self.mock_query_service.determine_query_type.assert_called_once()
        self.mock_handler_registry.find_handler.assert_called_once()
        mock_handler.handle.assert_called_once()
        
        # Verify result
        self.assertEqual(result, "Test response")
    
    def test_handle_query_not_initialized(self):
        """Test query handling when engine is not initialized."""
        # Setup mocks
        self.engine.initialized = False
        self.engine.load = MagicMock()
        
        # Setup handler mock
        mock_handler = MagicMock(spec=QueryHandler)
        mock_result = MagicMock(spec=QueryResult)
        mock_result.formatted_response = "Test response"
        mock_handler.handle.return_value = mock_result
        self.mock_handler_registry.find_handler.return_value = mock_handler
        
        # Call method under test
        self.engine.handle_query("What satisfies CSE 8A?")
        
        # Verify engine was loaded
        self.engine.load.assert_called_once()
    
    def test_handle_query_no_documents(self):
        """Test query handling when no documents are loaded."""
        # Setup mocks
        self.engine.initialized = True
        self.mock_doc_repo.documents = []
        
        # Call method under test
        result = self.engine.handle_query("What satisfies CSE 8A?")
        
        # Verify result
        self.assertEqual(result, "No documents loaded. Unable to process query.")
    
    def test_handle_query_no_handler(self):
        """Test query handling when no handler is found."""
        # Setup mocks
        self.engine.initialized = True
        self.mock_query_service.extract_filters.return_value = {"uc_course": ["CSE 8A"]}
        self.mock_query_service.determine_query_type.return_value = QueryType.UNKNOWN
        self.mock_handler_registry.find_handler.return_value = None
        
        # Call method under test
        result = self.engine.handle_query("What satisfies CSE 8A?")
        
        # Verify result
        self.assertEqual(result, "I'm unable to process this query.")
    
    def test_handle_query_no_result(self):
        """Test query handling when handler returns no result."""
        # Setup mocks
        self.engine.initialized = True
        self.mock_query_service.extract_filters.return_value = {"uc_course": ["CSE 8A"]}
        self.mock_query_service.determine_query_type.return_value = QueryType.COURSE_EQUIVALENCY
        
        mock_handler = MagicMock(spec=QueryHandler)
        mock_handler.handle.return_value = None
        self.mock_handler_registry.find_handler.return_value = mock_handler
        
        # Call method under test
        result = self.engine.handle_query("What satisfies CSE 8A?")
        
        # Verify result
        self.assertEqual(result, "No relevant information found.")
    
    def test_handle_query_exception(self):
        """Test query handling when an exception occurs."""
        # Setup mocks
        self.engine.initialized = True
        self.mock_query_service.extract_filters.side_effect = Exception("Test exception")
        self.mock_config.get.return_value = False  # debug_mode = False
        
        # Call method under test
        result = self.engine.handle_query("What satisfies CSE 8A?")
        
        # Verify result
        self.assertEqual(result, "An error occurred while processing your query.")
        
        # With debug mode
        self.mock_config.get.return_value = True  # debug_mode = True
        result = self.engine.handle_query("What satisfies CSE 8A?")
        self.assertIn("Test exception", result)
    
    @patch('llm.engine.transfer_engine.load_handler_classes')
    def test_auto_register_handlers(self, mock_load_classes):
        """Test automatic handler registration."""
        # Create handler class mocks with PRECEDENCE attributes
        handler_class1 = MagicMock()
        handler_class1.__name__ = "MockHandler1"
        handler_class1.PRECEDENCE = 10
        
        handler_class2 = MagicMock()
        handler_class2.__name__ = "MockHandler2"
        handler_class2.PRECEDENCE = 20
        
        # Setup handler instances
        handler_instance1 = MagicMock(spec=QueryHandler)
        handler_instance2 = MagicMock(spec=QueryHandler)
        
        # Setup returns
        handler_class1.return_value = handler_instance1
        handler_class2.return_value = handler_instance2
        mock_load_classes.return_value = [handler_class2, handler_class1]  # Intentionally out of order
        
        # Call method under test
        self.engine._auto_register_handlers()
        
        # Verify handler classes were sorted by precedence
        self.mock_handler_registry.register_all.assert_called_once()
        
        # Check handlers are registered in correct order (lowest precedence first)
        args, _ = self.mock_handler_registry.register_all.call_args
        self.assertEqual(len(args[0]), 2)


class TestTransferAIEngineIntegration(unittest.TestCase):
    """Integration tests for the TransferAIEngine class."""
    
    @patch('llm.handlers.validation_handler.ValidationQueryHandler')
    @patch('llm.handlers.course_handler.CourseEquivalencyHandler')
    @patch('llm.handlers.group_handler.GroupQueryHandler')
    @patch('llm.handlers.honors_handler.HonorsQueryHandler')
    @patch('llm.handlers.fallback_handler.FallbackQueryHandler')
    def test_integration(self, mock_fallback, mock_honors, mock_group, 
                        mock_course, mock_validation):
        """Integration test for the full query handling flow."""
        # Setup __name__ attributes to prevent AttributeError
        mock_validation.__name__ = "ValidationQueryHandler"
        mock_course.__name__ = "CourseEquivalencyHandler"
        mock_group.__name__ = "GroupQueryHandler"
        mock_honors.__name__ = "HonorsQueryHandler"
        mock_fallback.__name__ = "FallbackQueryHandler"
        
        # Setup mock config
        config = MagicMock(spec=Config)
        config.get.return_value = "STANDARD"
        config.as_dict.return_value = {"verbosity": "STANDARD"}
        
        # Setup mock document repository
        doc_repo = MagicMock(spec=DocumentRepository)
        doc_repo.documents = ["doc1", "doc2"]
        doc_repo.uc_course_catalog = set(["CSE 8A", "CSE 8B"])
        doc_repo.ccc_course_catalog = set(["MATH 1A", "MATH 1B"])  # Using correct attribute name
        
        # Setup mock query service
        query_service = MagicMock(spec=QueryService)
        query_service.extract_filters.return_value = {"uc_course": ["CSE 8A"]}
        query_service.determine_query_type.return_value = QueryType.COURSE_EQUIVALENCY
        
        # Setup mock handler
        mock_handler = MagicMock(spec=QueryHandler)
        mock_result = MagicMock(spec=QueryResult)
        mock_result.formatted_response = "Test integration response"
        mock_handler.handle.return_value = mock_result
        mock_course.return_value = mock_handler
        
        # Setup mock handler registry
        mock_registry = MagicMock(spec=HandlerRegistry)
        mock_registry.find_handler.return_value = mock_handler
        
        # Create engine with mocks
        with patch('llm.engine.transfer_engine.HandlerRegistry', return_value=mock_registry):
            engine = TransferAIEngine(
                config=config,
                document_repository=doc_repo,
                query_service=query_service
            )
            
            # Mark as initialized to skip loading
            engine.initialized = True
            
            # Test query handling
            result = engine.handle_query("What satisfies CSE 8A?")
            
            # Verify result
            self.assertEqual(result, "Test integration response")
            
            # Verify flow
            query_service.extract_filters.assert_called_once()
            query_service.determine_query_type.assert_called_once()
            mock_registry.find_handler.assert_called_once()
            mock_handler.handle.assert_called_once()


if __name__ == "__main__":
    unittest.main() 