# TransferAI Architecture Overview

This document provides a detailed description of the TransferAI system architecture, with a particular focus on the articulation package.

## System Overview

TransferAI is designed to evaluate and validate course transferability between educational institutions. The system processes articulation logic, validates course selections, and generates human-readable explanations of validation results.

```
+------------------+      +-------------------+      +-----------------+
|                  |      |                   |      |                 |
|  Input Sources   +----->+  Core Processing  +----->+    Response    |
|                  |      |                   |      |   Formatting    |
+------------------+      +-------------------+      +-----------------+
                                   ^
                                   |
                                   v
                          +------------------+
                          |                  |
                          |  Articulation    |
                          |    Package       |
                          |                  |
                          +------------------+
```

## Articulation Package

The articulation package (`llm/articulation/`) is the core component responsible for processing and validating course articulation logic. It follows a modular design with clear separation of concerns.

### Module Structure

```
articulation/
├── __init__.py      # Public API
├── models.py        # Data structures
├── validators.py    # Core validation logic
├── renderers.py     # Presentation logic
├── formatters.py    # Response formatting
├── analyzers.py     # Analysis utilities
└── detectors.py     # Special case detection
```

### Module Responsibilities

#### models.py

The models module defines the core data structures used throughout the articulation package using Pydantic.

Key classes:
- `CourseOption`: Represents a single course option that can satisfy a requirement
- `LogicBlock`: Represents a logical grouping of requirements (AND/OR combinations)
- `ValidationResult`: Contains the results of validation operations

Data flow:
1. External systems provide articulation data
2. Data is parsed into Pydantic models
3. Models are used throughout the validation process

#### validators.py

The validators module contains the core logic for determining if course selections satisfy articulation requirements.

Key functions:
- `is_articulation_satisfied`: Top-level validation function
- `validate_combo_against_group`: Validates a course selection against logic groups
- `explain_if_satisfied`: Provides detailed explanation of validation results

Processing flow:
1. Receive course selections and articulation logic
2. Evaluate selections against logic
3. Generate detailed validation results

#### renderers.py

The renderers module transforms articulation logic into human-readable text formats.

Key functions:
- `render_logic_str`: Renders logic blocks into string representations
- `render_combo_validation`: Renders validation results
- `render_group_summary`: Generates summaries of logic group requirements

Processing flow:
1. Receive logic structures or validation results
2. Transform into human-readable formats
3. Return formatted strings ready for presentation

#### formatters.py

The formatters module structures and formats responses based on validation results.

Key functions:
- `render_binary_response`: Formats yes/no responses with explanations
- `include_validation_summary`: Adds validation summaries to responses
- `get_course_summary`: Generates concise course summaries

Processing flow:
1. Receive validation results
2. Structure comprehensive responses
3. Format for appropriate presentation

#### analyzers.py

The analyzers module extracts insights and patterns from articulation logic.

Key functions:
- `extract_honors_info_from_logic`: Identifies honors course requirements
- `count_uc_matches`: Counts matching courses
- `summarize_logic_blocks`: Generates high-level summaries

Processing flow:
1. Receive articulation logic
2. Apply analysis algorithms
3. Return structured insights

#### detectors.py

The detectors module identifies special cases and patterns in articulation logic.

Key functions:
- `is_honors_required`: Detects when only honors courses satisfy requirements
- `detect_redundant_courses`: Identifies redundant course selections
- `is_honors_pair_equivalent`: Determines honors/non-honors equivalency

Processing flow:
1. Receive articulation logic
2. Apply detection algorithms
3. Return special case indicators

## Data Flow

The articulation package processes data through the following typical flow:

```
+-------------+     +------------+     +-------------+     +-------------+
|             |     |            |     |             |     |             |
|   Models    +---->+ Validators +---->+  Renderers  +---->+ Formatters  |
|             |     |            |     |             |     |             |
+-------------+     +------------+     +-------------+     +-------------+
                         ^
                         |
      +-------------+    |    +-------------+
      |             |    |    |             |
      |  Analyzers  +----+--->+  Detectors  |
      |             |         |             |
      +-------------+         +-------------+
```

1. Input data is transformed into model objects
2. Validators evaluate if course selections satisfy requirements
3. Analyzers and detectors identify patterns and special cases
4. Renderers transform validation results into human-readable text
5. Formatters structure responses for final presentation

## Example Flow

### Course Validation Process

1. Course data and articulation logic are parsed into `CourseOption` and `LogicBlock` objects
2. `validators.is_articulation_satisfied()` evaluates if courses satisfy requirements
3. `detectors.is_honors_required()` checks for special honors requirements
4. `renderers.render_combo_validation()` creates a human-readable explanation
5. `formatters.render_binary_response()` structures the final response

## Extension Points

The articulation package is designed for extensibility:

1. **New Validation Rules**: Add methods to `validators.py`
2. **Additional Rendering Formats**: Add functions to `renderers.py`
3. **Custom Response Structures**: Extend `formatters.py`
4. **New Analysis Capabilities**: Add methods to `analyzers.py`
5. **Additional Pattern Detection**: Extend `detectors.py`

## Design Principles

The articulation package follows these key design principles:

1. **Separation of Concerns**: Each module has a distinct responsibility
2. **Strong Typing**: Type hints and Pydantic models ensure data integrity
3. **Stateless Processing**: Functions are pure and avoid side effects
4. **Extensibility**: System is designed for adding new capabilities
5. **Testability**: Modules are designed for comprehensive unit testing

## Performance Considerations

- Validators are optimized for fast validation of large logic structures
- Renderers pre-compute common patterns to avoid repeated work
- Models use efficient data structures for validation operations
- Analyzers cache results for repeated queries 