# TransferAI Data Directory

This directory contains all data files for the TransferAI system, including articulation data scraped from ASSIST.org and related resources.

## Directory Structure

After the v2 refactoring, this directory is organized as follows:

```
data/
├── assist_data/                     # Main articulation data
│   └── de_anza_college/             # Organized by source college
│       └── university_of_california_san_diego/  # Target university
│           ├── cse_computer_science_bs__2024_2025.json
│           ├── biology_bs__2024_2025.json
│           └── [other_major_slug]__2024_2025.json
│
├── screenshots/                     # Visual validation of scraped data
│   └── de_anza_college/
│       └── university_of_california_san_diego/
│           ├── cse_computer_science_bs/
│           │   ├── full_page.png    # Complete articulation page
│           │   ├── group_1.png      # Group-level screenshots
│           │   └── group_2.png
│           └── [other_major_slug]/
│
├── raw_html/                        # Archived HTML for debugging/validation
│   └── de_anza_college/
│       └── university_of_california_san_diego/
│           ├── cse_computer_science_bs.html
│           └── [other_major_slug].html
│
├── qa_reports/                      # Quality assurance data
│   └── de_anza_college/
│       └── university_of_california_san_diego/
│           ├── cse_computer_science_bs_qa.json  # Per-major QA report
│           ├── [other_major_slug]_qa.json
│           └── summary.json         # Overall QA summary
│
└── majors/                          # Major lists for each college-university pair
    ├── de_anza_college__university_of_california_san_diego__majors.json
    └── [other_college]__[other_university]__majors.json
```

## Scraper Code Structure

The current monolithic `scrape.py` will be refactored into a modular structure:

```
scripts/
├── run_scraper.py                   # Main entry point with CLI interface
├── scraper/                         # Modular scraper components
│   ├── __init__.py
│   ├── config.py                    # Configuration and constants
│   ├── major_scraper.py             # MajorScraper class
│   ├── group_parser.py              # GroupParser class
│   ├── course_extractor.py          # CourseLogicExtractor class
│   ├── screenshot_manager.py        # ScreenshotManager class
│   ├── html_archiver.py             # Raw HTML archiving
│   └── utils/
│       ├── __init__.py
│       ├── selectors.py             # DOM selectors
│       ├── browser.py               # Browser setup and utilities
│       └── text_processing.py       # Text normalization functions
│
├── validation/                      # Validation components
│   ├── __init__.py
│   ├── schema_validator.py          # JSON schema validation
│   ├── logic_validator.py           # Articulation logic validation
│   └── qa_reporter.py               # QA report generation
│
├── pipelines/                       # Orchestration components
│   ├── __init__.py
│   ├── full_pipeline.py             # End-to-end pipeline
│   └── monitoring.py                # Health monitoring
│
└── tools/                           # Additional utilities
    ├── __init__.py
    ├── dashboard_generator.py       # Audit dashboard generation
    └── data_migration.py            # For migrating old data formats
```

### Key Modules and Classes

#### MajorScraper (major_scraper.py)
Responsible for navigating to specific majors and orchestrating the scraping process:

```python
class MajorScraper:
    def __init__(self, driver, config=None):
        self.driver = driver
        self.config = config or default_config
        self.screenshot_manager = ScreenshotManager(driver)
        self.html_archiver = HTMLArchiver()
    
    def scrape_major(self, college, university, major_name):
        """Scrape a single major's articulation data."""
        # Navigate to major
        # Extract and process data
        # Return structured data
        
    def get_available_majors(self, college, university):
        """Get list of available majors for a college-university pair."""
```

#### GroupParser (group_parser.py)
Parses articulation group containers and their sections:

```python
class GroupParser:
    def __init__(self, driver, screenshot_manager=None):
        self.driver = driver
        self.screenshot_manager = screenshot_manager
        self.course_extractor = CourseLogicExtractor(driver)
    
    def parse_groups(self, group_elements):
        """Parse all articulation groups from a major page."""
        
    def parse_group(self, group_element, group_id):
        """Parse a single articulation group."""
        
    def parse_section(self, section_element, section_id, group_id):
        """Parse a section within a group."""
```

#### CourseLogicExtractor (course_extractor.py)
Extracts course information and logic blocks:

