"""
Unit tests for the PromptService class.

These tests verify that the prompt service correctly selects, prepares, and renders
templates for different types of queries.
"""

import unittest
from unittest.mock import patch, MagicMock

from llm.services.prompt_service import PromptService, PromptType, VerbosityLevel, build_prompt


class TestPromptService(unittest.TestCase):
    """Test suite for the PromptService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = PromptService()
    
    def test_init_default_verbosity(self):
        """Test that the service initializes with default verbosity."""
        self.assertEqual(self.service.verbosity, VerbosityLevel.STANDARD)
    
    def test_init_custom_verbosity(self):
        """Test that the service initializes with custom verbosity."""
        service = PromptService(verbosity=VerbosityLevel.MINIMAL)
        self.assertEqual(service.verbosity, VerbosityLevel.MINIMAL)
        
        service = PromptService(verbosity="DETAILED")
        self.assertEqual(service.verbosity, VerbosityLevel.DETAILED)
    
    def test_set_verbosity(self):
        """Test setting verbosity after initialization."""
        self.service.set_verbosity(VerbosityLevel.DETAILED)
        self.assertEqual(self.service.verbosity, VerbosityLevel.DETAILED)
        
        self.service.set_verbosity("MINIMAL")
        self.assertEqual(self.service.verbosity, VerbosityLevel.MINIMAL)
    
    def test_normalize_verbosity_invalid(self):
        """Test normalization of invalid verbosity values."""
        self.assertEqual(self.service._normalize_verbosity("INVALID"), VerbosityLevel.STANDARD)
        self.assertEqual(self.service._normalize_verbosity(123), VerbosityLevel.STANDARD)
    
    def test_get_verbosity_key(self):
        """Test getting the verbosity key."""
        self.service.verbosity = VerbosityLevel.MINIMAL
        self.assertEqual(self.service.get_verbosity_key(), "MINIMAL")
        
        self.service.verbosity = VerbosityLevel.STANDARD
        self.assertEqual(self.service.get_verbosity_key(), "STANDARD")
        
        self.service.verbosity = VerbosityLevel.DETAILED
        self.assertEqual(self.service.get_verbosity_key(), "DETAILED")
    
    @patch('llm.templates.helpers.enrich_with_descriptions')
    def test_build_course_prompt(self, mock_enrich):
        """Test building a course prompt."""
        # Set up mock
        mock_enrich.return_value = "Enriched logic text"
        
        # Test with minimal verbosity
        self.service.verbosity = VerbosityLevel.MINIMAL
        prompt = self.service._build_course_prompt(
            user_question="What satisfies CSE 8A?",
            rendered_logic="Sample logic",
            uc_course="CSE 8A",
            uc_course_title="Intro to Programming",
            is_no_articulation=False
        )
        
        # Verify basic structure
        self.assertIn("CSE 8A", prompt)
        self.assertIn("What satisfies CSE 8A?", prompt)
        self.assertIn("Enriched logic", prompt)
        self.assertIn("Be extremely brief", prompt)
        
        # Test with standard verbosity
        self.service.verbosity = VerbosityLevel.STANDARD
        prompt = self.service._build_course_prompt(
            user_question="What satisfies CSE 8A?",
            rendered_logic="Sample logic",
            uc_course="CSE 8A",
            uc_course_title="Intro to Programming",
            is_no_articulation=False
        )
        
        self.assertIn("You are TransferAI", prompt)
        self.assertIn("Be clear but concise", prompt)
    
    @patch('llm.templates.helpers.enrich_with_descriptions')
    def test_build_group_prompt(self, mock_enrich):
        """Test building a group prompt."""
        # Set up mock
        mock_enrich.return_value = "Enriched group logic"
        
        # Test with minimal verbosity
        self.service.verbosity = VerbosityLevel.MINIMAL
        prompt = self.service._build_group_prompt(
            user_question="What satisfies Group 1?",
            rendered_logic="Sample group logic",
            group_id="1",
            group_title="Math Requirement",
            group_logic_type="select_n_courses",
            n_courses=2
        )
        
        # Verify basic structure
        self.assertIn("Group: 1", prompt)
        self.assertIn("What satisfies Group 1?", prompt)
        self.assertIn("Enriched group logic", prompt)
        self.assertIn("Be extremely brief", prompt)
        
        # Test with detailed verbosity
        self.service.verbosity = VerbosityLevel.DETAILED
        prompt = self.service._build_group_prompt(
            user_question="What satisfies Group 1?",
            rendered_logic="Sample group logic",
            group_id="1",
            group_title="Math Requirement",
            group_logic_type="select_n_courses",
            n_courses=2
        )
        
        self.assertIn("thorough explanation", prompt.lower())
        self.assertIn("Math Requirement", prompt)
    
    @patch('llm.services.prompt_service.PromptService._build_course_prompt')
    @patch('llm.services.prompt_service.PromptService._build_group_prompt')
    def test_build_prompt_routing(self, mock_group, mock_course):
        """Test that build_prompt routes to the appropriate method."""
        # Set up mocks
        mock_course.return_value = "Course prompt"
        mock_group.return_value = "Group prompt"
        
        # Test course prompt
        result = self.service.build_prompt(
            prompt_type=PromptType.COURSE_EQUIVALENCY,
            user_question="What satisfies CSE 8A?",
            rendered_logic="Logic",
            uc_course="CSE 8A"
        )
        
        mock_course.assert_called_once()
        self.assertEqual(result, "Course prompt")
        
        # Reset mocks
        mock_course.reset_mock()
        mock_group.reset_mock()
        
        # Test group prompt
        result = self.service.build_prompt(
            prompt_type=PromptType.GROUP_LOGIC,
            user_question="What satisfies Group 1?",
            rendered_logic="Logic",
            group_id="1"
        )
        
        mock_group.assert_called_once()
        self.assertEqual(result, "Group prompt")
    
    @patch('llm.services.prompt_service.PromptService.build_prompt')
    def test_backward_compatibility(self, mock_build):
        """Test the backward compatibility function."""
        # Set up mock
        mock_build.return_value = "Compatible prompt"
        
        # Test backward compatibility function
        result = build_prompt(
            logic="Logic text",
            user_question="What satisfies CSE 8A?",
            uc_course="CSE 8A",
            prompt_type=PromptType.COURSE_EQUIVALENCY,
            verbosity=VerbosityLevel.STANDARD
        )
        
        # Verify service was created and called correctly
        mock_build.assert_called_once()
        self.assertEqual(result, "Compatible prompt")
    
    def test_no_articulation_detection(self):
        """Test detection of no articulation courses."""
        # Create a mock to avoid dependency on enrich_with_descriptions
        with patch('llm.templates.helpers.enrich_with_descriptions', return_value="Enriched logic"):
            # Test no articulation detection
            prompt = self.service._build_course_prompt(
                user_question="What satisfies CSE 8A?",
                rendered_logic="Sample logic",
                uc_course="CSE 8A",
                uc_course_title="Intro to Programming",
                is_no_articulation=True
            )
            
            self.assertIn("must be completed at UC San Diego", prompt)
            self.assertNotIn("following De Anza course options", prompt)


if __name__ == "__main__":
    unittest.main() 