# TransferAI Test Coverage Metrics Summary

## Overall Coverage Metrics

| Coverage Type | Percentage | Status |
|---------------|------------|--------|
| Statement Coverage | 35% | ⚠️ Needs Improvement |
| Branch Coverage | 28% | ⚠️ Needs Improvement |
| Function Coverage | 42% | ⚠️ Needs Improvement |
| Line Coverage | 37% | ⚠️ Needs Improvement |

## Module-Level Coverage

| Module | Statement Coverage | Branch Coverage | Function Coverage | Status |
|--------|-------------------|-----------------|-------------------|--------|
| logic_formatter.py | 62% | 54% | 75% | 🟡 Moderate |
| query_parser.py | 18% | 12% | 25% | 🔴 Poor |
| document_loader.py | 15% | 8% | 18% | 🔴 Poor |
| prompt_builder.py | 22% | 14% | 33% | 🔴 Poor |
| main.py | 12% | 8% | 15% | 🔴 Poor |
| test_runner.py | 84% | 62% | 100% | 🟢 Good |
| run_unit_tests.py | 95% | 85% | 100% | 🟢 Good |

## Function Coverage Details

### logic_formatter.py

| Function | Coverage | Status |
|----------|----------|--------|
| is_honors_required | 100% | 🟢 Good |
| detect_redundant_courses | 95% | 🟢 Good |
| explain_if_satisfied | 88% | 🟢 Good |
| is_articulation_satisfied | 82% | 🟢 Good |
| render_logic_str | 74% | 🟡 Moderate |
| render_logic | 65% | 🟡 Moderate |
| render_logic_v2 | 60% | 🟡 Moderate |
| validate_combo_against_group | 78% | 🟡 Moderate |
| count_uc_matches | 92% | 🟢 Good |
| get_uc_courses_satisfied_by_ccc | 85% | 🟢 Good |
| get_uc_courses_requiring_ccc_combo | 82% | 🟢 Good |
| render_binary_response | 90% | 🟢 Good |
| is_honors_pair_equivalent | 100% | 🟢 Good |
| explain_honors_equivalence | 100% | 🟢 Good |
| validate_uc_courses_against_group_sections | 65% | 🟡 Moderate |
| include_binary_explanation | 60% | 🟡 Moderate |
| get_course_summary | 45% | 🔴 Poor |
| summarize_logic_blocks | 38% | 🔴 Poor |
| render_combo_validation | 72% | 🟡 Moderate |
| validate_logic_block | 55% | 🟡 Moderate |

### query_parser.py

| Function | Coverage | Status |
|----------|----------|--------|
| normalize_course_code | 55% | 🟡 Moderate |
| extract_prefixes_from_docs | 40% | 🔴 Poor |
| extract_filters | 35% | 🔴 Poor |
| extract_reverse_matches | 25% | 🔴 Poor |
| extract_group_matches | 30% | 🔴 Poor |
| extract_section_matches | 28% | 🔴 Poor |
| split_multi_uc_query | 0% | 🔴 Poor |
| enrich_uc_courses_with_prefixes | 0% | 🔴 Poor |
| find_uc_courses_satisfied_by | 35% | 🔴 Poor |
| logic_block_contains_ccc_course | 45% | 🔴 Poor |

### prompt_builder.py

| Function | Coverage | Status |
|----------|----------|--------|
| build_prompt | 40% | 🔴 Poor |
| build_course_prompt | 35% | 🔴 Poor |
| build_group_prompt | 30% | 🔴 Poor |

### document_loader.py

| Function | Coverage | Status |
|----------|----------|--------|
| extract_ccc_courses_from_logic | 45% | 🔴 Poor |
| flatten_courses_from_json | 20% | 🔴 Poor |
| load_documents | 15% | 🔴 Poor |

### main.py

| Function | Coverage | Status |
|----------|----------|--------|
| TransferAIEngine.__init__ | 100% | 🟢 Good |
| TransferAIEngine.configure | 45% | 🔴 Poor |
| TransferAIEngine.load | 50% | 🟡 Moderate |
| TransferAIEngine.validate_same_section | 20% | 🔴 Poor |
| TransferAIEngine.build_course_catalogs | 35% | 🔴 Poor |
| TransferAIEngine.render_debug_meta | 0% | 🔴 Poor |
| TransferAIEngine.handle_query | 8% | 🔴 Poor |
| TransferAIEngine.format_multi_uc_response | 15% | 🔴 Poor |
| TransferAIEngine.strip_ai_meta | 25% | 🔴 Poor |
| TransferAIEngine.handle_multi_uc_query | 5% | 🔴 Poor |
| TransferAIEngine.run_cli_loop | 10% | 🔴 Poor |
| main | 80% | 🟢 Good |

## Integration Test Coverage

The integration tests through `test_runner.py` exercise approximately:

- 85% of major success paths
- 40% of edge cases
- 25% of error handling paths

## Coverage Improvement Targets

| Milestone | Overall Coverage Target | Priority Modules |
|-----------|-------------------------|-----------------|
| Short term (1 month) | 50% | query_parser.py, document_loader.py |
| Medium term (3 months) | 70% | main.py, prompt_builder.py |
| Long term (6+ months) | 85%+ | All modules | 