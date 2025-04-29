# TransferAI Final Refactoring Plan

## 1. Current Architecture Analysis

The TransferAI system currently consists of several components:

- **main.py** (TransferAIEngine): Core orchestration with heavy business logic and query handling
- **document_loader.py**: Document loading, transforming, and indexing for retrieval
- **query_parser.py**: Query analysis and entity extraction
- **prompt_builder.py**: Prompt construction for LLM interactions
- **articulation/ package**: Modular components handling articulation logic:
  - validators.py: Core validation logic
  - renderers.py: Text rendering of articulation logic
  - formatters.py: Response formatting
  - analyzers.py: Logic analysis utilities
  - detectors.py: Special case detection
  - models.py: Data structures

### Key Issues:

1. **Monolithic Engine**: The TransferAIEngine class in main.py contains a 350+ line handle_query method with complex nested conditionals
2. **Direct Dependencies**: The engine directly calls functions from multiple modules without abstraction layers
3. **Mixed Responsibilities**: Query parsing, document matching, and response generation are tightly coupled
4. **Limited Testability**: Complex logic paths make testing difficult
5. **Hard-coded Templates**: Prompt templates are embedded in code
6. **Configuration Spread**: Settings and configuration are scattered throughout the code

## 2. Target Architecture

We'll implement a modular architecture using established design patterns:

### 2.1 Core Design Patterns

- **Strategy Pattern**: For specialized query handlers
- **Repository Pattern**: For document access and caching
- **Facade Pattern**: For simplified interfaces to subsystems
- **Dependency Injection**: For loose coupling and testability

### 2.2 System Components

```
┌────────────┐      ┌────────────┐      ┌────────────┐
│            │      │            │      │            │
│ TransferAI │──────▶ QueryRouter│──────▶ QueryHandler│
│  Engine    │      │            │      │ Registry   │
│            │      │            │      │            │
└────────────┘      └────────────┘      └──────┬─────┘
                                               │
                                               ▼
┌────────────┐      ┌────────────┐      ┌────────────┐
│            │      │            │      │            │
│ Prompt     │◀─────┤ Specialized│◀─────┤ Document   │
│ Manager    │      │ Handlers   │      │ Repository │
│            │      │            │      │            │
└────────────┘      └─────┬──────┘      └────────────┘
                          │
                          ▼
                   ┌────────────┐
                   │            │
                   │Articulation│
                   │  Facade    │
                   │            │
                   └────────────┘
```

### 2.3 Directory Structure

```
llm/
├── engine/
│   ├── __init__.py
│   ├── transfer_engine.py        # Core engine (simplified TransferAIEngine)
│   ├── config.py                 # Configuration management
│   └── utils.py                  # Shared utilities
├── handlers/
│   ├── __init__.py
│   ├── base.py                   # Handler base class and registry 
│   ├── course_handler.py         # Course equivalency handler
│   ├── validation_handler.py     # Validation query handler
│   ├── group_handler.py          # Group requirement handler
│   ├── honors_handler.py         # Honors queries handler
│   └── fallback_handler.py       # Default/fallback handler
├── repositories/
│   ├── __init__.py
│   ├── document_repository.py    # Document access layer
│   ├── course_repository.py      # Course info access layer
│   └── template_repository.py    # Template storage
├── services/
│   ├── __init__.py
│   ├── document_service.py       # Document loading & processing
│   ├── query_service.py          # Query parsing & processing
│   ├── prompt_service.py         # Prompt building & management
│   ├── matching_service.py       # Document matching & filtering
│   └── articulation_facade.py    # Unified interface to articulation
├── models/
│   ├── __init__.py
│   ├── document.py               # Document model wrapper around llama_index
│   ├── query.py                  # Query models
│   ├── response.py               # Response models
│   └── config.py                 # Configuration models
├── templates/                    # Prompt templates
│   ├── course_templates.py
│   ├── group_templates.py
│   └── helpers.py
├── articulation/                 # Existing articulation package (unchanged)
│   ├── validators.py
│   ├── renderers.py
│   ├── formatters.py
│   ├── analyzers.py
│   ├── detectors.py
│   └── models.py
├── data/                         # Data files (unchanged)
│   └── rag_data.json
└── main.py                       # Entry point
```

