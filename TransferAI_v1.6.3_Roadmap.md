# TransferAI v1.6.3+ Roadmap

## Test-Level Improvements

### ✅ Group 1 Section Requirements (Tests 5 & 6)
1. Make results more explicit about whether mixing courses across sections is allowed
2. Add clearer guidance about the Group 1 section requirements

### ✅ Group Presentation Format (Tests 8 & 9)
1. Add more explicit section headers for clarity
2. Improve formatting to make it easier to scan group requirements

### ✅ No Articulation Messaging (Test 14)
1. Include information about alternatives at UCSD
2. Add recommendations for courses that could be taken at UCSD instead

### ✅ Partial Completion Guidance (Test 15)
1. Include more detailed guidance on the complete pathway for CSE 30
2. Add context about CIS 26B/26BH being the only remaining course needed

### ✅ Group 3 Selection Clarity (Test 27)
1. Clarify that students need to select exactly 2 courses from Group 3
2. Explicitly note that CHEM 6A and PHYS 2A satisfy Group 3 requirements

## General Recommendations

- **Query Type Detection**: Improve consistency, especially for "which courses satisfy X" type questions
- **Handler Selection**: Fix incorrect identification of course lookup queries as honors requirement queries
- **Messaging Consistency**: Ensure consistent messaging for courses with no articulation across all handlers
- **Test Coverage**: Add more tests for edge cases like partial matches and complex articulation logic
- **Metadata Usage**: Review handlers to ensure they're using the correct metadata fields for articulation validation
- **Group Query Handling**: Make sure group queries with orphaned "No articulation" messages are handled consistently
- **Comparison Query Testing**: Add more explicit tests for the COURSE_COMPARISON query type to ensure robust comparison handling
- **Response Formatting**: Improve formatting of responses for better readability, especially for group requirements

## Follow-Up Tasks

### What's Covered
- Reverse lookups (Test 31, 35: What does CIS 36A satisfy)
- Honors and non-honors matching (Tests 32, 33: Are honors courses required)
- Multi-section group articulation (Tests 8, 9, 23, 26: Group requirement tests)
- Courses with no articulation (Tests 14, 16: CSE 21, CSE 15L)

### Still Needed
- "Same as" equivalencies could be more explicit
- Explicit tests for group completion with mixed honors/non-honors courses
- Tests for more complex articulation structures
- Tests for queries about transfer requirements not covered by articulation data

## Changelog: Fixes Implemented (v1.6.3)

1. Fixed query type detection in `query_service.py` for course lookup and validation queries
2. Restructured query type detection priority order to properly identify validation queries vs lookup queries
3. Improved honors requirement detection to only trigger on explicit requirement questions
4. Added comprehensive test cases to verify correct query type detection
5. Removed over-aggressive honors detection for simple course lookup queries with multiple courses
6. Fixed orphaned "No articulation" messages in group presentations by properly formatting courses with no articulation
7. Implemented clear "No Articulation Available" section for courses without community college equivalents
8. Added explicit messaging for courses that must be completed at UCSD after transfer