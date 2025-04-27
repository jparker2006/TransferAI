# TransferAI v1.5 Implementation Plan

## Phase 1: Critical Bugs (Week 1)

### 1.1 Fix Contradictory Logic in Single Course Validation ✅ COMPLETED
- **Tasks**:
  - ✅ Reviewed `articulation/validators.py` and `articulation/formatters.py` to identify inconsistent validation logic
  - ✅ Updated `render_binary_response` function in `formatters.py` to detect and fix the contradictory "alone only satisfies" pattern
  - ✅ Added unit tests to verify corrected behavior for single course validation
  - ✅ Fixed `include_binary_explanation` function to handle contradictory logic in validation summaries
- **Estimated Time**: 1-2 days
- **Actual Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Test 12 and 36
- **Notes**: Fixed by detecting the pattern "No, X alone only satisfies Y" and replacing it with "Yes, X satisfies Y" while updating the response state to affirmative.

### 1.2 Fix Data Fabrication in Group 2 Response ✅ COMPLETED
- **Tasks**:
  - ✅ Updated `llm/prompt_builder.py` to fix fabrication issues in the group prompt responses
  - ✅ Added explicit "DO NOT FABRICATE COURSE OPTIONS" section to the prompt instructions
  - ✅ Provided clear examples of what not to fabricate (e.g., "MATH 20C (complete all) or MATH 20D, MATH 20E")
  - ✅ Verified fix against Test 9 by confirming only verified data is displayed
- **Estimated Time**: 2-3 days
- **Actual Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Test 9
- **Notes**: Fixed by directly enhancing the LLM prompt with explicit instructions not to invent course options.

### 1.3 Improve Partial Match Explanations ✅ COMPLETED
- **Tasks**:
  - ✅ Redesigned partial match template in `articulation/formatters.py`
  - ✅ Fixed formatting issues to ensure missing courses are properly displayed in bold
  - ✅ Improved regex extraction to preserve bold formatting in partial match explanations
  - ✅ Added conditional logic to prevent double bold formatting of text
  - ✅ Enhanced `format_partial_match` to handle both bold and non-bold course inputs
- **Estimated Time**: 1-2 days
- **Actual Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Test 25 and 15
- **Notes**: Fixed by updating `format_partial_match` and `render_binary_response` functions to properly handle and display bold formatting for missing courses. Also improved key term highlighting to avoid interfering with partial match formatting.

## Phase 2: High Priority Improvements

### 2.1 Fix Course Description Accuracy (Test 17) ✅ COMPLETED
- **Task**: Update course description data and logic to ensure all descriptions match the official catalog
- **Subtasks**:
  - Identify source of incorrect course descriptions
  - Create mapping of course codes to accurate descriptions
  - Update document_loader.py to use correct course descriptions
  - Add unit tests to verify course descriptions
  - Confirm Test 17 passes with accurate descriptions
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Assigned To**: TBD
- **Status**: ✅ Completed
- **Milestone**: Test 17 passes with correct course descriptions

### 2.2 Standardize Honors Course Notation (Tests 13, 20, 34) ✅ COMPLETED
- **Task**: Create consistent formatting for honors courses across all responses
- **Subtasks**:
  - Create dedicated function in formatters.py for honors course formatting
  - Update all references to honors courses to use the new function
  - Add unit tests for honors course formatting
  - Verify Tests 13, 20, and 34 pass with consistent honors notation
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Assigned To**: TBD
- **Status**: ✅ Completed
- **Milestone**: Tests 13, 20, and 34 pass with consistent honors course notation

### 2.3 Reduce Response Verbosity (Tests 7, 8, 22) ✅ COMPLETED
- **Task**: Make responses more concise and focused on essential information
- **Subtasks**:
  - Review and trim templates in prompt_builder.py
  - Create ultra-concise formats for MINIMAL verbosity level
  - Remove unnecessary instructional text and explanatory sections 
  - Implement more efficient format for data presentation
  - Fix issue where MINIMAL verbosity produced longer prompts than STANDARD
  - Add dedicated test script for verifying verbosity levels
  - Test response length and clarity with modified prompts
- **Estimated Time**: 2 days
- **Dependencies**: None 
- **Assigned To**: TBD
- **Status**: ✅ Completed
- **Milestone**: Tests 7, 8, 22 pass with concise, focused responses

