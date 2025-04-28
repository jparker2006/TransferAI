# TransferAI LLM Engine

## Overview

TransferAI is a language model-powered system designed to help California Community College (CCC) students understand how their courses will transfer to University of California (UC) schools. The system uses Retrieval Augmented Generation (RAG) to process complex articulation logic from ASSIST.org and provide accurate, counselor-like responses to student queries.

## Key Features

- **Semantic Search**: Finds relevant articulation information based on natural language queries
- **Complex Logic Processing**: Handles AND/OR combinations, course sequences, and group requirements
- **LLM-Powered Explanations**: Generates clear, accurate responses in a counselor-like tone
- **Validation**: Verifies whether specific course combinations satisfy requirements
- **Multi-Course Queries**: Processes questions about multiple courses at once
- **Honors Course Detection**: Identifies and handles honors course equivalences
- **Local Embedding Support**: Uses local Hugging Face embeddings for consistent results

## Directory Structure

```
llm/
├── articulation/              # Modular articulation components
│   ├── analyzers.py           # Course matching and analysis tools
│   ├── detectors.py           # Course and pattern detection
│   ├── formatters.py          # Response formatting utilities
│   ├── models.py              # Data models for articulation
│   ├── renderers.py           # Logic rendering components
│   ├── validators.py          # Validation logic for requirements
│   └── __init__.py            # Package exports
├── data/                      # RAG data storage
│   ├── rag_data.json          # Structured articulation data
│   └── README.md              # Data documentation
├── docs/                      # Documentation files
├── regression tests/          # Regression testing and roadmaps
│   ├── TransferAI v1.5.txt    # Latest test results
│   └── TransferAI v1.5 Roadmap.md # Current roadmap
├── tests/                     # Unit and integration tests
├── architecture/              # Architecture documentation
├── document_loader.py         # Loads and processes articulation documents
├── logic_formatter.py         # Legacy formatter (being phased out)
├── logic_formatter_adapter.py # Adapter for backward compatibility
├── main.py                    # Core engine with query handling
├── prompt_builder.py          # Constructs prompts for the LLM
├── query_parser.py            # Parses and analyzes user queries
├── test_runner.py             # Test suite for system validation
├── run_unit_tests.py          # Runs focused unit tests
└── README.md                  # Main documentation
```

## Component Documentation

### Core Components

- **main.py**: The `TransferAIEngine` class that orchestrates the entire system
- **document_loader.py**: Loads and processes articulation documents for indexing
- **query_parser.py**: Extracts structured information from natural language queries
- **prompt_builder.py**: Generates specialized prompts for different query types

### Articulation Module

The articulation module replaces the monolithic logic_formatter.py, dividing functionality into specialized components:

- **analyzers.py**: Functions for analyzing course matches and articulation paths
- **detectors.py**: Tools for detecting course patterns and special conditions
- **formatters.py**: Formats responses for different articulation scenarios
- **models.py**: Pydantic models for structured articulation data
- **renderers.py**: Renders articulation logic into human-readable format
- **validators.py**: Validates if course combinations satisfy requirements

### Compatibility Layers

- **logic_formatter.py**: Legacy code being phased out (most functionality moved to articulation/)
- **logic_formatter_adapter.py**: Adapter to maintain backward compatibility during transition

## Getting Started

### Requirements

TransferAI requires the following dependencies:

- Python 3.8+
- LlamaIndex (core)
- Ollama (for local LLM inference)
- Hugging Face Transformers (for embeddings)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Install Ollama following instructions at [ollama.ai](https://ollama.ai)
4. Pull the required models:
   ```
   ollama pull deepseek-r1:1.5b
   ```

### Running the Engine

To start the TransferAI engine:

```python
from llm.main import TransferAIEngine

engine = TransferAIEngine()
engine.configure()  # Set up LLM and embeddings
engine.load()       # Load articulation data
engine.handle_query("What De Anza courses satisfy CSE 8A at UCSD?")
```

### Running Tests

To run specific tests:

```
python llm/test_runner.py -t 1  # Run test #1
python llm/test_runner.py -p "Which courses satisfy CSE 8A?"  # Run custom prompt
python llm/test_runner.py -l  # List all available tests
```

## How It Works

1. **Data Loading**: The system loads structured articulation data
2. **Query Processing**: When a user submits a query, `query_parser.py` extracts relevant entities
3. **Document Retrieval**: Vector search finds documents matching the query
4. **Logic Processing**: `articulation` module renders and validates the articulation logic
5. **Prompt Building**: `prompt_builder.py` constructs a prompt for the LLM
6. **Response Generation**: The LLM generates a response based on the articulation data

## Query Types

TransferAI handles various query types:

1. **Course Equivalency**: "What De Anza courses satisfy CSE 8A at UCSD?"
2. **Validation**: "Does CIS 36A satisfy CSE 8A?"
3. **Group Requirements**: "What courses satisfy Group 2?"
4. **Multi-Course**: "What equals both CSE 8A and 8B?"
5. **No Articulation**: "Is there an equivalent for CSE 15L?"
6. **Honors Variants**: "Does MATH 1AH satisfy MATH 20A?"

## Technical Implementation

- **LLM**: Uses Ollama with DeepSeek models for reliable responses
- **Embeddings**: Uses Hugging Face's sentence-transformers for semantic search
- **Vector Database**: Uses LlamaIndex for document retrieval

## Development and Extension

When extending TransferAI:

1. **New Articulation Data**: Add new data using the documented format
2. **New Query Types**: Update `query_parser.py` and add test cases to `test_runner.py`
3. **Logic Improvements**: Enhance the `articulation` module to handle new patterns
4. **Prompt Refinements**: Modify `prompt_builder.py` to improve LLM outputs
5. **Testing**: Add new test cases and check against regression tests

## Current Development Status

The system currently:

- Passes 36/36 test cases with perfect accuracy
- Uses modular articulation components instead of monolithic logic processing
- Supports local embeddings and LLM inference
- Has standardized honors course notation and validation
- Includes improved validation response formatting

## Ongoing Improvements

Key improvements in progress:

- Refactoring `main.py` to reduce the monolithic `handle_query` method
- Further improving response consistency and format
- Reducing debug information in user-facing content
- Enhancing maintainability through better modularization 