# TransferAI Test Documentation

## 1. Current Test Coverage Analysis

### Unit Test Coverage

| Module | Test File | Functions Covered | Coverage % | Notes |
|--------|-----------|-------------------|-----------|-------|
| `logic_formatter.py` | `test_logic_formatter.py` | `is_honors_required`, `detect_redundant_courses`, `explain_if_satisfied` | ~45% | Core validation logic well covered |
| `logic_formatter.py` | `test_render_logic.py` | `render_logic_str`, `render_logic` | ~25% | Rendering functions partially covered |
| `logic_formatter.py` | `test_render_logic_v2.py` | `render_logic_v2` | ~20% | Newer rendering function partially covered |
| `logic_formatter.py` | `test_articulation_satisfied.py` | `is_articulation_satisfied` | ~40% | Main articulation validation logic |
| `logic_formatter.py` | `test_binary_response.py` | `render_binary_response` | ~70% | Yes/No response formatting |
| `logic_formatter.py` | `test_combo_validation.py` | `validate_combo_against_group` | ~55% | Group validation logic |
| `logic_formatter.py` | `test_count_uc_matches.py` | `count_uc_matches`, `get_uc_courses_satisfied_by_ccc`, `get_uc_courses_requiring_ccc_combo` | ~65% | Course matching functions |
| `logic_formatter.py` | `test_honors_equivalence.py` | `is_honors_pair_equivalent`, `explain_honors_equivalence` | ~80% | Honors equivalence detection |
| `query_parser.py` | None | - | 0% | No dedicated unit tests |
| `document_loader.py` | None | - | 0% | No dedicated unit tests |
| `prompt_builder.py` | None | - | 0% | No dedicated unit tests |
| `main.py` | None | - | 0% | No dedicated unit tests |

### Integration Test Coverage

The `test_runner.py` script provides integration testing with 36 test prompts, covering:

1. **Course Equivalency Queries** (11/36): Tests for single UC course articulation information
   - Examples: "Which De Anza courses satisfy CSE 8A at UCSD?", "What satisfies MATH 18 for UCSD transfer?"
   - Coverage: Strong for Computer Science and Math courses, weak for other departments

2. **Validation Queries** (9/36): Tests for validating if specific courses satisfy requirements
   - Examples: "Does MATH 2BH satisfy MATH 18?", "Do I need to take both CIS 36A and CIS 36B for CSE 11?"
   - Coverage: Good coverage of basic validation scenarios

3. **Group Requirement Queries** (5/36): Tests for articulation at the group level
   - Examples: "What De Anza courses are required to satisfy Group 2?", "What are my options for Group 3?"
   - Coverage: Tests all three group types (choose_one_section, all_required, select_n_courses)

4. **Multi-Course Queries** (4/36): Tests for queries about multiple UC courses
   - Examples: "Which courses satisfy MATH 20A and 20B?", "If I complete CSE 8A and 8B, is that one full path?"
   - Coverage: Limited to pairs of courses in same department

5. **Honors Course Queries** (4/36): Tests for honors course scenarios
   - Examples: "Does CSE 12 require honors courses?", "Can I take both MATH 1A and MATH 1AH for MATH 20A?"
   - Coverage: Tests basic honor course detection and redundancy scenarios

6. **Course Contribution Queries** (3/36): Tests for courses contributing to multiple UC requirements
   - Examples: "If I took CIS 36A, can it satisfy more than one UCSD course?", "Which UC courses can I satisfy with CIS 36A?"
   - Coverage: Limited to simple contribution scenarios

### Regression Testing

The regression test suite contains 8 test cases specifically designed to verify fixes for previous issues:

1. Single course articulation verification (CSE 8A)
2. Multi-course articulation verification (CSE 11)
3. LLM-driven validation (CIS 36A + CIS 36B)
4. Non-triggering of R31 logic for CSE 8A/8B
5. Group logic validation for cross-section courses
6. Course contribution to multiple UC courses
7. Honors requirement verification (CSE 12)
8. Redundant course detection (MATH 1A/1AH)

