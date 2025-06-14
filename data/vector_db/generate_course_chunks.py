import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional

from tqdm import tqdm


###############################################################################
# Utility helpers
###############################################################################

def parse_units(units_str: Optional[str]) -> Optional[float]:
    """Convert a catalogue *units* string (e.g. "6 UNITS", "2.5 UNITS") to a
    numeric value.  Returns *None* if the string cannot be parsed.
    """
    if not units_str:
        return None

    match = re.search(r"(\d+(?:\.\d+)?)", units_str)
    if not match:
        return None

    number = float(match.group(1))
    # Return an ``int`` whenever possible to avoid decimals like ``6.0``
    return int(number) if number.is_integer() else number


def build_page_content(course: Dict[str, Any]) -> str:
    """Create a human-readable description chunk for a course."""
    title = course.get("course_title", "").strip()
    description = (course.get("description") or "").strip()

    if description:
        # Build combined text with title prefix (if present).
        separator = " " if not description.startswith(('.', ',', ':', ';')) else ""
        combined = f"{title}:{separator}{description}" if title else description

        # Soft-limit page content to ~120 words (≈100-120 tokens) for better embedding
        # performance, but *only* truncate if the text exceeds 150 words.  This retains
        # almost all courses unchanged while trimming a handful of unusually long ones.
        words = combined.split()
        if len(words) > 150:
            combined = " ".join(words[:120]) + " …"

        return combined

    return title  # fall back to title only


def clean_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys where the value is *None*, empty, or an empty list."""
    return {
        k: v for k, v in raw.items()
        if v not in (None, "", [], {})
    }


def course_to_chunk(course: Dict[str, Any], program_name: str, source_file: str) -> Optional[Dict[str, Any]]:
    """Convert a *course* dict (from the parser output) into a chunk suitable for
    LangChain ingestion."""
    course_id = course.get("course_id")
    if not course_id:
        # Log a warning; still create a chunk using a fallback ID
        print(
            f"[WARN] Course missing course_id – '{course.get('course_title', 'UNKNOWN')}'"
            f" ({source_file})"
        )
        # Fallback: slugified course_code
        fallback_id = re.sub(r"\s+", "-", course.get("course_code", "NO-CODE")).upper()
        course_id = fallback_id

    metadata: Dict[str, Any] = {
        "course_id": course_id,
        "course_code": course.get("course_code"),
        "program_name": program_name,
        "units": parse_units(course.get("units")),
        "transfer_info": course.get("transfer_info"),
        "c_id": course.get("c_id"),
        "cal_getc_area": course.get("cal_getc_area"),
        # same_as is more descriptive than linked_course but spec asks for linked_course
        "linked_course": course.get("same_as"),
        "prerequisites": course.get("prerequisites"),
        "corequisites": course.get("corequisites"),
        "advisory": course.get("advisory"),
        "formerly": course.get("formerly"),
        "special_notes": course.get("special_notes"),
    }

    return {
        "page_content": build_page_content(course),
        "metadata": clean_metadata(metadata),
    }


def process_catalog_dir(input_dir: str) -> List[Dict[str, Any]]:
    """Walk *input_dir* collecting course chunks from every programme JSON file."""
    chunks: List[Dict[str, Any]] = []

    files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
    for filename in tqdm(files, desc="Parsing programme files"):
        filepath = os.path.join(input_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[ERROR] Failed to read {filepath}: {exc}")
            continue

        program_name: str = data.get("program_name", os.path.splitext(filename)[0])
        for course in data.get("courses", []):
            chunk = course_to_chunk(course, program_name, filename)
            if chunk:
                chunks.append(chunk)

    return chunks


def write_jsonl(chunks: List[Dict[str, Any]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")


###############################################################################
# CLI
###############################################################################


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate LangChain-compatible course chunks from parsed catalogue JSON files.")
    parser.add_argument(
        "--input_dir",
        default="../SMC_catalog/parsed_programs",
        help="Directory containing programme JSON files produced by parse_catalog.py",
    )
    parser.add_argument(
        "--output_file",
        default="output/course_chunks.jsonl",
        help="Destination .jsonl file (one JSON object per line).",
    )

    args = parser.parse_args()

    chunks = process_catalog_dir(args.input_dir)
    write_jsonl(chunks, args.output_file)

    print(f"\n✔ Generated {len(chunks):,} course chunks → {args.output_file}")


if __name__ == "__main__":
    main() 