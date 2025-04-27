# TransferAI Module Documentation

## Core Modules

### 1. Main Engine (`main.py`)

#### Responsibilities
- Configures LLM and embedding models
- Loads and indexes articulation data
- Processes user queries and routes to appropriate handlers
- Generates responses based on retrieved information
- Handles multi-course and validation queries

#### Edge Cases & Limitations
- Complex multi-UC course combinations may exceed the context window size
- Queries with mixed course types (UC and CCC) can sometimes be ambiguous
- Edge cases in group logic interpretation when multiple logic types are involved
- Limited configuration options for different institutions or majors

### 2. Document Loader (`document_loader.py`)

#### Responsibilities
- Loads articulation data from JSON files
- Extracts CCC course codes from logic blocks
- Flattens nested JSON structures into searchable documents
- Enriches documents with metadata for retrieval

#### Edge Cases & Limitations
- Non-standard logic structures may not be properly parsed
- Large articulation datasets could cause memory issues
- Limited validation of input data structure
- Edge cases in extracting course codes from complex nested structures

### 3. Query Parser (`query_parser.py`)

#### Responsibilities
- Normalizes course codes to a standard format
- Extracts UC and CCC course codes from natural language queries
- Identifies group and section references in queries
- Matches queries to specific articulation documents

#### Edge Cases & Limitations
- Complex queries with multiple course codes may not be fully parsed
- Department code inference has limited accuracy for ambiguous cases
- Course codes with special formats may not be properly normalized
- Dependency on spaCy model which may have its own limitations

### 4. Logic Formatter (`logic_formatter.py`)

#### Responsibilities
- Validates if selected courses satisfy articulation requirements
- Renders logic blocks as human-readable text
- Processes complex logic combinations (AND/OR) with nested hierarchies
- Handles special cases like honors courses and no-articulation situations
- Provides detailed explanations of validation results

#### Edge Cases & Limitations
- Deeply nested logic structures may cause performance issues
- Honors/non-honors equivalence detection has edge cases
- Redundant course detection may miss some scenarios
- Logic validation in the presence of cross-section requirements is complex
- Recursive algorithms without memoization can be inefficient for complex blocks

### 5. Prompt Builder (`prompt_builder.py`)

#### Responsibilities
- Constructs prompts for the LLM based on query type
- Creates course-specific articulation prompts
- Creates group-level articulation prompts
- Ensures consistent counselor-like tone in prompts

#### Edge Cases & Limitations
- Prompt length may exceed model context windows for complex articulations
- Limited customization options for different educational institutions
- Fixed prompt templates that may not be optimal for all query types
- No dynamic adjustment based on LLM model capabilities

## Cross-Module Limitations

### Performance Considerations
- Recursive logic processing without caching creates redundant work
- Vector search may return irrelevant results for ambiguous queries
- Document indexing process can be memory-intensive for large datasets
- No distributed processing capabilities for scaling

### Data Structure Limitations
- Rigid data schema that requires specific format from ASSIST.org
- Limited support for alternative articulation data sources
- No formal validation of data structures between modules
- Nested logic structures can become unwieldy for complex articulations

### Edge Case Handling
- Mixing course codes across institutions can lead to ambiguity
- Articulation paths that span multiple sections require special handling
- Complex honors course logic with multiple equivalent options
- Inferring department codes for standalone course numbers has limitations
- No versioning support for articulation data that changes over time

## Suggested Improvements
- Implement caching for recursive logic functions
- Add proper schema validation for input data
- Enhance course code normalization to handle more edge cases
- Implement more sophisticated context handling for complex queries
- Add configurable templates for different institutions and majors
- Implement a more robust testing framework for edge cases 