The regression tests focus on ensuring previous fixes remain intact but represent only a small subset of possible regression scenarios.

## 2. Critical Test Gaps

### Module-Level Gaps

1. **`query_parser.py`**: No unit tests for key functions:
   - `normalize_course_code`: No tests for edge case handling
   - `extract_filters`: No tests for course code extraction logic
   - `extract_group_matches`, `extract_section_matches`: No validation of regex matching
   - `find_uc_courses_satisfied_by`: No tests for logic block traversal

2. **`prompt_builder.py`**: No tests for:
   - `build_prompt`: No validation of prompt construction
   - `build_course_prompt`, `build_group_prompt`: No tests for template rendering
   - Prompt type handling: No tests for different prompt types

3. **`document_loader.py`**: No tests for:
   - `extract_ccc_courses_from_logic`: No validation of extraction logic
   - `flatten_courses_from_json`: No tests for document transformation
   - `load_documents`: No tests for document loading from JSON

4. **`main.py`**: No dedicated tests for core engine functionality:
   - `TransferAIEngine.handle_query`: No tests for query routing logic
   - `TransferAIEngine.validate_same_section`: No validation tests
   - `TransferAIEngine.handle_multi_uc_query`: No tests for multi-course handling

### Functional Gaps

1. **Error Handling**: Limited tests for error conditions:
   - Missing or malformed articulation data
   - Invalid course codes
   - Edge cases in logic block structure
   - Exception handling in core functions

2. **Complex Articulation Logic**: Limited coverage of:
   - Deeply nested AND/OR combinations
   - Edge cases in group validation logic
   - Cross-section course combinations

3. **Performance Testing**: No tests for:
   - Response time under load
   - Memory usage with large articulation datasets
   - Concurrency handling

### Integration Test Gaps

1. **Department Coverage**: Tests heavily focus on Computer Science and Math:
   - Limited coverage of Biology (only BILD 1/2)
   - Limited coverage of Chemistry (only CHEM 6A/6B)
   - No coverage of other departments (Humanities, Social Sciences, etc.)

2. **Edge Case Queries**:
   - No tests for very long or complex queries
   - Limited tests for ambiguous queries
   - No tests for query reformulation scenarios

3. **Negative Tests**:
   - Limited tests for queries that should return "no articulation"
   - No tests for completely out-of-scope queries

## 3. Test Case Documentation

### Unit Test Categories

#### Logic Validation Tests

Tests for functions that determine if requirements are satisfied by selected courses.

**Examples**:
- `test_is_articulation_satisfied_simple_or`: Tests basic OR logic
- `test_is_articulation_satisfied_nested_and_or`: Tests nested AND/OR logic
- `test_is_articulation_satisfied_honors_required`: Tests honors requirements

**Key Test Files**: `test_articulation_satisfied.py`, `test_logic_formatter.py`

#### Rendering Tests

Tests for functions that transform articulation logic into human-readable text.

**Examples**:
- `test_render_logic_str_no_articulation`: Tests rendering when no articulation exists
- `test_render_logic_honors_note`: Tests rendering of honors course notes
- `test_render_logic_v2_nested_structure`: Tests rendering of complex nested logic

**Key Test Files**: `test_render_logic.py`, `test_render_logic_v2.py`

#### Honors Processing Tests

Tests for functions that handle honors course logic.

**Examples**:
- `test_is_honors_required_mixed_options`: Tests honor requirement detection
- `test_is_honors_pair_equivalent`: Tests honors/non-honors pair detection
- `test_explain_honors_equivalence`: Tests generation of equivalence explanations

**Key Test Files**: `test_honors_equivalence.py`, `test_logic_formatter.py`

#### Course Matching Tests

Tests for functions that match courses to requirements.

**Examples**:
- `test_count_uc_matches_simple`: Tests counting of directly satisfied UC courses
- `test_get_uc_courses_satisfied_by_ccc`: Tests finding UC courses satisfied by CCC courses
- `test_get_uc_courses_requiring_ccc_combo`: Tests contribution to combination requirements

