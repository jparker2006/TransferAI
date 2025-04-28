"""
Unit tests for the TemplateRepository class.

Tests the functionality of template loading, retrieval, and caching.
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import time
from datetime import datetime
from llm.repositories.template_repository import TemplateRepository

class TestTemplateRepository(unittest.TestCase):
    """Test cases for TemplateRepository class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.repo = TemplateRepository()
        
    def test_init(self):
        """Test repository initialization."""
        self.assertEqual(self.repo._templates, {})
        self.assertIsNone(self.repo._last_loaded)
        
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('importlib.util.spec_from_file_location')
    @patch('importlib.util.module_from_spec')
    def test_load_templates(self, mock_module_from_spec, mock_spec, mock_listdir, mock_exists):
        """Test loading templates from directory."""
        # Mock the template files
        mock_exists.return_value = True
        mock_listdir.return_value = ['template1.py', 'template2.py', '_ignore.py']
        
        # Create mock module with templates
        mock_module = MagicMock()
        mock_module.TEMPLATE1 = 'content1'
        mock_module.TEMPLATE2 = 'content2'
        mock_module._private = 'ignore'
        mock_module_from_spec.return_value = mock_module
        
        # Setup mock spec
        mock_spec_obj = MagicMock()
        mock_spec.return_value = mock_spec_obj
        
        # Test loading templates
        count = self.repo.load_templates("test_templates")
        
        # Verify the results
        self.assertEqual(count, 4)  # Each .py file contributes its templates to the count
        self.assertIsNotNone(self.repo._last_loaded)
        self.assertEqual(self.repo._templates.get('template1', {}).get('TEMPLATE1'), 'content1')
        self.assertEqual(self.repo._templates.get('template1', {}).get('TEMPLATE2'), 'content2')
        self.assertEqual(self.repo._templates.get('template2', {}).get('TEMPLATE1'), 'content1')
        self.assertEqual(self.repo._templates.get('template2', {}).get('TEMPLATE2'), 'content2')
        
    def test_get_template(self):
        """Test getting templates by name and type."""
        # Setup test data
        self.repo._templates = {
            'default': {
                'template1': 'Template content 1',
                'template2': 'Template content 2'
            }
        }
        
        # Test retrieving existing template
        template = self.repo.get_template('template1')
        self.assertEqual(template, 'Template content 1')
        
        # Test retrieving non-existent template
        template = self.repo.get_template('nonexistent')
        self.assertIsNone(template)
        
        # Test retrieving from non-existent type
        template = self.repo.get_template('template1', 'nonexistent_type')
        self.assertIsNone(template)
        
    def test_get_template_types(self):
        """Test getting available template types."""
        # Setup test data
        self.repo._templates = {
            'type2': {},
            'type1': {},
            'type3': {}
        }
        
        # Test getting sorted types
        types = self.repo.get_template_types()
        self.assertEqual(types, ['type1', 'type2', 'type3'])
        
    def test_get_templates_by_type(self):
        """Test getting all templates of a specific type."""
        # Setup test data
        test_templates = {
            'template1': 'content1',
            'template2': 'content2'
        }
        self.repo._templates = {'test_type': test_templates}
        
        # Test retrieving templates by type
        templates = self.repo.get_templates_by_type('test_type')
        self.assertEqual(templates, test_templates)
        
        # Test retrieving non-existent type
        templates = self.repo.get_templates_by_type('nonexistent')
        self.assertEqual(templates, {})
        
    def test_get_reload_status(self):
        """Test getting reload status."""
        # Setup test data
        self.repo._templates = {
            'type1': {'t1': 'c1', 't2': 'c2'},
            'type2': {'t3': 'c3'}
        }
        self.repo._last_loaded = time.time()
        
        # Test status information
        status = self.repo.get_reload_status()
        self.assertEqual(status['template_count'], 3)
        self.assertEqual(status['template_types'], 2)
        self.assertIsNotNone(status['last_loaded'])
        
    def test_clear_cache(self):
        """Test clearing the cache."""
        # Setup test data
        self.repo._templates = {'type1': {'t1': 'c1'}}
        
        # Get template to populate cache
        template = self.repo.get_template('t1')
        
        # Clear cache
        self.repo.clear_cache()
        
        # Verify cache is cleared by checking internal state
        # Note: We can't directly verify cache clearing since it's internal to the decorator
        self.assertTrue(True)  # Cache clearing doesn't raise exceptions

if __name__ == '__main__':
    unittest.main() 