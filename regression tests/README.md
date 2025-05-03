# TransferAI Testing Directory Documentation

## Overview

The `testing/` directory contains test files, version history, and progress tracking for TransferAI v1. These files document the evolution of the system, regression tests, and planned improvements to ensure the system maintains high accuracy and reliability.

## Directory Contents

```
testing/
├── TransferAI v1.0.txt     # Original version test results
├── TransferAI v1.1.txt     # First iteration test results
├── TransferAI v1.2.txt     # Second iteration test results  
└── TransferAI v1.3.txt     # Third iteration test results
```

## Version History Files

Each version file (`TransferAI v1.0.txt` through `v1.3.txt`) contains:

1. Test prompts used for that version
2. System responses to those prompts
3. Evaluation of response quality (✅ Perfect, ⚠️ Minor Issues, ❌ Major Errors)
4. Notes on specific issues or improvements

These files serve as historical records to track how the system has evolved and to ensure that new changes don't break existing functionality.

## Progress Tracking

`TransferAI v1 Progress.md` provides a quantitative summary of system improvement across versions:

| Version | ✅ Perfect | ⚠️ Minor Issues | ❌ Major Errors | 🎯 Strict Accuracy | 🎯 Adjusted Accuracy | 🔁 Improvements | 📉 Regressions |
|---------|------------|----------------|----------------|--------------------|----------------------|------------------|----------------|
| v1.0    | 22 / 32    | 6 / 32         | 4 / 32         | 68.75%             | 87.5%                | —                | —              |
| v1.1    | 23 / 32    | 3 / 32         | 6 / 32         | 71.88%             | 90.63%               | —                | —              |
| v1.2    | 26 / 32    | 4 / 32         | 2 / 32         | 81.25%             | 93.75%               | 12 / 32          | 1 / 32          |
| **v1.3**| **30 / 32**| **2 / 32**     | **0 / 32**     | **93.75%**         | **100%**             | **5 / 32**       | **0 / 32**      |

This shows the progression of accuracy metrics as the system has been refined.

## Todo and Roadmap

`TransferAI v1.4 Todo.txt` outlines planned improvements for the next iteration, including:

### Bug Fixes
- Honors course requirement detection
- Redundant course flagging
- Honors/non-honors equivalence clarification
- UC course articulation counting

### Prompt & Tone Enhancements
- Consistent yes/no formatting
- More concise UC → CCC course mappings
- Better distinction between complete and partial options
- More direct language in group-level prompts

### Validation & Structure Upgrades
- Structured output for articulation validation
- Improved rendering for multi-course combinations
- Flattened metadata summaries
- Better handling of "no articulation" cases

### Tooling Recommendations
- Schema validation with Pydantic
- JSON validation with jsonschema
- Potential API with FastAPI
- Improved logging with rich
- Custom testing CLI
- Diff utilities for version comparison

## Testing Methodology

The test suite evaluates TransferAI on several dimensions:

1. **Accuracy**: Does the system provide correct information about course articulation?
2. **Completeness**: Does it cover all relevant aspects of the articulation requirement?
3. **Clarity**: Is the information presented in a clear, counselor-like manner?
4. **Consistency**: Are similar queries handled in a consistent way?
5. **Logic Handling**: Does it correctly interpret complex AND/OR logic in articulation requirements?

### Test Categories

The test prompts cover a range of query types:

1. **Simple Course Equivalency**: "Which De Anza courses satisfy CSE 8A at UCSD?"
2. **Validation Queries**: "Do I need to take both CIS 36A and CIS 36B to get credit for CSE 11?"
3. **Group Requirements**: "What De Anza courses are required to satisfy Group 2?"
4. **No Articulation Cases**: "Does De Anza have an equivalent for CSE 21?"
5. **Logic-Intensive Queries**: "Can I mix CIS 22A and CIS 35A for Group 1?"
6. **Honors Course Queries**: "Does MATH 1CH and 1DH count for MATH 20C?"
7. **Multi-Course Queries**: "Which courses satisfy MATH 20A and 20B?"

### Regression Testing

The system includes regression tests to ensure that previously fixed issues don't reappear in new versions. These tests focus on edge cases and scenarios that have proven challenging in earlier versions.

### Pre-Expansion QA Checklist

Before scaling to new institutions or majors, the system undergoes a comprehensive quality assurance check:

- UC course to CCC logic mapping accuracy
- Standardized phrasing for yes/no questions
- Clear indication of honors requirements
- Full support for different group logic types
- Flagging of redundant course options
- Structured output for programmatic use
- Independent processing of multi-UC queries
- Absence of hallucinated or speculative information

## Running Tests

Tests can be run using the `test_runner.py` script in the main `llm/` directory. This script:

1. Initializes the TransferAI engine
2. Configures the LLM and embeddings
3. Loads the test articulation data
4. Runs a series of test prompts
5. Outputs responses for manual evaluation

Results can be compared against previous version outputs to identify improvements or regressions.

## Extending the Test Suite

To add new tests:

1. Add new test prompts to the `test_prompts` list in `test_runner.py`
2. Run the tests and evaluate responses
3. Document the results in the appropriate version file
4. Update the progress tracking document

For regression testing, add specific prompts to the `regression_tests` list that cover previously problematic scenarios. 