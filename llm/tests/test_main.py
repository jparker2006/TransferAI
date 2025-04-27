"""
Tests for the main TransferAI engine functionality.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from llm.main import TransferAIEngine
from llm.prompt_builder import VerbosityLevel


class TestTransferAIEngine(unittest.TestCase):
    """Test cases for the TransferAIEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.engine = TransferAIEngine()

    def test_initialization(self):
        """Test that the engine initializes correctly."""
        self.assertIsNotNone(self.engine)
        self.assertEqual(len(self.engine.documents), 0)
        self.assertIsNone(self.engine.llm)
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.STANDARD)
        self.assertFalse(self.engine.config["debug_mode"])

    def test_configure(self):
        """Test the configuration method."""
        # Test setting known configuration options
        self.engine.configure(debug_mode=True, temperature=0.5)
        self.assertTrue(self.engine.config["debug_mode"])
        self.assertEqual(self.engine.config["temperature"], 0.5)
        
        # Test setting unknown configuration option (should be ignored)
        self.engine.configure(unknown_option="value")
        self.assertNotIn("unknown_option", self.engine.config)

    def test_verbosity_configuration(self):
        """Test setting verbosity levels."""
        # Test setting verbosity with enum
        self.engine.configure(verbosity=VerbosityLevel.MINIMAL)
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.MINIMAL)
        
        # Test setting verbosity with string
        self.engine.configure(verbosity="DETAILED")
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.DETAILED)
        
        # Test invalid verbosity string (should default to STANDARD)
        self.engine.configure(verbosity="INVALID")
        self.assertEqual(self.engine.config["verbosity"], VerbosityLevel.STANDARD)

    @patch('llm.document_loader.load_documents')
    def test_load(self, mock_load_documents):
        """Test loading documents."""
        mock_docs = [MagicMock(), MagicMock()]
        mock_load_documents.return_value = mock_docs
        
        self.engine.load()
        
        mock_load_documents.assert_called_once()
        self.assertEqual(self.engine.documents, mock_docs)

    @patch('llm.main.TransferAIEngine._call_llm')
    @patch('llm.main.build_prompt')
    def test_verbosity_in_handle_query(self, mock_build_prompt, mock_call_llm):
        """Test that verbosity level is passed to build_prompt."""
        # Setup
        self.engine.documents = [MagicMock()]
        self.engine.documents[0].metadata = {
            "uc_course": "CSE 11",
            "uc_title": "Introduction to Programming",
            "logic_block": {}
        }
        
        mock_call_llm.return_value = "Response"
        
        # Test with MINIMAL verbosity
        self.engine.configure(verbosity=VerbosityLevel.MINIMAL)
        self.engine._find_matching_documents = MagicMock(return_value=[self.engine.documents[0]])
        self.engine._generate_response = MagicMock()
        
        self.engine.handle_query("What courses satisfy CSE 11?")
        
        # Verify verbosity was passed correctly
        calls = mock_build_prompt.call_args_list
        for call in calls:
            if 'verbosity' in call.kwargs:
                self.assertEqual(call.kwargs['verbosity'], VerbosityLevel.MINIMAL)
        
        # Test with DETAILED verbosity
        self.engine.configure(verbosity=VerbosityLevel.DETAILED)
        self.engine.handle_query("What courses satisfy CSE 11?")
        
        calls = mock_build_prompt.call_args_list
        for call in calls:
            if 'verbosity' in call.kwargs:
                self.assertEqual(call.kwargs['verbosity'], VerbosityLevel.DETAILED)


if __name__ == '__main__':
    unittest.main() 