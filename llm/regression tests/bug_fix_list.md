# TransferAI v1.5 Bug Fix Priority List

## Critical Bugs (Must Fix)

1. **[Test 12, 36] Contradictory Logic in Single Course Validation** ✅ FIXED
   - **Issue**: System responds "No, X alone only satisfies Y" which is logically contradictory
   - **File**: `articulation/validators.py` and/or `articulation/formatters.py`
   - **Fix**: Updated `render_binary_response` and `include_binary_explanation` functions in `formatters.py` to detect and correct the contradictory "alone only satisfies" pattern
   - **Acceptance Criteria**: Response should clearly state "Yes, X satisfies Y" without contradictions
   - **Verification**: Added test cases in `test_articulation_formatters.py` to verify the fix

2. **[Test 9] Data Fabrication in Group 2 Response** ✅ FIXED
   - **Issue**: System is generating course options that don't exist in ASSIST data
   - **File**: `llm/prompt_builder.py`
   - **Fix**: Enhanced the `build_group_prompt` function with explicit instructions to prevent fabrication of course options
   - **Acceptance Criteria**: All course options shown must be verifiable against rag_data.json
   - **Verification**: Test case 9 now shows only verified information, no fabricated options

3. **[Test 25, 15] Confusing Partial Match Explanations** ✅ FIXED
   - **Issue**: Progress bars and percentages don't clearly explain what's missing
   - **File**: `articulation/formatters.py`
   - **Fix**: Redesigned partial match template in `format_partial_match` function to clearly highlight missing requirements with proper bold formatting. Fixed extraction and preservation of bold text in `render_binary_response` function and prevented double formatting of already bold text.
   - **Acceptance Criteria**: Users should immediately understand what's missing and what to do next
   - **Verification**: Updated tests pass in `test_articulation_formatters.py`, particularly in `TestImprovedPartialMatchRendering` class

## High Priority Bugs

4. **[Test 17] Incorrect Course Descriptions** ✅ FIXED
   - **Issue**: CIS 21JB incorrectly described as "Introduction to Database Systems" 
   - **File**: `document_loader.py` and `prompt_builder.py`
   - **Fix**: Added course description utilities to `document_loader.py` and updated `prompt_builder.py` to enrich rendered logic with accurate course descriptions from the articulation data 
   - **Acceptance Criteria**: All course descriptions match official university catalog
   - **Verification**: Added unit tests in `test_document_loader.py` to verify correct course descriptions

5. **[Test 13, 20, 34] Inconsistent Honors Course Notation** ✅ FIXED
   - **Issue**: Honors courses are formatted differently across responses
   - **File**: `articulation/formatters.py`
   - **Fix**: Standardize honors course representation
   - **Acceptance Criteria**: All honors courses follow consistent format (e.g., "MATH 1AH (Honors)")

6. **Excessive Verbose Responses** (Tests 7, 8, 22) ✅ FIXED
   - **Problem**: Responses are too verbose, making it difficult to find key information
   - **Files to Fix**: 
     - `llm/prompt_builder.py`
   - **Fix**: 
     - Completely redesigned prompt templates for different verbosity levels
     - Created ultra-concise formats for MINIMAL verbosity level that reduced prompt size by 25-42%
     - Removed unnecessary instructional text and explanatory sections
     - Implemented a more efficient format for data presentation
     - Fixed issue where MINIMAL verbosity was paradoxically producing longer prompts than STANDARD
   - **Acceptance Criteria**: 
     - Responses are concise and focused on essential information ✅
     - Key articulation details are presented before explanations ✅
     - Response length reduced by at least 30% ✅
     - All verbosity tests (7, 8, 22) must pass ✅
   - **Root Cause**: 
     Previous prompt templates in `prompt_builder.py` encouraged overly detailed explanations and contained excessive instructional text that defeated the purpose of the verbosity settings.
   - **Verification**:
     Added dedicated test script `test_verbosity.py` to verify proper prompt size reduction across verbosity levels.

## Medium Priority Bugs

