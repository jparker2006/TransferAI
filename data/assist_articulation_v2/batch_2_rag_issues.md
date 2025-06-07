# Batch 2 RAG Issues Log

## File: `rag_output/santa_monica_college/university_of_california_san_diego/art_studio_ba_visual_arts.json`

### ~~Issue 1: Redundant and Misplaced Section-Level Rules~~
**Resolution:** Fixed by restructuring the RAG JSON to have a `requirement_groups` hierarchy. Section-level rules are now stored once per section object, eliminating redundancy in the final course requirement text.

*   **Observation:** In the RAG file, instructions that apply to a whole group of courses, such as "Select 2 courses from the following," are repeated for every single course within that group. This makes the output verbose and the sentence structure awkward.
*   **Example from RAG file (`ART MAKING` section):**
    ```json
    {
      "type": "Course Requirement",
      "requirement_area": "ART MAKING",
      "group_id": 2,
      "section_label": "A",
      "text": "Requirement Area: ART MAKING. Section Rule: Select 2 courses from the following. To satisfy the 'VIS 1: Introduction to Art-Making: Two-Dimensional Practices (4.00 units)' requirement at University of California, San Diego, a student from Santa Monica College must complete: No Course Articulated"
    }
    ```
    The `Section Rule: Select 2 courses from the following.` part is repeated for VIS 1, VIS 2, VIS 3, etc.

*   **Expected Behavior:** The instruction "Select N courses from the following" is a rule for the entire section. It should be represented as a single, group-level piece of information rather than being prepended to each individual course requirement's text.

*   **Root Cause Analysis:** In `assist_to_rag.py`, the `section_advisement_text` (which contains the rule) is calculated once per section but is then appended to the `text_parts` list inside the inner loop that iterates over each course (`cell`). This results in the rule being duplicated for every course document generated within that section.

## File: `rag_output/santa_monica_college/university_of_california_san_diego/chemistry_and_biochemistry_chemistry_bs.json`

### ~~Issue 1: Missing Group-Level Instruction~~
**Resolution:** Fixed by the new JSON structure, which includes a `group_instruction` field at the group level.

*   **Observation:** The instruction "Complete the following," which applies to the first requirement group (containing sections A, B, C, and D), is completely missing from the RAG output.
*   **Example from Screenshot:** The heading for the first group of requirements is "1 Complete the following".
*   **RAG File State:** There is no text in any of the documents for `group_id: 1` that reflects this instruction.
*   **Root Cause Analysis:** The logic in `assist_to_rag.py` for handling group-level instructions (`group_instruction_text`) is too specific. It currently only processes instructions that involve an "Or" conjunction between sections (e.g., "Complete A or B"). It ignores general instructions like "Complete the following" because it doesn't fit that narrow pattern.

### ~~Issue 2: Awkward Formatting for "OR" Conditions with Single Courses~~
**Resolution:** Fixed by modifying `_generate_text_for_sending_articulation` to only add parentheses around course groups that contain more than one course.

*   **Observation:** For requirements that can be satisfied by one of several single courses, the generated text wraps each individual course in parentheses, leading to an awkward structure.
*   **Example from RAG file (`PHYS 2DL` requirement):**
    ```json
    "text": "... must complete: (PHYSCS 23: Fluids, Waves, Thermodynamics, Optics with Lab (5.00 units)) OR (PHYSCS 24: Modern Physics with Lab (3.00 units))"
    ```
*   **Root Cause Analysis:** In `_generate_text_for_sending_articulation`, the code wraps every course group in parentheses (`f"({conjunction.join(course_texts)})"`) before joining them. This happens even when the group contains only one course, leading to the redundant parentheses in the final output.

## File: `rag_output/santa_monica_college/university_of_california_san_diego/economics_bs.json`

### ~~Issue 1: Missing Requirement Area Title~~
**Resolution:** Fixed by the new JSON structure, which includes a `requirement_area` field at the group level. This provides a natural place for this context.

*   **Observation:** The `requirement_area` field is empty for all `Course Requirement` documents in the file.
*   **Example from RAG file:**
    ```json
    {
      "type": "Course Requirement",
      "requirement_area": "",
      "group_id": 1,
      ...
    }
    ```
*   **Expected Behavior:** While this specific agreement on ASSIST lacks an explicit, bolded title for the requirement sections (like "LOWER DIVISION MAJOR REQUIREMENTS"), the system should ideally assign a sensible default or find a way to represent the context instead of leaving it blank. The content is clearly part of the major requirements.
*   **Root Cause Analysis:** The script continues to rely on a `REQUIREMENT_TITLE` asset that doesn't exist in this data, causing the `current_requirement_area` variable to remain blank.

### ~~Issue 2: Redundant Group-Level Instruction (Recurring)~~
**Resolution:** Fixed by the new hierarchical JSON structure. Group-level instructions are stored once in the `group_instruction` field of the parent group.

