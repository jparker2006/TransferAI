"""
Test suite for the articulation.models module.

This module tests the Pydantic models in the articulation package, ensuring
that they properly validate inputs, handle serialization/deserialization,
and correctly enforce validation rules.

Tests focus on:
1. CourseOption model validation
2. LogicBlock model validation and nesting
3. ValidationResult model functionality
4. GroupLogicType enum values
5. GroupSection model validation
6. ArticulationGroup model with validation rules
"""

import unittest
import sys
import os
from typing import Dict, List, Any
import json
from pydantic import ValidationError

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm.articulation.models import (
    CourseOption,
    LogicBlock,
    ValidationResult,
    GroupLogicType,
    GroupSection,
    ArticulationGroup
)


class TestCourseOption(unittest.TestCase):
    """Test the CourseOption model for validation and serialization."""
    
    def test_init_with_valid_data(self):
        """Test initializing with valid data."""
        # Test with just required field
        course1 = CourseOption(course_letters="MATH 1A")
        self.assertEqual(course1.course_letters, "MATH 1A")
        self.assertEqual(course1.honors, False)  # Default value
        self.assertIsNone(course1.title)  # Default value
        self.assertIsNone(course1.course_id)  # Default value
        
        # Test with all fields
        course2 = CourseOption(
            course_letters="MATH 1AH",
            title="Calculus I Honors",
            honors=True,
            course_id="UC123"
        )
        self.assertEqual(course2.course_letters, "MATH 1AH")
        self.assertEqual(course2.title, "Calculus I Honors")
        self.assertEqual(course2.honors, True)
        self.assertEqual(course2.course_id, "UC123")
    
    def test_required_fields(self):
        """Test required fields (course_letters)."""
        # course_letters is required, so this should fail
        with self.assertRaises(ValidationError):
            CourseOption()
        
        # The error should mention course_letters
        try:
            CourseOption()
        except ValidationError as e:
            error_json = e.json()
            self.assertIn("course_letters", error_json)
    
    def test_optional_fields(self):
        """Test optional fields (title, honors, course_id)."""
        # Test setting each optional field individually
        course1 = CourseOption(course_letters="MATH 1A", title="Calculus I")
        self.assertEqual(course1.title, "Calculus I")
        self.assertEqual(course1.honors, False)  # Default value
        
        course2 = CourseOption(course_letters="MATH 1A", honors=True)
        self.assertEqual(course2.honors, True)
        self.assertIsNone(course2.title)  # Default value
        
        course3 = CourseOption(course_letters="MATH 1A", course_id="UC123")
        self.assertEqual(course3.course_id, "UC123")
        self.assertEqual(course3.honors, False)  # Default value
        self.assertIsNone(course3.title)  # Default value
    
    def test_serialization_to_dict(self):
        """Test serialization to dict."""
        course = CourseOption(
            course_letters="MATH 1A",
            title="Calculus I",
            honors=False,
            course_id="UC123"
        )
        
        # Convert to dict
        course_dict = course.dict()
        
        # Check dict values
        self.assertEqual(course_dict["course_letters"], "MATH 1A")
        self.assertEqual(course_dict["title"], "Calculus I")
        self.assertEqual(course_dict["honors"], False)
        self.assertEqual(course_dict["course_id"], "UC123")
    
    def test_deserialization_from_dict(self):
        """Test deserialization from dict."""
        # Create a dict
        course_dict = {
            "course_letters": "MATH 1A",
            "title": "Calculus I",
            "honors": False,
            "course_id": "UC123"
        }
        
        # Convert to CourseOption
        course = CourseOption(**course_dict)
        
        # Check values
        self.assertEqual(course.course_letters, "MATH 1A")
        self.assertEqual(course.title, "Calculus I")
        self.assertEqual(course.honors, False)
        self.assertEqual(course.course_id, "UC123")
        
        # Test with extra fields (should be ignored)
        course_dict_extra = {
            "course_letters": "MATH 1A",
            "title": "Calculus I",
            "honors": False,
            "course_id": "UC123",
            "extra_field": "should be ignored"
        }
        
        course_extra = CourseOption(**course_dict_extra)
        self.assertEqual(course_extra.course_letters, "MATH 1A")
        self.assertFalse(hasattr(course_extra, "extra_field"))


