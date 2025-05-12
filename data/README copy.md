# TransferAI ASSIST V2 Scraper

This module provides utilities for downloading and processing ASSIST articulation agreement data directly from the ASSIST.org API. This is an improved version of our previous web scraper approach, now using direct API access for more reliable and structured data.

## Features

- Download articulation agreements directly from ASSIST.org API
- Transform raw ASSIST JSON to TransferAI's standardized RAG format
- Preserve course articulation logic and requirements
- Extract course notes, honors designations, and other metadata
- Clean formatting of general advice and instructions

## Files

- `assist_json_downloader.py` - Downloads articulation agreements from ASSIST.org API
- `assist_to_rag.py` - Transforms ASSIST API JSON into our standardized RAG format
- `main.py` - Command-line interface for bulk downloading and processing

## Usage

### Downloading a single agreement

```python
from assist_json_downloader import download_agreement_json
from pathlib import Path

# Parameters for a specific agreement
year_id = "75"  # 2024-2025
sending_id = "113"  # De Anza College
receiving_id = "7"  # UC San Diego
major_key = "0a3e674e-b9e8-4340-6726-08dca807bc66"  # CS major
output_dir = Path("./json")

# Download the agreement
json_file = download_agreement_json(
    year_id, 
    sending_id, 
    receiving_id, 
    major_key, 
    output_dir
)
```

### Converting ASSIST JSON to RAG format

```python
from assist_to_rag import process_assist_json_file, save_rag_json

# Convert ASSIST JSON to RAG format
input_file = "json/De Anza College_to_University of California, San Diego_CSE:_Computer_Science_BS.json"
output_file = "rag/cse_cs_bs.json"
major_key = "0a3e674e-b9e8-4340-6726-08dca807bc66"  # For accurate source URL generation

rag_data = process_assist_json_file(input_file, major_key=major_key)
save_rag_json(rag_data, output_file)
```

### Command Line Usage

```bash
# Download an agreement
python main.py download --year 75 --sending 113 --receiving 7 --major 0a3e674e-b9e8-4340-6726-08dca807bc66

# Convert to RAG format 
python main.py convert --input json/De\ Anza\ College_to_University\ of\ California\,\ San\ Diego_CSE\:_Computer_Science_BS.json --output rag/cse_cs.json --major-key 0a3e674e-b9e8-4340-6726-08dca807bc66

# Batch process multiple agreements
python main.py batch --config batch_config.json
```

### Batch Configuration Format

For batch processing, create a JSON file like this:

```json
{
  "operations": [
    {
      "type": "download",
      "year_id": "75",
      "sending_id": "113",
      "receiving_id": "7",
      "major_key": "0a3e674e-b9e8-4340-6726-08dca807bc66",
      "output_dir": "json"
    },
    {
      "type": "convert",
      "input_file": "json/De Anza College_to_University of California, San Diego_CSE:_Computer_Science_BS.json",
      "output_file": "rag_output/de_anza_ucsd_cs_bs.json",
      "major_key": "0a3e674e-b9e8-4340-6726-08dca807bc66"
    }
  ]
}
```

## Data Structures

### RAG Format Structure

```
{
  "major": "Major name",
  "from": "Sending institution",
  "to": "Receiving institution",
  "source_url": "URL to the agreement",
  "catalog_year": "Academic year",
  "general_advice": "General advice text",
  "groups": [
    {
      "group_id": "1",
      "group_title": "Group instruction",
      "group_logic_type": "choose_one_section|all_required|select_n_courses",
      "sections": [
        {
          "section_id": "A",
          "section_title": "Section title",
          "section_logic_type": "all_required|select_n_courses",
          "uc_courses": [
            {
              "uc_course_id": "Course code",
              "uc_course_title": "Course title",
              "section_id": "Section ID",
              "section_title": "Section title",
              "logic_block": {
                "type": "OR",
                "courses": [
                  {
                    "type": "AND",
                    "courses": [
                      {
                        "name": "Course name",
                        "honors": true|false,
                        "course_id": "Hashed ID",
                        "course_letters": "Course code",
                        "title": "Course title"
                      }
                    ]
                  }
                ]
              },
              "units": 4.0,
              "uc_notes": ["Note 1", "Note 2"],
              "ccc_notes": ["Note 1", "Note 2"]
            }
          ]
        }
      ]
    }
  ]
}
```

## Notes

- The ASSIST API endpoints were reverse-engineered from the ASSIST.org website
- Institution IDs and major keys can be found by inspecting network traffic on ASSIST.org
- HTML content in the API responses is cleaned and formatted for readability
- RAG format preserves the logical structure of articulation requirements 