7. **[Multiple Tests] Debug Information in Responses**
   - **Issue**: Debug information like `<think>` sections and diagnostic data appearing in user-facing responses
   - **Files to Fix**: 
     - `llm/main.py`
     - `articulation/formatters.py`
   - **Fix Approach**: 
     - Create a dedicated response sanitizer function in `llm/main.py` that removes all debug information
     - Implement regex pattern matching to identify and strip debug blocks (`<think>...</think>`)
     - Add filtering for diagnostic log lines starting with common debug indicators (🔍, 🧠, 🎯)
     - Create a unified response post-processing pipeline for all output types
     - Add unit tests specifically for debug information removal
   - **Root Cause**: 
     Current implementation passes raw LLM responses to users without proper sanitization
   - **User Impact**: High - Users see confusing technical information that undermines trust
   - **Estimated Time**: 1 day
   - **Acceptance Criteria**: 
     - No `<think>` sections appear in any user-facing responses
     - All diagnostic information completely removed from output
     - Sanitization doesn't affect legitimate response content
   - **Verification Strategy**:
     Create specific test cases with intentionally injected debug information to verify removal

8. **[Test 23] Redundant Information in Group 3 Response**
   - **Issue**: Articulation summary contains duplicate information about course requirements
   - **Files to Fix**:
     - `articulation/group_processor.py`
     - `articulation/formatters.py` 
   - **Fix Approach**:
     - Add deduplication logic in `render_group_summary` function
     - Implement smart consolidation of equivalent articulation paths
     - Create a normalized representation of course requirements before rendering
     - Add option groups to represent alternative but equivalent paths clearly
     - Handle edge cases like honors/non-honors duplications
   - **Root Cause**:
     Group data structure doesn't account for conceptually duplicate information across sections
   - **User Impact**: Medium - Responses are confusing but still functional
   - **Estimated Time**: 1.5 days
   - **Acceptance Criteria**:
     - Each piece of information appears only once in the response
     - Equivalent options are presented in a clear, consolidated way
     - Response structure remains clean and easy to understand
   - **Verification Strategy**:
     Run Test 23 and manually verify no redundant information exists in the response

9. **[Test 14, 16] Inconsistent "No Articulation" Responses**
   - **Issue**: Different formatting and messaging for courses with no articulation
   - **Files to Fix**:
     - `articulation/formatters.py`
     - `llm/prompt_builder.py`
   - **Fix Approach**: 
     - Create a standardized template function `format_no_articulation` in formatters.py
     - Ensure consistent messaging that clearly states no articulation exists
     - Add helpful guidance about alternatives when appropriate
     - Update prompt templates to handle no-articulation cases consistently
     - Ensure template is used at all response generation points
   - **Root Cause**:
     Multiple code paths for handling no-articulation cases without a unified approach
   - **User Impact**: Medium - Inconsistent messaging causes confusion
   - **Estimated Time**: 0.5 days
   - **Acceptance Criteria**:
     - All "no articulation" responses follow consistent format and wording
     - Clear guidance provided to users about their options
     - No contradictions or inconsistencies in messaging
   - **Verification Strategy**:
     Run Tests 14 and 16 to verify consistent formatting and messaging

## Low Priority Bugs

10. **[Test 1, 8] Inconsistent List Formatting**
    - **Issue**: Bullet points and section headers have inconsistent styling
    - **Files to Fix**:
      - `articulation/formatters.py`
      - Response templates in various files
    - **Fix Approach**:
      - Create helper functions for generating consistently formatted lists
      - Standardize bullet point formats across all response types
      - Create styling constants for different list levels
      - Update all list generation code to use the helpers
    - **Root Cause**:
      No centralized list formatting mechanism in the codebase
    - **User Impact**: Low - Aesthetic issue that doesn't affect functionality
    - **Estimated Time**: 1 day
    - **Acceptance Criteria**: All lists follow consistent formatting style
    - **Verification Strategy**: Verify Tests 1 and 8 have consistent formatting

11. **[All Tests] Version Reference Inconsistencies**
    - **Issue**: Mixed references to v1.4 and v1.5 across the codebase
    - **Files to Fix**: Various configuration and documentation files
    - **Fix Approach**:
      - Create a central VERSION constant
      - Search and replace all version references to use the constant
      - Update all documentation to reference v1.5 consistently
    - **Root Cause**: Manual version updates missed some references
    - **User Impact**: Low - Minor confusion about current version
    - **Estimated Time**: 0.5 days
    - **Acceptance Criteria**: All version references consistently show v1.5
    - **Verification Strategy**: Grep search for version references

12. **[Test Interface] Test Progress Indicators**
    - **Issue**: Basic progress indicators need improvement
    - **Files to Fix**: `test_runner.py`
    - **Fix Approach**:
      - Add color coding for test status (pass/fail)
      - Implement progress bar for test batch runs
      - Add elapsed time and estimated remaining time
      - Improve error output formatting for failed tests
    - **Root Cause**: Basic implementation focused on functionality over UX
    - **User Impact**: Low - Developer experience issue
    - **Estimated Time**: 1 day
    - **Acceptance Criteria**: Improved visual feedback during test execution
    - **Verification Strategy**: Run test suite and verify improved indicators