## Phase 3: Medium Priority Bugs (Week 2)

### 3.1 Remove Debug Information (Multiple Tests)
- **Tasks**:
  - Create dedicated response sanitizer function in main.py
  - Implement regex pattern matching to identify and strip debug blocks (`<think>...</think>`)
  - Add filtering for diagnostic log lines (prefixed with 🔍, 🧠, 🎯, etc.)
  - Create unified response post-processing pipeline
  - Add unit tests specifically for debug information removal
  - Verify no debug information leaks in all response types
- **Estimated Time**: 1 day
- **Dependencies**: None
- **User Impact**: High - Confusing technical information undermines user trust
- **Milestone**: No debug information in responses
- **Implementation Details**:
  ```python
  def sanitize_response(response: str) -> str:
      """Remove all debug information from response text."""
      # Remove <think> sections
      sanitized = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
      
      # Remove diagnostic log lines
      sanitized = re.sub(r'^[🔍🧠🎯📍].*$', '', sanitized, flags=re.MULTILINE)
      
      # Remove any remaining debug prefixes
      sanitized = re.sub(r'^\[DEBUG\].*$', '', sanitized, flags=re.MULTILINE)
      
      # Clean up excessive whitespace left by removals
      sanitized = re.sub(r'\n{3,}', '\n\n', sanitized)
      
      return sanitized.strip()
  ```

### 3.2 Fix Redundant Information in Responses (Test 23)
- **Tasks**:
  - Analyze the structure of redundant information in group responses
  - Implement deduplication logic in render_group_summary function
  - Create normalized representation of course requirements
  - Add smart consolidation of equivalent articulation paths
  - Add option groups to clearly represent alternatives
  - Handle edge cases like honors/non-honors duplications
  - Test with different group structures to verify robustness
- **Estimated Time**: 1.5 days
- **Dependencies**: None
- **User Impact**: Medium - Confusing but functional responses
- **Milestone**: Passes Test 23 with no redundant information
- **Implementation Approach**:
  - Create a normalization function that identifies conceptually equivalent articulation paths
  - Use a hash-based deduplication system for course requirement lists
  - Implement smarter rendering of equivalent options with clear alternative markers
  - Add detailed docstrings explaining the deduplication logic

### 3.3 Standardize "No Articulation" Responses (Tests 14, 16)
- **Tasks**:
  - Create standardized template function `format_no_articulation` in formatters.py
  - Ensure consistent messaging for courses with no articulation
  - Add helpful guidance about alternatives when appropriate
  - Update all reference points to use the new template
  - Verify consistent formatting across different response types
- **Estimated Time**: 0.5 days
- **Dependencies**: None
- **User Impact**: Medium - Inconsistent messaging causes confusion
- **Milestone**: Passes Tests 14, 16 with consistent formatting
- **Implementation Details**:
  ```python
  def format_no_articulation(uc_course: str, additional_guidance: str = None) -> str:
      """Format a standardized response for courses with no articulation."""
      response = f"❌ **No articulation available:** {uc_course} must be completed at UC San Diego."
      
      if additional_guidance:
          response += f"\n\n{additional_guidance}"
      else:
          response += "\n\nThis course cannot be satisfied with community college courses."
      
      return response
  ```

## Phase 4: Low Priority Bugs (Week 3)

### 4.1 Standardize List Formatting
- **Tasks**:
  - Create helper functions for generating consistently formatted lists
  - Standardize bullet point formats across all response types
  - Create styling constants for different list levels
  - Update all list generation code to use the helpers
- **Estimated Time**: 1 day
- **Dependencies**: None
- **User Impact**: Low - Aesthetic issue that doesn't affect functionality
- **Milestone**: Consistent formatting in Tests 1, 8

### 4.2 Fix Version References
- **Tasks**:
  - Create a central VERSION constant in a config module
  - Search codebase for version references using grep
  - Update all references to use the constant or explicitly mention v1.5
  - Create script to verify version consistency
- **Estimated Time**: 0.5 days
- **Dependencies**: None
- **User Impact**: Low - Minor confusion about current version
- **Milestone**: Consistent version references

