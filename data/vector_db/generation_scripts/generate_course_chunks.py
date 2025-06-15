import argparse
import json
import os
import re
import statistics
from typing import Any, Dict, List, Optional

from tqdm import tqdm

# Optional dependency – during local development LangChain may not be installed.
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore
except ImportError:  # pragma: no cover – fallback if LangChain missing
    RecursiveCharacterTextSplitter = None  # type: ignore

# Hard character cap per chunk
HARD_CHAR_LIMIT = 900

# Collect warnings when overlap would exceed HARD_CHAR_LIMIT
SKIPPED_OVERLAP: List[str] = []

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


def clean_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Remove keys where the value is *None*, empty, or an empty list."""
    return {k: v for k, v in raw.items() if v not in (None, "", [], {})}


def split_description(text: str, context: str = "") -> List[str]:
    """Split *text* into semantically coherent parts using LangChain's splitter.

    Falls back to a naive split on double newlines if LangChain is not available.
    """

    if not text:
        return [""]

    # Split into sentences first (very naive). Keeps punctuation.
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: List[str] = []
    buf: List[str] = []
    current_len = 0
    for sent in sentences:
        if not sent:
            continue
        # +1 for space join later
        if current_len + len(sent) + 1 > 400 and buf:
            chunks.append(" ".join(buf).strip())
            buf, current_len = [], 0
        buf.append(sent)
        current_len += len(sent) + 1

    if buf:
        chunks.append(" ".join(buf).strip())

    # Add one full-sentence overlap between consecutive chunks (hard cap 500 chars)
    if len(chunks) > 1:
        overlapped: List[str] = [chunks[0]]
        sentence_tail_pattern = re.compile(r"(?<=[.!?])\s+")
        for i in range(1, len(chunks)):
            prev_tail_sentence = sentence_tail_pattern.split(chunks[i - 1])[-1].strip()

            if (not chunks[i].startswith(prev_tail_sentence)
                    and len(prev_tail_sentence) + 1 + len(chunks[i]) <= HARD_CHAR_LIMIT):
                new_chunk = f"{prev_tail_sentence} {chunks[i]}".strip()
            else:
                # Overlap would exceed hard limit; skip and record warning
                if context:
                    SKIPPED_OVERLAP.append(context)
                new_chunk = chunks[i]

            overlapped.append(new_chunk)

        chunks = overlapped

    return chunks


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

    for root, dirs, files in os.walk(input_dir):
        # skip extra_refs folders
        if 'extra_refs' in root.split(os.sep):
            continue

        for filename in files:
            if not filename.endswith('.json'):
                continue

            filepath = os.path.join(root, filename)
            rel_display = os.path.relpath(filepath, input_dir)

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:
                print(f"[ERROR] Failed to read {filepath}: {exc}")
                continue

            program_name: str = data.get("program_name", os.path.splitext(filename)[0])
            for course in data.get("courses", []):
                description = (course.get("description") or "").strip()
                parts = split_description(description, context=f"{course.get('course_code')} in {filename}") if description else [""]

                total_chunks = len(parts)
                for idx, part in enumerate(parts):
                    # Build metadata
                    course_id = course.get("course_id") or re.sub(r"\s+", "-", course.get("course_code", "NO-CODE")).upper()
                    metadata: Dict[str, Any] = {
                        "course_id": course_id,
                        "course_code": course.get("course_code"),
                        "program_name": program_name,
                        "units": parse_units(course.get("units")),
                        "transfer_info": course.get("transfer_info"),
                        "c_id": course.get("c_id"),
                        "cal_getc_area": course.get("cal_getc_area"),
                        "linked_course": course.get("same_as"),
                        "prerequisites": course.get("prerequisites"),
                        "corequisites": course.get("corequisites"),
                        "advisory": course.get("advisory"),
                        "formerly": course.get("formerly"),
                        "special_notes": course.get("special_notes"),
                        "chunk_index": idx + 1,
                        "total_chunks": total_chunks,
                    }

                    chunks.append({
                        "page_content": part,
                        "metadata": clean_metadata(metadata),
                    })

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
        default="data/SMC_catalog/parsed_programs",
        help="Directory containing programme JSON files produced by parse_catalog.py",
    )
    parser.add_argument(
        "--output_file",
        default="data/vector_db/chunk_output/course_chunks.jsonl",
        help="Destination .jsonl file (one JSON object per line).",
    )

    args = parser.parse_args()

    chunks = process_catalog_dir(args.input_dir)
    write_jsonl(chunks, args.output_file)

    # Print summary statistics for chunk lengths
    lengths = [len(c["page_content"]) for c in chunks]
    if lengths:
        mean_len = statistics.mean(lengths)
        median_len = statistics.median(lengths)
        std_len = statistics.pstdev(lengths) if len(lengths) > 1 else 0.0
        print("\nChunk length statistics (characters):")
        print(f"  min   : {min(lengths)}")
        print(f"  max   : {max(lengths)}")
        print(f"  mean  : {mean_len:.1f}")
        print(f"  median: {median_len}")
        print(f"  stdev : {std_len:.1f}")

    if SKIPPED_OVERLAP:
        print("\n[WARN] Overlap skipped (would exceed HARD_CHAR_LIMIT) for the following chunks:")
        for ctx in SKIPPED_OVERLAP:
            print(f"  • {ctx}")

    print(f"\n✔ Generated {len(chunks):,} course chunks → {args.output_file}")


if __name__ == "__main__":
    main() 