```python
class CourseLogicExtractor:
    def __init__(self, driver):
        self.driver = driver
    
    def extract_course_data(self, course_element):
        """Extract data for a single UC course."""
        
    def extract_logic_block(self, equivalency_element):
        """Extract the logic block for course equivalencies."""
        
    def build_reverse_mappings(self, articulation_data):
        """Create reverse mappings from CCC to UC courses."""
```

## Data File Formats

### Articulation JSON Files

Each major's articulation data is stored in a structured JSON format:

```json
{
  "major": "CSE: Computer Science B.S.",
  "from": "De Anza College",
  "to": "University of California, San Diego",
  "source_url": "https://assist.org/transfer/...",
  "catalog_year": "2024-2025",
  "general_advice": "...",
  "reverse_mappings": {
    "CCC_COURSE_ID": ["UC_COURSE_1", "UC_COURSE_2"],
    "MATH 22": ["CSE 20", "MATH 15A"]
  },
  "groups": [
    {
      "group_id": "1",
      "group_title": "...",
      "group_logic_type": "choose_one_section",
      "sections": [...]
    }
  ],
  "metadata": {
    "scrape_timestamp": "2023-05-10T15:30:45Z",
    "screenshot_paths": {
      "full_page": "screenshots/de_anza_college/university_of_california_san_diego/cse_computer_science_bs/full_page.png",
      "groups": {
        "1": "screenshots/de_anza_college/university_of_california_san_diego/cse_computer_science_bs/group_1.png"
      }
    },
    "raw_html_path": "raw_html/de_anza_college/university_of_california_san_diego/cse_computer_science_bs.html",
    "qa_report_path": "qa_reports/de_anza_college/university_of_california_san_diego/cse_computer_science_bs_qa.json"
  }
}
```

### QA Report Files

Quality assurance reports provide validation metrics for each major:

```json
{
  "major": "CSE: Computer Science B.S.",
  "validation_timestamp": "2023-05-10T15:35:22Z",
  "schema_validation": {
    "is_valid": true,
    "errors": []
  },
  "logic_validation": {
    "is_valid": true,
    "warnings": [],
    "logic_types_found": ["all_required", "choose_one_section", "select_n_courses"],
    "missing_logic_types": []
  },
  "metrics": {
    "group_count": 3,
    "section_count": 5,
    "course_count": 22,
    "no_articulation_count": 2
  },
  "audit_status": {
    "manually_verified": false,
    "verification_date": null,
    "verification_notes": null
  }
}
```

## Working with the Data

### Loading Articulation Data

```python
import json

# Load articulation data for a specific major
major_path = "data/assist_data/de_anza_college/university_of_california_san_diego/cse_computer_science_bs__2024_2025.json"
with open(major_path, "r") as f:
    articulation_data = json.load(f)

# Access reverse mappings
de_anza_course = "MATH 22"
equivalent_ucsd_courses = articulation_data["reverse_mappings"].get(de_anza_course, [])
print(f"{de_anza_course} satisfies: {', '.join(equivalent_ucsd_courses)}")
```

### Finding All Available Majors

```python
import glob
import os

# List all available majors for De Anza → UCSD
pattern = "data/assist_data/de_anza_college/university_of_california_san_diego/*.json"
major_files = glob.glob(pattern)
major_names = [os.path.basename(f).replace("__2024_2025.json", "") for f in major_files]
print(f"Available majors: {major_names}")
```

## Running the Scraper

After refactoring, the scraper can be run using the following commands:

```bash
# Scrape all majors for De Anza → UCSD
python scripts/run_scraper.py --college "De Anza College" --university "University of California, San Diego"

# Scrape specific majors
python scripts/run_scraper.py --college "De Anza College" --university "University of California, San Diego" --majors "CSE: Computer Science B.S.,Biology B.S."

# Run with different options
python scripts/run_scraper.py --college "De Anza College" --university "University of California, San Diego" --batch-size 3 --delay 60 --screenshot-mode "groups-only"

# Run validation only on existing data
python scripts/run_scraper.py --mode validation-only
```

## Data Maintenance

To update or refresh the data:

1. Run the full pipeline: `python scripts/run_scraper.py --college "De Anza College" --university "University of California, San Diego"`
2. For specific majors: `python scripts/run_scraper.py --college "De Anza College" --university "University of California, San Diego" --majors "CSE: Computer Science B.S."`
3. For validation only: `python scripts/validate_data.py --mode validation-only` 