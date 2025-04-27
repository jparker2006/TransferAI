# TransferAI Architecture Diagram

```mermaid
graph TD
    User[User Query] --> Main[TransferAIEngine]
    
    %% Main components
    subgraph Core["Core Components"]
        Main --> QP[Query Parser]
        Main --> DL[Document Loader]
        Main --> LF[Logic Formatter]
        Main --> PB[Prompt Builder]
        Main --> LLM[LLM Service]
    end
    
    %% Data flow
    DL --> |Loads| RD[(RAG Data)]
    DL --> |Creates| IDX[(Vector Index)]
    
    QP --> |Extracts| Filters[Filters & Entities]
    Main --> |Queries| IDX
    IDX --> |Returns| Docs[Matching Documents]
    
    Docs --> LF
    LF --> |Processes| Logic[Articulation Logic]
    Logic --> |Validates| Valid[Validation Results]
    
    Valid --> PB
    PB --> |Builds| Prompt[LLM Prompt]
    Prompt --> LLM
    LLM --> |Generates| Response[User Response]
    
    %% Testing components
    subgraph Testing["Testing Framework"]
        TR[Test Runner]
        Tests[Unit Tests]
        TR --> |Runs| Tests
    end
    
    %% Data models
    subgraph Models["Data Models"]
        LBM[Logic Block]
        UCM[UC Course]
        CCCM[CCC Course]
        GM[Group]
        SM[Section]
    end
    
    %% Function relationships
    subgraph QueryParsing["Query Parsing Functions"]
        EF[extract_filters]
        NC[normalize_course_code]
        EM[extract_matches]
    end
    
    subgraph LogicFormatting["Logic Formatting Functions"]
        IAS[is_articulation_satisfied]
        EIS[explain_if_satisfied]
        RL[render_logic]
        RGS[render_group_summary]
        DRC[detect_redundant_courses]
        IHR[is_honors_required]
    end
    
    %% Integration points
    Main --> |Uses| Ollama[Ollama LLM]
    Main --> |Uses| HF[HuggingFace Embeddings]
    
    %% Component descriptions
    classDef core fill:#ddf,stroke:#33f,stroke-width:2px
    classDef data fill:#fdd,stroke:#f33,stroke-width:2px
    classDef function fill:#dfd,stroke:#3f3,stroke-width:2px
    classDef external fill:#ddd,stroke:#333,stroke-width:2px
    
    class Core,QueryParsing,LogicFormatting core
    class RD,IDX,Docs,Logic,Valid,Prompt,Models data
    class EF,NC,EM,IAS,EIS,RL,RGS,DRC,IHR function
    class Ollama,HF external
```

## Architecture Flow Description

1. The system starts with a user query like "What De Anza courses satisfy CSE 8A at UCSD?"
2. The `TransferAIEngine` in `main.py` receives and processes this query
3. `query_parser.py` extracts relevant filters and entities (course codes, group references)
4. The system queries the vector index to retrieve matching documents
5. For each document, `logic_formatter.py` processes the articulation logic
6. Validation functions check if specific courses satisfy requirements
7. `prompt_builder.py` constructs an appropriate prompt for the LLM
8. The LLM (via Ollama) generates the final response

The system's modular design allows for targeted improvements in each component while maintaining overall functionality. The most complex component is `logic_formatter.py`, which handles the critical logic processing and validation logic. 