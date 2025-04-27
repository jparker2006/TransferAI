# TransferAI Logic Processing Flowchart

```mermaid
flowchart TD
    Start([User Query]) --> QueryParser[Query Parser]
    
    QueryParser --> |Extract Entities| FilterDec{Query Type?}
    
    FilterDec -->|Single UC Course| UC[UC Course Query]
    FilterDec -->|Group Request| Group[Group Query]
    FilterDec -->|Validation| Valid[Validation Query]
    FilterDec -->|Multiple UC| Multi[Multi-Course Query]
    
    UC --> DocRetrieval[Retrieve Matching Documents]
    Group --> GroupRetrieval[Retrieve Group Documents]
    Valid --> ValidRetrieval[Retrieve Logic for Validation]
    Multi --> MultiProcess[Process Each UC Course]
    
    DocRetrieval --> RenderLogic[Render Logic Block]
    GroupRetrieval --> GroupSummary[Render Group Summary]
    ValidRetrieval --> Validation[Run Validation Logic]
    MultiProcess --> MultiResponse[Combine Individual Responses]
    
    RenderLogic --> |Format Options| CourseResponse[Course Options Response]
    GroupSummary --> |Format Requirements| GroupResponse[Group Requirements Response]
    Validation --> |Check Satisfaction| ValidationResult{Is Satisfied?}
    MultiResponse --> FinalMulti[Multi-Course Response]
    
    ValidationResult -->|Yes| YesResponse[Format "Yes" Response]
    ValidationResult -->|No| NoResponse[Format "No" Response with Explanation]
    ValidationResult -->|Partial| PartialResponse[Format Partial Match Response]
    
    YesResponse --> BinaryResponse[Binary Response]
    NoResponse --> BinaryResponse
    PartialResponse --> BinaryResponse
    
    CourseResponse --> PromptBuilder[Prompt Builder]
    GroupResponse --> PromptBuilder
    BinaryResponse --> PromptBuilder
    FinalMulti --> PromptBuilder
    
    PromptBuilder --> |Generate Prompt| LLM[LLM Processing]
    LLM --> FinalResponse[Final User Response]
    
    subgraph Logic_Processing [Logic Processing Details]
        direction TB
        LogicBlock[Logic Block Input] --> TypeCheck{Block Type?}
        
        TypeCheck -->|OR Block| ProcessOR[Process Each Option]
        TypeCheck -->|AND Block| ProcessAND[Process All Requirements]
        
        ProcessOR --> OrCheck{Any Option Satisfied?}
        ProcessAND --> AndCheck{All Requirements Satisfied?}
        
        OrCheck -->|Yes| OrSatisfied[Option Satisfied]
        OrCheck -->|No| OrNotSatisfied[No Option Satisfied]
        
        AndCheck -->|Yes| AndSatisfied[All Satisfied]
        AndCheck -->|No| AndNotSatisfied[Missing Requirements]
        
        OrSatisfied --> RecurseCheck{More Nesting?}
        AndSatisfied --> RecurseCheck
        
        RecurseCheck -->|Yes| Recurse[Process Nested Blocks]
        RecurseCheck -->|No| Return[Return Result]
        
        OrNotSatisfied --> ReturnNot[Return Not Satisfied]
        AndNotSatisfied --> ReturnPartial[Return Partial Match]
        
        Recurse --> LogicBlock
    end
    
    Validation --> Logic_Processing
```

## Logic Processing Flowchart Description

### Query Flow

1. **Query Analysis**:
   - The system receives a user query and extracts relevant entities
   - Based on the detected entities, it classifies the query type

2. **Document Retrieval**:
   - Different retrieval strategies are used based on query type
   - For UC course queries, documents matching that course are retrieved
   - For group queries, all documents in the group are collected
   - For validation queries, logic blocks for specific courses are retrieved

3. **Logic Processing**:
   - The core logic processing (detailed in the subgraph) happens here
   - For validation queries, the system checks if selected courses satisfy requirements
   - For course queries, the system formats available articulation options
   - For group queries, the system summarizes all group requirements

4. **Response Generation**:
   - The processed logic is formatted into appropriate response templates
   - Binary (yes/no) responses include explanations
   - Course option responses list all valid articulation paths
   - Group summaries provide comprehensive requirement overviews

### Logic Processing Details

The core logic processing (shown in the subgraph) involves:

1. **Logic Block Analysis**:
   - Analyzing the type of logic block (OR vs AND)
   - For OR blocks, any one option needs to be satisfied
   - For AND blocks, all requirements must be satisfied

2. **Recursive Processing**:
   - Logic blocks can be deeply nested (e.g., OR of ANDs, AND of ORs)
   - The system recursively processes each level
   - Results propagate up through the logic tree

3. **Validation Results**:
   - Fully satisfied, partially satisfied, or not satisfied
   - For partial matches, missing requirements are identified
   - Redundant course selections are detected

This flowchart highlights the complexity of the logic processing system, which must handle nested boolean logic while maintaining accurate validation results. The recursive nature of the processing is a key consideration for optimizations in the v1.5 roadmap. 