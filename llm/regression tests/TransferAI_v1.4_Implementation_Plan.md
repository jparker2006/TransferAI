# TransferAI v1.4 Implementation Plan

## 1. Logic and Coverage Fixes

### 1.1. Implement `honors_required()` Function

**File**: `logic_formatter.py`

**Description**: Create a function to check if all articulation options for a UC course require honors courses.

**Implementation**:
```python
def is_honors_required(logic_block):
    """
    Returns True if only honors options exist in articulation logic.
    If any non-honors option is available, honors are not required.
    """
    if not logic_block:
        return False
        
    # Convert single block to list if needed
    if isinstance(logic_block, dict):
        logic_block = [logic_block]
        
    all_options_require_honors = True
    has_options = False
    
    # For each OR block
    for block in logic_block:
        if block.get("type") != "OR":
            continue
            
        # Check each option (usually AND blocks)
        for option in block.get("courses", []):
            has_options = True
            if option.get("type") != "AND":
                continue
                
            # Check if this option contains any non-honors courses
            option_courses = option.get("courses", [])
            if any(not course.get("honors", False) for course in option_courses):
                all_options_require_honors = False
                break
                
        if not all_options_require_honors:
            break
            
    # Only return True if there are options and all require honors
    return has_options and all_options_require_honors
```

**Integration**:
1. Add to the `render_logic_str` function in `logic_formatter.py` to include honors requirement info:
```python
if is_honors_required(block):
    honors_note += "\n\n⚠️ Important: Only honors courses will satisfy this requirement."
```

### 1.2. Add Redundant CCC Course Detection

**File**: `logic_formatter.py`

**Description**: Create a function to detect when multiple CCC courses are mentioned that satisfy the same requirement redundantly.

**Implementation**:
```python
def detect_redundant_courses(selected_courses, logic_block):
    """
    Detects redundant courses (courses that satisfy the same requirement).
    Returns a list of groups of redundant courses.
    """
    if not logic_block or not isinstance(logic_block, dict) or not selected_courses:
        return []
        
    redundant_groups = []
    selected_set = {c.upper().strip() for c in selected_courses}
    
    # Process OR options
    if logic_block.get("type") == "OR":
        # Map courses to the options they satisfy
        course_to_options = {}
        
        for i, option in enumerate(logic_block.get("courses", [])):
            # Only process AND blocks with a single course (direct equivalents)
            if isinstance(option, dict) and option.get("type") == "AND" and len(option.get("courses", [])) == 1:
                course = option["courses"][0].get("course_letters", "").upper().strip()
                if course and course in selected_set:
                    course_to_options.setdefault(course, []).append(i)
        
        # Find sets of courses that satisfy the same options
        option_to_courses = {}
        for course, options in course_to_options.items():
            option_key = tuple(sorted(options))
            option_to_courses.setdefault(option_key, []).append(course)
            
        # Return groups of redundant courses
        for courses in option_to_courses.values():
            if len(courses) > 1:
                redundant_groups.append(courses)
                
    return redundant_groups
```

**Integration**:
1. Add to `explain_if_satisfied` function in `logic_formatter.py`:
```python
redundant_groups = detect_redundant_courses(selected_courses, logic_block)
if redundant_groups:
    redundant_note = "\n\n⚠️ Redundant courses detected:\n"
    for group in redundant_groups:
        redundant_note += f"- Courses {', '.join(group)} are equivalent. Only one is needed.\n"
    feedback += redundant_note
```

### 1.3. Standardize Honors Equivalence Phrasing

**File**: `logic_formatter.py`

**Description**: Create a helper function to standardize phrasing for honors/non-honors equivalence.

**Implementation**:
```python
def explain_honors_equivalence(honors_course, non_honors_course):
    """
    Returns standardized phrasing for honors/non-honors equivalence.
    """
    return f"{honors_course} and {non_honors_course} are equivalent for UC transfer credit. You may choose either."
```

**Integration**:
1. Modify the `is_honors_pair_equivalent` function case in `main.py`:
```python
if len(selected) == 2 and is_honors_pair_equivalent(logic_block, selected[0], selected[1]):
    print("✅ [Honors Shortcut] Detected honors/non-honors pair for same UC course.")
    return f"✅ Yes, {explain_honors_equivalence(selected[0], selected[1])}"
```

