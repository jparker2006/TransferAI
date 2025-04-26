# TransferAI LLM Engine

## Overview

TransferAI is a language model-powered system designed to help California Community College (CCC) students understand how their courses will transfer to University of California (UC) schools. The system uses Retrieval Augmented Generation (RAG) to process complex articulation logic from ASSIST.org and provide accurate, counselor-like responses to student queries.

## Key Features

- **Semantic Search**: Finds relevant articulation information based on natural language queries
- **Complex Logic Processing**: Handles AND/OR combinations, course sequences, and group requirements
- **LLM-Powered Explanations**: Generates clear, accurate responses in a counselor-like tone
- **Validation**: Verifies whether specific course combinations satisfy requirements
- **Multi-Course Queries**: Processes questions about multiple courses at once

## Directory Structure

```
llm/
├── data/                    # RAG data storage
│   ├── rag_data.json        # Structured articulation data
│   └── README.md            # Data documentation
├── testing/                 # Test files and version history
│   ├── TransferAI v1.0-1.3.txt  # Version logs
│   ├── TransferAI v1.4 Todo.txt # Planned improvements
│   ├── TransferAI v1 Progress.md # Progress tracking
│   └── README.md            # Testing documentation
├── document_loader.py       # Loads and processes articulation documents
├── logic_formatter.py       # Formats articulation logic for presentation
├── main.py                  # Core engine with query handling
├── prompt_builder.py        # Constructs prompts for the LLM
├── query_parser.py          # Parses and analyzes user queries
├── test_runner.py           # Test suite for system validation
└── README.md                # Main documentation
```

## Component Documentation

- [Main LLM Engine](README.md) - Core components and workflow
- [Data Directory](data/README.md) - RAG data structure and format
- [Testing Directory](testing/README.md) - Test methodology and version history

## Getting Started

### Requirements

TransferAI requires the following dependencies:

- Python 3.8+
- LlamaIndex
- spaCy (with `en_core_web_sm` model)
- Ollama (for local LLM inference)
- Hugging Face Transformers (for embeddings)

### Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```
3. Install Ollama following instructions at [ollama.ai](https://ollama.ai)
4. Pull the LLaMA3 model:
   ```
   ollama pull llama3
   ```

### Running the Engine

To start the TransferAI engine:

```python
from main import TransferAIEngine

engine = TransferAIEngine()
engine.configure()  # Set up LLM and embeddings
engine.load()       # Load articulation data
engine.handle_query("What De Anza courses satisfy CSE 8A at UCSD?")
```

### Running Tests

To run the test suite:

```
python test_runner.py
```

## How It Works

1. **Data Loading**: The system loads structured articulation data from `data/rag_data.json`
2. **Query Processing**: When a user submits a query, `query_parser.py` extracts relevant entities
3. **Document Retrieval**: Vector search finds documents matching the query
4. **Logic Processing**: `logic_formatter.py` renders the articulation logic into readable text
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

- **LLM**: Uses Ollama with LLaMA3 for deterministic, reliable responses
- **Embeddings**: Uses Hugging Face's all-mpnet-base-v2 for semantic search
- **Vector Database**: Uses LlamaIndex for document retrieval
- **NLP Processing**: Uses spaCy for query parsing and entity extraction

## Development and Extension

When extending TransferAI:

1. **New Articulation Data**: Add new data to `data/rag_data.json` using the documented format
2. **New Query Types**: Update `query_parser.py` and add test cases to `test_runner.py`
3. **Logic Improvements**: Enhance `logic_formatter.py` to handle new patterns
4. **Prompt Refinements**: Modify `prompt_builder.py` to improve LLM outputs
5. **Testing**: Add new test cases and check against regression tests

## Future Roadmap

See [TransferAI v1.4 Todo.txt](testing/TransferAI%20v1.4%20Todo.txt) for planned improvements:

- Enhanced honors course detection
- Redundant course flagging
- Improved validation outputs
- Integration with API endpoints
- Additional testing tools 