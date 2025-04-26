# TransferAI LLM Unit Tests

This directory contains unit tests for the TransferAI LLM implementation. These tests verify the correctness of individual components without running the full model.

## Test Organization

The tests are organized by module:

- `test_logic_formatter.py`: Tests for the logic_formatter module functions
- `test_render_logic.py`: Tests for the rendering of articulation logic

## Running Tests

Run all tests from the project root directory:

```bash
python3 llm/run_unit_tests.py
```

Run individual test files:

```bash
python3 -m llm.tests.test_logic_formatter
python3 -m llm.tests.test_render_logic
```

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