### 1.4. Add `count_uc_matches()`

**File**: `logic_formatter.py`

**Description**: Create a function to explain when a CCC course satisfies multiple UC requirements.

**Implementation**:
```python
def count_uc_matches(ccc_course, docs):
    """
    Counts and lists all UC courses satisfied by this CCC course.
    Returns a tuple: (count, list of courses, contribution list)
    Where contribution list shows courses where this CCC is part of a combination.
    """
    ccc_normalized = ccc_course.strip().upper()
    
    # Find UC courses where this CCC course is a direct match
    direct_matches = get_uc_courses_satisfied_by_ccc(ccc_course, docs)
    
    # Find UC courses where this CCC course is part of a combination
    contributing_matches = get_uc_courses_requiring_ccc_combo(ccc_course, docs)
    
    # Remove any overlap
    contributing_only = [uc for uc in contributing_matches if uc not in direct_matches]
    
    return (len(direct_matches), direct_matches, contributing_only)
```

**Integration**:
1. Enhance the R31 logic in `main.py` to include the contribution information:
```python
if filters.get("ccc_courses") and len(filters["ccc_courses"]) == 1:
    ccc = filters["ccc_courses"][0]
    match_count, uc_matches, contribution_matches = count_uc_matches(ccc, self.docs)
    
    if match_count == 1:
        message = f"❌ No, {ccc} alone only satisfies {uc_matches[0]}."
        if contribution_matches:
            message += f"\n\nHowever, {ccc} can contribute to satisfying {', '.join(contribution_matches)} when combined with additional courses."
        return message
```

## 2. Prompt & Tone Enhancements

### 2.1. Add `render_binary_response()`

**File**: `logic_formatter.py`

**Description**: Standardize the format of yes/no responses.

**Implementation**:
```python
def render_binary_response(is_satisfied, explanation, course=None):
    """
    Renders a standardized binary (yes/no) response.
    """
    if is_satisfied:
        header = "✅ Yes, based on official articulation."
    else:
        header = "❌ No, based on verified articulation logic."
        
    if course:
        header += f" {course}"
        
    return f"{header}\n\n{explanation}"
```

**Integration**:
1. Replace all binary responses in `main.py` with calls to this function:
```python
# Before:
return f"✅ Yes! Your courses ({', '.join(filters['ccc_courses'])}) fully satisfy Group {group_id}.\n\nMatched UC courses: {', '.join(validation['satisfied_uc_courses'])}."

# After:
explanation = f"Your courses ({', '.join(filters['ccc_courses'])}) fully satisfy Group {group_id}.\n\nMatched UC courses: {', '.join(validation['satisfied_uc_courses'])}."
return render_binary_response(True, explanation)
```

### 2.2. Improve UC → CCC Course Maps

**File**: `logic_formatter.py`

**Description**: Make UC to CCC mappings more concise with clearer grouping.

**Implementation**:
```python
def render_logic_v2(metadata):
    """
    Enhanced version of render_logic_str with more concise formatting.
    Groups options better and makes the UC course more prominent.
    """
    if metadata.get("no_articulation", False) or metadata.get("logic_block", {}).get("no_articulation", False):
        return "❌ This course must be completed at UCSD."
        
    block = metadata.get("logic_block", {})
    options = []
    
    if block.get("type") == "OR":
        for i, option in enumerate(block.get("courses", [])):
            label = f"Option {chr(65 + i)}"
            
            if isinstance(option, dict) and option.get("type") == "AND":
                courses = option.get("courses", [])
                if len(courses) > 1:
                    course_codes = [c.get("course_letters", "UNKNOWN") for c in courses]
                    options.append(f"**{label}**: {', '.join(course_codes)} (complete all)")
                elif courses:
                    course = courses[0]
                    is_honors = course.get("honors", False)
                    code = course.get("course_letters", "UNKNOWN")
                    options.append(f"**{label}**: {code}{' (honors)' if is_honors else ''}")
            
    # Add honors information
    honors_info = extract_honors_info_from_logic(block)
    
    # Format the result
    result = "\n".join(options)
    
    # Add honors notes if applicable
    if honors_info["honors_courses"]:
        result += f"\n\n🔹 Honors courses accepted: {', '.join(honors_info['honors_courses'])}."
    if honors_info["non_honors_courses"]:
        result += f"\n🔹 Non-honors courses also accepted: {', '.join(honors_info['non_honors_courses'])}."
        
    # Add honors requirement warning if needed
    if is_honors_required(block):
        result += "\n\n⚠️ Important: Only honors courses will satisfy this requirement."
        
    return result
```

