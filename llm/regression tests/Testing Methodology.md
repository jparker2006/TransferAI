# TransferAI Testing Methodology

## Testing Philosophy

The TransferAI testing strategy focuses on ensuring high-quality output and reliable performance across a wide range of course articulation scenarios. Our testing methodology is built on these key principles:

1. **Comprehensive Coverage**: Tests should cover all critical code paths, particularly the core articulation logic.
2. **Regression Prevention**: Tests must prevent previously fixed issues from recurring.
3. **Modular Testing**: Each module should have its own dedicated test suite.
4. **Documentation**: Tests should serve as living documentation of expected behavior.
5. **Continuous Improvement**: Test coverage should expand over time, particularly in high-risk areas.

## Test Types

### 1. Unit Tests

Unit tests focus on testing individual functions or classes in isolation. These tests should follow these guidelines:

- **Test Location**: Place in the `llm/tests/` directory with a `test_` prefix matching the module name.
- **Test Granularity**: Write separate test methods for each distinct behavior of a function.
- **Mocking**: Use mocks to isolate the function under test from its dependencies.
- **Naming Convention**: Test methods should clearly describe what they're testing (e.g., `test_normalize_course_code_with_hyphens`).
- **Coverage Target**: Aim for at least 80% statement coverage for each module.

**Example Unit Test**:
```python
def test_is_honors_required_when_honors_in_description():
    # Given a course description that mentions honors
    course = {"description": "This is an honors course"}
    
    # When we check if honors is required
    result = is_honors_required(course)
    
    # Then it should return True
    assert result is True
```

### 2. Integration Tests

Integration tests verify that different modules work together correctly. In TransferAI, these mainly test the query processing pipeline:

- **Test Location**: Integration tests are managed through `test_runner.py`.
- **Test Structure**: Use a standardized JSON format for expected outputs.
- **Coverage**: Tests should cover different query types and articulation scenarios.
- **Test Input**: Tests should use realistic queries that mimic actual user input.
- **Verification**: Tests should verify both the structure and content of responses.

**Example Integration Test**:
```python
{
    "id": "course_equivalency_basic",
    "prompt": "Does CIS 22A satisfy CSE 8A?",
    "expected_checks": [
        {"contains": "CIS 22A does satisfy CSE 8A"},
        {"not_contains": "honors"}
    ]
}
```

### 3. Regression Tests

Regression tests ensure that previously fixed issues don't recur:

- **Test Location**: Store regression test cases in `llm/regression tests/`.
- **Documentation**: Each test should reference the issue it's designed to prevent.
- **Versioning**: Track which version of the system fixed the issue.
- **Verification**: Clear pass/fail criteria should be established.

**Example Regression Test**:
```python
{
    "id": "v1_3_honors_detection_fix",
    "prompt": "Does MATH 10H satisfy any requirement?",
    "expected_checks": [
        {"contains": "honors equivalent"},
        {"contains": "MATH 10"}
    ],
    "issue_reference": "Issue #42: Honors course detection",
    "fixed_in_version": "1.3"
}
```

## Test Data Management

### Test Data Organization

- **Standard Test Inputs**: Store in `llm/tests/test_data/`.
- **Mock Responses**: Store LLM mock responses in `llm/tests/mock_responses/`.
- **Course Catalogs**: Use minimal sample catalog data in `llm/tests/test_catalogs/`.

### Test Data Guidelines

1. **Reproducibility**: Test data should be version controlled and consistent.
2. **Minimal Examples**: Test data should be as small as possible while still testing the target functionality.
3. **Synthetic Data**: Use generated data that mimics real data without exposing actual university data.
4. **Edge Cases**: Include test data that covers boundary conditions and edge cases.

## Test Execution

### Running Tests

Unit tests should be executed using pytest:

```bash
# Run all unit tests
python -m pytest llm/tests/

# Run tests for a specific module
python -m pytest llm/tests/test_logic_formatter.py

# Run with coverage
python -m pytest --cov=llm llm/tests/
```