class TestLogicBlock(unittest.TestCase):
    """Test the LogicBlock model, particularly its recursive structure."""
    
    def test_simple_logic_block_with_course_options(self):
        """Test simple LogicBlock with course options."""
        # Create a simple OR block with course options
        logic_block = LogicBlock(
            type="OR",
            courses=[
                CourseOption(course_letters="MATH 1A"),
                CourseOption(course_letters="MATH 1AH", honors=True)
            ]
        )
        
        self.assertEqual(logic_block.type, "OR")
        self.assertEqual(len(logic_block.courses), 2)
        self.assertEqual(logic_block.courses[0].course_letters, "MATH 1A")
        self.assertEqual(logic_block.courses[1].course_letters, "MATH 1AH")
        self.assertEqual(logic_block.courses[1].honors, True)
        self.assertEqual(logic_block.no_articulation, False)  # Default value
        
        # Create a simple AND block with course options
        logic_block = LogicBlock(
            type="AND",
            courses=[
                CourseOption(course_letters="MATH 1A"),
                CourseOption(course_letters="MATH 1B")
            ]
        )
        
        self.assertEqual(logic_block.type, "AND")
        self.assertEqual(len(logic_block.courses), 2)
        self.assertEqual(logic_block.courses[0].course_letters, "MATH 1A")
        self.assertEqual(logic_block.courses[1].course_letters, "MATH 1B")
    
    def test_nested_logic_block(self):
        """Test nested LogicBlock (AND inside OR)."""
        # Create a nested block: (MATH 1A AND MATH 1B) OR (MATH 1AH AND MATH 1BH)
        logic_block = LogicBlock(
            type="OR",
            courses=[
                LogicBlock(
                    type="AND",
                    courses=[
                        CourseOption(course_letters="MATH 1A"),
                        CourseOption(course_letters="MATH 1B")
                    ]
                ),
                LogicBlock(
                    type="AND",
                    courses=[
                        CourseOption(course_letters="MATH 1AH", honors=True),
                        CourseOption(course_letters="MATH 1BH", honors=True)
                    ]
                )
            ]
        )
        
        self.assertEqual(logic_block.type, "OR")
        self.assertEqual(len(logic_block.courses), 2)
        
        # Check first nested block
        nested_block1 = logic_block.courses[0]
        self.assertEqual(nested_block1.type, "AND")
        self.assertEqual(len(nested_block1.courses), 2)
        self.assertEqual(nested_block1.courses[0].course_letters, "MATH 1A")
        self.assertEqual(nested_block1.courses[1].course_letters, "MATH 1B")
        
        # Check second nested block
        nested_block2 = logic_block.courses[1]
        self.assertEqual(nested_block2.type, "AND")
        self.assertEqual(len(nested_block2.courses), 2)
        self.assertEqual(nested_block2.courses[0].course_letters, "MATH 1AH")
        self.assertEqual(nested_block2.courses[0].honors, True)
        self.assertEqual(nested_block2.courses[1].course_letters, "MATH 1BH")
        self.assertEqual(nested_block2.courses[1].honors, True)
    
    def test_deeply_nested_structures(self):
        """Test deeply nested structures."""
        # Create a deeply nested structure with 3 levels
        logic_block = LogicBlock(
            type="OR",
            courses=[
                LogicBlock(
                    type="AND",
                    courses=[
                        CourseOption(course_letters="MATH 1A"),
                        LogicBlock(
                            type="OR",
                            courses=[
                                CourseOption(course_letters="PHYS 2A"),
                                CourseOption(course_letters="PHYS 2AH", honors=True)
                            ]
                        )
                    ]
                ),
                CourseOption(course_letters="MATH 1AH", honors=True)
            ]
        )
        
        self.assertEqual(logic_block.type, "OR")
        self.assertEqual(len(logic_block.courses), 2)
        
        # Check first nested block
        nested_block1 = logic_block.courses[0]
        self.assertEqual(nested_block1.type, "AND")
        self.assertEqual(len(nested_block1.courses), 2)
        self.assertEqual(nested_block1.courses[0].course_letters, "MATH 1A")
        
        # Check deepest nested block
        deepest_block = nested_block1.courses[1]
        self.assertEqual(deepest_block.type, "OR")
        self.assertEqual(len(deepest_block.courses), 2)
        self.assertEqual(deepest_block.courses[0].course_letters, "PHYS 2A")
        self.assertEqual(deepest_block.courses[1].course_letters, "PHYS 2AH")
        self.assertEqual(deepest_block.courses[1].honors, True)
        
        # Check second course option directly in the top level
        self.assertEqual(logic_block.courses[1].course_letters, "MATH 1AH")
        self.assertEqual(logic_block.courses[1].honors, True)
    
    def test_validation_of_type_field(self):
        """Test validation of the 'type' field (must be AND or OR)."""
        # Valid types
        LogicBlock(type="AND", courses=[])
        LogicBlock(type="OR", courses=[])
        
        # Invalid type
        with self.assertRaises(ValidationError):
            LogicBlock(type="XOR", courses=[])
        
        # The error should mention the type field
        try:
            LogicBlock(type="XOR", courses=[])
        except ValidationError as e:
            error_json = e.json()
            self.assertIn("type", error_json)
    
    def test_error_handling_for_malformed_input(self):
        """Test error handling for malformed input."""
        # Missing required field 'type'
        with self.assertRaises(ValidationError):
            LogicBlock(courses=[])
        
        # Missing required field 'courses'
        with self.assertRaises(ValidationError):
            LogicBlock(type="AND")
        
        # Invalid type for 'courses' (should be a list)
        with self.assertRaises(ValidationError):
            LogicBlock(type="AND", courses="not a list")
    
    def test_serialization_deserialization_of_nested_structures(self):
        """Test serialization/deserialization of nested structures."""
        # Create a nested structure
        logic_block = LogicBlock(
            type="OR",
            courses=[
                LogicBlock(
                    type="AND",
                    courses=[
                        CourseOption(course_letters="MATH 1A"),
                        CourseOption(course_letters="MATH 1B")
                    ]
                ),
                CourseOption(course_letters="MATH 1AH", honors=True)
            ]
        )
        
        # Serialize to dict
        logic_dict = logic_block.dict()
        
        # Check dict structure
        self.assertEqual(logic_dict["type"], "OR")
        self.assertEqual(len(logic_dict["courses"]), 2)
        self.assertEqual(logic_dict["courses"][0]["type"], "AND")
        self.assertEqual(logic_dict["courses"][0]["courses"][0]["course_letters"], "MATH 1A")
        self.assertEqual(logic_dict["courses"][0]["courses"][1]["course_letters"], "MATH 1B")
        self.assertEqual(logic_dict["courses"][1]["course_letters"], "MATH 1AH")
        self.assertEqual(logic_dict["courses"][1]["honors"], True)
        
        # Serialize to JSON and back to dict
        logic_json = logic_block.json()
        logic_dict_from_json = json.loads(logic_json)
        
        # Check that the structure is preserved
        self.assertEqual(logic_dict_from_json["type"], "OR")
        self.assertEqual(len(logic_dict_from_json["courses"]), 2)
        self.assertEqual(logic_dict_from_json["courses"][0]["type"], "AND")
        
        # Deserialize from dict
        reconstructed_block = LogicBlock(**logic_dict)
        
        # Check that the reconstructed block matches the original
        self.assertEqual(reconstructed_block.type, logic_block.type)
        self.assertEqual(len(reconstructed_block.courses), len(logic_block.courses))
        self.assertEqual(reconstructed_block.courses[0].type, logic_block.courses[0].type)
        self.assertEqual(
            reconstructed_block.courses[0].courses[0].course_letters,
            logic_block.courses[0].courses[0].course_letters
        )


