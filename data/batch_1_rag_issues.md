# Outstanding Issues from Batch 1 RAG Review (SMC-UCSD)

This document summarizes the open issues identified during the quality assurance review of the Batch 1 RAG JSON files (Chemistry, Art Studio, Economics, History, Physics, Structural Engineering) against their corresponding ASSIST screenshots. Addressing these items is necessary to perfect this batch.

## Specific Bugs (from Individual RAG Reviews)

1.  **Art Studio B.A. - Visual Arts (`art_studio_ba_visual_arts.json`):**
    *   **Incorrect Group Title:** `groups[0].group_title` is currently "All of the following UC courses are required" but should be "FOUNDATION LEVEL - REQUIRED COURSEWORK" to match the screenshot. *(Status: FIXED)*
    *   **Missing Overarching Title:** `groups[1]` lacks the required `overarching_title: "ART MAKING"`. *(Status: FIXED)*
    *   **Missing Overarching Title:** `groups[2]` lacks the required `overarching_title: "ART HISTORY"`. *(Status: FIXED)*

2.  **Economics B.S. (`economics_bs.json`):**
    *   **Leading Space in Course Title:** The UC course `ECON 5` title (`groups[1].sections[0].uc_courses[2].uc_course_title`) contains an extraneous leading space (" Data Analytics..."). *(Status: FIXED)* *(See Roadmap: Phase 1, Task 1, Batch 1 Finding)*

## General / Recurring Issues Observed in Batch 1

1.  **General Advice Duplication:**
    *   **Issue:** The `general_advice` field contains duplicated paragraphs in multiple RAG files reviewed in this batch (including Chemistry, Art Studio, Economics, Physics, Structural Engineering) and previous batches.
    *   **Roadmap Ref:** Phase 2, Item 3. *(Status: FIXED as a side-effect of overarching_title logic improvements)*

2.  **Group Title Generation Strategy:**
    *   **Issue:** The script currently defaults to generating "All of the following UC courses are required" as the `group_title` when the ASSIST interface only displays a group number (e.g., "1", "2") or lacks an explicit title for that block. This was observed in Economics, Physics, and Structural Engineering RAGs.
    *   **Needed Improvement:** The logic needs refinement to:
        *   Handle cases where no explicit group title exists more gracefully (perhaps leaving it null or using a different placeholder).
        *   Prioritize using the *actual* title from the screenshot when one is present (as highlighted by the Art Studio mismatch). This is related to the specific Art Studio bug listed above but represents a broader strategy point. *(Status: FIXED)* 