### 4.3 Improve Test Progress Indicators
- **Tasks**:
  - Add color coding for test status (pass/fail)
  - Implement progress bar for test batch runs
  - Add elapsed time and estimated remaining time
  - Improve error output formatting for failed tests
- **Estimated Time**: 1 day
- **Dependencies**: None
- **User Impact**: Low - Developer experience issue
- **Milestone**: Improved test runner output

## Phase 5: Code Refactoring (Weeks 4-5)

### 5.1 Refactor main.py (Week 4)
- **Tasks**:
  - Create comprehensive test suite for current behavior
  - Document the main query handling pipeline
  - Break down `handle_query` (200+ lines) into smaller components:
    - Query preprocessing
    - Document matching
    - Section and group handling
    - Course validation
    - Response generation
  - Extract nested conditionals into discrete, testable functions
  - Implement proper error handling and logging
  - Create clean interfaces between components
  - Update documentation to reflect new architecture
- **Estimated Time**: 5 days
- **Dependencies**: All bug fixes completed
- **Refactoring Patterns**:
  - Extract Method: Split large methods into focused functions
  - Strategy Pattern: For different query handling approaches
  - Factory Pattern: For response generation
- **Testing Strategy**:
  - Create snapshot tests before refactoring
  - Verify equivalent behavior after refactoring
  - Add unit tests for each extracted component

### 5.2 Modularize query_parser.py (Week 4-5)
- **Tasks**:
  - Add comprehensive unit tests for current functionality
  - Create class-based structure for filter extraction
  - Break down complex parsing logic into smaller components:
    - Course code normalization
    - Filter extraction
    - Group and section matching
    - Document filtering
  - Improve separation between course extraction and matching logic
  - Add stronger type annotations throughout
  - Create clear interfaces between parsing components
- **Estimated Time**: 4 days
- **Dependencies**: main.py refactoring
- **Refactoring Patterns**:
  - Command Pattern: For different parsing operations
  - Visitor Pattern: For traversing query structures
  - Builder Pattern: For constructing filter objects
- **Testing Strategy**:
  - Unit tests for each parser component
  - Property-based testing for parser robustness
  - Integration tests with main.py

### 5.3 Improve prompt_builder.py architecture (Week 5)
- **Tasks**:
  - Extract hardcoded templates into configuration files
  - Create a cleaner abstraction layer for verbosity control
  - Implement OOP approach for prompt building
  - Add stronger typing and validation for prompt parameters
  - Create a template registry for better organization
  - Add more comprehensive docstrings
- **Estimated Time**: 3 days
- **Dependencies**: main.py and query_parser.py refactoring
- **Refactoring Patterns**:
  - Template Method: For prompt construction
  - Decorator: For verbosity modifications
  - Composite: For prompt component assembly
- **Testing Strategy**:
  - Unit tests for each prompt builder function
  - Visual diff testing for template changes

### 5.4 Establish Clean Interfaces (Week 5)
- **Tasks**:
  - Define clear module boundaries throughout the codebase
  - Document interfaces between components
  - Create consistent patterns for data flow
  - Add integration tests to verify component interactions
  - Update type annotations to support clear interfaces
  - Create interface documentation
- **Estimated Time**: 2 days
- **Dependencies**: Previous refactoring steps
- **Deliverables**:
  - Interface documentation
  - Integration test suite
  - Updated architecture diagram

## Timeline Summary

- **Week 1** (Completed): Critical bugs and high-priority improvements (Phases 1-2)
- **Week 2** (Current): Medium-priority bugs (Phase 3)
- **Week 3**: Low-priority bugs and testing (Phase 4)
- **Week 4**: Refactoring main.py and beginning query_parser.py (Phase 5.1-5.2)
- **Week 5**: Completing refactoring and integration testing (Phase 5.2-5.4)

## Resource Allocation

- 1 senior developer for refactoring complex components
- 1 developer for bug fixes and testing
- 1 QA engineer for test development and verification
- Product manager for review and sign-off

## Success Criteria

1. All tests pass in the regression test suite
2. No new bugs introduced during fixes or refactoring
3. Response quality and correctness improved
4. Performance maintained or improved
5. Code maintainability metrics improved (complexity, coupling, cohesion)
6. Documentation updated to reflect new architecture 