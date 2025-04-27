# TransferAI Module Dependencies

```mermaid
graph TD
    %% Core modules
    main[main.py] --> doc_loader[document_loader.py]
    main --> query_parser[query_parser.py]
    main --> logic_formatter[logic_formatter.py]
    main --> prompt_builder[prompt_builder.py]
    
    %% Secondary dependencies
    query_parser --> spacy[spacy]
    doc_loader --> json[json]
    
    %% External dependencies
    main --> llama_index[LlamaIndex]
    main --> ollama[Ollama]
    main --> huggingface[HuggingFace]
    
    %% Cross-module dependencies
    doc_loader --> LLMDoc[LlamaIndex Document]
    query_parser --> logic_formatter
    
    %% Testing dependencies
    test_runner[test_runner.py] --> main
    tests[tests/] --> logic_formatter
    tests --> query_parser
    tests --> doc_loader
    
    %% Data dependencies
    doc_loader --> rag_data[data/rag_data.json]
    
    %% Function dependencies within logic_formatter
    subgraph logic_formatter_funcs[Logic Formatter Functions]
        is_articulation[is_articulation_satisfied]
        explain_if[explain_if_satisfied]
        render_logic[render_logic_str/v2]
        group_summary[render_group_summary]
        binary_response[render_binary_response]
        combo_validation[render_combo_validation]
        honors_required[is_honors_required]
        detect_redundant[detect_redundant_courses]
    end
    
    explain_if --> is_articulation
    combo_validation --> is_articulation
    binary_response --> explain_if
    group_summary --> render_logic
    
    %% Style definitions
    classDef core fill:#f9f,stroke:#333,stroke-width:2px
    classDef external fill:#bbf,stroke:#333,stroke-width:1px
    classDef data fill:#fdd,stroke:#333,stroke-width:1px
    classDef testing fill:#dfd,stroke:#333,stroke-width:1px
    
    class main,doc_loader,query_parser,logic_formatter,prompt_builder core
    class llama_index,ollama,huggingface,spacy,json external
    class rag_data,LLMDoc data
    class test_runner,tests testing
```

## Module Dependency Description

### Core Module Dependencies

1. **main.py** - The central engine module that depends on:
   - `document_loader.py` for loading articulation data
   - `query_parser.py` for extracting query entities
   - `logic_formatter.py` for processing articulation logic
   - `prompt_builder.py` for generating LLM prompts
   - External libraries: LlamaIndex, Ollama, HuggingFace

2. **document_loader.py** - Depends on:
   - `json` for parsing RAG data
   - LlamaIndex Document model for creating searchable documents

3. **query_parser.py** - Depends on:
   - `spacy` for natural language processing
   - Has some references to logic_formatter functions

4. **logic_formatter.py** - Contains the most internal dependencies:
   - `is_articulation_satisfied` - Core validation function
   - `explain_if_satisfied` - Uses is_articulation_satisfied
   - Various rendering functions that depend on each other

5. **prompt_builder.py** - Relatively independent module with PromptType enum

### Testing Dependencies

- `test_runner.py` depends on the main engine
- Unit tests in the `tests/` directory directly test individual modules

### Data Flow Dependencies

- `document_loader.py` reads from `data/rag_data.json`
- `main.py` builds the vector index from loaded documents
- `query_parser.py` extracts filters from user queries
- `logic_formatter.py` processes documents and logic blocks
- `prompt_builder.py` creates prompts based on processed data

This module structure highlights how `logic_formatter.py` has become a central, complex component with multiple responsibilities that would benefit from refactoring into more focused modules as outlined in the v1.5 roadmap. 