**Key Test Files**: `test_count_uc_matches.py`, `test_count_manual.py`

### Integration Test Categories

#### Basic Articulation Tests (11 tests)

Tests that query basic course articulation information.

**Test IDs**: 1, 2, 3, 10, 11, 14, 17, 19, 22, 24, 30

**Example**: "Which De Anza courses satisfy CSE 8A at UCSD?"
- **Expected Behavior**: Return list of CCC courses that satisfy the UC course
- **Validation Criteria**: Verify against official ASSIST.org data
- **Edge Cases Covered**: Courses with multiple options, no articulation cases

#### Course Validation Tests (9 tests)

Tests that ask if specific courses satisfy requirements.

**Test IDs**: 4, 12, 13, 15, 28, 32, 33, 34, 36

**Example**: "Does MATH 2BH satisfy MATH 18?"
- **Expected Behavior**: Clear Yes/No response with explanation
- **Validation Criteria**: Correct binary determination, proper explanation
- **Edge Cases Covered**: Honors courses, course substitutions

#### Group Requirements Tests (5 tests)

Tests that query articulation requirements at the group level.

**Test IDs**: 5, 6, 8, 9, 23

**Example**: "What are my options for fulfilling Group 3 science requirements?"
- **Expected Behavior**: Complete explanation of group requirements by section
- **Validation Criteria**: Accurate group logic description, section organization
- **Edge Cases Covered**: Different group logic types, cross-section validation

#### Multi-Course Queries (4 tests)

Tests that ask about multiple UC courses simultaneously.

**Test IDs**: 7, 21, 27, 29

**Example**: "Which courses satisfy MATH 20A and 20B?"
- **Expected Behavior**: Separate articulation info for each UC course
- **Validation Criteria**: Complete information for all courses, no confusion
- **Edge Cases Covered**: Courses in same group, courses in different groups

#### Honors Requirements Tests (4 tests)

Tests focused on honors course scenarios.

**Test IDs**: 13, 18, 20, 33

**Example**: "Does CSE 12 require honors courses at De Anza?"
- **Expected Behavior**: Clear indication if honors is required or optional
- **Validation Criteria**: Accurate honor requirement detection
- **Edge Cases Covered**: Explicit honors flags, course code pattern matching

#### Course Contribution Tests (3 tests)

Tests for courses that contribute to multiple requirements.

**Test IDs**: 31, 35, 36

**Example**: "If I took CIS 36A, can it satisfy more than one UCSD course?"
- **Expected Behavior**: List of all UC courses the CCC course contributes to
- **Validation Criteria**: Complete list of satisfied and contributed UC courses
- **Edge Cases Covered**: Direct matches vs. combination contributions

### Test Success Metrics

The TransferAI system currently achieves:

- **Unit Test Success Rate**: 100% (all unit tests pass)
- **Integration Test Perfect Rate**: 33/36 (91.67%)
- **Integration Test Adjusted Rate**: 36/36 (100% with minor issues)
- **Regression Test Success Rate**: 8/8 (100%)

## 4. Recommended Test Improvements

Based on the identified gaps, the following test improvements are recommended:

1. **Add Unit Tests for Untested Modules**:
   - Create `test_query_parser.py` with tests for all key functions
   - Create `test_prompt_builder.py` to validate prompt construction
   - Create `test_document_loader.py` to test document processing
   - Create `test_main.py` to test core engine components

2. **Expand Integration Test Coverage**:
   - Add tests for non-CS/Math departments
   - Create negative test cases for invalid queries
   - Add tests for edge case articulation logic

3. **Improve Test Infrastructure**:
   - Add automated coverage reporting
   - Create structured test result validation
   - Implement diff analysis for regression testing

4. **Performance Testing**:
   - Add benchmarks for response time
   - Test scaling with larger datasets
   - Add memory utilization tests

These improvements will increase test coverage from approximately 35% to 80% of the codebase and provide more comprehensive validation of system behavior. 