**Integration**:
1. Gradually replace `render_logic_str` with `render_logic_v2` in key parts of the code:
```python
# Modify build_prompt in prompt_builder.py to use the new rendering
rendered_logic = render_logic_v2(metadata) if use_v2_formatting else render_logic_str(metadata)
```

### 2.3. Add Clear Complete/Partial Option Labels

**File**: `logic_formatter.py`

**Description**: Clearly label complete and partial articulation options.

**Implementation**:
Enhance the `render_logic_v2` function to include completion labels:

```python
def render_logic_v2(metadata):
    # ... existing implementation ...
    
    for i, option in enumerate(block.get("courses", [])):
        label = f"Option {chr(65 + i)}"
        
        if isinstance(option, dict) and option.get("type") == "AND":
            courses = option.get("courses", [])
            if len(courses) > 1:
                course_codes = [c.get("course_letters", "UNKNOWN") for c in courses]
                options.append(f"**{label} (✅ Complete option)**: {', '.join(course_codes)} (complete all)")
            elif courses:
                course = courses[0]
                is_honors = course.get("honors", False)
                code = course.get("course_letters", "UNKNOWN")
                options.append(f"**{label} (✅ Complete option)**: {code}{' (honors)' if is_honors else ''}")
        
        # Add partial match labels to explain_if_satisfied
        if missing:
            feedback_lines.append(f"{label}: ⚠️ **Partial match** — missing: {', '.join(sorted(missing))}")
```

### 2.4. Improve Group-Level Prompts

**File**: `prompt_builder.py`

**Description**: Make group-level prompts more direct and structured.

**Implementation**:
Update the `build_group_prompt` function to use clearer language:

```python
def build_group_prompt(
    rendered_logic: str,
    user_question: str,
    group_id: str = "Unknown",
    group_title: str = "",
    group_logic_type: str = "",
    n_courses: int = None,
) -> str:
    group_label = f"Group {group_id}" if group_id else "this group"
    
    # Enhanced logic explanations
    if group_logic_type == "choose_one_section":
        group_logic_explanation = (
            f"To satisfy {group_label}, you must complete **all UC courses from exactly ONE section** (such as Section A or B).\n"
            "Do not mix courses from different sections."
        )
    elif group_logic_type == "all_required":
        group_logic_explanation = (
            f"To satisfy {group_label}, you must complete **every UC course listed below**.\n"
            "Each UC course may have multiple articulation options."
        )
    elif group_logic_type == "select_n_courses" and n_courses:
        group_logic_explanation = (
            f"To satisfy {group_label}, you must complete **any {n_courses} UC courses** from the list below."
        )
    else:
        group_logic_explanation = f"Refer to the articulation requirements for {group_label}."
        
    # Rest of the function remains similar but with the improved explanations
```

## 3. Validation & Structure Upgrades

### 3.1. Implement `is_articulation_satisfied()`

**File**: `logic_formatter.py`

**Description**: Create a structured validation function that returns standardized output.

**Implementation**:
```python
def is_articulation_satisfied(ccc_courses, uc_course, logic_block):
    """
    Validates if CCC courses satisfy a UC course articulation.
    
    Returns a structured dict:
    {
        "is_satisfied": bool,
        "missing_courses": list,
        "satisfied_paths": list,
        "redundant_courses": list,
        "requires_honors": bool
    }
    """
    if not logic_block or not isinstance(logic_block, dict):
        return {
            "is_satisfied": False,
            "missing_courses": [],
            "satisfied_paths": [],
            "redundant_courses": [],
            "requires_honors": False
        }
        
    selected_set = {c.upper().strip() for c in ccc_courses}
    satisfied_paths = []
    all_missing_courses = set()
    redundant_groups = detect_redundant_courses(ccc_courses, logic_block)
    requires_honors = is_honors_required(logic_block)
    
    for i, option in enumerate(logic_block.get("courses", [])):
        label = f"Option {chr(65 + i)}"
        
        # Process AND blocks
        if isinstance(option, dict) and option.get("type") == "AND":
            required = {c.get("course_letters", "").upper() for c in option.get("courses", []) if "course_letters" in c}
            missing = required - selected_set
            
            if not missing:  # All required courses are present
                satisfied_paths.append(label)
            else:
                all_missing_courses.update(missing)
                
    return {
        "is_satisfied": len(satisfied_paths) > 0,
        "missing_courses": sorted(all_missing_courses),
        "satisfied_paths": satisfied_paths,
        "redundant_courses": redundant_groups,
        "requires_honors": requires_honors
    }
```