class TestValidationResult(unittest.TestCase):
    """Test the ValidationResult model for storing validation outcomes."""
    
    def test_creation_with_minimal_fields(self):
        """Test creation with minimal fields."""
        # Create with just required fields
        result = ValidationResult(satisfied=True, explanation="Requirements are satisfied")
        
        self.assertEqual(result.satisfied, True)
        self.assertEqual(result.explanation, "Requirements are satisfied")
        self.assertEqual(result.satisfied_by, set())  # Default empty set
        self.assertEqual(result.missing_requirements, [])  # Default empty list
    
    def test_default_factory_values(self):
        """Test default factory values for sets and lists."""
        # Create two instances
        result1 = ValidationResult(satisfied=True, explanation="First result")
        result2 = ValidationResult(satisfied=False, explanation="Second result")
        
        # Check that they have different instances of satisfied_by and missing_requirements
        self.assertIsNot(result1.satisfied_by, result2.satisfied_by)
        self.assertIsNot(result1.missing_requirements, result2.missing_requirements)
        
        # Modify the first instance
        result1.satisfied_by.add("MATH 1A")
        result1.missing_requirements.append("PHYS 2A")
        
        # Check that the second instance is not affected
        self.assertEqual(result2.satisfied_by, set())
        self.assertEqual(result2.missing_requirements, [])
    
    def test_adding_to_satisfied_by_set(self):
        """Test adding to satisfied_by set."""
        result = ValidationResult(satisfied=True, explanation="Requirements are satisfied")
        
        # Add courses to satisfied_by
        result.satisfied_by.add("MATH 1A")
        result.satisfied_by.add("PHYS 2A")
        
        self.assertEqual(result.satisfied_by, {"MATH 1A", "PHYS 2A"})
        
        # Try adding a duplicate (should not appear twice due to set behavior)
        result.satisfied_by.add("MATH 1A")
        self.assertEqual(result.satisfied_by, {"MATH 1A", "PHYS 2A"})
    
    def test_adding_to_missing_requirements_list(self):
        """Test adding to missing_requirements list."""
        result = ValidationResult(satisfied=False, explanation="Missing requirements")
        
        # Add requirements to missing_requirements
        result.missing_requirements.append("MATH 1A")
        result.missing_requirements.append("PHYS 2A")
        
        self.assertEqual(result.missing_requirements, ["MATH 1A", "PHYS 2A"])
        
        # Try adding a duplicate (should appear twice since it's a list)
        result.missing_requirements.append("MATH 1A")
        self.assertEqual(result.missing_requirements, ["MATH 1A", "PHYS 2A", "MATH 1A"])


