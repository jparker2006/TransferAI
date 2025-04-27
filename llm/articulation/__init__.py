"""
TransferAI Articulation Package

This package modularizes the articulation logic processing from the monolithic logic_formatter.py file
into clearly separated components with focused responsibilities. The package processes articulation 
logic for course transfer between California Community Colleges and University of California campuses.

The package provides functions for:
1. Validating if course selections satisfy articulation requirements
2. Rendering articulation logic into human-readable formats
3. Analyzing logic structures for special cases and patterns
4. Formatting responses for different query types
5. Detecting special conditions like honors requirements

This modularization is part of the v1.5 refactoring effort to improve code maintainability,
facilitate testing, and prepare for the v2 expansion to all majors.

Usage:
    from articulation import is_articulation_satisfied, render_logic_str
    
    # Or for more explicit imports:
    from articulation.validators import is_articulation_satisfied
    from articulation.renderers import render_logic_str
"""

# Version
__version__ = "1.5.0"

# Core validation API - functions for determining if requirements are satisfied
from .validators import (
    is_articulation_satisfied,
    explain_if_satisfied,
    validate_combo_against_group,
    validate_uc_courses_against_group_sections,
)

# Rendering API - functions for converting logic to human-readable text
from .renderers import (
    render_logic_str,
    render_logic_v2,
    render_group_summary,
    render_combo_validation,
)

# Formatting API - functions for structuring responses
from .formatters import (
    render_binary_response,
    include_binary_explanation,
    get_course_summary,
)

# Analysis API - functions for examining logic structures
from .analyzers import (
    extract_honors_info_from_logic,
    count_uc_matches,
    summarize_logic_blocks,
)

# Detection API - functions for identifying special cases
from .detectors import (
    is_honors_required,
    detect_redundant_courses,
    is_honors_pair_equivalent,
    explain_honors_equivalence,
)

# Model exports - data structures for articulation logic
from .models import (
    CourseOption,
    LogicBlock,
    ValidationResult,
) 