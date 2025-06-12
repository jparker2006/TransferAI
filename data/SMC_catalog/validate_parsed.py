import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple

BASE_DIR = Path(__file__).parent
CATALOG_PATH = BASE_DIR / "catalog_cleaned.txt"
PARSED_DIR = BASE_DIR / "parsed_programs"
REPORT_PATH = BASE_DIR / "validation_report.txt"

COURSE_HEADER_RE = re.compile(r'^((?:[A-Z]+\s+)?[A-Z]+(?:\s+ST)?\s+[A-Z]*\d+[A-Z]*)\s*,', re.MULTILINE)
UNITS_RE = re.compile(r'\b\d+(?:\.\d+)?\s+UNITS?\b', re.IGNORECASE)

ALLOWED_EMPTY_DESCRIPTION_PATTERNS = [
    re.compile(r'^Please see "Independent Studies" section\.$'),
    re.compile(r'^Please see "Internships" section\.$'),
]

REQUIRED_COURSE_FIELDS = [
    "course_code",
    "course_title",
    "units",
    "description",
]

SKIP_PROGRAM_FILES = {"independent_studies.json", "internships.json"}


def extract_catalog_course_codes() -> List[str]:
    """Return course codes that have an accompanying units declaration within the next 5 lines.
    This skips headers like support courses (e.g. MATH 3C) that do not list their own units."""
    lines = CATALOG_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    codes: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = COURSE_HEADER_RE.match(line)
        if m:
            code = m.group(1).strip()
            # look ahead up to 5 lines for units pattern
            window = "\n".join(lines[i:i+6])
            if UNITS_RE.search(window):
                codes.append(code)
            i += 1
        else:
            i += 1
    return sorted(set(codes))


def extract_json_course_codes() -> Tuple[List[str], Dict[str, Path]]:
    codes: List[str] = []
    code_to_file: Dict[str, Path] = {}
    for file_path in PARSED_DIR.glob("*.json"):
        if file_path.name in SKIP_PROGRAM_FILES:
            continue
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for course in data.get("courses", []):
            code = course.get("course_code")
            if code:
                codes.append(code)
                code_to_file[code] = file_path
    codes = sorted(set(codes))
    return codes, code_to_file


def is_placeholder_description(desc: str) -> bool:
    desc = desc.strip()
    return any(pat.match(desc) for pat in ALLOWED_EMPTY_DESCRIPTION_PATTERNS)


def validate_course(course: Dict) -> List[str]:
    errors = []
    code = course.get("course_code", "<unknown>")
    # required fields
    for field in REQUIRED_COURSE_FIELDS:
        if field not in course:
            errors.append(f"[{code}] Missing field '{field}'")
    # non-empty description (unless placeholder)
    desc = course.get("description", "").strip()
    if not desc:
        errors.append(f"[{code}] Empty description")
    elif is_placeholder_description(desc):
        # allowed placeholder – treat as OK
        pass
    else:
        # should start with capital letter, no leading whitespace
        if not desc[0].isupper():
            errors.append(f"[{code}] Description does not start with capital letter")
    # check special_notes type
    if course.get("special_notes") is not None and not isinstance(course["special_notes"], list):
        errors.append(f"[{code}] special_notes should be a list but is {type(course['special_notes']).__name__}")
    # field newline checks
    for f in ["prerequisites", "advisory", "description", "prerequisite_notes", "advisory_notes"]:
        val = course.get(f)
        if isinstance(val, str) and "\n" in val:
            errors.append(f"[{code}] Field '{f}' contains newline characters")
    return errors


def main():
    catalog_codes = extract_catalog_course_codes()
    json_codes, code_to_file = extract_json_course_codes()

    missing = sorted(set(catalog_codes) - set(json_codes))
    extras = sorted(set(json_codes) - set(catalog_codes))

    validation_errors: List[str] = []
    for file_path in PARSED_DIR.glob("*.json"):
        if file_path.name in SKIP_PROGRAM_FILES:
            continue
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for course in data.get("courses", []):
            validation_errors.extend(validate_course(course))

    # Write report
    with REPORT_PATH.open("w", encoding="utf-8") as rep:
        rep.write("=== COURSE COVERAGE ===\n")
        rep.write(f"Catalog course count : {len(catalog_codes)}\n")
        rep.write(f"JSON course count    : {len(json_codes)} (excluding skipped programs)\n")
        rep.write(f"Missing in JSON      : {len(missing)}\n")
        for m in missing:
            rep.write(f"  - {m}\n")
        rep.write(f"Extra in JSON        : {len(extras)}\n")
        for e in extras:
            rep.write(f"  - {e}\n")
        rep.write("\n=== FIELD VALIDATION ERRORS ===\n")
        rep.write(f"Total errors: {len(validation_errors)}\n")
        for err in validation_errors:
            rep.write(f"  - {err}\n")

    print("Validation complete. Report written to", REPORT_PATH)


if __name__ == "__main__":
    main() 