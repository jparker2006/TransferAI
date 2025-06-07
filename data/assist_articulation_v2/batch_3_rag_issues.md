# Batch 3 RAG Scraper Bug Report

This document outlines bugs found during manual review of the RAG JSON output from the `assist_to_rag.py` scraper for batch 3 agreements.

## Bug 3: Missing Cross-listed Course Information (Political Science)

-   **File**: Associated with Political Science B.A.
-   **Issue**: A course in the Political Science B.A. agreement is missing its cross-listing information.
-   **Course**: `POL SC 51: Political Philosophy (3.00 units)`
-   **Expected Note**: `(Same as PHILOS 51)`
-   **Suspected Cause**: The `visibleCrossListedCourses` data for the `Course` object is likely not being populated or formatted correctly by `Cell.from_dict` or `_format_course`.

## Bug 4: Missing Group Instructions (Public Health)

-   **File**: Associated with Public Health B.S. (Epidemiology)
-   **Issue**: In the Public Health B.S. agreement, requirement groups 2 and 4 are missing their instructions (e.g., "Complete the following").
-   **Suspected Cause**: The logic for generating `group_instruction_text` from `asset.instruction` within `process_assist_json_file` might be failing for these specific groups. The structure of `asset.instruction` for these groups should be inspected.

