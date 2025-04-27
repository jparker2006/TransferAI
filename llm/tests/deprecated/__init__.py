"""
Deprecated Tests Directory

This directory contains test files that are no longer actively maintained and have been 
replaced by module-specific test files in the parent directory.

These files are preserved temporarily to aid in the migration process but will be 
removed in future versions of TransferAI.

Please use the corresponding module-specific test files instead:
- test_honors_equivalence.py → test_articulation_detectors.py
- test_binary_response.py → test_articulation_formatters.py
- test_combo_validation.py → test_articulation_renderers.py
- test_count_uc_matches.py → test_articulation_analyzers.py
- test_render_logic.py → test_articulation_renderers.py
- test_render_logic_v2.py → test_articulation_renderers.py
- test_articulation_satisfied.py → test_articulation_validators.py
- test_logic_formatter.py → multiple module-specific test files
"""

import warnings

warnings.warn(
    "The tests in the 'deprecated' directory are obsolete and will be removed in future releases. "
    "Please use the module-specific test files in the parent directory.",
    DeprecationWarning,
    stacklevel=2
)
