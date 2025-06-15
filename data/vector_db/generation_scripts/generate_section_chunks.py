import os
import json
import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

from tqdm import tqdm

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def infer_time_range(time_str: str) -> str:
    """Return 'morning' if the start time is < 12:00, else 'afternoon'.

    Expects a string like "9:00a.m.-10:25a.m." or "13:30-15:00".
    """
    try:
        start_part = time_str.split("-")[0]
        # remove am/pm markers and periods
        start_part = start_part.replace("a.m.", "").replace("p.m.", "")
        hour_token = start_part.split(":")[0]
        hour = int(hour_token)
    except Exception:
        return "unknown"

    return "morning" if hour < 12 else "afternoon"


def clean_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys where the value is None or empty."""
    return {k: v for k, v in raw.items() if v not in (None, "", [], {})}


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def generate_section_chunks(input_dir: Path) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    json_files: List[Path] = [p for p in input_dir.rglob("*.json") if "extra_refs" not in p.parts]

    for file_path in tqdm(json_files, desc="Scanning programme files"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARN] Could not read {file_path}: {exc}", file=sys.stderr)
            continue

        program_name: str = data.get("program_name", file_path.stem)

        for course in data.get("courses", []):
            course_code = course.get("course_code")
            course_id = course.get("course_id")
            sections = course.get("sections") or []
            if not sections:
                continue

            for section in sections:
                section_number = section.get("section_number")
                modality = section.get("modality", "")
                co_enroll = section.get("co_enrollment_with")

                schedule_entries = section.get("schedule") or []
                if not schedule_entries:
                    print(f"[WARN] {course_code} section {section_number} has no schedule entry.", file=sys.stderr)
                    continue

                # Use first schedule row for summary
                sched = schedule_entries[0]
                days_str = sched.get("days", "")
                days = list(days_str) if days_str else []
                time = sched.get("time", "")
                location = sched.get("location", "")
                instructor = sched.get("instructor", "")

                time_range = infer_time_range(time) if time else "unknown"

                page_content = (
                    f"{course_code} Section {section_number}: "
                    f"{', '.join(days)} {time} at {location}, {modality}, instructor {instructor}."
                )

                meta: Dict[str, Any] = {
                    "program_name": program_name,
                    "course_code": course_code,
                    "course_id": course_id,
                    "section_number": section_number,
                    "days": days,
                    "time_range": time_range,
                    "location": location,
                    "instructor": instructor,
                    "modality": modality,
                }
                if co_enroll:
                    meta["co_enrollment_with"] = co_enroll

                chunks.append({
                    "page_content": page_content,
                    "metadata": clean_metadata(meta),
                })

    return chunks


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate section-level LangChain chunks from parsed catalogue JSON files.")
    parser.add_argument(
        "--input-dir",
        default="data/SMC_catalog/parsed_programs",
        help="Directory containing parsed programme JSON files",
    )
    parser.add_argument(
        "--output-file",
        default="data/vector_db/chunk_output/section_chunks.jsonl",
        help="Destination .jsonl file",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    chunks = generate_section_chunks(input_dir)

    out_path = Path(args.output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    print(f"\n✔ Generated {len(chunks):,} section chunks → {args.output_file}")


if __name__ == "__main__":
    main() 