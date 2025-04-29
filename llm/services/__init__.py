"""
TransferAI Services Package

This package contains service modules that implement the business logic for the TransferAI system,
providing interfaces between the core articulation logic and external components like document
processing, query handling, and LLM prompting.

The package provides services for:
1. Articulation validation and processing through a unified facade
2. Document loading and management for articulation data
3. Query parsing and processing for user requests
4. Prompt construction for LLM interaction
5. Course matching and comparison

This modularization is part of the v1.5 refactoring effort to improve code maintainability,
facilitate testing, and prepare for the v2 expansion to all majors.

Usage:
    from llm.services import ArticulationFacade, QueryService
    
    # Or for more explicit imports:
    from llm.services.document_service import DocumentService
    from llm.services.prompt_service import PromptService
"""

# Version
__version__ = "1.5.0"

# Articulation Facade - provides unified interface to articulation validation
from .articulation_facade import (
    ArticulationFacade,
)

# Document Service - functions for loading and managing articulation documents
from .document_service import (
    DocumentService,
)

# Query Service - functions for processing user queries
from .query_service import (
    QueryService,
)

# Prompt Service - functions for building prompts for LLM interaction
from .prompt_service import (
    PromptService,
    build_prompt,
)

# Matching Service - functions for course matching and comparison
from .matching_service import (
    MatchingService,
)