**Integration**:
1. Update relevant parts of `main.py` to use this function:
```python
validation = is_articulation_satisfied(
    filters["ccc_courses"], 
    doc.metadata.get("uc_course", ""),
    doc.metadata.get("logic_block", {})
)

if validation["is_satisfied"]:
    explanation = f"Your courses satisfy {doc.metadata.get('uc_course')} via {', '.join(validation['satisfied_paths'])}."
    return render_binary_response(True, explanation)
else:
    explanation = f"Your courses do not satisfy {doc.metadata.get('uc_course')}."
    if validation["missing_courses"]:
        explanation += f"\nMissing courses: {', '.join(validation['missing_courses'])}"
    return render_binary_response(False, explanation)
```

### 3.2. Implement `render_combo_validation()`

**File**: `logic_formatter.py`

**Description**: Create a function to visualize validation results for multi-course combinations.

**Implementation**:
```python
def render_combo_validation(validations, uc_to_ccc_map=None):
    """
    Renders a validation summary for multiple UC courses.
    
    Args:
        validations: Dict mapping UC course to validation result
        uc_to_ccc_map: Optional dict mapping UC course to CCC courses that satisfy it
        
    Returns:
        Formatted validation summary as a string
    """
    lines = ["## Course Validation Summary\n"]
    lines.append("| UC Course | Status | Missing Courses | Satisfied By |")
    lines.append("|-----------|--------|----------------|-------------|")
    
    for uc_course, validation in validations.items():
        status = "✅ Satisfied" if validation["is_satisfied"] else "❌ Not Satisfied"
        missing = ", ".join(validation["missing_courses"]) or "None"
        satisfied_by = ""
        
        if uc_to_ccc_map and uc_course in uc_to_ccc_map:
            satisfied_by = ", ".join(uc_to_ccc_map[uc_course])
        
        lines.append(f"| {uc_course} | {status} | {missing} | {satisfied_by} |")
    
    return "\n".join(lines)
```

**Integration**:
1. Use in multi-course validation scenarios:
```python
validations = {}
uc_to_ccc_map = {}

for uc_course in filters["uc_course"]:
    doc = next((d for d in self.docs if d.metadata.get("uc_course") == uc_course), None)
    if doc:
        validations[uc_course] = is_articulation_satisfied(
            filters["ccc_courses"], 
            uc_course,
            doc.metadata.get("logic_block", {})
        )
        uc_to_ccc_map[uc_course] = [ccc for ccc in filters["ccc_courses"]]

return render_combo_validation(validations, uc_to_ccc_map)
```

### 3.3. Add `summarize_logic_blocks()`

**File**: `logic_formatter.py`

**Description**: Create a function to generate quick metadata summaries for articulation.

**Implementation**:
```python
def summarize_logic_blocks(logic_block):
    """
    Creates a flattened metadata summary of articulation logic.
    
    Returns:
        Dict with key metrics about the articulation logic
    """
    if not logic_block or not isinstance(logic_block, dict):
        return {
            "options_count": 0,
            "max_courses_required": 0,
            "has_honors_options": False,
            "requires_honors": False,
            "no_articulation": True
        }
        
    options_count = 0
    max_courses = 0
    has_honors = False
    
    if logic_block.get("type") == "OR":
        options = logic_block.get("courses", [])
        options_count = len(options)
        
        for option in options:
            if isinstance(option, dict) and option.get("type") == "AND":
                courses = option.get("courses", [])
                max_courses = max(max_courses, len(courses))
                
                for course in courses:
                    if course.get("honors", False):
                        has_honors = True
    
    return {
        "options_count": options_count,
        "max_courses_required": max_courses,
        "has_honors_options": has_honors,
        "requires_honors": is_honors_required(logic_block),
        "no_articulation": logic_block.get("no_articulation", False)
    }
```