## 3. Step-by-Step Refactoring Roadmap

This section outlines the exact steps we'll take to transform the current codebase into the target architecture. Each step builds upon the previous one, maintaining a working system throughout the refactoring process.

### Step 1: Create Directory Structure and Skeleton Files (Day 1-2) ✅
1. Create new directory structure as outlined in Section 2.3
2. Set up empty __init__.py files in each directory
3. Create skeleton files for all major components
4. Set up new entry point that imports the current functionality

### Step 2: Define Core Models and Interfaces (Day 3-5) ✅
1. Create Query and QueryResult models in models/query.py
2. Define BaseHandler interface in handlers/base.py
3. Define DocumentRepository interface in repositories/document_repository.py
4. Create configuration models in models/config.py

### Step 3: Implement ArticulationFacade (Day 6-7) ✅
1. Create services/articulation_facade.py
2. Implement methods that wrap existing articulation functionality
3. Test facade with simple test cases
4. Ensure all current articulation module features are accessible

### Step 4: Create DocumentRepository Implementation (Day 8-10) ✅
1. Extract document loading code from current system
2. Implement document_repository.py with search methods
3. Create caching layer for efficient document access
4. Write tests for document repository functionality
5. Fix caching functionality to properly handle instance methods

### Step 5: Implement QueryService (Day 11-13) ✅
1. Extract query parsing from query_parser.py to services/query_service.py
2. Implement filter extraction logic
3. Create query type detection algorithms
4. Write comprehensive tests for the QueryService
5. Update main.py and document_repository.py to use the new QueryService

### Step 6: Implement MatchingService (Day 14-15) ✅
1. Create MatchingService implementation in services/matching_service.py
2. Extract document matching logic from main.py
3. Implement various matching strategies (course, group, section, reverse, semantic)
4. Add filtering and ranking functionality
5. Write comprehensive tests for the MatchingService
6. Update main.py to use the new MatchingService

### Step 7: Create First Query Handler (Day 16-18) ✅
1. Implement ValidationQueryHandler for course validation queries
2. Extract business logic from main.py handle_query method
3. Integrate with DocumentRepository and MatchingService
4. Test with validation test cases

### Step 8: Create Additional Handlers (Day 19-23)
1. Implement GroupQueryHandler for group requirement queries ✅
2. Implement CourseEquivalencyHandler for course equivalency queries ✅
3. Implement HonorsQueryHandler for honors-related queries ✅
4. Implement FallbackQueryHandler for unknown query types
5. Test each handler with relevant test cases

### Step 9: Extract Templates and Create PromptService (Day 24-26)
1. Extract templates from prompt_builder.py to templates directory
2. Implement PromptService for dynamic template selection
3. Create context building functions for templates
4. Test with various prompts and configurations

### Step 10: Implement New TransferAIEngine (Day 27-29)
1. Create simplified engine/transfer_engine.py
2. Implement handler selection logic
3. Set up configuration management
4. Integrate all components
5. Test with comprehensive test suite
6. Implement Document model wrapper class
7. Create document_service.py to handle document loading functionality

### Step 11: Update Main Entry Point (Day 30)
1. Update main.py to use the new architecture
2. Ensure backward compatibility
3. Add configuration options
4. Test the complete system

### Step 12: Comprehensive Testing and Refinement (Day 31-35)
1. Run regression tests against all test cases
2. Fix any issues or inconsistencies
3. Optimize performance
4. Refine error handling
5. Update documentation

## 4. Implementation Strategy

### 4.1 Key Components Implementation

#### 4.1.1 Articulation Facade

