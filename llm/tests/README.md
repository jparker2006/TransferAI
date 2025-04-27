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
- `test_articulation_detectors.py` - Tests for detection functions
- `test_document_loader.py` - Tests for document loading functionality
- `test_main.py` - Tests for the main TransferAI engine
- `test_prompt_builder.py` - Tests for prompt building functionality
- `test_migration.py` - Tests to ensure output equivalence between legacy code and new articulation package

### Prompt Testing Suite
The `prompt_tests/` directory contains specialized tests for prompt construction and LLM interaction:

- `test_builder_prompt.py` - Tests for prompt builder templates
- `test_local_embeddings.py` - Tests for local embedding functionality
- `test_prompt.py` - Tests for prompt generation
- `test_enrichment.py` - Tests for course description enrichment
- `test_verbosity.py` - Tests for response verbosity control
- `verbosity_test.py` - Alternative verbosity testing

## Running Tests

To run all tests:

```
python -m unittest discover -s llm/tests
```

To run a specific test file:

```
python -m unittest llm/tests/test_articulation_validators.py
```

To run prompt-specific tests:

```
python -m unittest llm/tests/prompt_tests/test_prompt.py
```

## Test Coverage

The current test coverage focuses on:
1. Core validation logic for articulation requirements
2. Rendering of articulation options in different formats
3. Detection of special cases (honors requirements, redundant courses)
4. Response formatting for different query types
5. Migration validation to ensure backward compatibility
6. Prompt construction and LLM interaction
7. Document loading and processing
8. Verbosity control and course enrichment

## Feature Coverage

### Core Articulation Tests

- **Validators**: Tests articulation logic satisfaction checking
- **Renderers**: Tests display of articulation options
- **Formatters**: Tests response formatting
- **Analyzers**: Tests analysis of articulation data
- **Detectors**: Tests detection of special cases (honors requirements)
- **Models**: Tests Pydantic data models

### Prompt and LLM Tests

- **Prompt Building**: Tests generation of prompts for different query types
- **Course Enrichment**: Verifies that course descriptions are properly added
- **Verbosity Control**: Tests different levels of response verbosity
- **Local Embeddings**: Tests embedding functionality without API dependency

## Test Data

The tests use synthetic logic blocks that mirror the structure found in the actual ASSIST.org data, with a focus on:

- Honor/non-honor pairs
- Single vs multi-course articulation paths
- Various nesting levels of logic blocks
- Edge cases (empty blocks, invalid structures)

## Adding New Tests

When adding new features to the TransferAI implementation, extend the existing test files or create new ones following the same pattern. Ensure that:

1. All new functions have dedicated test cases
2. Edge cases are covered
3. Integration with existing functionality is verified

Test files should be named `test_*.py` to be automatically discovered by the test runner. 