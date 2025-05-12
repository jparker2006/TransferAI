# TransferAI RAG Quality Assurance Roadmap

## Overview
This document outlines the systematic approach to verify and ensure the quality of our RAG (Retrieval-Augmented Generation) output for articulation agreements between community colleges and universities.

## Verification Steps

### 1. Initial Setup
- [x] Update `assist_to_rag.py` to include notes and course equivalency information
- [x] Create batch configuration for multiple majors across diverse disciplines
- [ ] Create structured testing methodology

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
- [ ] Develop automated tests for verifying key structural elements

## Implementation Approach
1. Start with Computer Science B.S. as our baseline (already verified)
2. Progress through STEM majors (Physics, Biology, Mathematics)  
3. Continue with Social Sciences and Humanities
4. Compare patterns across disciplines to identify potential weaknesses in our parser
5. Create automated testing suite based on findings

## Quality Metrics
- Structural accuracy: All groups, sections, and logic blocks match source
- Content accuracy: All courses, notes, and equivalencies are preserved
- Logical accuracy: AND/OR logic and course selection rules work as expected

## Next Steps
1. Run batch processing to generate RAG output for all 10 selected majors
2. Begin systematic verification using this roadmap
3. Document any issues found for further refinement of `assist_to_rag.py`
4. Update this roadmap as new verification needs are discovered 