The facade will provide a simplified interface to the articulation package:

```python
# services/articulation_facade.py
from typing import Dict, List, Any, Optional
from llm.articulation import validators, renderers, formatters, analyzers, detectors

class ArticulationFacade:
    """Provides a unified interface to articulation functionality."""
    
    def validate_courses(self, logic_block: Dict[str, Any], courses: List[str]) -> Dict[str, Any]:
        """Validate if courses satisfy articulation requirements."""
        return validators.is_articulation_satisfied(logic_block, courses)
    
    def render_articulation_logic(self, metadata: Dict[str, Any]) -> str:
        """Render articulation logic in human-readable format."""
        return renderers.render_logic_str(metadata)
    
    def format_binary_response(self, is_satisfied: bool, explanation: str, uc_course: str = "") -> str:
        """Format a binary (yes/no) response."""
        return formatters.render_binary_response(is_satisfied, explanation, uc_course)
    
    # Additional methods wrapping other articulation functionality...
```

#### 4.1.2 Handler Base Class

```python
# handlers/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from llm.models.query import Query, QueryResult
from llm.services.articulation_facade import ArticulationFacade

class QueryHandler(ABC):
    """Base class for all query handlers."""
    
    def __init__(self, document_repository, config):
        self.document_repository = document_repository
        self.config = config
        self.articulation = ArticulationFacade()
    
    @abstractmethod
    def can_handle(self, query: Query) -> bool:
        """Determine if this handler can process the query."""
        pass
    
    @abstractmethod
    def handle(self, query: Query) -> Optional[QueryResult]:
        """Process the query and return results."""
        pass
```

#### 4.1.3 Document Repository

```python
# repositories/document_repository.py
from typing import List, Dict, Any, Optional
from llama_index.core import Document

class DocumentRepository:
    """Provides access to articulation documents."""
    
    def __init__(self, documents=None):
        self.documents = documents or []
        self.uc_course_catalog = set()
        self.ccc_course_catalog = set()
        
    def load_documents(self, path=None):
        """Load documents from the data source."""
        from llm.services.document_service import load_documents
        self.documents = load_documents(path)
        self._build_course_catalogs()
        
    def find_by_uc_course(self, uc_course: str) -> List[Document]:
        """Find documents for a specific UC course."""
        return [
            doc for doc in self.documents
            if doc.metadata.get("uc_course", "").upper() == uc_course.upper()
        ]
    
    def find_by_ccc_courses(self, ccc_courses: List[str]) -> List[Document]:
        """Find documents containing specific CCC courses."""
        return [
            doc for doc in self.documents
            if all(cc.upper() in [c.upper() for c in doc.metadata.get("ccc_courses", [])]
                  for cc in ccc_courses)
        ]
        
    def find_by_group(self, group_id: str) -> List[Document]:
        """Find documents for a specific group."""
        return [
            doc for doc in self.documents
            if doc.metadata.get("group") == group_id
        ]
        
    # Additional search methods...
    
    def _build_course_catalogs(self):
        """Build the UC and CCC course catalogs."""
        from llm.services.query_service import normalize_course_code
        
        self.uc_course_catalog = set()
        self.ccc_course_catalog = set()
        
        for doc in self.documents:
            uc = doc.metadata.get("uc_course")
            if uc:
                self.uc_course_catalog.add(normalize_course_code(uc))
                
            for ccc in doc.metadata.get("ccc_courses", []):
                if ccc:
                    self.ccc_course_catalog.add(normalize_course_code(ccc))
```

#### 4.1.4 Query Model

```python
# models/query.py
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Any, Optional

class QueryType(Enum):
    COURSE_EQUIVALENCY = auto()
    COURSE_VALIDATION = auto()
    GROUP_REQUIREMENT = auto()
    HONORS_REQUIREMENT = auto()
    UNKNOWN = auto()

@dataclass
class Query:
    """Structured representation of a user query."""
    text: str
    filters: Dict[str, Any]
    config: Dict[str, Any]
    query_type: QueryType = QueryType.UNKNOWN
    
@dataclass
class QueryResult:
    """Result of processing a query."""
    raw_response: str
    formatted_response: str
    satisfied: Optional[bool] = None
    matched_docs: List[Any] = None
    metadata: Dict[str, Any] = None
```

