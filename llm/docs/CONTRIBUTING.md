# Contributing to TransferAI

This guide outlines how to contribute to the TransferAI project, with a specific focus on the articulation package that handles course articulation logic.

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/TransferAI.git
   cd TransferAI
   ```

2. **Set up your development environment**
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Run tests to verify setup
   python -m llm.run_unit_tests
   ```

## Project Architecture

TransferAI has a modular architecture with the following key components:

- **llm/articulation/** - Core package for articulation logic
- **llm/main.py** - Main application entry point
- **llm/tests/** - Test suite for all components

The articulation package follows a modular design:

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

## Development Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow existing code style and patterns
   - Add appropriate tests for new functionality
   - Update documentation as needed

3. **Run tests**
   ```bash
   python -m llm.run_unit_tests
   ```

4. **Submit a pull request**
   - Provide a clear description of the changes
   - Reference any related issues

## Coding Guidelines

### General Guidelines

- Follow PEP 8 style guidelines
- Use type hints for all function parameters and return values
- Write docstrings for all functions and classes
- Keep functions focused on a single responsibility
- Maintain backward compatibility with existing APIs

### Articulation Package Guidelines

1. **Models (models.py)**
   - Use Pydantic for data validation
   - Define clear relationships between models
   - Document validation rules

2. **Validators (validators.py)**
   - Keep validation logic separate from presentation
   - Return structured validation results
   - Handle edge cases gracefully

3. **Renderers (renderers.py)**
   - Focus exclusively on presentation logic
   - Support different output formats as needed
   - Make output human-readable and clear

4. **Formatters (formatters.py)**
   - Maintain consistent response structures
   - Make formatting customizable where appropriate
   - Focus on high-level response organization

5. **Analyzers (analyzers.py)**
   - Design for non-destructive analysis
   - Optimize for performance on large datasets
   - Return structured analysis results

6. **Detectors (detectors.py)**
   - Focus on pattern recognition and special cases
   - Document detected patterns clearly
   - Handle edge cases gracefully

### Testing Guidelines

1. **Test Structure**
   - Group tests by functionality in test classes
   - Follow AAA pattern (Arrange, Act, Assert)
   - Use descriptive test names

2. **Test Coverage**
   - Aim for 90%+ coverage of new code
   - Test edge cases and error conditions
   - Include integration tests for interactions between components

3. **Test Data**
   - Use realistic test fixtures
   - Explain test data in comments
   - Keep test data maintainable and clear

## Documentation Guidelines

1. **Code Documentation**
   - Every function should have a docstring
   - Include parameter descriptions and return value
   - Document exceptions and edge cases

2. **Module Documentation**
   - Each module should have a top-level docstring
   - Explain module purpose and key concepts
   - Document relationships with other modules

3. **Example Documentation**
   - Provide usage examples for key functions
   - Include real-world scenarios
   - Show input/output relationships

## Contribution Process

1. **For small changes:**
   - Submit a pull request with the fix or enhancement
   - Include tests and documentation

2. **For larger features:**
   - Open an issue to discuss the design first
   - Break down implementation into manageable PRs
   - Update documentation comprehensively

## Code Review Criteria

Pull requests will be evaluated based on:
- Adherence to coding guidelines
- Test coverage and quality
- Documentation completeness
- Performance considerations
- Maintainability and readability

## Need Help?

If you have questions or need guidance, please:
- Open an issue with the "question" label
- Check existing documentation first
- Provide context about your contribution goals

Thank you for contributing to TransferAI! 