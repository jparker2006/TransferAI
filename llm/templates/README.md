# TransferAI Templates Module

This module contains prompt templates and helper functions for generating prompts for different types of articulation queries in the TransferAI system.

## Structure

- `__init__.py`: Exports key functionality from the module
- `course_templates.py`: Templates for course-related prompts
- `group_templates.py`: Templates for group-related prompts
- `helpers.py`: Utility functions for template processing

## Usage

Templates should be used through the `PromptService` class in `llm.services.prompt_service`. For example:

```python
from llm.services.prompt_service import PromptService, PromptType, VerbosityLevel

# Create a prompt service with standard verbosity
service = PromptService(verbosity=VerbosityLevel.STANDARD)

# Build a course-specific prompt
prompt = service.build_prompt(
    prompt_type=PromptType.COURSE_EQUIVALENCY,
    user_question="What satisfies CSE 8A?",
    rendered_logic="* Option 1: CIS 22A",
    uc_course="CSE 8A",
    uc_course_title="Introduction to Programming"
)

# Build a group-specific prompt
prompt = service.build_prompt(
    prompt_type=PromptType.GROUP_LOGIC,
    user_question="What satisfies Group 1?",
    rendered_logic="Section A: CSE 8A, CSE 8B",
    group_id="1",
    group_title="Computer Science Core",
    group_logic_type="choose_one_section"
)
```

## Verbosity Levels

The `PromptService` supports three verbosity levels:

- `MINIMAL`: Brief, direct responses with minimal explanation
- `STANDARD`: Balanced responses with moderate explanation
- `DETAILED`: Thorough responses with extensive explanation

## Template Customization

To customize templates, modify the template dictionaries in `course_templates.py` and `group_templates.py`. Each template is organized by verbosity level and uses Python's string formatting syntax with named placeholders.

## Backward Compatibility

The original `prompt_builder.py` module is now deprecated but still works for backward compatibility. It now uses the new `PromptService` implementation behind the scenes. New code should use `PromptService` directly. 