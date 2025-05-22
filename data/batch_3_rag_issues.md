<!-- General Note: Formatting issues within the 'general_advice' field will be reviewed and addressed holistically at a later stage, rather than as individual per-major bugs, to ensure consistency and efficiency. -->

## Chemical and Nano Engineering: NanoEngineering B.S.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/chemical_and_nano_engineering_nanoengineering_bs.json

#### Issue Category: Structure
* **Location:** `groups[0].sections[3].uc_courses[0].logic_block` (for UC course NANO 15)
* **Problem:** The `no_articulation_reason` field is missing for UC course NANO 15, while `no_articulation` is set to `true`. The screenshot explicitly states "No Course Articulated". This is inconsistent with other non-articulated courses like NANO 4, which correctly populates this field.
* **ASSIST Reference:** Screenshot Section D, articulation status for NANO 15.
* **Correction Needed:** Add `no_articulation_reason: "No Course Articulated"` to the `logic_block` for the NANO 15 UC course entry.
* **Status:** ✅ FIXED - Modified assist_to_rag.py to ensure all no_articulation cases include a no_articulation_reason field

#### Issue Category: Course Information
* **Location:** Applies to all CCC course objects within `groups[*].sections[*].uc_courses[*].logic_block.courses[*].courses[*]` (and similar paths where CCC courses are defined).
* **Problem:** Unit information for California Community College (CCC) courses is present on the ASSIST screenshot but is not included in the RAG JSON structure for CCC courses. For example, MATH 13 is shown as 3.00 units on ASSIST, but the JSON object for MATH 13 does not include its unit value.
* **ASSIST Reference:** Unit values displayed on the right-hand side for all articulated CCC courses in the screenshot (e.g., MATH 13 (3.00 units), PHYSCS 21 (5.00 units), etc. for the NanoEngineering major, and generally across all majors).
* **Correction Needed:** Implement a `units` field (e.g., `"units": 3.0`) within each CCC course object in the RAG JSON files and populate it with the correct unit values from ASSIST. This change should be applied consistently across all relevant RAG JSON files.
* **Status:** ✅ FIXED - Added units field to all CCC course objects

## Data Science B.S.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/data_science_bs.json

* **Location:** `groups[1].group_title`
* **Problem:** The `group_title` in the JSON is "ADDITIONAL MAJOR REQUIREMENTS", while the corresponding group header on the ASSIST screenshot is "Complete A, B, C, D, or E". While the `overarching_title` field contains "ADDITIONAL MAJOR REQUIREMENTS", the direct `group_title` should ideally match the instructional header from ASSIST when present.
* **ASSIST Reference:** Screenshot 2, header for the second group of requirements.
* **Correction Needed:** Change `groups[1].group_title` from "ADDITIONAL MAJOR REQUIREMENTS" to "Complete A, B, C, D, or E" to match the ASSIST screenshot's group header. (Alternatively, confirm if `overarching_title` is the intended field for the static title and `group_title` for the direct ASSIST header).
* **Status:** ✅ FIXED - Logic in assist_to_rag.py updated to prioritize instruction-derived group titles.

## Human Developmental Sciences B.S. with a Specialization in Equity & Diversity

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/human_developmental_sciences_bs_with_a_specialization_in_equity_and_diversity.json

#### Issue Category: Structure
* **Location:** 
    * `groups[2].sections[0]` (related to ASSIST "Group 3: Complete 2 courses from the following")
    * `groups[3].sections[0]` (related to ASSIST "Group 4: Complete 2 courses from the following")
* **Problem:** In these groups, the parent group object correctly specifies `n_courses: 2` (e.g., `groups[2].n_courses = 2`). However, the single child section within each (`sections[0]`), which lists the available UC course options, incorrectly has `n_courses: 1`. This contradicts the group-level requirement. The section's `n_courses` should match the parent group's requirement when it's the sole section providing all choices for that group requirement.
* **ASSIST Reference:** Screenshots 2 (for Group 3) and 3 (for Group 4) - specifically the "Complete 2 courses from the following" instruction.
* **Correction Needed:** 
    * Change `groups[2].sections[0].n_courses` from `1` to `2`.
    * Change `groups[3].sections[0].n_courses` from `1` to `2`.
* **Status:** ✅ FIXED - Modified assist_to_rag.py to ensure single sections inherit their parent group's n_courses value when appropriate

* **Location:** `groups[4]` (related to ASSIST "Group 5: Complete 2 courses from the following") and its child sections:
    * `groups[4].sections[0]` (corresponds to ASSIST Group 5, sub-section A)
    * `groups[4].sections[2]` (corresponds to ASSIST Group 5, sub-section C)
