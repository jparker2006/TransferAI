# TransferAI RAG Quality Assurance Roadmap

## Overview
This document outlines the systematic approach to verify and ensure the quality of our RAG (Retrieval-Augmented Generation) output for articulation agreements between community colleges and universities.

## Verification Steps

### 1. Initial Setup
- [x] Update `assist_to_rag.py` to include notes and course equivalency information
- [x] Create batch configuration for multiple majors across diverse disciplines
- [x] Create structured testing methodology

### 2. Quality Assurance Checklist

#### 2.1 Metadata Verification
- [ ] Confirm institution names and IDs are correct
- [ ] Verify major names and identifiers match source data
- [ ] Check academic year information
- [ ] Ensure all metadata fields are properly populated

#### 2.2 Structure Verification
- [ ] Confirm all groups are correctly identified and labeled
- [ ] Verify section divisions match ASSIST source
- [ ] Ensure proper nesting of logic blocks (AND/OR)
- [ ] Check for missing or duplicate sections

#### 2.3 Course Information Validation
- [ ] Verify all course codes match source data
- [ ] Confirm course titles are accurate
- [ ] Check credit units information
- [ ] Ensure course notes (including "Same as" statements) are captured
- [ ] Confirm honors course designations are correctly handled

#### 2.4 Logic Verification
- [ ] Test AND/OR logic handling across different articulation patterns
- [ ] Verify correct handling of course selection requirements
- [ ] Check for proper grouping of alternative courses
- [ ] Ensure complex nesting in requirements is preserved

#### 2.5 Cross-Major Comparison
- [ ] Compare common courses across different majors for consistency
- [ ] Identify patterns in how articulation varies by discipline
- [ ] Check for anomalies in course mappings

### 3. Manual Sampling and Verification
- [ ] Select representative sections from each major for manual review
- [ ] Compare RAG JSON against ASSIST visual representation
- [ ] Document any discrepancies or issues found

### 4. Edge Case Testing
- [ ] Test majors with unusually complex articulation requirements
- [ ] Verify handling of special notations and advisories
- [ ] Test courses with multiple cross-listings
- [ ] Check handling of courses with prerequisites mentioned in notes

### 5. Expansion Plan
- [ ] Prioritize additional majors based on complexity and student demand
- [ ] Create system for tracking verified vs. unverified agreements
- [ ] Document institution-specific quirks or patterns
- [x] Develop automated tests for verifying key structural elements

## Practical Testing Approaches

### Visual Comparison Method
1. **Side-by-Side Verification**:
   - Open ASSIST website for the specific major
   - Open the generated RAG JSON in a JSON viewer
   - Compare key sections visually for structure and content match
   - Document any discrepancies in a standardized format

2. **Sampling Strategy**:
   - For each major, select 3-5 representative sections:
     - A simple course-to-course mapping
     - A complex logic block (nested AND/OR)
     - A section with special notes or advisories
     - A section with course selection requirements (e.g., "select 2 from")
   - Focus detailed verification on these samples rather than entire documents

### Semi-Automated Verification Tools

1. **JSON Structure Validator** ✅:
   - Created `test_rag_quality.py` with validation command
   - Verifies all required fields, group structures, and logic blocks
   - Ensures no empty or malformed blocks exist
   - Example check: `python3 data/tests/test_rag_quality.py validate data/rag_output/santa_monica_college/university_of_california_san_diego/`

2. **Course Note Extractor** ✅:
   - Added `notes` command to `test_rag_quality.py`
   - Extracts and lists all courses with notes for manual verification
   - Example: `python3 data/tests/test_rag_quality.py notes data/rag_output/file.json`

3. **Logic Block Counter** ✅:
   - Integrated into `test_rag_quality.py validate` command
   - Counts AND/OR blocks, courses, and maximum nesting levels
   - Provides statistics for each RAG JSON file

4. **Cross-Major Comparison Tool** ✅:
   - Added `compare` command to `test_rag_quality.py`
   - Identifies courses that appear across multiple majors
   - Detects inconsistencies in course titles or notes
   - Example: `python3 data/tests/test_rag_quality.py compare data/rag_output/santa_monica_college/university_of_california_san_diego/`

### Regression Testing Strategy

1. **Known Good Examples**:
   - Maintain a collection of verified "golden" examples (like CSE B.S.)
   - After any parser changes, re-run these examples and compare outputs
   - Use simple diff tools to identify any changes in output structure

2. **Edge Case Library**:
   - Create a catalog of edge cases found during verification
   - Document the expected handling for each case
   - Re-test these specific cases after any parser modifications

3. **Incremental Verification**:
   - When adding new majors, prioritize verification of new structural patterns
   - Focus testing efforts on elements not previously encountered
   - Document new patterns for future reference

## Implementation Approach
1. Start with Computer Science B.S. as our baseline (already verified)
2. Progress through STEM majors (Physics, Biology, Mathematics)  
3. Continue with Social Sciences and Humanities
4. Compare patterns across disciplines to identify potential weaknesses in our parser
5. Create lightweight verification scripts based on findings

## Quality Metrics
- Structural accuracy: All groups, sections, and logic blocks match source
- Content accuracy: All courses, notes, and equivalencies are preserved
- Logical accuracy: AND/OR logic and course selection rules work as expected

## Next Steps
1. Run batch processing to generate RAG output for all 10 selected majors
2. ✅ Create simple validation scripts for structure checking
3. Begin systematic verification using this roadmap
4. Document any issues found for further refinement of `assist_to_rag.py`
5. Update this roadmap as new verification needs are discovered

## Expansion Strategy

### Phase 1: Core Majors (Current)
- Focus on 10 diverse majors across disciplines
- Establish baseline quality and identify common patterns
- Refine parser based on initial findings

### Phase 2: Targeted Expansion
- Add 15-20 additional high-demand majors
- Prioritize majors with unique articulation patterns
- Focus on majors with complex requirements to stress-test the parser

### Phase 3: Comprehensive Coverage
- Expand to all available majors between SMC and UCSD
- Implement automated batch processing and verification
- Document institution-specific patterns and exceptions

### Phase 4: Multi-Institution Expansion
- Select additional community college and UC pairs
- Test parser adaptability to different institution formats
- Scale verification process for multiple institution pairs 