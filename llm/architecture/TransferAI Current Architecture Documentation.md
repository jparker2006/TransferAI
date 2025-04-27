# TransferAI Current Architecture Documentation

## 1. System Overview

TransferAI is a language model-powered system designed to help California Community College (CCC) students understand how their courses will transfer to University of California (UC) schools. The system uses Retrieval Augmented Generation (RAG) to process complex articulation logic from ASSIST.org and provide accurate, counselor-like responses to student queries.

The current implementation focuses on De Anza College to UC San Diego Computer Science major transfers, processing articulation data with complex boolean logic (AND/OR combinations) to validate course equivalencies.

## 2. Core Components

### 2.1 Main Engine (`main.py`)

The `TransferAIEngine` class serves as the central controller for the application and implements the following key functionality:

- **Configuration**: Sets up the LLM (Ollama with DeepSeek) and embedding model (HuggingFace's all-mpnet-base-v2)
- **Data Loading**: Loads and indexes articulation documents from RAG data
- **Query Handling**: Routes queries to appropriate handlers based on type detection
- **Multi-Course Processing**: Handles queries about combinations of courses

Key methods:
- `configure()`: Sets up LLM and embedding models
- `load()`: Loads and indexes documents
- `handle_query()`: Main entry point for processing user questions
- `handle_multi_uc_query()`: Processes queries involving multiple UC courses

### 2.2 Data Management (`document_loader.py`)

Responsible for loading and transforming raw articulation data into a format suitable for retrieval:

- **JSON Loading**: Loads structured articulation data from `rag_data.json`
- **Data Enrichment**: Adds metadata to documents for better retrieval
- **Flattening**: Converts nested structures into flat, indexed documents
- **CCC Course Extraction**: Extracts community college course codes from logic blocks

Key functions:
- `load_documents()`: Main function to load and transform the articulation data
- `flatten_courses_from_json()`: Converts nested JSON to flat documents with rich metadata
- `extract_ccc_courses_from_logic()`: Extracts all CCC course codes from a logic block

### 2.3 Query Parsing (`query_parser.py`)

Analyzes user queries to extract relevant information for retrieval:

- **Entity Extraction**: Identifies course codes, groups, and sections in natural language
- **Filter Generation**: Creates filters for document retrieval
- **Normalization**: Standardizes course codes for matching
- **Reverse Matching**: Finds UC courses satisfied by CCC courses

Key functions:
- `extract_filters()`: Extracts UC and CCC course filters from queries
- `normalize_course_code()`: Standardizes course codes like "CIS-21JA" → "CIS 21JA"
- `extract_group_matches()`: Identifies group references in queries
- `extract_section_matches()`: Identifies section references in queries

### 2.4 Logic Processing (`logic_formatter.py`)

The largest and most complex component, responsible for processing articulation logic and generating explanations:

- **Logic Validation**: Checks if selected courses satisfy articulation requirements
- **Rendering**: Converts logic blocks into human-readable text
- **Edge Case Handling**: Manages special cases like honors courses and no articulation
- **Response Formatting**: Structures responses in a consistent format

Key functions:
- `is_articulation_satisfied()`: Determines if selected courses satisfy a logic block
- `explain_if_satisfied()`: Provides detailed explanation of validation results
- `render_logic_str()` and `render_logic_v2()`: Render logic blocks as readable text
- `render_group_summary()`: Summarizes articulation requirements for a group
- `is_honors_required()`: Determines if honors courses are required
- `detect_redundant_courses()`: Identifies redundant course selections

### 2.5 Prompt Generation (`prompt_builder.py`)

Constructs prompts for the LLM based on query type and retrieved information:

- **Type-Specific Templates**: Different templates for course equivalency vs. group logic queries
- **Structured Format**: Consistent format with clear instructions for the LLM
- **Counselor Voice**: Enforces a professional, counselor-like tone

Key functions:
- `build_prompt()`: Main entry point for prompt construction
- `build_course_prompt()`: Builds prompts for individual course queries
- `build_group_prompt()`: Builds prompts for group-level queries

### 2.6 Testing Framework (`test_runner.py`, `tests/`)

Comprehensive testing infrastructure to ensure accuracy and reliability:

- **Test Suite**: Extensive collection of test prompts covering various query types
- **Regression Testing**: Verification that previously fixed issues don't resurface
- **Unit Tests**: Component-level tests for critical functions
- **Batch Testing**: Ability to run tests in batches and save results

Key functionality:
- Test prompts covering all articulation scenarios
- Specialized regression tests for critical functionality
- Unit tests for logic formatting, validation, and rendering functions

## 3. Data Structures

### 3.1 Articulation Data Structure (`rag_data.json`)

A hierarchical structure mirroring articulation agreements from ASSIST.org:

```
{
  "major": String,              // Major name
  "groups": [                   // Array of requirement groups
    {
      "group_id": String,       // Group identifier (e.g., "1", "2")
      "group_logic_type": String, // Logic type (choose_one_section, all_required, select_n_courses)
      "sections": [             // Array of sections within the group
        {
          "section_id": String, // Section identifier (e.g., "A", "B")
          "uc_courses": [       // Array of UC courses in this section
            {
              "uc_course_id": String,    // UC course code
              "logic_block": {           // Articulation logic for this course
                "type": String,          // Logic type ("OR" or "AND")
                "courses": [             // Array of course options or blocks
                  // Nested structure of AND/OR blocks and courses
                ]
              }
            }
          ]
        }
      ]
    }
  ]
}
```

### 3.2 Logic Block Structure

The core data structure representing articulation requirements:

```
{
  "type": "OR",          // Top level is usually OR (different options)
  "courses": [           // Array of options (usually AND blocks)
    {
      "type": "AND",     // AND means all courses required together
      "courses": [       // Array of CCC courses in this option
        {
          "course_letters": "CIS 22A",  // Course code
          "title": "...",               // Course title
          "honors": false               // Whether it's an honors course
        }
      ]
    }
  ]
}
```

### 3.3 Document Structure

Each document in the RAG system represents a single UC course with its articulation options, enriched with metadata:

```
{
  "text": "...",          // Text content for semantic search
  "metadata": {
    "uc_course": "CSE 8A",    // UC course code
    "group": "1",             // Group identifier
    "section": "A",           // Section identifier
    "logic_block": {...},     // Articulation logic for this course
    "ccc_courses": [...]      // List of CCC courses in this articulation
  }
}
```

## 4. Application Flow

### 4.1 Initialization Process

1. `TransferAIEngine` is instantiated
2. `configure()` sets up LLM and embedding models
3. `load()` loads articulation data and creates searchable index
4. Course prefixes and catalogs are extracted for query parsing

### 4.2 Query Processing Flow

1. User submits a question (e.g., "What De Anza courses satisfy CSE 8A?")
2. `handle_query()` receives the question
3. `extract_filters()` detects relevant course codes
4. Based on query type:
   - For single UC course: Retrieve matching documents and render logic
   - For validation: Apply validation logic and generate response
   - For group-level queries: Find group documents and summarize requirements
   - For multi-course queries: Process each course individually or validate combinations

### 4.3 Response Generation Flow

1. Relevant documents are retrieved based on filters
2. Logic blocks are processed or validated as needed
3. For validation, `is_articulation_satisfied()` and `explain_if_satisfied()` are called
4. Results are formatted using appropriate rendering function
5. A prompt is constructed using `build_prompt()`
6. The prompt is sent to the LLM for final response generation

## 5. Technical Implementation Details

### 5.1 LLM & Embedding Configuration

- **LLM**: Uses Ollama with DeepSeek model (1.5b parameters)
- **Temperature**: Set to 0 for deterministic, non-speculative responses
- **System Prompt**: Detailed instructions for accurate articulation handling
- **Embeddings**: HuggingFace's all-mpnet-base-v2 for semantic search

### 5.2 Document Retrieval

- Vector storage using LlamaIndex for semantic search
- Top-K retrieval (k=10) with similarity ranking
- Special case handling for specific query types (reverse lookup, group detection)

### 5.3 Articulation Logic Processing

- Recursive algorithms for traversing nested logic structures
- Support for complex boolean logic: AND, OR, nested combinations
- Honors course detection and special handling
- Redundancy detection for course combinations

### 5.4 Edge Case Handling

- No articulation cases (courses that must be taken at UC)
- Honors vs. non-honors equivalence
- Multi-course requirement validation
- Cross-section validation for group requirements

## 6. Technical Debt & Known Limitations

### 6.1 Code Structure Issues

- `logic_formatter.py` is overly large (1200+ lines) with mixed responsibilities
- Lack of clear separation between data processing and presentation
- Some duplicated functionality across files
- Limited use of typed interfaces for function parameters

### 6.2 Performance Considerations

- Recursive algorithms in logic processing without memoization
- No explicit caching mechanism for common queries
- Potential bottlenecks in deep nested logic traversal

### 6.3 Testing Coverage

- Comprehensive functional tests, but inconsistent unit test coverage
- Some complex edge cases lack dedicated tests
- Limited performance and load testing

### 6.4 Documentation Gaps

- Limited inline documentation for complex functions
- Inconsistent docstring coverage
- Missing module-level documentation
- No formal API specifications

## 7. Integration Points

### 7.1 Data Integration

- System loads data from `rag_data.json`
- New articulation data can be added by updating this file
- Requires specific JSON structure following the established schema

### 7.2 LLM Integration

- Uses Ollama for local LLM inference
- Configurable to use different models through Settings.llm
- Prompt templates designed for specific articulation use cases

### 7.3 Embedding Integration

- Uses HuggingFace for embeddings
- Configurable through Settings.embed_model
- Could be extended to other embedding providers

## 8. Conclusion

The current TransferAI architecture provides a solid foundation for accurate articulation processing with complex logic handling. However, it would benefit from modularization, better separation of concerns, and more comprehensive documentation. The large, monolithic `logic_formatter.py` represents the most significant technical debt that should be addressed in future versions.

The system successfully demonstrates the RAG pattern for education-specific LLM applications, with strong accuracy for articulation logic. With appropriate refactoring and modularization, it could be extended to support additional institutions and majors while maintaining its core capabilities. 