* **Problem:** `groups[4]` correctly indicates `n_courses: 2` should be selected overall. However, `sections[0]` and `sections[2]` within this group are both defined with `section_logic_type: "all_required"`. This would incorrectly force a student to take all courses listed in `sections[0]` (4 courses) or all courses in `sections[2]` (5 courses) if they pick any course from these sub-sections to satisfy the parent group's "select 2" requirement. This prevents correctly fulfilling the "select 2 courses from the overall options in Group 5 (A, B, or C lists on ASSIST)" logic. The structure does not properly represent choosing 2 from the combined pool.
* **ASSIST Reference:** Screenshot 4 - "Group 5: Complete 2 courses from the following" and its sub-sections A, B (Select 1 course), and C.
* **Correction Needed:** The structure of `groups[4]` and its sections needs to be revised to accurately reflect that 2 courses must be selected from the combined pool of options presented in ASSIST Group 5's sub-sections A, B, and C. This likely involves changing `section_logic_type` for `groups[4].sections[0]` and `groups[4].sections[2]` from `"all_required"` to a selection type (e.g., `"select_n_courses"`) and ensuring the `n_courses` values at various levels correctly sum up to the parent group's requirement, or flattening the choices under `groups[4]` if appropriate.

## International Studies - Economics B.A.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/international_studies_economics_ba.json

#### Issue Category: Course Information
* **Location:** UC course entries in the JSON that represent a series of courses (where `_is_uc_series_requirement: true`), primarily within `groups[2].sections[0].uc_courses` (Language Requirement section).
* **Problem:** These UC course series entries (e.g., `uc_course_id: "LIAB 1D + LIAB 1DX"`) are missing a top-level `units` field in the JSON. This field should represent the total units for completing the entire UC series. While ASSIST shows units for individual components of the series (e.g., LIAB 1D is 2.50 units, LIAB 1DX is 2.50 units), the JSON object for the combined series requirement does not sum these to provide a total (e.g., `units: 5.0`). Individual non-series UC courses in the same list do have their `units` specified.
* **ASSIST Reference:** Screenshot 2 (Language Requirement). For example, component courses like LIAB 1D (2.50 units) and LIAB 1DX (2.50 units) are listed with their units, implying the series is 5.0 units total.
* **Correction Needed:** Add a top-level `units` field to each UC course series object in the JSON. The value of this field should be the sum of the units of its component courses as indicated on ASSIST. For example, for the series `LIAB 1D + LIAB 1DX`, the JSON object should include `"units": 5.0`. This ensures that the RAG data for UC series requirements includes total unit information.
* **Status:** ✅ FIXED - Added summed units field to all UC course series objects

## Literature/Writing B.A.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/literature_writing_ba.json

#### Issue Category: Structure
* **Location:** Representation of the requirement to select 2 courses from a specific list of 11 literature and GSS courses (LTEN 21, 22, 23, 25, 27, 28, 29, GSS 21, 22, 23, 25, 26), while LTEN 26 is a separate standalone requirement.
* **Problem:** The RAG JSON currently groups these courses into `groups[0].sections[0]` through `groups[0].sections[3]`. Since `groups[0]` and these sections are effectively `all_required`, it incorrectly mandates all 11 courses from the list, instead of allowing a selection of 2. (LTEN 26 is correctly handled as a separate requirement within `groups[0].sections[1]` which is `all_required`).
* **ASSIST Reference:** `general_advice` section in the RAG JSON (requirement 2: "Any two of the following..."). Individual courses listed on ASSIST Screenshot 1 (Sections A, B, C, D).
* **Correction Needed:** Restructure the JSON to create a dedicated group or section for the 11 specified UC courses (LTEN 21, 22, 23, 25, 27, 28, 29, GSS 21, 22, 23, 25, 26). This new group/section must have a `select_n_courses: 2` logic applied. This is separate from ensuring LTEN 26 is required.

* **Location:** Representation of the secondary language and literature requirement.
* **Problem:** The JSON (`groups[0]`, which is `all_required`) lists multiple language sequences (French, Hebrew, German, etc., in `sections[5]` through `sections[14]`). Each of these language sections is also set to `section_logic_type: "all_required"`. This incorrectly implies that a student must complete all courses in *all* listed languages. The requirement is to choose *one* language and complete its sequence to proficiency.
* **ASSIST Reference:** `general_advice` section in the RAG JSON (requirement 4). Language options are shown across ASSIST Screenshots 2, 3, 4, 5 (Sections F through O).
* **Correction Needed:** Create a new parent group to contain all the individual language sections (currently `groups[0].sections[5]` through `sections[14]`). This new parent group must have a `group_logic_type: "choose_one_section"` (or equivalent, like `select_n_courses: 1` if each language section is considered one choice). The individual language sections nested under this new group should then retain their `section_logic_type: "all_required"` because all courses within the *chosen* language sequence are required.

## Psychology B.S. with a Specialization in Clinical Psychology

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/psychology_bs_with_a_specialization_in_clinical_psychology.json