#### 4.1.5 Refactored TransferAIEngine

```python
# engine/transfer_engine.py
from typing import Optional, Dict, Any
from llm.models.query import Query, QueryResult
from llm.handlers.base import QueryHandler
from llm.repositories.document_repository import DocumentRepository
from llm.services.query_service import QueryService
from llm.services.prompt_service import PromptService

class TransferAIEngine:
    """Core engine for TransferAI."""
    
    def __init__(self):
        self.config = self._default_config()
        self.document_repository = DocumentRepository()
        self.query_service = QueryService()
        self.prompt_service = PromptService()
        self.handlers = []
        
    def configure(self, **kwargs):
        """Configure the engine with custom settings."""
        for key, value in kwargs.items():
            if key in self.config:
                self.config[key] = value
                
    def load(self):
        """Load data and initialize components."""
        self.document_repository.load_documents()
        self._register_handlers()
        
    def handle_query(self, query_text: str) -> Optional[str]:
        """Process a user query and generate response."""
        if not self.document_repository.documents:
            print("⚠️ No documents loaded. Call load() before querying.")
            return None
            
        try:
            # Parse the query
            filters = self.query_service.extract_filters(
                query_text,
                uc_course_catalog=self.document_repository.uc_course_catalog,
                ccc_course_catalog=self.document_repository.ccc_course_catalog
            )
            
            # Create query object
            query = Query(
                text=query_text,
                filters=filters,
                config=self.config
            )
            
            # Determine query type
            query.query_type = self.query_service.determine_query_type(query)
            
            # Find handler
            handler = self._find_handler(query)
            if not handler:
                return "I'm unable to process this query."
                
            # Process query
            result = handler.handle(query)
            if not result:
                return "No relevant information found."
                
            return result.formatted_response
                
        except Exception as e:
            print(f"[Error] {e}")
            if self.config.get("debug_mode"):
                import traceback
                traceback.print_exc()
            return None
    
    def _register_handlers(self):
        """Register query handlers."""
        from llm.handlers.group_handler import GroupQueryHandler
        from llm.handlers.validation_handler import ValidationQueryHandler
        from llm.handlers.course_handler import CourseEquivalencyHandler
        from llm.handlers.honors_handler import HonorsQueryHandler
        from llm.handlers.fallback_handler import FallbackQueryHandler
        
        self.handlers = [
            GroupQueryHandler(self.document_repository, self.config),
            ValidationQueryHandler(self.document_repository, self.config),
            HonorsQueryHandler(self.document_repository, self.config),
            CourseEquivalencyHandler(self.document_repository, self.config),
            FallbackQueryHandler(self.document_repository, self.config)
        ]
        
    def _find_handler(self, query: Query) -> Optional[QueryHandler]:
        """Find an appropriate handler for the query."""
        for handler in self.handlers:
            if handler.can_handle(query):
                return handler
        return None
        
    def _default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "verbosity": "STANDARD",
            "debug_mode": False,
            "temperature": 0.2,
            "max_tokens": 1000,
            "timeout": 30
        }
```

### 3.2 Migration Strategy

We'll implement a phased migration approach:

#### Phase 1: Foundation (2 weeks)
- Create core models and interfaces
- Implement ArticulationFacade
- Implement DocumentRepository
- Set up QueryService with extracted functionality from query_parser.py
- Create base handler infrastructure

#### Phase 2: Core Handlers (2 weeks)
- Implement ValidationQueryHandler
- Implement GroupQueryHandler
- Implement CourseEquivalencyHandler
- Implement specialized handlers for edge cases