*   **Observation:** The group-level instruction, "Complete A or B," is repeated in the `text` field for every single course within that group (group_id: 1).
*   **Example from RAG file:** The text `"Instruction: Complete A or B."` is prepended to the requirement text for MATH 20A, 20B, 20C, 10A, 10B, and 10C.
*   **Expected Behavior:** This instruction should be represented as a single, group-level piece of information, not repeated for each course.
*   **Root Cause Analysis:** Similar to the issue in the Art Studio file, the `group_instruction_text` is calculated once per group but then appended to the `text_parts` list inside the inner loop that iterates over each course, causing the duplication.

### ~~Issue 3: Awkward Parentheses for Complex Logic (Recurring)~~
**Resolution:** Fixed by modifying `_generate_text_for_sending_articulation` to only add parentheses around course groups that contain more than one course.

*   **Observation:** The logic for nested requirements is technically correct but formatted awkwardly with redundant parentheses around single courses.
*   **Example from RAG file (`MATH 10B` requirement):**
    ```json
    "text": "... must complete: (MATH 8: Calculus 2 (5.00 units)) OR (MATH 28: Calculus 1 for Business and Social Science (5.00 units) AND MATH 29: Calculus 2 for Business and Social Science (3.00 units))"
    ```
*   **Root Cause Analysis:** This is the same issue as reported for the Chemistry file. The `_generate_text_for_sending_articulation` function wraps every `COURSE_GROUP` item in parentheses, regardless of whether it contains one course or multiple.

## File: `rag_output/santa_monica_college/university_of_california_san_diego/history_ba.json`

### Issue 1: Critical Failure to Parse Many-to-Many Articulation

*   **Observation:** The RAG file completely omits the first, most complex requirement shown in Section A of the ASSIST screenshot. The screenshot shows that completing the series `HILD 2A` AND `HILD 2B` AND `HILD 2C` at UCSD can be satisfied by completing the series `HIST 11` AND `HIST 12` at Santa Monica College. The generated RAG file has no record of this rule. It also completely omits any mention of `HILD 2B`.
*   **RAG File State:** The file only contains individual requirements for `HILD 2A` and `HILD 2C`, which seem to correspond to the simpler, single-course articulation options listed *below* the main series requirement in the screenshot.
*   **Expected Behavior:** The RAG output should contain a document or structure that accurately represents the `(HILD 2A + 2B + 2C) -> (HIST 11 + HIST 12)` relationship.
*   **Root Cause Analysis:** This points to a fundamental flaw in how `assist_to_rag.py` processes the `rows` and `cells` in a `Section`. The logic appears to only handle one-to-one or one-to-many course relationships within a single row. It does not seem capable of understanding multi-row requirements where several courses are grouped on the left-hand side to satisfy a requirement on the right.

### ~~Issue 2: Missing Requirement Area Title (Recurring)~~
**Resolution:** Fixed by the new JSON structure, which includes a `requirement_area` field at the group level.

*   **Observation:** The `requirement_area` field is empty for all `Course Requirement` documents.
*   **Root Cause Analysis:** Same as the Economics file. The script expects a `REQUIREMENT_TITLE` asset, which is not present in this agreement's data.

### ~~Issue 3: Redundant Group-Level Instruction (Recurring)~~
**Resolution:** Fixed by the new hierarchical JSON structure. Group-level instructions are stored once in the `group_instruction` field of the parent group.

*   **Observation:** The instruction "Select A, B, or C" is repeated for every course requirement in the group.
*   **Root Cause Analysis:** Same as the Art Studio and Economics files. The `group_instruction_text` is being misapplied inside a loop.

### ~~Issue 4: Awkward Parentheses for "OR" Conditions (Recurring)~~
**Resolution:** Fixed by modifying `_generate_text_for_sending_articulation` to only add parentheses around course groups that contain more than one course.

*   **Observation:** The requirement for `HILD 2C` is formatted with unnecessary parentheses: `... complete: (HIST 12: ...) OR (HIST 13: ...)`
*   **Root Cause Analysis:** Same as the Chemistry and Economics files. The `_generate_text_for_sending_articulation` function incorrectly wraps single-course groups in parentheses.

## File: `rag_output/santa_monica_college/university_of_california_san_diego/structural_engineering_bs.json`

### ~~Issue 1: Missing Requirement Area Title (Recurring)~~
**Resolution:** Fixed by the new JSON structure, which includes a `requirement_area` field at the group level.

*   **Observation:** The `requirement_area` field is empty for all `Course Requirement` documents in the file. As with the other agreements lacking a formal title, the context is lost.
*   **Root Cause Analysis:** The script continues to rely on a `REQUIREMENT_TITLE` asset that doesn't exist in this data, causing the `current_requirement_area` variable to remain blank.

### ~~Issue 2: Awkward Parentheses for Single Courses (Recurring)~~
**Resolution:** Fixed by modifying `_generate_text_for_sending_articulation` to only add parentheses around course groups that contain more than one course.

*   **Observation:** Every articulated course or course group, even single courses, is wrapped in parentheses.
*   **Example from RAG file (`MATH 18` requirement):**
    ```json
    "text": "... must complete: (MATH 13: Linear Algebra (3.00 units))"
    ```
*   **Root Cause Analysis:** This is the same root cause seen in all previous files. The `_generate_text_for_sending_articulation` function wraps all course groups in parentheses, regardless of their complexity.