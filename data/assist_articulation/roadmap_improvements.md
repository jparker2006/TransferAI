# Comprehensive RAG Generation Roadmap (ASSIST Alignment - V2: All SMC to UCSD Majors)

This roadmap outlines improvements for `assist_to_rag.py` to create RAG JSON that accurately reflects ASSIST articulation agreements for **all University of California, San Diego (UCSD) agreements from Santa Monica College (SMC)**. The focus is on achieving structural accuracy and capturing essential contextual information before optimizing for LLM interpretation.

---

## Phase 1: Scaling Core Logic & Capturing Specific Notes

*Goal: Ensure the fundamental RAG structure is accurate across all SMC-UCSD majors and capture critical, localized contextual notes.*

1.  **Task:** Scalability and Generalization Testing (Formerly Phase 2, Item 5)
    *   **Description:** Ensure improvements made and core logic generalize well to all other SMC to UCSD institutions and majors.
    *   **Suggestion:** Implement an iterative scaling approach:
        *   **Initial Set (Completed):** Started with Physics, Biology, Math, Computer Science.
        *   **Batch 1 Processing:** Add a diverse set of ~5 new majors to the processing configuration (e.g., Structural Engineering, Economics, History, Art Studio, Chemistry). Always retain previously processed majors to check for regressions.
        *   **Analyze & Fix:** Run `assist_to_rag.py` on the expanded set. Analyze the RAG output for these new majors, specifically looking for:
            *   Incorrect `group_logic_type` or `section_logic_type`.
            *   Mismatched or missing overarching/group titles.
            *   Errors in parsing `logic_block` structures (AND/OR logic, course representation).
            *   New patterns or edge cases in requirement structures.
            *   Identify specific notes/advisements needing capture (feeds into Task 2).
        *   **Batch 1 Processing (Completed):** All identified major-specific and general structural issues from Batch 1 (Physics, Biology, Math, Computer Science, Structural Engineering, Economics, History, Art Studio, Chemistry) are now addressed.
        *   **Next Steps for Task 1 (Scalability and Generalization Testing):**
            *   **Define and Process Batch 2:** Select a new diverse set of ~5-10 majors for the next processing batch.
            *   **Concurrent Focus for Batch 2:** While processing Batch 2, actively begin implementation for **Issue 2: Handling `AdvisementText` and Embedded Notes**.
            *   Analyze Batch 2 RAG outputs for new structural patterns, edge cases, and further `AdvisementText` capture needs.
        *   **Repeat:** Define subsequent batches (Batch 3, etc.) and repeat the processing, analysis, and fixing steps until all SMC-UCSD majors are successfully processed.
    *   **Status:** Open (Ongoing - Batch 2 Definition & Processing Next)

2.  **Issue:** Handling `AdvisementText` and Embedded Notes (Formerly Phase 1, Item 1 - Addressed *during* Scaling)
    *   **Majors Affected:** All (extent varies)
    *   **Description:** Small text snippets (footnotes, advisements) associated with courses/sections/groups provide crucial context. This task runs concurrently with Task 1.
    *   **Suggestion:**
        *   As new agreements are processed (Task 1), identify `AdvisementText` and similar embedded notes.
        *   Analyze their content (informational, logic-altering, conditional). For notes that provide critical context to specific courses or requirement groups (e.g., the BILD 1-4 sequence completion rule for Biology, or advice to complete a full sequence at one institution), prioritize associating these notes directly with the relevant RAG objects (group or course level `notes: []` array).
        *   When specific text explains *why* a course doesn't articulate (e.g., Physics ECE 15: "This course must be taken at the university after transfer"), capture this in a `no_articulation_reason` field within the logic block, rather than just using a generic `no_articulation: true` flag.
        *   Develop robust methods to place these notes correctly during RAG generation.
        *   Consider adding specific flags for common conditions (e.g., `minimum_grade: "C"`).
    *   **Status:** Open

---

## Post-Phase 1 Considerations (After Batch 2 and initial `AdvisementText` implementation)

*   **Refactor `assist_to_rag.py`:** Evaluate and implement refactoring of `assist_to_rag.py` to improve modularity, maintainability, and testability. This becomes more critical as new features (like detailed note handling) are added.

## Phase 2: Refining Global Context & Advice

*Goal: Process and structure the global advisory text after the core structure is stabilized across all majors.*

3.  **Issue:** Granularity and Duplication of `general_advice` (Formerly Phase 1, Item 2)
    *   **Majors Affected:** All
    *   **Description:** The `general_advice` field is currently a single large text block, sometimes with duplicated information (observed in Biology, Physics, Structural Engineering, Economics, History, Art Studio, and Chemistry RAGs), making it hard for the LLM to use effectively.
    *   **Suggestion:**
        *   *After Phase 1 is largely complete*, analyze the full collection of `general_advice` fields gathered from all SMC-UCSD RAGs.
        *   Implement robust deduplication logic.
        *   Analyze source `ReportNote` assets and identify patterns for structuring the advice (e.g., break down into specific fields or a structured list of advice objects like `grading_policy_note`, `ap_ib_note`, `transfer_sequence_advice`, etc.).
        *   Refine the `general_advice` field in all generated RAGs based on this analysis.
    *   **Status:** Open (Dependent on Phase 1)

---

## Phase 3: LLM Integration & Iterative Refinement (Formerly Phase 2)

*Goal: Optimize the RAG based on downstream LLM performance.*

4.  **Task:** Prompt Engineering for RAG Synthesis (Formerly Phase 2, Item 3)
    *   **Description:** Develop and refine LLM prompts that instruct the model to effectively use the multi-faceted RAG (structure, specific notes, general advice).
    *   **Suggestion:** Create prompts that prioritize structure, then incorporate notes, then consider general advice. Test different prompting strategies.
    *   **Status:** Open (Dependent on Phase 1 & 2)

5.  **Task:** Establish Feedback Loop (Formerly Phase 2, Item 4)
    *   **Description:** Implement a process for evaluating LLM responses based on the RAG, identifying errors, and tracing them back to potential RAG deficiencies.
    *   **Suggestion:** Use test cases (student queries, known edge cases) across a diverse set of SMC to UCSD majors. If LLM fails, determine if RAG needs more clarity, missing info, or structural changes. Feed findings back into `assist_to_rag.py` improvements.
    *   **Status:** Open (Ongoing, after Phase 1 & 2)

---
