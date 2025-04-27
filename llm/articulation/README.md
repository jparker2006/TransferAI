# TransferAI Articulation Package

The `articulation` package is the core logic implementation for processing course articulation rules between California Community Colleges and University of California campuses. This package is the result of a major refactoring effort (v1.5) to modularize the monolithic `logic_formatter.py` into maintainable, focused components.

## Package Structure

The package is organized into modules with clear responsibilities:

| Module | Description | Key Functions |
|--------|-------------|---------------|
| `models.py` | Data structures using Pydantic | `LogicBlock`, `CourseOption`, `ValidationResult` |
| `validators.py` | Core validation logic | `is_articulation_satisfied`, `explain_if_satisfied`, `validate_combo_against_group` |
| `renderers.py` | Presentation logic | `render_logic_str`, `render_logic_v2`, `render_group_summary` |
| `formatters.py` | Response formatting | `render_binary_response`, `include_binary_explanation`, `get_course_summary` |
| `analyzers.py` | Analysis utilities | `extract_honors_info_from_logic`, `count_uc_matches`, `summarize_logic_blocks` |
| `detectors.py` | Special case detection | `is_honors_required`, `detect_redundant_courses`, `is_honors_pair_equivalent` |

## Key Concepts

### Logic Blocks

Logic blocks represent articulation requirements, structured as nested "AND/OR" combinations:

```json
{
  "type": "OR",
  "courses": [
    {
      "type": "AND",
      "courses": [
        {"course_letters": "MATH 1A", "honors": false}
      ]
    },
    {
      "type": "AND",
      "courses": [
        {"course_letters": "MATH 1AH", "honors": true}
      ]
    }
  ]
}
```

### Validation Process

The validation process determines if selected courses satisfy articulation requirements:

1. Parse the logic structure using `models.py`
2. Apply validation rules from `validators.py`
3. Handle special cases using `detectors.py`
4. Format the response using `formatters.py` and `renderers.py`

## Usage Examples

### Basic Validation

```python
from articulation import is_articulation_satisfied

logic_block = {
    "type": "OR",
    "courses": [
        {
            "type": "AND", 
            "courses": [
                {"course_letters": "MATH 1A", "honors": False}
            ]
        }
    ]
}
selected_courses = ["MATH 1A"]

result = is_articulation_satisfied(logic_block, selected_courses)
print(f"Is satisfied: {result['is_satisfied']}")
```

### Rendering Logic

```python
from articulation import render_logic_str

metadata = {
    "uc_course": "MATH 20A",
    "logic_block": logic_block
}

explanation = render_logic_str(metadata)
print(explanation)
```

## Development Guide

### Adding New Features

When adding new features:
1. Identify the appropriate module based on responsibility
2. Maintain backward compatibility with existing interfaces
3. Add comprehensive tests for the new functionality

### Testing

Each module has a corresponding test file in the `tests/` directory:
- `test_articulation_models.py`
- `test_articulation_validators.py`
- etc.

Run tests with:
```
python -m llm.run_unit_tests
```

## Migration from Legacy Code

The package provides a transitional adapter in `logic_formatter_adapter.py` that maintains the original interfaces while delegating to the new modular components.

Legacy code should be migrated to use the articulation package directly rather than `logic_formatter.py`. 