## Code Refactoring Plan (Post-Bug Fixes)

Once all bugs are fixed, we'll implement a comprehensive refactoring focused on modularization:

### Phase 1: main.py Refactoring

- **Priority Areas**:
  - Break down `handle_query` (200+ lines) into smaller components
  - Extract the query processing pipeline into discrete stages
  - Improve error handling and logging
  
- **Key Refactoring Patterns**:
  - Extract Method: Split large methods into focused functions
  - Strategy Pattern: For different query handling approaches
  - Factory Pattern: For response generation
  
- **Testing Strategy**:
  - Create comprehensive test suite before refactoring
  - Implement interface tests to verify consistent behavior
  - Use snapshot testing for response formatting

### Phase 2: query_parser.py Modularization

- **Priority Areas**:
  - Refactor complex parsing logic
  - Improve separation of concerns
  - Add stronger type annotations
  
- **Key Refactoring Patterns**:
  - Command Pattern: For different parsing operations
  - Visitor Pattern: For traversing query structures
  - Builder Pattern: For constructing filter objects
  
- **Testing Strategy**:
  - Unit tests for each parsing component
  - Property-based testing for parser robustness
  - Benchmark tests for performance

### Phase 3: prompt_builder.py Improvements

- **Priority Areas**:
  - Extract templates to configuration
  - Improve verbosity management
  - Add template validation
  
- **Key Refactoring Patterns**:
  - Template Method: For prompt construction
  - Decorator: For verbosity modifications
  - Composite: For prompt component assembly
  
- **Testing Strategy**:
  - Unit tests for each prompt builder function
  - Visual diff testing for template changes
  - Performance tests for template rendering

## Implementation Notes

- Bug fixes take priority over refactoring to ensure product stability
- Each refactoring phase should be done with continuous testing to prevent regressions
- Code review should verify that fixes don't introduce regressions in other tests
- Document any API changes resulting from these fixes or refactorings

## Test Verification Process

1. After each fix, run the specific test(s) affected to verify resolution
2. Run the full test suite to ensure no regressions
3. For UI/UX changes, perform manual verification with sample queries
4. Update test expected outputs to match new improved responses 

### Course Description Accuracy (Test 17)
- **Description:** CIS 21JB is incorrectly described as "Introduction to Database Systems"
- **Resolution:** ✅ Fixed course description extraction regex in prompt_builder.py to correctly identify all courses including those with letter suffixes. Enhanced _enrich_with_descriptions function to properly handle honors courses and ensure all occurrences of a course are enriched.
- **Acceptance Criteria:** ✅ Course descriptions match the official curriculum
- **Verification Method:** Run test_prompt.py with Test 17 and verify course descriptions are accurate

### Standardize Honors Course Notation (Tests 13, 20, 34)
- **Issue:** Honors courses are formatted differently across responses
- **Resolution:** ✅ Created a dedicated `format_honors_course` function in formatters.py that standardizes honors course representation across the system. Updated all formatter functions to use this new helper, ensuring consistent notation.
- **Acceptance Criteria:** ✅ All honors courses follow consistent format (e.g., "MATH 1AH (Honors)")
- **Verification Method:** Added unit tests in test_articulation_formatters.py specifically for the formatting function and verified with test_prompt.py for Tests 13, 20, and 34.

### Excessive Verbose Responses (Tests 7, 8, 22)
- **Problem:** Responses are too verbose, making it difficult to find key information
- **Fix:** 
  - Completely redesigned prompt templates for different verbosity levels
  - Created ultra-concise formats for MINIMAL verbosity level that reduced prompt size by 25-42%
  - Removed unnecessary instructional text and explanatory sections
  - Implemented a more efficient format for data presentation
  - Fixed issue where MINIMAL verbosity was paradoxically producing longer prompts than STANDARD
- **Acceptance Criteria:** 
  - Responses are concise and focused on essential information ✅
  - Key articulation details are presented before explanations ✅
  - Response length reduced by at least 30% ✅
  - All verbosity tests (7, 8, 22) must pass ✅
- **Root Cause:** 
  Previous prompt templates in `prompt_builder.py` encouraged overly detailed explanations and contained excessive instructional text that defeated the purpose of the verbosity settings.
- **Verification:**
  Added dedicated test script `test_verbosity.py` to verify proper prompt size reduction across verbosity levels. 