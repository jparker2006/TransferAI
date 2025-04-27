# TransferAI Test Suite

This directory contains the test suite for the TransferAI system.

## Test Organization

The tests are organized into module-specific test files that align with the articulation package structure:

### Primary Test Files
- `test_articulation_models.py` - Tests for Pydantic data models
- `test_articulation_validators.py` - Tests for validation logic
- `test_articulation_renderers.py` - Tests for rendering functions
- `test_articulation_formatters.py` - Tests for formatting functions
- `test_articulation_analyzers.py` - Tests for analyzer functions
- `test_articulation_detectors.py` - Tests for detector functions

### Migration Validation
- `test_migration.py` - Tests to ensure output equivalence between legacy code and new articulation package

### Deprecated Tests
All legacy test files that have been replaced by the module-specific tests have been moved to the `deprecated/` directory:

- `test_articulation_satisfied.py` → `test_articulation_validators.py`
- `test_binary_response.py` → `test_articulation_formatters.py`
- `test_combo_validation.py` → `test_articulation_renderers.py`
- `test_count_uc_matches.py` → `test_articulation_analyzers.py`
- `test_logic_formatter.py` → Various module-specific tests
- `test_render_logic.py` → `test_articulation_renderers.py`
- `test_render_logic_v2.py` → `test_articulation_renderers.py`
- `test_honors_equivalence.py` → `test_articulation_detectors.py`

## Running Tests

To run all tests:

```
python -m unittest discover -s tests
```

To run a specific test file:

```
python -m unittest tests/test_articulation_validators.py
```

## Test Coverage

The current test coverage focuses on:
1. Core validation logic for articulation requirements
2. Rendering of articulation options in different formats
3. Detection of special cases (honors requirements, redundant courses)
4. Response formatting for different query types
5. Migration validation to ensure backward compatibility

## Feature Coverage

### Logic Formatter Tests

- `is_honors_required`: Verifies that honors course requirements are correctly detected
- `detect_redundant_courses`: Tests the detection of redundant courses (e.g., honors/non-honors pairs)
- `explain_if_satisfied`: Tests the articulation logic satisfaction checking with redundancy reporting

### Render Logic Tests

- Honor requirements rendering: Tests that honor requirements are correctly displayed in articulation logic
- Various rendering scenarios: Tests different articulation scenarios (no articulation, empty logic blocks, etc.)

## Test Data

The tests use synthetic logic blocks that mirror the structure found in the actual ASSIST.org data, with a focus on:

- Honor/non-honor pairs
- Single vs multi-course articulation paths
- Various nesting levels of logic blocks
- Edge cases (empty blocks, invalid structures)

## Adding New Tests

When adding new features to the LLM implementation, extend the existing test files or create new ones following the same pattern. Ensure that:

1. All new functions have dedicated test cases
2. Edge cases are covered
3. Integration with existing functionality is verified

Test files should be named `test_*.py` to be automatically discovered by the test runner. 