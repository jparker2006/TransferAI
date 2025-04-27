# TransferAI Migration Plan: From Logic Formatter to Articulation Package

## Overall Migration Strategy

The migration from the monolithic `logic_formatter.py` to the modular `articulation` package will follow a phased approach to minimize disruption and ensure stability. This document outlines the specific steps required to complete the migration.

## Phase 1: Complete the Imports Migration (In Progress)

### 1. Update Import Statements in Dependent Modules

All imports from `logic_formatter.py` or `logic_formatter_adapter.py` should be changed to import from the `articulation` package instead:

```python
# Before
from logic_formatter import is_articulation_satisfied, render_logic_str

# After
from articulation import is_articulation_satisfied, render_logic_str
```

For specialized functions, use the appropriate submodule:

```python
# For analyzer functions
from articulation.analyzers import find_uc_courses_satisfied_by, count_uc_matches

# For model classes
from articulation.models import CourseOption, LogicBlock
```

### 2. Handle Function Name Changes

Some functions may have been renamed or their signatures slightly modified. The main changes to be aware of:

- `render_logic()` has been replaced by `render_logic_str()` - update all calls accordingly
- The `articulation.find_uc_courses_satisfied_by()` function now exists in the analyzers module

### 3. Update Tests to Use Articulation Package

All test files should import from the articulation package rather than logic_formatter:

```python
# Before
from logic_formatter import is_articulation_satisfied

# After
from articulation import is_articulation_satisfied
```

## Phase 2: Test and Validate the Migration

### 1. Create Migration Test Suite

The `test_migration.py` file has been created to verify that the articulation package produces identical results to the original logic_formatter functions. This test suite:

- Imports both the legacy and new implementations
- Runs the same inputs through both
- Verifies the outputs are identical

### 2. Fix Any Pydantic Model Issues

We've encountered a Pydantic validation error in the models. This needs to be fixed:

```python
# In articulation/models.py, change:
@root_validator
def validate_n_courses(cls, values):
    # existing code...

# To:
@root_validator(skip_on_failure=True)
def validate_n_courses(cls, values):
    # existing code...
```

Or better, migrate to Pydantic v2 pattern:

```python
@model_validator
def validate_n_courses(self) -> 'ArticulationGroup':
    # Updated validation logic
    return self
```

### 3. Run Existing Tests with New Implementation

Run the entire test suite to verify that everything works correctly with the new imports:

```
python3 -m unittest discover -s llm/tests
```

## Phase 3: Replace the Legacy File

### 1. Rename the Adapter File

Once all tests pass:

```bash
# Backup the original logic_formatter.py
mv llm/logic_formatter.py llm/logic_formatter.py.bak

# Install the adapter as the new logic_formatter.py
cp llm/logic_formatter_adapter.py llm/logic_formatter.py
```

### 2. Update the Readme

Update documentation to reflect the new architecture and preferred import patterns:

```markdown
## Importing Articulation Functions

For best practices, import directly from the articulation package:

```python
from articulation import is_articulation_satisfied
from articulation.validators import explain_if_satisfied
from articulation.models import LogicBlock
```

Legacy imports from `logic_formatter` will continue to work but are deprecated.
```

## Phase 4: Complete Migration to Direct Imports

### 1. Gradually Update Legacy Imports

Over time, update all modules to import directly from the appropriate articulation submodules:

```python
# Instead of:
from articulation import is_articulation_satisfied

# Prefer:
from articulation.validators import is_articulation_satisfied
```

This makes dependencies clearer and improves code organization.

### 2. Final Cleanup

Once all modules use direct imports, the adapter layer can be simplified or eventually removed entirely, completing the migration.

## Timeline

1. **Week 1**: Complete import updates in main.py and prompt_builder.py
2. **Week 1**: Fix Pydantic validation issues and run migration tests
3. **Week 2**: Replace logic_formatter.py with the adapter
4. **Weeks 3-4**: Gradually update all imports to use direct submodule imports 