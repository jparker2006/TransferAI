# TransferAI

TransferAI helps California students understand how their community college courses transfer to UC campuses, using AI to interpret complex articulation rules and provide clear, accurate guidance.

## Version 1.5.2 - 100% Test Accuracy Release

This version represents our latest milestone with perfect accuracy across all 36 test cases. Key improvements include:

- Fixed contradictory logic in course validation
- Resolved data fabrication issues in group responses
- Enhanced partial match explanations with clear formatting
- Fixed course description accuracy
- Standardized honors course notation
- Reduced response verbosity
- Added local embeddings support (no OpenAI API dependency)

## Project Structure

The project is organized as follows:

```
TransferAI/
├── llm/                      # Core TransferAI package
│   ├── articulation/         # Course articulation logic modules
│   ├── data/                 # Data files for the system
│   ├── docs/                 # Documentation
│   ├── regression tests/     # End-to-end test files
│   ├── tests/                # Unit and integration tests
│   ├── document_loader.py    # Module for loading articulation documents
│   ├── logic_formatter.py    # Legacy formatter (now modularized)
│   ├── main.py               # Main TransferAI engine
│   ├── prompt_builder.py     # LLM prompt construction
│   └── query_parser.py       # User query parsing
├── data/                     # Additional data files
└── webpage/                  # Web interface components
```

## Getting Started

### Prerequisites

- Python 3.9+
- Sentence Transformers (for local embeddings)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/TransferAI.git
   cd TransferAI
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run tests to verify installation:
   ```
   python3 llm/tests/prompt_tests/test_local_embeddings.py
   ```

## Usage

```python
from llm.main import TransferAIEngine

# Initialize the engine
engine = TransferAIEngine()
engine.configure()
engine.load()

# Process a query
response = engine.handle_query("Which De Anza courses satisfy CSE 8A at UCSD?")
print(response)
```

## Development

### Running Tests

Unit tests:
```
python -m pytest llm/tests/
```

Regression tests:
```
python test_prompt.py
```

### Code Organization

- `articulation/` - Core logic modules for course validation
  - `analyzers.py` - Analyzes course articulation data
  - `detectors.py` - Detects patterns in articulation rules
  - `formatters.py` - Formats articulation responses
  - `models.py` - Data models for articulation
  - `renderers.py` - Renders articulation data for display
  - `validators.py` - Validates course combinations against requirements

## Roadmap

See the [TransferAI v1.5 Roadmap](llm/regression%20tests/TransferAI%20v1.5%20Roadmap.md) for details on our future plans.

## Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 