**Integration**:
1. Use for API endpoints or summary displays:
```python
metadata = summarize_logic_blocks(doc.metadata.get("logic_block", {}))
print(f"Course has {metadata['options_count']} articulation options, " +
      f"with up to {metadata['max_courses_required']} courses required per option.")
```

### 3.4. Improve No Articulation Cases

**File**: `logic_formatter.py`

**Description**: Enhance the handling of courses with no articulation.

**Implementation**:
Update the handling of no_articulation flags:

```python
def render_logic_v2(metadata):
    if metadata.get("no_articulation", False) or metadata.get("logic_block", {}).get("no_articulation", False):
        reason = metadata.get("no_articulation_reason", "No articulation available")
        return f"❌ This course must be completed at UCSD.\n\nReason: {reason}"
```

## Testing Strategy

### Unit Tests

1. **Create test_logic_formatter.py**:
   - Test each new function with representative logic blocks
   - Ensure honors detection works correctly
   - Verify redundant course detection
   - Test binary response formatting

2. **Create test_prompt_builder.py**:
   - Ensure improved group-level prompts are generated correctly
   - Verify binary response integration

3. **Test articulation validation**:
   - Create test cases for basic articulation
   - Test complex logic with multiple paths
   - Test honors course requirements
   - Verify redundant course detection

### Integration Tests

1. **Update `test_runner.py`**:
   - Add specific test cases for honors requirements
   - Add test cases for redundant course detection
   - Test binary response formatting
   - Verify validation output structure

2. **Example Test Cases**:
   ```python
   # Test 32: Honors requirement detection
   "Does CSE 12 require honors courses at De Anza?",
   
   # Test 33: Redundant course detection
   "Can I take both MATH 1A and MATH 1AH for MATH 20A?",
   
   # Test 34: Multiple UC mapping
   "Which UC courses can I satisfy with CIS 36A?",
   
   # Test 35: Binary response clarity
   "Does CIS 22C satisfy CSE 12?"
   ```

### Validation Strategy

1. **Automated Testing**:
   - Run all unit tests and integration tests
   - Verify expected output for each function
   - Compare output to known correct answers

2. **Manual Verification**:
   - Run through key test cases manually
   - Verify improved formatting and clarity
   - Check for edge cases

## Implementation Rollout Plan

### Phase 1: Logic Fixes (High Priority)

1. Implement `is_honors_required()` in `logic_formatter.py`
2. Add unit tests for honors detection
3. Enhance `render_logic_str` with honors requirement info
4. Implement `detect_redundant_courses()` function
5. Add redundant course detection to `explain_if_satisfied`
6. Test with representative examples

### Phase 2: Validation Structure (Medium Priority)

1. Implement `is_articulation_satisfied()` with full structure
2. Integrate with existing code in main.py
3. Add structured validation unit tests
4. Implement `count_uc_matches()` function
5. Update R31 logic to use the new function
6. Test multi-course validation scenarios

### Phase 3: Output Formatting (Lower Priority)

1. Implement `render_binary_response()`
2. Update all binary responses in the codebase
3. Create `render_logic_v2()` with improved formatting
4. Gradually replace render_logic_str with render_logic_v2
5. Implement `render_combo_validation()` for multi-course validation
6. Update group-level prompts in prompt_builder.py
7. Run full integration tests on all components

### Phase 4: Advanced Features (Final Priority)

1. Implement `summarize_logic_blocks()` for metadata summaries
2. Update handling of no_articulation cases
3. Standardize honors equivalence phrasing
4. Final comprehensive testing
5. Documentation updates

### Completion Criteria
For each feature:
1. Code implementation completed and reviewed
2. Unit tests passing
3. Integration tests passing
4. Manual verification of key test cases
5. Documentation updated

## Final Recommendations

1. **Prioritize Accuracy**: Ensure logic functions are accurate before updating formatting
2. **Maintain Backward Compatibility**: Use flags to gradually transition to new formats
3. **Track Test Results**: Keep detailed records of test improvements
4. **Document API Changes**: Update documentation to reflect new function signatures
5. **Consider Adding Type Hints**: For better code maintainability and error detection 