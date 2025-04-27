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

## Phase 2: High Priority Bugs (Week 2)

### 2.1 Fix Course Description Accuracy
- **Tasks**:
  - Audit course descriptions in the system against official catalog
  - Update CIS 21JB description and any other inaccurate descriptions
  - Create a validation routine to flag description mismatches
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Test 17

### 2.2 Standardize Honors Course Notation
- **Tasks**:
  - Update honors course formatting in `articulation/formatters.py`
  - Create consistent honors notation helper (e.g., `format_honors_course`)
  - Replace all instances of honors formatting with the new helper
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Tests 13, 20, 34

### 2.3 Reduce Response Verbosity
- **Tasks**:
  - Review and trim templates in `prompt_builder.py`
  - Create more concise versions of explanation templates
  - Add configuration option for verbosity level
- **Estimated Time**: 2 days
- **Dependencies**: None
- **Milestone**: Passes Tests 7, 8, 22

## Phase 3: Medium Priority Bugs (Week 3)

### 3.1 Remove Debug Information
- **Tasks**:
  - Add post-processing filter to remove `<think>` sections
  - Update response generation pipeline to clean debug info
  - Create regression tests to ensure debug info doesn't leak
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Milestone**: No `<think>` sections in responses

### 3.2 Fix Redundant Information in Responses
- **Tasks**:
  - Update `articulation/group_processor.py` to deduplicate information
  - Add deduplication helper function for response generation
  - Verify all group articulation summaries are deduplicated
- **Estimated Time**: 1-2 days
- **Dependencies**: None
- **Milestone**: Passes Test 23

### 3.3 Standardize "No Articulation" Responses
- **Tasks**:
  - Create standard template for no-match scenarios in `articulation/formatters.py`
  - Update all reference points to use this template
  - Verify consistent formatting across response types
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Tests 14, 16

## Phase 4: Low Priority Bugs & Integration (Week 4)

### 4.1 Standardize List Formatting
- **Tasks**:
  - Review all response templates for formatting inconsistencies
  - Create standardized list formatting helpers
  - Update templates to use consistent styling
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Milestone**: Passes Tests 1, 8

### 4.2 Fix Version References
- **Tasks**:
  - Search codebase for version references
  - Update all references to consistently show v1.5
  - Add version constant to prevent future inconsistencies
- **Estimated Time**: 0.5 days
- **Dependencies**: None
- **Milestone**: Consistent version references

### 4.3 Improve Test Progress Indicators
- **Tasks**:
  - Update `test_runner.py` with better progress visualization
  - Add elapsed time and remaining estimate
  - Implement colored output for pass/fail status
- **Estimated Time**: 1 day
- **Dependencies**: None
- **Milestone**: Improved test runner UI

## Final Integration & Regression Testing (Week 4)

### 5.1 Full Regression Testing
- **Tasks**:
  - Run complete test suite
  - Verify all previously failing tests now pass
  - Document any remaining edge cases
- **Estimated Time**: 1 day
- **Dependencies**: All previous phases
- **Milestone**: All tests passing

### 5.2 Performance Validation
- **Tasks**:
  - Measure response generation time before and after changes
  - Ensure no performance regressions
  - Optimize any slow operations identified
- **Estimated Time**: 1 day
- **Dependencies**: Phase 5.1
- **Milestone**: Performance at or better than v1.4

### 5.3 Documentation Update
- **Tasks**:
  - Update user-facing documentation
  - Document API changes for developers
  - Update test documentation
- **Estimated Time**: 1 day
- **Dependencies**: Phase 5.1
- **Milestone**: Updated documentation

## Timeline Summary

- **Week 1**: Critical bugs (Phase 1)
- **Week 2**: High priority bugs (Phase 2)
- **Week 3**: Medium priority bugs (Phase 3)
- **Week 4**: Low priority bugs, integration, and final testing (Phase 4-5)

## Resource Allocation

- 1 senior developer for validation logic fixes
- 1 developer for UI/formatting improvements
- 1 QA engineer for test development and verification
- Product manager for review and documentation

## Success Criteria

1. All tests pass in the regression test suite
2. No new bugs introduced during fixes
3. Response quality and correctness improved
4. Performance maintained or improved
5. Documentation updated to reflect changes 