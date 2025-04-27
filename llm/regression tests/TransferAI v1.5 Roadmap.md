# TransferAI v1.5 Roadmap

## Overview
This roadmap outlines improvements needed for the TransferAI system based on analysis of the test results. The focus is on enhancing accuracy, consistency, and user experience by fixing identified issues in the current implementation.

## Detailed Analysis of Test Results

### Common Error Patterns

1. **Logical Contradictions in Responses**
   - Tests 12 and 36 exhibit similar logical errors where the system responds "No, X alone only satisfies Y" which is contradictory.
   - This suggests a bug in the validation and response generation logic, particularly in handling single-course validations.

2. **Inconsistent Group Validation**
   - Group logic works correctly for some tests (5, 6) but produces fabricated data in others (9).
   - The system appears to successfully detect when courses span across sections but struggles with displaying complex group requirements.

3. **Honors Course Handling**
   - The system correctly identifies honors/non-honors pairs (Test 13, 20, 34) but formats them inconsistently.
   - The response generation needs standardization for honors course notation.

4. **Verbosity Issues**
   - Many responses (Tests 1, 7, 8, 9, 22) contain excessive text that doesn't add value.
   - The `<think>` sections need to be removed in production and responses streamlined.

### Test Failure Analysis

| Test # | Issue Type | Root Cause | Recommended Fix |
|--------|------------|------------|-----------------|
| 12 | Logic Error | Incorrect negation in validation result | Fix validation_result_formatter.py to handle single course validations correctly |
| 36 | Logic Error | Same as Test 12 | Same fix as Test 12 |
| 9 | Data Fabrication | Course options not found in rag_data.json | Ensure group_logic_processor.py only returns options from the actual data |
| 17 | Course Description | Incorrect course description mapping | Update course_description_mapping in articulation/formatters.py |
| 22 | Verbosity | Excessive explanation in template | Simplify course_options_template in prompt_builder.py |
| 25 | Partial Match | Unclear explanation of missing courses | Improve partial_match_template in articulation/formatters.py |

## High Priority Improvements

### 1. Response Accuracy and Formatting Issues
- **Fix Test 12 Response Format:** The response "No, MATH 2BH alone only satisfies MATH 18" is confusing and contains a logical error. It should either read "Yes, MATH 2BH satisfies MATH 18" or "MATH 2BH satisfies MATH 18 only."
- **Improve Test 36 Response:** The response "No, CIS 22C alone only satisfies CSE 12" is contradictory. It should be "Yes, CIS 22C satisfies CSE 12."
- **Fix List Format Consistency:** In several responses (like Test 8), ensure consistent formatting for listing course options, with clear section headers and bullet points.

### 2. Group Logic Handling
- **Enhance Group Logic Validation:** For tests like Test 5 and Test 6, the logic correctly identifies that courses from different sections don't satisfy Group 1, but the presentation could be clearer.
- **Improve Group 3 Response (Test 23):** The articulation summary has redundant and potentially confusing information. Simplify while maintaining accuracy.
- **Fix Group 2 Response (Test 9):** The current response fabricates non-existent options and is not based on the actual ASSIST data.

### 3. Honors Course Representation
- **Standardize Honors Course Notation:** Ensure consistent notation for honors courses across all responses (e.g., "MATH 1AH (Honors)" vs. different variations).
- **Clarify Honors Course Equivalency:** For tests like Test 13 and Test 34, make it clearer that honors and non-honors courses are equivalent but not meant to be taken together.

## Medium Priority Improvements

### 4. Response Structure and Brevity
- **Reduce Response Length:** Many responses like Test 7, Test 9, and Test 22 contain excessive explanation or repeated information. Streamline while maintaining accuracy.
- **Remove <think> Sections in Production:** Ensure thought process sections are removed in the production version.
- **Standardize Counselor Voice:** Ensure all responses maintain a consistent, professional tone without artificial "Counselor Voice Requirements" sections.

### 5. Edge Case Handling
- **Improve Partial Match Explanations:** For tests like Test 15 and Test 25, make the partial match explanations more helpful by providing clearer next steps.
- **Enhance No Articulation Responses:** For Test 14 and Test 16, provide more consistent formatting for courses with no articulation.

### 6. Technical Accuracy
- **Fix CSE 30 Course Description (Test 17):** The current description misidentifies CIS 21JB as "Introduction to Database Systems" when it's actually "Advanced x86 Processor Assembly Programming."
- **Correct Course Names:** Ensure all course titles match the actual ASSIST data (verify with rag_data.json).

## Low Priority Improvements

### 7. UI/UX Enhancements
- **Standardize Progress Indicators:** Make the batch running indicators (e.g., "🧪 Running TransferAI test batch X...") more visually appealing.
- **Improve Error Visualization:** For failure cases, make the visualization of errors (like the progress bar in Test 15) more intuitive.

### 8. Documentation and Metadata
- **Update Version References:** Current test output shows inconsistent references to v1.4 and v1.5. Standardize to v1.5 throughout.
- **Add Test Coverage Information:** Include metadata about which aspects of the articulation logic are tested by each test case.

## Code Changes Required

1. **articulation/validators.py**
   ```python
   # Fix the single course validation logic
   def validate_single_course(uc_course, ccc_course):
       # Current problematic logic:
       # return False, f"No, {ccc_course} alone only satisfies {uc_course}."
       
       # Fixed logic:
       return True, f"Yes, {ccc_course} satisfies {uc_course}."
   ```

2. **articulation/formatters.py**
   ```python
   # Standardize honors course notation
   def format_course_name(course_name):
       if course_name.endswith('H'):
           base_name = course_name[:-1]
           return f"{base_name}H (Honors)"
       return course_name
   
   # Improve partial match template
   partial_match_template = """
   ⚠️ **Partial match ({percentage}%)** [{progress_bar}]
   
   **Best option: {best_option}**
   ✓ Matched: {matched_courses}
   ✗ Missing: **{missing_courses}**
   
   To complete this requirement, you need to take the missing course(s).
   """
   ```

3. **articulation/group_logic_processor.py**
   ```python
   # Ensure we only use data from rag_data.json
   def get_group_options(group_id):
       # Add validation to ensure options exist in the data
       options = fetch_options_from_data(group_id)
       if not options:
           return "No options found for this group."
       return options
   ```

## Implementation Plan

### Phase 1: Critical Fixes (1-2 weeks)
- Address all high-priority items, focusing first on response accuracy issues
- Fix contradictory or confusing responses in Tests 12 and 36
- Correct the Group 2 response fabrication issue

### Phase 2: Refinement (2-3 weeks)
- Implement medium-priority improvements
- Standardize response formats and honors course notation
- Improve edge case handling

### Phase 3: Polish (1-2 weeks)
- Address low-priority UI/UX enhancements
- Update documentation and version references
- Conduct comprehensive regression testing

## Conclusion
By addressing these improvements, TransferAI v1.5 will provide more accurate, consistent, and helpful articulation information to students. The focus should be on ensuring factual correctness first, then improving clarity and user experience.