#### Phase 3: Prompt & Template System (1 week)
- Extract templates from prompt_builder.py
- Create PromptService with dynamic template selection

#### Phase 4: Engine Refactoring (1 week)
- Reimplement TransferAIEngine to use new components
- Add query routing logic
- Integrate all services and handlers

#### Phase 5: Testing & Refinement (2 weeks)
- Develop comprehensive test suite
- Run regression tests against all 36 test cases
- Optimize for performance and reliability

## 5. Testing Strategy

### 5.1 Unit Tests
- Test each component in isolation
- Mock dependencies for controlled testing
- Cover all edge cases and special logic

### 5.2 Integration Tests
- Test complete flows through the system
- Verify component integration
- Test various query types

### 5.3 Regression Tests
- Run tests against all 36 standard test cases
- Compare results with known good outputs
- Measure performance and reliability

## 6. Implementation Principles

### 6.1 Keep core articulation module unchanged
The articulation package has been well-refactored already. We'll create an ArticulationFacade to provide a clean interface without changing the existing implementation.

### 6.2 Make incremental changes
Each phase will result in a working system. We'll refactor component by component, ensuring stability throughout.

### 6.3 Focus on clean interfaces
Each component will have a well-defined interface. We'll use dependency injection to allow for easy testing and component replacement.

### 6.4 Prioritize maintainability and extensibility
The new architecture will allow for easy extension to support more majors, institutions, and query types.

## 7. Phased Implementation Schedule

| Phase | Duration | Components | Deliverables |
|-------|----------|------------|--------------|
| 1     | 2 weeks  | Core infrastructure | Models, Repositories, Services interfaces |
| 2     | 2 weeks  | Handlers | Core handlers implementation |
| 3     | 1 week   | Templates | Prompt templates and service |
| 4     | 1 week   | Engine | Refactored engine |
| 5     | 2 weeks  | Testing & Refinement | Complete test suite, optimizations |

## 8. Conclusion

This refactoring plan transforms the TransferAI system from a monolithic architecture to a modular, maintainable, and extensible system. By applying established design patterns and focusing on clean interfaces, we'll create a codebase that is easier to understand, test, and extend.

The separation of concerns will allow developers to work on components independently and make changes with confidence. The final architecture will support the addition of new features and the expansion to more institutions and majors without significant architectural changes. 

## 9. Business Logic Transfer Validation Plan

Initial testing of the refactored architecture has revealed that certain query patterns that worked in the original system are not being properly handled in the new architecture. This section outlines steps to identify and address these gaps to ensure complete functional parity.

### 9.1 Identify Missing Query Capabilities (1 week)

1. **Analyze Original System Logic**
   - Review the monolithic `handle_query` method in the original codebase
   - Document each conditional branch and response generation logic
   - Create inventory of query patterns with expected responses
   - Identify implicit business rules embedded in the code

2. **Implement Side-by-Side Testing**
   - Create test harness to run identical queries through both systems
   - Compare responses to identify discrepancies
   - Categorize and prioritize issues by query type and frequency
   - Focus on "Which courses satisfy X?" pattern failures

### 9.2 Enhance Query Type Detection (1 week)

1. **Improve Query Classification Logic**
   - Update `QueryService.determine_query_type` implementation
   - Add detection for general course equivalency questions
   - Enhance support for implicit group and section references
   - Improve detection of user intent from natural language queries

2. **Expand QueryType Categorization**
   - Add new query types if necessary
   - Create more flexible pattern matching for common query variations
   - Implement confidence scoring for ambiguous queries
   - Add fallback detection for partial information

### 9.3 Update Handler Implementation (2 weeks)

1. **Enhance CourseEquivalencyHandler**
   - Add support for general "Which courses satisfy X?" pattern
   - Implement reverse lookup capability (UC → CCC mapping)
   - Support queries without explicit CCC course mentions
   - Improve handling of course series and prerequisite chains