Integration tests should be run using the test runner:

```bash
# Run all integration tests
python llm/run_unit_tests.py

# Run a specific test category
python llm/run_unit_tests.py --category course_equivalency
```

### Continuous Integration

Tests should be automated in the CI/CD pipeline with these steps:

1. Run unit tests with coverage reporting
2. Run integration tests
3. Run regression tests
4. Generate consolidated test reports
5. Block merges if tests fail or coverage drops

## Test Writing Guidelines

### When to Write Tests

1. **New Features**: Tests should be written before or alongside new feature development.
2. **Bug Fixes**: Each bug fix should include a test that would have caught the bug.
3. **Refactoring**: Before refactoring, ensure adequate tests exist to validate behavior.

### Test Structure

Each test should follow the Arrange-Act-Assert pattern:

1. **Arrange**: Set up the test data and preconditions
2. **Act**: Call the function or method being tested
3. **Assert**: Verify the expected outcome

Example:
```python
def test_detect_redundant_courses():
    # Arrange
    courses = ["MATH 1A", "MATH 1B", "MATH 1C", "MATH 1"]
    
    # Act
    redundant = detect_redundant_courses(courses)
    
    # Assert
    assert "MATH 1" in redundant
    assert "MATH 1A" not in redundant
```

### Test Isolation

1. **Independent Tests**: Tests should not depend on other tests.
2. **Clean State**: Reset any shared state between tests.
3. **Mock External Dependencies**: Use mocks for external services (e.g., LLM APIs).

## Test Documentation

### Test Documentation Standards

Every test file should include:

1. A module-level docstring explaining what's being tested
2. Function-level docstrings explaining the test scenario
3. Comments for complex test logic

Example:
```python
"""
Tests for the logic_formatter module that formats and explains articulation logic.

These tests verify that logic blocks are correctly analyzed, formatted, and 
explained in user-friendly language.
"""

def test_render_group_summary():
    """
    Test that group summaries are rendered correctly for AND logic.
    
    This test verifies that a group with AND logic correctly summarizes
    the requirement that all courses must be taken.
    """
    # Test implementation
```

## Mocking Strategy

### LLM Response Mocking

For testing components that interact with LLMs:

1. **Mock Responses**: Store sample LLM responses in JSON files.
2. **Response Swapping**: Replace real LLM calls with mocked responses.
3. **Parameterized Testing**: Test the same function with different mock responses.

Example:
```python
@patch('llm.openai_manager.call_openai')
def test_analyze_query_with_mock(mock_openai):
    # Load mock response
    with open('tests/mock_responses/course_equivalency.json', 'r') as f:
        mock_openai.return_value = json.load(f)
    
    # Test the function with the mock
    result = analyze_query("Does CIS 22A satisfy CSE 8A?")
    
    # Assert expected behavior
    assert "CSE 8A" in result
```

## Performance Testing

Performance tests should measure:

1. **Response Time**: Time to process different query types
2. **Memory Usage**: Peak memory consumption
3. **Scaling**: Performance with increasing catalog size

Performance tests should be run on standardized hardware and establish baseline metrics that future changes can be measured against.

## Test Coverage Goals

| Module | Current Coverage | Target Coverage | Priority |
|--------|-----------------|-----------------|----------|
| logic_formatter.py | ~65% | 90% | High |
| query_parser.py | ~20% | 85% | Critical |
| main.py | ~15% | 80% | Critical |
| document_loader.py | ~30% | 75% | Medium |
| prompt_builder.py | ~25% | 80% | High |

## Continuous Improvement Process

The test suite should evolve through this process:

1. **Gap Analysis**: Quarterly review of coverage reports.
2. **Prioritization**: Focus on high-risk, low-coverage areas.
3. **Documentation**: Update test documentation as coverage improves.
4. **Automation**: Improve test automation and reporting.
5. **Review**: Regular review of test effectiveness in catching issues. 