class TestGroupModels(unittest.TestCase):
    """Test the group-related models (GroupLogicType, GroupSection, ArticulationGroup)."""
    
    def test_group_logic_type_enum_values(self):
        """Test GroupLogicType enum values."""
        self.assertEqual(GroupLogicType.CHOOSE_ONE_SECTION, "choose_one_section")
        self.assertEqual(GroupLogicType.ALL_REQUIRED, "all_required")
        self.assertEqual(GroupLogicType.SELECT_N_COURSES, "select_n_courses")
        
        # Test string conversion - fixed to use the correct string representation
        self.assertEqual(str(GroupLogicType.ALL_REQUIRED), "GroupLogicType.ALL_REQUIRED")
        
        # Test assignment from string
        logic_type = GroupLogicType("choose_one_section")
        self.assertEqual(logic_type, GroupLogicType.CHOOSE_ONE_SECTION)
        
        # Test invalid value
        with self.assertRaises(ValueError):
            GroupLogicType("invalid_value")
    
    def test_group_section_model(self):
        """Test GroupSection model."""
        # Create with just required fields
        section = GroupSection(section_id="A")
        
        self.assertEqual(section.section_id, "A")
        self.assertIsNone(section.section_title)
        self.assertEqual(section.uc_courses, [])
        
        # Create with all fields
        section = GroupSection(
            section_id="B", 
            section_title="Math Courses",
            uc_courses=[
                {"course_id": "MATH 1A", "title": "Calculus I"},
                {"course_id": "MATH 1B", "title": "Calculus II"}
            ]
        )
        
        self.assertEqual(section.section_id, "B")
        self.assertEqual(section.section_title, "Math Courses")
        self.assertEqual(len(section.uc_courses), 2)
        self.assertEqual(section.uc_courses[0]["course_id"], "MATH 1A")
        self.assertEqual(section.uc_courses[1]["title"], "Calculus II")
    
    def test_articulation_group_model(self):
        """Test ArticulationGroup model."""
        # Create a basic group
        group = ArticulationGroup(
            group_id="1",
            group_title="Math Requirements",
            group_logic_type=GroupLogicType.ALL_REQUIRED,
            sections=[
                GroupSection(section_id="A", section_title="Calculus")
            ]
        )
        
        self.assertEqual(group.group_id, "1")
        self.assertEqual(group.group_title, "Math Requirements")
        self.assertEqual(group.group_logic_type, GroupLogicType.ALL_REQUIRED)
        self.assertEqual(len(group.sections), 1)
        self.assertEqual(group.sections[0].section_id, "A")
        self.assertEqual(group.sections[0].section_title, "Calculus")
        self.assertIsNone(group.n_courses)
    
    def test_n_courses_validation(self):
        """Test n_courses validation (required for SELECT_N_COURSES type)."""
        # Valid case: n_courses provided for SELECT_N_COURSES
        group = ArticulationGroup(
            group_id="1",
            group_logic_type=GroupLogicType.SELECT_N_COURSES,
            n_courses=2
        )
        self.assertEqual(group.n_courses, 2)
        
        # Invalid case: n_courses missing for SELECT_N_COURSES
        with self.assertRaises(ValidationError):
            ArticulationGroup(
                group_id="1",
                group_logic_type=GroupLogicType.SELECT_N_COURSES
            )
        
        # n_courses not required for other logic types
        group = ArticulationGroup(
            group_id="1",
            group_logic_type=GroupLogicType.ALL_REQUIRED
        )
        self.assertIsNone(group.n_courses)
        
        group = ArticulationGroup(
            group_id="1",
            group_logic_type=GroupLogicType.CHOOSE_ONE_SECTION
        )
        self.assertIsNone(group.n_courses)
    
    def test_sections_validation(self):
        """Test sections validation."""
        # Empty sections is valid
        group = ArticulationGroup(
            group_id="1",
            group_logic_type=GroupLogicType.ALL_REQUIRED
        )
        self.assertEqual(group.sections, [])
        
        # Add multiple sections
        group = ArticulationGroup(
            group_id="1",
            group_logic_type=GroupLogicType.CHOOSE_ONE_SECTION,
            sections=[
                GroupSection(section_id="A", section_title="Math"),
                GroupSection(section_id="B", section_title="Physics")
            ]
        )
        self.assertEqual(len(group.sections), 2)
        self.assertEqual(group.sections[0].section_id, "A")
        self.assertEqual(group.sections[1].section_id, "B")


if __name__ == "__main__":
    unittest.main() 