2. **Refine Other Handlers**
   - Update GroupQueryHandler for implicit group references
   - Enhance ValidationQueryHandler for partial validation scenarios
   - Improve handler selection logic to choose optimal handler
   - Add support for multi-intent queries

### 9.4 Template and Response Generation (1 week)

1. **Compare Template Usage**
   - Identify missing templates from original system
   - Ensure context building includes all necessary information
   - Verify template selection for all query patterns
   - Match response formatting to original system

2. **Final Validation**
   - Run comprehensive test suite against both systems
   - Fix any remaining discrepancies
   - Document enhanced query handling capabilities
   - Provide examples for handling each query pattern

## 10. Implementation Timeline

| Week | Focus | Key Deliverables |
|------|-------|------------------|
| 1    | Query Pattern Analysis | Pattern catalog, test suite, comparison framework |
| 2    | Query Type Detection | Enhanced detection logic, disambiguation support |
| 3    | Course & Group Handlers | Improved course and group query handling |
| 4    | Validation & Selection | Enhanced validation, better handler selection |
| 5    | Templates & Context | Updated templates, better context building |
| 6    | Testing & Documentation | Final validation, comprehensive documentation | 

## 11. Regression Test Bugs Analysis

After running the v1.6 regression test suite, several critical bugs have been identified that need to be fixed to ensure the refactored system provides accurate articulation information.

### 11.1 Summary of Key Issues

| Bug ID | Description | Test Examples | Severity |
|--------|-------------|--------------|----------|
| B-01   | CourseLookupHandler fails to access articulation data correctly | Tests 1-3, 10-11, 17, 19, 21-22, 24, 30, 33 | HIGH |
| B-02   | Inconsistent query type classification | Tests 24, 29, 32 | MEDIUM |
| B-03   | Group query detection not identifying all relevant cases | Test 7 | MEDIUM |
| B-04   | FallbackQueryHandler not providing useful information | Tests 16, 29 | LOW |
| B-05   | HonorsQueryHandler providing incomplete responses | Test 32 | LOW |

### 11.2 Detailed Bug Analysis

#### B-01: CourseLookupHandler Missing Articulation Data

The CourseLookupHandler consistently returns "No articulation for [COURSE]" for courses that demonstrably have articulation options. For example:

- Tests 1-3: Incorrectly reports no articulation for CSE 8A, 8B, and 11 even though tests 4-6 successfully validate these same courses
- Tests 10-11: Reports no articulation for CSE 12 and MATH 18 but test 12 successfully validates MATH 2BH for MATH 18
- Test 17: Reports no articulation for CSE 30 but test 15 correctly validates CIS 21JA and 21JB as partial match for CSE 30
- Test 19: Reports no articulation for MATH 20C but test 18 validates MATH 1CH and 1DH for MATH 20C
- Tests 21-22: Reports no articulation for MATH 20A, MATH 20B, and CSE 30 yet other tests show these have articulation options

**Root Cause Analysis**: 
The CourseLookupHandler is likely not accessing the articulation data correctly. It appears to be using a different data source or query method than the ValidationQueryHandler. Looking at the logs, the same courses return completely different responses depending on which handler processes them, indicating a data access inconsistency.

**Fix Plan**:
1. Audit CourseLookupHandler's data access methods
2. Ensure CourseLookupHandler and ValidationQueryHandler access the same articulation data
3. Implement consistent lookup logic between handlers
4. Add debug logging to verify data access sources
5. Create specific unit tests for course lookup data consistency

#### B-02: Inconsistent Query Type Classification

The query service is inconsistently classifying similar query types:

- Test 24: "What courses count for BILD 1?" is classified as QueryType.UNKNOWN instead of QueryType.COURSE_LOOKUP
- Test 29: "Does BILD 2 require the same BIOL series as BILD 1?" is incorrectly sent to FallbackQueryHandler
- Test 32: Generic honors query routed to HonorsQueryHandler but returns unhelpful response

