# TransferAI Data Directory Documentation

## Overview

The `data/` directory contains the structured articulation data used by the TransferAI engine. This data is formatted as JSON and is used for the Retrieval Augmented Generation (RAG) system that powers the articulation logic processing.

## Directory Contents

```
data/
└── rag_data.json    # Structured articulation data from ASSIST.org
```

## RAG Data JSON Format

The `rag_data.json` file contains structured data extracted from ASSIST.org articulation agreements. This is the core data that the TransferAI engine processes to answer student queries about course transfers.

### JSON Schema

The data follows a hierarchical structure that mirrors the organization of articulation agreements on ASSIST.org:

```
{
  "major": String,              // Major name
  "from": String,               // Source institution (CCC)
  "to": String,                 // Destination institution (UC)
  "source_url": String,         // Original ASSIST.org URL
  "catalog_year": String,       // Academic year of the articulation
  "general_advice": String,     // Advisory text about the major/transfer
  "groups": [                   // Array of requirement groups
    {
      "group_id": String,       // Group identifier (e.g., "1", "2")
      "group_title": String,    // Group title (e.g., "Complete A or B")
      "group_logic_type": String, // Logic type (choose_one_section, all_required, select_n_courses)
      "sections": [             // Array of sections within the group
        {
          "section_id": String, // Section identifier (e.g., "A", "B")
          "section_title": String, // Section title
          "uc_courses": [       // Array of UC courses in this section
            {
              "uc_course_id": String,    // UC course code
              "uc_course_title": String, // UC course title
              "units": Number,           // Course units
              "section_id": String,      // Section this course belongs to
              "section_title": String,   // Section title
              "logic_block": {           // Articulation logic for this course
                "type": String,          // Logic type ("OR" or "AND")
                "courses": [             // Array of course options or blocks
                  {
                    "type": String,      // Logic type for this block ("AND" or "OR")
                    "courses": [         // Array of CCC courses
                      {
                        "name": String,          // Full course name with title
                        "honors": Boolean,       // Whether this is an honors course
                        "course_id": String,     // Unique identifier
                        "course_letters": String, // CCC course code
                        "title": String          // CCC course title
                      },
                      // Additional courses if needed for AND logic
                    ]
                  },
                  // Additional options for OR logic
                ]
              }
            },
            // Additional UC courses
          ]
        },
        // Additional sections
      ]
    },
    // Additional groups
  ]
}
```

### Key Concepts

1. **Groups**: Represent major categories of requirements. Each group has a logic type:
   - `choose_one_section`: Student must complete all courses in exactly one section
   - `all_required`: Student must complete all UC courses listed
   - `select_n_courses`: Student must select a specific number of courses

2. **Sections**: Subdivisions within groups, typically labeled A, B, C, etc.
   - In `choose_one_section` groups, each section represents an alternative path
   - In `all_required` groups, sections may be used for organizational purposes

3. **UC Courses**: Individual courses at the destination UC institution
   - Each UC course has one or more articulation options from the CCC

4. **Logic Blocks**: Define how CCC courses satisfy UC requirements
   - `type`: "OR" (any one option) or "AND" (all courses required)
   - `courses`: Array of course options or nested blocks
   - Can represent complex logic like "(Course A AND Course B) OR Course C"

5. **CCC Courses**: Individual courses at the community college
   - `honors`: Boolean flag for honors courses
   - `course_letters`: The course code (e.g., "CIS 22A")

6. **No Articulation**: When a UC course has no equivalent at the CCC
   - Represented by a special flag in the logic block
   - Indicates the course must be completed at the UC

### Example Logic Structures

#### Simple Equivalency (One-to-One)
```json
"logic_block": {
  "type": "OR",
  "courses": [
    {
      "type": "AND",
      "courses": [
        {
          "name": "MATH 1A Calculus",
          "honors": false,
          "course_letters": "MATH 1A",
          "title": "Calculus"
        }
      ]
    }
  ]
}
```

#### Multiple Options (OR Logic)
```json
"logic_block": {
  "type": "OR",
  "courses": [
    {
      "type": "AND",
      "courses": [
        {
          "course_letters": "CIS 22A",
          "title": "Beginning Programming Methodologies in C++"
        }
      ]
    },
    {
      "type": "AND",
      "courses": [
        {
          "course_letters": "CIS 36A",
          "title": "Introduction to Computer Programming Using Java"
        }
      ]
    }
  ]
}
```

#### Sequence Requirement (AND Logic)
```json
"logic_block": {
  "type": "OR",
  "courses": [
    {
      "type": "AND",
      "courses": [
        {
          "course_letters": "MATH 1C",
          "title": "Multivariable Calculus"
        },
        {
          "course_letters": "MATH 1D",
          "title": "Differential Equations"
        }
      ]
    }
  ]
}
```

#### Complex Logic (OR of ANDs)
```json
"logic_block": {
  "type": "OR",
  "courses": [
    {
      "type": "AND",
      "courses": [
        {
          "course_letters": "CIS 35A",
          "title": "Java Programming"
        }
      ]
    },
    {
      "type": "AND",
      "courses": [
        {
          "course_letters": "CIS 36A",
          "title": "Introduction to Computer Programming Using Java"
        },
        {
          "course_letters": "CIS 36B",
          "title": "Intermediate Problem Solving in Java"
        }
      ]
    }
  ]
}
```

#### No Articulation
```json
"logic_block": {
  "type": "OR",
  "courses": [
    {
      "name": "No Course Articulated",
      "honors": false,
      "course_letters": "N/A",
      "title": "No Course Articulated"
    }
  ],
  "no_articulation": true
}
```

## Data Processing

The TransferAI engine processes this data through several steps:

1. **Loading**: The `document_loader.py` script loads the RAG data
2. **Flattening**: Complex nested structures are flattened into documents
3. **Enrichment**: Metadata is added to each document for better retrieval
4. **Indexing**: Documents are indexed for vector search
5. **Retrieval**: When a query is received, relevant documents are retrieved
6. **Logic Formatting**: The `logic_formatter.py` script renders the logic into human-readable text

## Extending the Data

To add new articulation agreements:

1. Scrape new data from ASSIST.org using the scraper in the parent `data/` directory
2. Process the data into the RAG format
3. Replace or add to the `rag_data.json` file
4. Update the LLM engine as needed to handle any new patterns

## Data Quality Considerations

When working with the articulation data, consider:

1. **Completeness**: Ensure all UC courses have their articulation logic
2. **Correctness**: Validate that the logic accurately reflects ASSIST.org
3. **Currency**: Update data to match the current academic year
4. **Consistency**: Maintain consistent structure across different agreements

The TransferAI engine relies on this data being accurate and complete to provide reliable answers to student queries. 