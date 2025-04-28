"""
Unit tests for the main entry point of TransferAI.

Tests the command-line interface, configuration handling, and error cases.
"""

import unittest
from unittest.mock import patch, MagicMock
import argparse
import logging
from llm.main import TransferAIEngine, VerbosityLevel, ConfigurationError, DocumentLoadError, QueryProcessingError

class TestMainEntryPoint(unittest.TestCase):
    """Test cases for the main entry point."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TransferAIEngine()
        
    def test_init_default_config(self):
        """Test initialization with default configuration."""
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.STANDARD)
        self.assertFalse(self.engine.config["debug_mode"])
        self.assertEqual(self.engine.config["timeout"], 30)
        self.assertEqual(self.engine.config["temperature"], 0.2)
        self.assertEqual(self.engine.config["max_tokens"], 1000)
        
    def test_configure_verbosity(self):
        """Test configuring verbosity level."""
        self.engine.configure(verbosity="DETAILED")
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.DETAILED)
        
        # Test invalid verbosity
        with self.assertLogs(level='WARNING'):
            self.engine.configure(verbosity="INVALID")
            self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.STANDARD)
            
    def test_configure_debug_mode(self):
        """Test configuring debug mode."""
        self.engine.configure(debug_mode=True)
        self.assertTrue(self.engine.config["debug_mode"])
        
    def test_configure_multiple_options(self):
        """Test configuring multiple options at once."""
        self.engine.configure(
            verbosity="DETAILED",
            debug_mode=True,
            timeout=60,
            temperature=0.5
        )
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.DETAILED)
        self.assertTrue(self.engine.config["debug_mode"])
        self.assertEqual(self.engine.config["timeout"], 60)
        self.assertEqual(self.engine.config["temperature"], 0.5)
        
    @patch('llm.document_loader.load_documents')
    def test_load_error_handling(self, mock_load):
        """Test error handling during document loading."""
        mock_load.return_value = None  # Simulate no documents loaded
        
        with self.assertRaises(DocumentLoadError):
            self.engine.load()
            
    def test_handle_query_error_handling(self):
        """Test error handling in query processing."""
        # Test empty query
        result = self.engine.handle_query("")
        self.assertIsNone(result)
        
        # Test query with no documents loaded
        with self.assertRaises(QueryProcessingError) as context:
            self.engine.handle_query("test query")
        self.assertEqual(str(context.exception), "No documents loaded. Unable to process query.")
        
        # Test query processing error
        with patch.object(self.engine, '_process_query_with_handler') as mock_process:
            mock_process.side_effect = Exception("Test error")
            with self.assertRaises(QueryProcessingError):
                self.engine.handle_query("test query")
        
    @patch('builtins.print')
    def test_cli_interface(self, mock_print):
        """Test command-line interface functionality."""
        with patch('argparse.ArgumentParser.parse_args') as mock_args:
            mock_args.return_value = argparse.Namespace(
                query="test query",
                verbosity="STANDARD",
                debug=False,
                use_new_architecture=False,
                log_level="INFO",
                config=None
            )
            
            # Import here to avoid circular import
            from llm.main import main
            
            # Mock sys.exit to prevent test from exiting
            with patch('sys.exit'):
                # Mock load_documents to return some data
                with patch('llm.document_loader.load_documents') as mock_load:
                    mock_load.return_value = [MagicMock(text="test")]
                    
                    # Mock query_engine to avoid actual LLM calls
                    with patch('llama_index.core.VectorStoreIndex.as_query_engine') as mock_engine:
                        mock_engine.return_value.query.return_value = "Test response"
                        
                        main()
                        
                        # Verify output
                        mock_print.assert_called()
            
    def test_backward_compatibility(self):
        """Test backward compatibility with old architecture."""
        # Test that old-style configuration still works
        old_engine = TransferAIEngine(verbosity=VerbosityLevel.STANDARD, debug_mode=False)
        self.assertEqual(old_engine.config["verbosity"], VerbosityLevel.STANDARD)
        
        # Test string-based verbosity
        old_engine = TransferAIEngine(verbosity="STANDARD", debug_mode=False)
        self.assertEqual(old_engine.config["verbosity"], VerbosityLevel.STANDARD)
        
        # Test that old-style method calls still work
        self.assertIsNotNone(old_engine.set_verbosity)
        self.assertIsNotNone(old_engine.configure)
        
if __name__ == '__main__':
    unittest.main() 