**Root Cause Analysis**:
The query classification system appears to have too strict pattern matching for certain query types. The heuristics for determining query type don't consistently handle variations in phrasing, leading to inappropriate handler selection.

**Fix Plan**:
1. Review and expand pattern matching in QueryService.determine_query_type()
2. Implement more flexible semantic classification for similar query patterns
3. Add fallback classification that prioritizes COURSE_LOOKUP for course-specific queries
4. Improve confidence scoring to better disambiguate between query types
5. Create comprehensive test suite for query classification

#### B-03: Missing Group Query Detection

Test 7: "If I complete CSE 8A and 8B, is that one full path?" is a group-related query incorrectly routed to CourseLookupHandler, which then fails to provide relevant information.

**Root Cause Analysis**:
The system is not correctly identifying queries that relate to completion paths or groups when they're phrased in certain ways. The term "path" should trigger group-related handling.

**Fix Plan**:
1. Enhance GroupQueryHandler to recognize terms like "path", "track", "sequence", etc.
2. Add detection for queries mentioning multiple related courses
3. Improve handling of completion-oriented questions
4. Create specific test cases for group path identification

#### B-04: FallbackQueryHandler Insufficient Helpfulness

For queries it doesn't understand, the FallbackQueryHandler provides a generic message without attempting to extract useful information:

- Test 16: "Does CSE 15L have any articulation?" gets a generic response
- Test 29: "Does BILD 2 require the same BIOL series as BILD 1?" gets a generic response

**Root Cause Analysis**:
The FallbackQueryHandler isn't attempting to extract partial information or provide context-sensitive guidance.

**Fix Plan**:
1. Implement partial information extraction in FallbackQueryHandler
2. Add course existence verification to provide more helpful responses
3. Create smarter fallback responses based on recognized entities
4. Provide more specific guidance based on query content

#### B-05: HonorsQueryHandler Limited Functionality

Test 32: "Are any honors courses required for the CS transfer path from De Anza to UCSD?" is correctly routed to HonorsQueryHandler but gets an unhelpful response asking for a specific course.

**Root Cause Analysis**:
The HonorsQueryHandler is designed only to answer questions about specific courses, not to provide general information about honors requirements across all courses.

**Fix Plan**:
1. Expand HonorsQueryHandler to support general honors queries
2. Implement aggregation of honors information across course requirements
3. Add specific handling for transfer path queries
4. Create more comprehensive honors requirement reporting

### 11.3 Code Cleanup Recommendations

Based on the regression test findings, several components could be removed or simplified:

1. **query_parser.py**: This component seems to be causing inconsistent classification. Consider replacing with a more robust classifier.

2. **_auto_register_handlers method in transfer_engine.py**: Not properly routing queries to appropriate handlers. Consider implementing explicit handler registration with proper precedence rules.

3. **Redundant matching code**: There appear to be multiple implementations of articulation matching logic causing inconsistent results. Consolidate to a single source of truth.

### 11.4 Fix Implementation Plan

#### Week 1: Critical Data Access Fixes
- Fix B-01: CourseLookupHandler articulation data access
- Document all articulation data access patterns
- Create unit tests for each use case
- Verify all lookup scenarios against test suite

#### Week 2: Query Classification and Routing
- Fix B-02: Improve query classification
- Fix B-03: Enhance group query detection
- Update handler selection logic
- Implement comprehensive test suite for query typing

#### Week 3: Handler Enhancements
- Fix B-04: Improve FallbackQueryHandler
- Fix B-05: Expand HonorsQueryHandler
- Clean up redundant code
- Final integration testing

### 11.5 Conclusion

The regression testing has revealed important issues that need to be addressed to ensure the new architecture provides consistent, accurate responses. Most critically, the data access inconsistency in the CourseLookupHandler needs immediate attention as it affects a large percentage of queries. By systematically addressing these issues, we can preserve the benefits of the refactored architecture while restoring all the functionality present in the original system. 