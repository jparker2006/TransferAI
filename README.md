# TransferAI

TransferAI helps California students understand how their community college courses transfer to UC campuses, using AI to interpret complex articulation rules and provide clear, accurate guidance.

## Version 1.6 - Modular Architecture Release

This version represents a significant architectural refactoring to enhance maintainability, testability, and extensibility. Key improvements include:

- Implemented modular architecture with clear separation of concerns
- Added specialized query handlers for different query types
- Created a unified ArticulationFacade for all articulation operations
- Enhanced test coverage and organization
- Fixed contradictory logic in course validation
- Standardized honors course notation
- Improved query classification and processing
- Added full support for local embeddings (no OpenAI API dependency)

## System Architecture

TransferAI is built using established design patterns for robust and maintainable code:

### Design Patterns

- **Strategy Pattern**: Specialized query handlers for different query types
- **Repository Pattern**: Document access and data caching
- **Facade Pattern**: Simplified interfaces to complex subsystems
- **Dependency Injection**: Loose coupling and enhanced testability

### System Flow

1. **Query Intake**: User queries enter the system through the `TransferAIEngine`
2. **Query Processing**:
   - `QueryService` parses the query and extracts relevant filters
   - `QueryService` determines the query type (course validation, lookup, honors, etc.)
3. **Query Routing**:
   - The engine routes the query to the appropriate specialized handler via the handler registry
   - Each handler is optimized for specific query types (validation, equivalency, group, honors, etc.)
4. **Document Retrieval**:
   - Handlers access relevant articulation documents through the `DocumentRepository`
   - Documents are filtered based on extracted course codes, groups, or sections
5. **Articulation Logic**:
   - The `ArticulationFacade` provides a unified interface to all articulation functionality
   - Core validation, formatting, and rendering logic is delegated to specialized modules
6. **Response Generation**:
   - Handlers use the `PromptService` to build appropriate prompts
   - Responses are formatted according to query type and articulation rules
7. **Response Delivery**: Formatted responses are returned to the user

## Project Structure

The project follows a modular architecture:

```
TransferAI/
├── llm/                          # Core TransferAI package
│   ├── engine/                   # Core engine components
│   │   ├── transfer_engine.py    # Main engine - entry point for queries
│   │   ├── config.py             # Configuration management
│   │   └── utils.py              # Shared utilities
│   ├── handlers/                 # Query handlers
│   │   ├── base.py               # Handler base class and registry
│   │   ├── validation_handler.py # Course validation handler
│   │   ├── course_handler.py     # Course equivalency handler
│   │   ├── course_lookup_handler.py # Course lookup handler
│   │   ├── group_handler.py      # Group requirement handler
│   │   ├── honors_handler.py     # Honors queries handler
│   │   └── fallback_handler.py   # Default/fallback handler
│   ├── repositories/             # Data access layer
│   │   ├── document_repository.py # Document access and caching
│   │   ├── course_repository.py  # Course information access
│   │   └── template_repository.py # Template storage
│   ├── services/                 # Core services
│   │   ├── document_service.py   # Document loading & processing
│   │   ├── query_service.py      # Query parsing & classification
│   │   ├── prompt_service.py     # Prompt building & management
│   │   ├── matching_service.py   # Document matching & filtering
│   │   └── articulation_facade.py # Unified interface to articulation
│   ├── models/                   # Data models
│   │   ├── document.py           # Document wrapper models
│   │   ├── query.py              # Query models and types
│   │   ├── response.py           # Response models
│   │   └── config.py             # Configuration models
│   ├── templates/                # Prompt templates
│   │   ├── course_templates.py   # Course-related templates
│   │   ├── group_templates.py    # Group-related templates
│   │   └── helpers.py            # Template helper functions
│   ├── articulation/             # Core articulation logic
│   │   ├── validators.py         # Validates course requirements
│   │   ├── renderers.py          # Renders articulation data
│   │   ├── formatters.py         # Formats articulation responses
│   │   ├── analyzers.py          # Analyzes articulation data
│   │   ├── detectors.py          # Detects patterns in articulation
│   │   └── models.py             # Articulation data models
│   ├── data/                     # Data files for the system
│   ├── docs/                     # Documentation
│   ├── tests/                    # Unit and integration tests
│   │   ├── engine/               # Tests for engine components
│   │   ├── handlers/             # Tests for query handlers
│   │   ├── services/             # Tests for services
│   │   └── articulation/         # Tests for articulation logic
│   └── main.py                   # Application entry point
├── data/                         # Additional data files
├── regression tests/             # End-to-end test files
└── webpage/                      # Web interface components
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
   python3 llm/run_unit_tests.py
   ```

## Usage

```python
from llm.engine.transfer_engine import TransferAIEngine

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
python3 llm/run_unit_tests.py
```

Specific test module:
```
python3 llm/run_unit_tests.py services.test_articulation_facade
```

Regression tests:
```
python3 llm/regression_tests/test_runner.py
```

### Key Components

#### Engine
The core `TransferAIEngine` manages the query processing pipeline, coordinating between services and handlers.

#### Handlers
Specialized query handlers process different types of queries:
- `ValidationQueryHandler`: Validates if courses satisfy requirements
- `CourseEquivalencyHandler`: Identifies equivalent courses
- `CourseLookupHandler`: Provides information about courses that satisfy a specific UC course
- `GroupQueryHandler`: Processes group requirement queries
- `HonorsQueryHandler`: Handles honors course requirements
- `FallbackQueryHandler`: Processes queries that don't match other handlers

#### Services
- `DocumentService`: Loads and manages articulation documents
- `QueryService`: Parses and classifies user queries
- `PromptService`: Builds prompts for different query types
- `MatchingService`: Matches queries to relevant documents
- `ArticulationFacade`: Provides a unified interface to articulation logic

#### Models
The models package contains data structures that represent core system entities:
- `document.py`: Document models for articulation data representation
- `query.py`: Query models including QueryType enumeration for classification
- `response.py`: Response models for structured handler output
- `config.py`: Configuration models for system settings and parameters

#### Articulation Package
The core articulation modules handle the complex logic of course articulation:
- `validators.py`: Validates course combinations against requirements
- `renderers.py`: Renders articulation data in human-readable format
- `formatters.py`: Formats articulation responses consistently
- `analyzers.py`: Analyzes articulation data for patterns
- `detectors.py`: Detects specific patterns in articulation rules

## Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) before submitting pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 