# TransferAI Architecture Overview

This document provides a detailed description of the TransferAI system architecture as of version 1.5, reflecting the current state after modularization and cleanup efforts.

## System Overview

TransferAI is designed to evaluate and validate course transferability between California Community Colleges (particularly De Anza College) and University of California campuses (currently focused on UCSD). The system processes articulation logic, validates course selections, and generates human-readable explanations of validation results.

```
+----------------------+      +----------------------+      +----------------------+
|                      |      |                      |      |                      |
|  Document Loading    +----->+  Core Processing     +----->+  Response Generation |
|  (document_loader.py)|      |  (main.py)           |      |  (prompt_builder.py) |
|                      |      |                      |      |                      |
+----------------------+      +----------+-----------+      +----------------------+
                                         |
                                         v
                              +----------------------+
                              |                      |
                              |  Articulation Package|
                              |  (articulation/)     |
                              |                      |
                              +----------------------+
                                         ^
                                         |
                              +----------------------+
                              |                      |
                              |  Query Processing    |
                              |  (query_parser.py)   |
                              |                      |
                              +----------------------+
```

## Core Components

### TransferAIEngine (main.py)

The `TransferAIEngine` class in `main.py` serves as the central coordinator for the entire system. It handles:

1. Configuration of LLM and embedding models
2. Loading and indexing of articulation data
3. Processing user queries and routing to appropriate handlers
4. Generating responses based on retrieved articulation information
5. Handling various query types (course equivalency, validation, group requirements)

The engine uses two primary strategies for answering queries:
- **Rule-based matching** for explicit course code mentions
- **Vector search** for semantic queries without explicit course codes

### Document Loader (document_loader.py)

The document loader module handles:

1. Loading JSON articulation data from source files
2. Transforming nested articulation data into flat, searchable documents
3. Extracting metadata for retrieval and presentation
4. Creating LlamaIndex Document objects for vector indexing
5. Providing consistent course information through utility functions

This module maintains a course cache to ensure consistent course information is used throughout the application and handles the transformation of articulation data into formats suitable for both rule-based and vector-based retrieval.

### Query Parser (query_parser.py)

The query parser module is responsible for:

1. Normalizing course codes for consistent matching
2. Extracting UC and CCC course codes from user queries
3. Identifying group and section references
4. Matching queries to specific articulation documents

Using a combination of NLP (spaCy) and regex patterns, this module handles various formats and edge cases in course code notation to ensure accurate interpretation of user queries.

### Prompt Builder (prompt_builder.py)

The prompt builder module constructs prompts for the LLM based on:

1. Query type (course-specific or group-level)
2. Verbosity level (MINIMAL, STANDARD, DETAILED)
3. Articulation data and rendered logic

It ensures that prompts maintain a consistent professional tone, include appropriate context based on verbosity level, and provide clear instructions to the LLM about response formatting. The module handles response rules to prevent thinking sections or duplicative content.

### Articulation Package (articulation/)

The articulation package is the core logic component with clear separation of concerns:

#### Module Structure

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

#### Module Responsibilities

**models.py**
- Defines core data structures using Pydantic
- Includes `CourseOption`, `LogicBlock`, and `ValidationResult` models
- Ensures type safety throughout the articulation process

**validators.py**
- Contains the core logic for determining if course selections satisfy requirements
- Implements `is_articulation_satisfied`, `validate_combo_against_group`, etc.
- Handles complex nested logic structures

**renderers.py**
- Transforms articulation logic into human-readable text formats
- Implements `render_logic_str`, `render_combo_validation`, etc.
- Handles consistent formatting of articulation explanations

**formatters.py**
- Structures and formats responses based on validation results
- Implements `render_binary_response`, `include_validation_summary`, etc.
- Ensures consistent response structure regardless of query type

**analyzers.py**
- Extracts insights and patterns from articulation logic
- Implements `extract_honors_info_from_logic`, `count_uc_matches`, etc.
- Supports answering analytical questions about articulation paths

**detectors.py**
- Identifies special cases and patterns in articulation logic
- Implements `is_honors_required`, `detect_redundant_courses`, etc.
- Handles edge cases like honors course equivalency

## Data Flow

### Query Processing Flow

```
User Query → TransferAIEngine → Query Parser → Document Matching → Validation → Response
```

1. User submits a natural language query about course transferability
2. TransferAIEngine processes the query and identifies its type
3. Query Parser extracts course codes, groups, and sections from the query
4. Engine matches query against appropriate documents from the document loader
5. Articulation package components validate and analyze the matching documents
6. Prompt Builder creates a structured prompt for the LLM
7. LLM generates a response which is cleaned and returned to the user

### Articulation Module Data Flow

```
+-------------+     +------------+     +-------------+     +-------------+
|             |     |            |     |             |     |             |
|   Models    +---->+ Validators +---->+  Renderers  +---->+ Formatters  |
|             |     |            |     |             |     |             |
+-------------+     +------+-----+     +-------------+     +-------------+
                           ^
                           |
      +-------------+      |      +-------------+
      |             |      |      |             |
      |  Analyzers  +------+----->+  Detectors  |
      |             |             |             |
      +-------------+             +-------------+
```

1. Input data is transformed into model objects
2. Validators evaluate if course selections satisfy requirements
3. Analyzers and detectors identify patterns and special cases
4. Renderers transform validation results into human-readable text
5. Formatters structure responses for final presentation

## Configuration and Settings

The TransferAI system supports various configuration options:

1. **Verbosity Levels**: Controls the detail level of responses
   - MINIMAL: Brief, direct responses with minimal explanation
   - STANDARD: Balanced responses with moderate explanation
   - DETAILED: Thorough responses with extensive explanation

2. **Model Configuration**:
   - Supports local embedding models (HuggingFaceEmbedding)
   - Can use various LLM backends, currently configured with deepseek-r1:1.5b via Ollama

3. **Debug Mode**: Provides additional logging and debugging information

## Extension Points

The articulation package is designed for extensibility:

1. **New Validation Rules**: Add methods to `validators.py`
2. **Additional Rendering Formats**: Add functions to `renderers.py`
3. **Custom Response Structures**: Extend `formatters.py`
4. **New Analysis Capabilities**: Add methods to `analyzers.py`
5. **Additional Pattern Detection**: Extend `detectors.py`

## Current Implementation Status

The current implementation focuses on:

1. De Anza College to UCSD Computer Science major articulation
2. Support for courses, course groups, and honors requirements
3. Three verbosity levels for different user needs
4. Local embedding and LLM operation for privacy and performance

Ongoing development includes:
1. Refactoring main.py to improve maintainability
2. Enhancing response consistency for edge cases
3. Preparing for expansion to additional majors and institutions 