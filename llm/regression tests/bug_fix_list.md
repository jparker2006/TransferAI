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

4. **[Test 17] Incorrect Course Descriptions**
   - **Issue**: CIS 21JB incorrectly described as "Introduction to Database Systems" 
   - **File**: `articulation/formatters.py` or relevant course description mapping
   - **Fix**: Update course descriptions to match actual curriculum
   - **Acceptance Criteria**: All course descriptions match official university catalog

5. **[Test 13, 20, 34] Inconsistent Honors Course Notation**
   - **Issue**: Honors courses are formatted differently across responses
   - **File**: `articulation/formatters.py`
   - **Fix**: Standardize honors course representation
   - **Acceptance Criteria**: All honors courses follow consistent format (e.g., "MATH 1AH (Honors)")

6. **[Test 7, 8, 22] Excessive Verbose Responses**
   - **Issue**: Responses contain unnecessary text and explanations
   - **File**: `prompt_builder.py` and template files
   - **Fix**: Trim response templates to essential information only
   - **Acceptance Criteria**: Responses should be concise and focused on answering the user's question

## Medium Priority Bugs

7. **[Multiple Tests] `<think>` Sections in Responses**
   - **Issue**: Debug information showing up in user-facing responses
   - **File**: Output formatting in response generation pipeline
   - **Fix**: Add filter to remove all `<think>` sections from final output
   - **Acceptance Criteria**: No `<think>` sections appear in any user-facing response

8. **[Test 23] Redundant Information in Group 3 Response**
   - **Issue**: Articulation summary contains duplicate information
   - **File**: `articulation/group_processor.py` or similar
   - **Fix**: Deduplicate information in group articulation summaries
   - **Acceptance Criteria**: Each piece of information appears only once in the response

9. **[Test 14, 16] Inconsistent "No Articulation" Responses**
   - **Issue**: Different formatting for courses with no articulation
   - **File**: `articulation/formatters.py`
   - **Fix**: Create standard template for no-match scenarios
   - **Acceptance Criteria**: All "no articulation" responses follow consistent format

## Low Priority Bugs

10. **[Test 1, 8] Inconsistent List Formatting**
    - **Issue**: Bullet points and section headers have inconsistent styling
    - **File**: Response formatting templates
    - **Fix**: Standardize list formatting across all response types
    - **Acceptance Criteria**: All lists and sections follow consistent formatting style

11. **[All Tests] Version Reference Inconsistencies**
    - **Issue**: Mixed references to v1.4 and v1.5
    - **File**: Various configuration files
    - **Fix**: Update all version references to v1.5
    - **Acceptance Criteria**: All version references consistently show v1.5

12. **[Test Interface] Test Progress Indicators**
    - **Issue**: Basic progress indicators ("Running TransferAI test batch X...")
    - **File**: `test_runner.py`
    - **Fix**: Enhance visual progress indicators
    - **Acceptance Criteria**: More intuitive visual feedback during test execution

## Implementation Notes

- Fixes for Critical and High Priority bugs should be completed before v1.5 release
- Each fix should include a corresponding test case to verify the fix
- Code review should verify that fixes don't introduce regressions in other tests
- Document any API changes resulting from these fixes

## Test Verification Process

1. After each fix, run the specific test(s) affected to verify resolution
2. Run the full test suite to ensure no regressions
3. For UI/UX changes, perform manual verification with sample queries
4. Update test expected outputs to match new improved responses 