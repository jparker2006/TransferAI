## Political Science/Data Analytics B.S.

*   **File:** `data/rag_output/santa_monica_college/university_of_california_san_diego/political_science_data_analytics_bs.json`
    *   **Issue:** Incorrect Group Logic and Title for the main lower-division requirement group.
        *   **Path:** `groups[0]`
        *   **Screenshot:** "LOWER DIVISION MAJOR REQUIREMENTS" block, encompassing both Section A and the "Select 2 courses from the following" instruction for Section B. General Information text also relevant.
        *   **Details:** `groups[0]` has `group_logic_type: "select_n_courses"`, `n_courses: 2`, and `group_title: "Select 2 courses from the following."`. This is incorrect because Section A (POLI 5, POLI 30) is fully required, and the "Select 2" rule applies only to Section B. The `group_logic_type` should be "all_required", `group_title` should be `null`, and the group-level `n_courses` should be removed.
    *   **Issue:** Missing course note "Same as PHILOS 51" for CCC articulation.
        *   **Path:** `groups[0].sections[1].uc_courses[3].logic_block.courses[0].courses[0]` (SMC's `POL SC 51` course object).
        *   **Screenshot:** "LOWER DIVISION MAJOR REQUIREMENTS" block, Section B, articulation for UC course "POLI 13 Power and Justice". The note is under "POL SC 51 Political Philosophy".
        *   **Details:** The note "Same as PHILOS 51" associated with SMC's `POL SC 51` is missing from its RAG JSON object. It should have a `note: "Same as PHILOS 51"` field.

## MAE: Mechanical Engineering B.S.

*   **File:** `data/rag_output/santa_monica_college/university_of_california_san_diego/mae_mechanical_engineering_bs.json`
    *   **Issue:** Incorrect logic for articulation of UC course MAE 30A.
        *   **Path:** `groups[0].sections[5].uc_courses[0].logic_block` (for UC course MAE 30A)
        *   **Screenshot:** "LOWER DIVISION MAJOR REQUIREMENTS" block, Section F, articulation for UC course "MAE 30A Statics & Introduction to Dynamics".
        *   **Details:** The RAG JSON implies an OR relationship between SMC's ENGR 12 and ENGR 16 for MAE 30A (i.e., ENGR 12 OR ENGR 16). The screenshot shows an AND relationship (i.e., ENGR 12 AND ENGR 16 are *both* required). The `logic_block.courses` array should contain a single AND block with both ENGR 12 and ENGR 16 if that's the sole articulated pathway.

## Sociology/Law and Society B.A.

*   **File:** `data/rag_output/santa_monica_college/university_of_california_san_diego/sociology_law_and_society_ba.json`
    *   **Issue:** Incorrect Group Logic and Title for the main requirement group.
        *   **Path:** `groups[0]`
        *   **Screenshot:** Main requirement block (labeled "1"), encompassing both Section A and the "Select 1 course from the following" instruction for Section B. General Information text also relevant.
        *   **Details:** `groups[0]` has `group_logic_type: "select_n_courses"`, `n_courses: 1`, and `group_title: "Select 1 course from the following."`. This is incorrect because Section A (SOCI 1, SOCI 2, SOCI 60) is fully required, and the "Select 1" rule applies only to Section B. The `group_logic_type` should be "all_required", `group_title` should be `null`, and the group-level `n_courses` should be removed.

## Music B.A.

*   **File:** `data/rag_output/santa_monica_college/university_of_california_san_diego/music_ba.json`
    *   **Issue:** Missing note "Articulation is subject to placement by proficiency exam" for UC course series.
        *   **Paths:**
            *   `groups[0].sections[0].uc_courses[0]` (MUS 2A + MUS 2AK series)
            *   `groups[0].sections[0].uc_courses[1]` (MUS 2B + MUS 2BK series)
            *   `groups[0].sections[0].uc_courses[2]` (MUS 2C + MUS 2CK series)
        *   **Screenshot:** Requirement block "1", Section A. The note is displayed above each MUS course pairing.
        *   **Details:** The note "Articulation is subject to placement by proficiency exam" is missing from the `note` field of all three UC course series objects in the RAG JSON. Each should have `note: "Articulation is subject to placement by proficiency exam"`.

## Public Health with Concentration in Epidemiology B.S.

*   **File:** `data/rag_output/santa_monica_college/university_of_california_san_diego/public_health_with_concentration_in_epidemiology_bs.json`
    *   **Issue:** Incorrect logic and title for Group 2.
        *   **Path:** `groups[1]` (Corresponds to screenshot block "2")
        *   **Screenshot:** Requirement block "2", showing "Complete 2 courses from the following" above PH 50, PH 80, PH 91.
        *   **Details:** RAG JSON has `group_logic_type: "all_required"` and `group_title: null`. It should be `group_logic_type: "select_n_courses"`, `n_courses: 2`, and `group_title: "Complete 2 courses from the following"`.
    *   **Issue:** Incorrect logic and title for Group 4 and its section.
        *   **Path:** `groups[3]` (Corresponds to screenshot block "4") and `groups[3].sections[0]`.
        *   **Screenshot:** Requirement block "4", showing "Complete 1 course from A".
        *   **Details:** RAG JSON `groups[3]` has `group_title: "All of the following UC courses are required"`. It should be `group_title: "Complete 1 course from A"`. Additionally, `groups[3].sections[0]` has `section_logic_type: "all_required"`. It should be `section_logic_type: "select_n_courses"` with `n_courses: 1`.