#### Issue Category: Structure
* **Location:** `groups[0].sections[0]` (representing ASSIST's Group 1, Section A), `groups[0].sections[2]` (Section C), and `groups[0].sections[3]` (Section D).
* **Problem:** These sections in the RAG JSON are marked with `section_logic_type: "all_required"`. However, the parent `groups[0]` correctly states `group_logic_type: "select_n_courses", n_courses: 3`, meaning the student must complete 3 courses from the combined offerings of sections A, B, C, D, and E. If a student picks a course from section A (or C, or D) as one of their three, they are not required to take *all* courses within that specific section. The `all_required` on these sections incorrectly implies a stricter condition. These sections (A, C, D on ASSIST) primarily list available options for the overarching "select 3" requirement.
* **ASSIST Reference:** Screenshot 1, the main instruction for Group 1 is "Complete 3 courses from the following". Sub-sections A, C, and D list courses without an intrinsic "complete all of these" mandate when contributing to the parent group's selection.
* **Correction Needed:** The `section_logic_type` for `groups[0].sections[0]` (A), `groups[0].sections[2]` (C), and `groups[0].sections[3]` (D) should be changed from `all_required`. A type that better reflects them as lists of options for the group-level selection (e.g., `select_n_courses` where `n_courses` equals the number of courses in that list, or a more generic "options_provider" type if the schema allows) should be used. The critical part is removing the incorrect `all_required` constraint.

#### Issue Category: Notes/Advisements
* **Location:** `groups[4]` in the RAG JSON (corresponding to ASSIST Group 5 "Complete 1 course from A").
* **Problem:** The ASSIST screenshot for Group 5 clearly states "Must be taken for a letter grade" directly below the group title. This important condition is not captured in the RAG JSON, either in the `group_title` or as a separate `group_advisement` or `section_advisement`.
* **ASSIST Reference:** Screenshot 4, Group 5, the text "Must be taken for a letter grade".
* **Correction Needed:** Add the advisement "Must be taken for a letter grade" to the `groups[4]` object in the RAG JSON. Ideally, this would be via a dedicated `group_advisement` field.

## Real Estate and Development B.S.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/real_estate_and_development_bs.json

#### Issue Category: Structure
* **Location:** `groups[1]` (corresponding to ASSIST Group 2).
* **Problem:** The RAG JSON has `group_title: null` for this group. While ASSIST doesn't provide an explicit header for this group, it's a distinct requirement block. Other groups in the JSON have descriptive titles (e.g., "Complete 1 course from the following"). For consistency and clarity, this group should also have a title reflecting its mandatory nature.
* **ASSIST Reference:** Screenshot, the visual separation and numbering of Group 2, which implies an "all required" structure for its sub-sections.
* **Correction Needed:** Add a descriptive `group_title` to `groups[1]`. A title such as "Complete all courses from the following sections" or "Complete Section A and Section B" would be appropriate.

## Theatre B.A.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/theatre_ba.json

#### Issue Category: Structure
* **Location:** `groups[0].group_title`
* **Problem:** The RAG JSON has `group_title: "All of the following UC courses are required"`. The ASSIST screenshot does not display an explicit title for this group. While the logic is `all_required`, the title should be absent (`null`) or match ASSIST if one were present.
* **ASSIST Reference:** Screenshot, the first group of courses is presented without an explicit heading.
* **Correction Needed:** Change `groups[0].group_title` to `null` or an empty string.

#### Issue Category: Course Information
* **Location:** `groups[0].sections[0].uc_courses[8]` (UC course TDPR 6 'Theatre Practicum').
* **Problem:** The RAG JSON lists `units: 4.0` for TDPR 6. The ASSIST screenshot shows variable units: "4.00 - 6.00".
* **ASSIST Reference:** Screenshot, Section A, course TDPR 6, units column.
* **Correction Needed:** Update the `units` for TDPR 6 to reflect the range. If the schema only supports a float for `units`, this might require a schema change (e.g., to allow a string like "4.00 - 6.00" or add `min_units`/`max_units` fields). For logging, note the need to represent this range accurately.
* **Status:** ✅ FIXED - Added support for variable unit ranges using min_units and max_units fields

## Urban Studies and Planning B.A.

### File: data/rag_output/santa_monica_college/university_of_california_san_diego/urban_studies_and_planning_ba.json

#### Issue Category: Structure
* **Location:** `groups[0].group_title`
* **Problem:** The RAG JSON has `group_title: null` for the main requirement group. Given this group combines an all-required section (A) with two select-one sections (B and C), a descriptive title is needed for clarity (e.g., "Complete Section A, and select one course from Section B, and one course from Section C" or similar summary).
* **ASSIST Reference:** Screenshot, Group 1, encompassing sections A (all required), B (select 1), and C (select 1).
* **Correction Needed:** Add an appropriate `group_title` to `groups[0]` to summarize its multi-part requirement.

* **Location:** `groups[0].sections[1].section_title` (for Section B) and `groups[0].sections[2].section_title` (for Section C).
* **Problem:** The RAG JSON uses generic titles ("Section B", "Section C"). The ASSIST screenshot explicitly titles these sections as "Select 1 course from the following."
* **ASSIST Reference:** Screenshot, headers for Section B and Section C.
* **Correction Needed:** 
    * Change `groups[0].sections[1].section_title` to "Select 1 course from the following."
    * Change `groups[0].sections[2].section_title` to "Select 1 course from the following."