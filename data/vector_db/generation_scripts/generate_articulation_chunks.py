import argparse
import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Tuple

import re
import statistics
import urllib.parse
from datetime import datetime

from tqdm import tqdm

# Optional dependency – during local development LangChain may not be installed.
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore
except ImportError:  # pragma: no cover – fallback if LangChain missing
    RecursiveCharacterTextSplitter = None  # type: ignore

###############################################################################
# Text splitting and course parsing helpers (single source-of-truth)
###############################################################################

def split_sentences(text: str, max_chars: int = 400, overlap_chars: int = 50) -> List[str]:
    """Split *text* into sentence-aligned chunks suitable for embedding.

    When LangChain is available we defer to ``RecursiveCharacterTextSplitter`` to
    handle smart sentence segmentation with overlaps. Otherwise we fall back to
    a simple regex-based splitter that maintains paragraph integrity.
    """

    text = text.strip()
    if not text:
        return [""]

    if RecursiveCharacterTextSplitter is not None:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_chars,
            chunk_overlap=overlap_chars,
            separators=["\n\n", "\n", ". ", "! ", "? "],
        )
        parts = [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]
        return parts or [text]

    # --- fallback
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: List[str] = []
    buf: List[str] = []
    length = 0
    for sent in sentences:
        if not sent:
            continue
        if length + len(sent) + 1 > max_chars and buf:
            chunks.append(" ".join(buf).strip())
            buf, length = [], 0
        buf.append(sent)
        length += len(sent) + 1
    if buf:
        chunks.append(" ".join(buf).strip())
    return chunks


# Regex helpers for extracting course code / title / units

COURSE_PATTERN = re.compile(
    r"(?P<code>[A-Z]{2,}\s?\d+[A-Z]?)\s*:\s*(?P<title>.*?)\s*\((?P<units>\d+(?:\.\d+)?)\s*units?\)",
    flags=re.IGNORECASE | re.DOTALL,
)

UNITS_PATTERN = re.compile(r"\((\d+(?:\.\d+)?)\s*units?\)", flags=re.IGNORECASE)


def parse_course_text(text: str) -> Dict[str, Optional[str]]:
    """Extract structured info from *text* like ``MATH 31: Calculus I (5.00 units)``.

    Returns ``course_code``, ``course_title``, and ``units`` keys – any may be
    ``None`` if they cannot be parsed.
    """

    cleaned = " ".join(text.replace("\n", " ").split())

    match = COURSE_PATTERN.search(cleaned)
    if match:
        try:
            units_raw = float(match.group("units"))
            units_val: Optional[float] = int(units_raw) if units_raw.is_integer() else units_raw
        except Exception:
            units_val = None

        return {
            "course_code": match.group("code").strip(),
            "course_title": match.group("title").strip(),
            "units": units_val,
        }

    # Fallback – only units
    units_val2: Optional[float] = None
    um = UNITS_PATTERN.search(cleaned)
    if um:
        try:
            val = float(um.group(1))
            units_val2 = int(val) if val.is_integer() else val
        except Exception:
            pass

    return {"course_code": None, "course_title": None, "units": units_val2}


###############################################################################
# Helper utilities
###############################################################################

def clean_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of *raw* without ``None``, empty strings, lists, or dicts."""
    return {k: v for k, v in raw.items() if v not in (None, "", [], {})}


def clean_chunk_text(text: str) -> str:
    """Remove leading punctuation artifacts (e.g., stray periods) and trim whitespace."""
    return text.lstrip(". ").strip()


def extract_major_type(title: str) -> Optional[str]:
    """Return major type token such as 'B.A.', 'B.S.', 'Minor', etc."""
    if not title:
        return None
    match = re.search(r"\b(BA|B\.A\.|BS|B\.S\.|Minor|Certificate|AA-T|AS-T)\b", title, re.IGNORECASE)
    if match:
        return match.group(0).upper()
    return None


def extract_keywords(texts: List[str]) -> List[str]:
    """Return a list of domain-specific keywords found in *texts*."""
    tokens: Set[str] = set()
    joined = " ".join(texts).lower()
    for kw in ASSIST_KEYWORDS:
        if kw.lower() in joined:
            tokens.add(kw)
    return sorted(tokens)


def calculate_completeness(meta: Dict[str, Any]) -> float:
    """Very naive completeness metric: proportion of non-empty metadata fields."""
    total = len(meta)
    non_empty = sum(1 for v in meta.values() if v not in (None, "", [], {}))
    return round(non_empty / total, 2) if total else 0.0


def validate_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Run simple quality checks, print warnings if failures detected."""
    for idx, ch in enumerate(chunks):
        txt = ch.get("page_content", "")
        meta = ch.get("metadata", {})
        if txt.startswith('.'):
            print(f"[WARN] Chunk {idx} starts with period.")
        if len(txt) < GENERAL_INFO_MIN:
            print(f"[WARN] Chunk {idx} shorter than minimum length ({len(txt)} chars).")
        if meta.get("type") == "requirement":
            # Quick presence check for course info
            if "course_mappings" not in meta and "receiving_course_text" not in meta:
                print(f"[WARN] Requirement chunk {idx} missing course info.")


def enrich_relationships(chunks: List[Dict[str, Any]]) -> None:
    """Populate shared_courses and alternative_paths in chunk metadata."""
    # Map course_code -> set of parent_major_id
    course_map: Dict[str, Set[str]] = {}
    for ch in chunks:
        meta = ch["metadata"]
        if meta.get("type") != "requirement":
            continue
        parent_id = meta.get("parent_major_id")
        for code in meta.get("transferable_courses", []):
            if not code:
                continue
            course_map.setdefault(code, set()).add(parent_id)

    for ch in chunks:
        meta = ch["metadata"]
        if meta.get("type") != "requirement":
            continue
        parent_id = meta.get("parent_major_id")
        shared = [code for code in meta.get("transferable_courses", []) if len(course_map.get(code, set())) > 1]
        meta["shared_courses"] = shared
        alt_paths = sorted({mid for code in shared for mid in course_map.get(code, set()) if mid != parent_id})
        meta["alternative_paths"] = alt_paths


def build_general_info_chunks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate *general_info* chunks from a single articulation JSON *data*.

    Splits long paragraphs into sentence‐aligned sub-chunks and annotates each
    with ``chunk_index`` / ``total_chunks`` metadata fields. Uses content-aware
    grouping to reach 150–800 character windows and respects *PRESERVE_PATTERNS*."""

    base: Dict[str, Any] = {
        "source_url": data.get("source_url"),
        "agreement_title": data.get("agreement_title"),
        "academic_year": data.get("academic_year"),
        "sending_institution": data.get("sending_institution"),
        "receiving_institution": data.get("receiving_institution"),
        "url_metadata": parse_assist_url(data.get("source_url", "")),
        "parent_major_id": parse_assist_url(data.get("source_url", "")).get("major_id"),
    }

    chunks: List[Dict[str, Any]] = []
    keywords_set: Set[str] = set()

    for entry in data.get("general_information", []):
        raw_text = (entry.get("text") or "").strip()

        sentences = re.split(r"(?<=[.!?])\s+", raw_text)
        buf: List[str] = []
        current_len = 0
        temp_chunks: List[str] = []

        def flush_buf():
            nonlocal buf, current_len
            if not buf:
                return
            temp_chunks.append(" ".join(buf).strip())
            buf, current_len = [], 0

        for sent in sentences:
            # Respect preserve patterns
            if any(pat.search(sent) for pat in PRESERVE_PATTERNS):
                flush_buf()
                temp_chunks.append(sent.strip())
                continue

            if current_len + len(sent) + 1 > GENERAL_INFO_MAX:
                flush_buf()
            buf.append(sent)
            current_len += len(sent) + 1

        flush_buf()

        # Ensure min size by merging if needed
        consolidated: List[str] = []
        for chunk in temp_chunks:
            if consolidated and len(consolidated[-1]) < GENERAL_INFO_MIN:
                consolidated[-1] = f"{consolidated[-1]} {chunk}"
            else:
                consolidated.append(chunk)

        total = len(consolidated)

        for idx, part in enumerate(consolidated, start=1):
            meta = {
                **base,
                "type": "general_info",
                "chunk_index": idx,
                "total_chunks": total,
                "chunk_semantic_type": "program_description",
                "major_type": extract_major_type(base.get("agreement_title", "")),
            }

            cleaned = clean_chunk_text(part)
            keywords_set.update(extract_keywords([cleaned]))

            chunks.append({
                "page_content": cleaned,
                "metadata": clean_metadata(meta),
            })

    # Add keywords to all metadata entries for this major
    kw_list = sorted(keywords_set)
    for ch in chunks:
        ch["metadata"]["keywords"] = kw_list

    return chunks


def build_requirement_chunks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate higher‐level requirement chunks grouped by section within each group.

    Each chunk may contain multiple course mappings, preserving contextual
    headers and rules, and is sized to ~200–500 tokens (using a char cap)."""

    base: Dict[str, Any] = {
        "source_url": data.get("source_url"),
        "agreement_title": data.get("agreement_title"),
        "academic_year": data.get("academic_year"),
        "sending_institution": data.get("sending_institution"),
        "receiving_institution": data.get("receiving_institution"),
        "url_metadata": parse_assist_url(data.get("source_url", "")),
        "parent_major_id": parse_assist_url(data.get("source_url", "")).get("major_id"),
    }

    CHUNK_CHAR_LIMIT = REQUIREMENT_MAX

    chunks: List[Dict[str, Any]] = []

    for group in data.get("requirement_groups", []):
        group_id = group.get("group_id")
        requirement_area_raw = group.get("requirement_area", "") or ""
        requirement_area = requirement_area_raw.title()
        group_instruction = group.get("group_instruction", "")

        for section in group.get("sections", []):
            section_label = section.get("section_label")
            section_rule = section.get("section_rule", "")

            # Build list of mapping strings and parsed details
            mapping_strings: List[str] = []
            course_mappings: List[Dict[str, Any]] = []
            articulation_statuses: List[str] = []

            for req in section.get("requirements", []):
                recv_text = req.get("receiving_course_text", "")
                send_text = req.get("sending_course_text", "")

                mapping_strings.append(f"• {recv_text} → {send_text}")

                recv_parsed = parse_course_text(recv_text)
                send_parsed = parse_course_text(send_text)

                status = "articulated"
                if send_text.strip().lower().startswith("no course articulated"):
                    status = "no_articulation"
                elif send_text.strip().lower().startswith("this course must be taken"):  # university only
                    status = "university_only"

                articulation_statuses.append(status)

                course_mappings.append({
                    "receiving_course_text": recv_text,
                    "sending_course_text": send_text,
                    "receiving_course_code": recv_parsed.get("course_code"),
                    "sending_course_code": send_parsed.get("course_code"),
                    "receiving_units": recv_parsed.get("units"),
                    "sending_units": send_parsed.get("units"),
                    "articulation_status": status,
                })

            # Determine overall articulation status for the chunk
            status_set = set(articulation_statuses)
            if len(status_set) == 1:
                overall_status = status_set.pop()
            else:
                overall_status = "mixed"

            # Requirement level heuristic
            rl_lower = section_rule.lower()
            requirement_level = "optional" if any(x in rl_lower for x in ["select", "choose", "one of", "complete 1", "complete two", "complete 2"]) else "required"

            # Build header text
            header_parts = []
            if requirement_area:
                header_parts.append(requirement_area)
            if section_label:
                header_parts.append(f"Section {section_label}")
            header = " - ".join(header_parts)

            if section_rule:
                header += f" | Rule: {section_rule}"
            if group_instruction:
                header += f" | Group Instruction: {group_instruction}"

            # Assemble content and split into size-bound chunks
            current_lines: List[str] = [header]
            current_len = len(header)
            chunk_idx = 1

            def flush():
                nonlocal chunk_idx
                content = "\n".join(current_lines)
                meta: Dict[str, Any] = {
                    **base,
                    "type": "requirement",
                    "chunk_semantic_type": "requirement_group",
                    "group_id": group_id,
                    "requirement_area": requirement_area,
                    "section_label": section_label,
                    "section_rule": section_rule,
                    "group_instruction": group_instruction,
                    "requirement_level": requirement_level,
                    "articulation_status": overall_status,
                    "course_count_in_group": len(mapping_strings),
                    "course_mappings": course_mappings,
                    "receiving_course_text": "; ".join([m["receiving_course_text"] for m in course_mappings]),
                    "sending_course_text": "; ".join([m["sending_course_text"] for m in course_mappings]),
                    "department": base.get("agreement_title", "").split(" ")[0],
                    "transferable_courses": [m["sending_course_code"] for m in course_mappings if m["sending_course_code"]],
                    "chunk_index": chunk_idx,
                    "total_chunks_in_group": None,  # will set later
                    "information_density": round(len(course_mappings) / max(len(content), 1), 4),
                }

                # Compute content quality score now that meta exists
                meta["content_quality_score"] = calculate_completeness(meta)

                # Keywords
                meta["keywords"] = extract_keywords([header, " ".join(mapping_strings)])

                chunks.append({
                    "page_content": content,
                    "metadata": clean_metadata(meta),
                })

                chunk_idx += 1

            for line in mapping_strings:
                if current_len + len(line) + 1 > CHUNK_CHAR_LIMIT:
                    flush()
                    current_lines = [header, line]
                    current_len = len(header) + len(line) + 1
                else:
                    current_lines.append(line)
                    current_len += len(line) + 1

            # flush remaining
            if current_lines:
                flush()

            # Update total_chunks_in_group for all chunks just appended for this section
            # They are contiguous at end of list – update backwards until chunk_index reset
            total = chunk_idx - 1
            for back_i in range(1, total + 1):
                chunks[-back_i]["metadata"]["total_chunks_in_group"] = total

    return chunks


def generate_chunks(input_dir: Path) -> List[Dict[str, Any]]:
    """Walk *input_dir* recursively and build a combined list of articulation chunks."""
    chunks: List[Dict[str, Any]] = []

    json_files = [p for p in input_dir.rglob("*.json")]
    for file_path in tqdm(json_files, desc="Processing articulation JSONs"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[WARN] Could not parse {file_path}: {exc}")
            continue

        chunks.extend(build_general_info_chunks(data))
        chunks.extend(build_requirement_chunks(data))

    # After initial construction, enrich relationships and validate
    enrich_relationships(chunks)
    validate_chunks(chunks)

    return chunks


def write_jsonl(chunks: List[Dict[str, Any]], output_file: Path) -> None:
    """Write *chunks* as one JSON object per line to *output_file*."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")


###############################################################################
# CLI
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate articulation chunks for vector databases (combined or split mode).",
    )
    parser.add_argument(
        "--input-dir",
        default="data/assist_articulation_v2/rag_output/santa_monica_college/university_of_california_san_diego",
        help="Directory containing ASSIST articulation JSON files.",
    )
    parser.add_argument(
        "--mode",
        choices=["combined", "split"],
        default="split",
        help="combined: legacy single-file output; split: generate multi-vector JSONL files.",
    )
    parser.add_argument(
        "--output-file",
        default="data/vector_db/chunk_output/articulation_chunks.jsonl",
        help="Destination .jsonl file when --mode combined.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/vector_db/chunk_output",
        help="Directory to write split JSONL files when --mode split.",
    )

    args = parser.parse_args()

    input_dir = Path(args.input_dir)

    if args.mode == "combined":
        output_file = Path(args.output_file)
        chunks = generate_chunks(input_dir)
        write_jsonl(chunks, output_file)

        lengths = [len(c["page_content"]) for c in chunks]
        if lengths:
            print("\nChunk length statistics (characters):")
            print(f"  min   : {min(lengths)}")
            print(f"  max   : {max(lengths)}")
            print(f"  mean  : {statistics.mean(lengths):.1f}")
            print(f"  median: {statistics.median(lengths)}")

        print(f"\n✔ Generated {len(chunks):,} articulation chunks → {output_file}")
    else:
        output_dir = Path(args.output_dir)
        result = generate_split_chunks(input_dir)

        write_jsonl_with_header(result["course_mappings"], output_dir / "course_mappings_chunks.jsonl", result["header"])
        write_jsonl_with_header(result["requirements"], output_dir / "requirements_chunks.jsonl", result["header"])
        write_jsonl_with_header(result["program_info"], output_dir / "program_info_chunks.jsonl", result["header"])

        print("\n✔ Multi-vector chunk generation completed:")
        print(f"  Course mapping chunks : {len(result['course_mappings']):,}")
        print(f"  Requirement chunks    : {len(result['requirements']):,}")
        print(f"  Program info chunks   : {len(result['program_info']):,}")
        print(f"  Output directory      : {output_dir}")


# ---------------------------------------------------------------------------
# URL parsing helper
# ---------------------------------------------------------------------------

def parse_assist_url(url: str) -> Dict[str, Any]:
    """Extract structured metadata from an ASSIST agreement *url*.

    Returns keys matching the desired ``url_metadata`` spec. Returns an empty
    dict if parsing fails or the URL doesn't match expected shape."""

    if not url:
        return {}

    try:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)

        # Helper to pull single values from query params
        def _get(key: str) -> Optional[str]:
            return qs.get(key, [None])[0]

        year = _get("year")
        sending_inst_id = _get("institution")  # per observed pattern
        receiving_inst_id = _get("agreement")  # numeric id for UC campus
        agreement_type = _get("agreementType")

        major_id: Optional[str] = None
        view_by_key = _get("viewByKey")
        if view_by_key:
            parts = view_by_key.split("/")
            # Expected pattern: year/sending/to/receiving/Major/<uuid>
            if len(parts) >= 6:
                major_id = parts[-1]

        return {
            "academic_year_param": year,
            "sending_institution_id": sending_inst_id,
            "receiving_institution_id": receiving_inst_id,
            "agreement_type": agreement_type,
            "major_id": major_id,
        }
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Domain-specific constants
# ---------------------------------------------------------------------------

ASSIST_KEYWORDS = {
    "transfer", "articulation", "prerequisite", "major prep",
    "IGETC", "GE", "lower division", "upper division",
}

# Regex patterns that should not be split across chunks
PRESERVE_PATTERNS = [
    re.compile(r"MATH \d+[A-Z]?: .+? \(\d+\.\d+ units?\)", re.IGNORECASE),
    re.compile(r"https?://[^\s]+", re.IGNORECASE),
    re.compile(r"For more information.+?\.edu", re.IGNORECASE),
]

# Size limits (characters)
GENERAL_INFO_MAX = 800
GENERAL_INFO_MIN = 150
REQUIREMENT_MAX = 1000  # tighter cap for embedding models
REQUIREMENT_MIN = 150

# Insert helper utilities and constants for multi-vector DB generation
###############################################################################
# Multi-vector database helpers
###############################################################################

# Reusable regex for identifying course codes like "MATH 31A" or "CHEM 11".
COURSE_CODE_PATTERN = re.compile(r"[A-Z]{2,}\s?\d+[A-Z]?", re.IGNORECASE)


def extract_course_codes(text: str) -> List[str]:
    """Return a list of uppercase course codes with spaces removed found in *text*."""
    return [code.replace(" ", "").upper() for code in COURSE_CODE_PATTERN.findall(text or "")]


def _subject_area(code: Optional[str]) -> Optional[str]:
    """Return alphabetical prefix of a course code (e.g., 'MATH' from 'MATH31')."""
    if not code:
        return None
    match = re.match(r"([A-Z]{2,})", code)
    return match.group(1).upper() if match else None


def write_jsonl_with_header(chunks: List[Dict[str, Any]], output_file: Path, header_meta: Dict[str, Any]) -> None:
    """Write *chunks* to *output_file* preceded by a metadata header line."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"_metadata": header_meta}, ensure_ascii=False) + "\n")
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")


def generate_split_chunks(input_dir: Path) -> Dict[str, Any]:
    """Generate three distinct chunk collections – course mappings, requirements, program info –
    along with a summary header suitable for multi-vector database ingestion."""

    combined_chunks = generate_chunks(input_dir)

    # Containers for results
    course_map: Dict[Tuple[str, Tuple[str, ...], str], Dict[str, Any]] = {}
    requirement_chunks: List[Dict[str, Any]] = []
    program_chunks: List[Dict[str, Any]] = []

    majors_seen: Set[str] = set()
    warnings: List[str] = []

    for ch in combined_chunks:
        meta = ch.get("metadata", {})
        chunk_type_original = meta.get("type")

        # 1️⃣  Program overview chunks -----------------------------------------
        if chunk_type_original == "general_info":
            new_meta = {
                **meta,
                "chunk_type": "program_overview",
                "degree_type": extract_major_type(meta.get("agreement_title", "")),
            }
            new_meta.pop("type", None)
            program_chunks.append({"page_content": ch["page_content"], "metadata": clean_metadata(new_meta)})
            majors_seen.add(meta.get("agreement_title", ""))
            continue

        # 2️⃣  Requirement section chunks ------------------------------------
        if chunk_type_original == "requirement":
            # Copy and augment existing metadata
            new_meta = {
                **meta,
                "chunk_type": "requirement_section",
            }
            new_meta.pop("type", None)

            # Compute additional requirement-level statistics
            course_maps = meta.get("course_mappings", [])
            total_options = len(course_maps)
            transferable = sum(1 for m in course_maps if m.get("articulation_status") == "articulated")

            # Attempt to detect required course count from rule text (e.g., "Complete 3 courses …")
            required_num: Optional[int] = None
            rule_text = (meta.get("section_rule") or "").lower()
            match_num = re.search(r"(\d+)", rule_text)
            if match_num:
                try:
                    required_num = int(match_num.group(1))
                except Exception:
                    pass

            new_meta.update({
                "required_course_count": required_num,
                "total_options_available": total_options,
                "transferable_options_count": transferable,
                "non_transferable_count": total_options - transferable,
                "completion_difficulty": round(required_num / max(transferable, 1), 2) if required_num else None,
                "all_ucsd_courses": [m.get("receiving_course_code") for m in course_maps],
                "all_smc_options": [m.get("sending_course_code") for m in course_maps],
            })

            requirement_chunks.append({"page_content": ch["page_content"], "metadata": clean_metadata(new_meta)})

            # 3️⃣  Derive individual course-mapping chunks --------------------
            for m in course_maps:
                recv_code = m.get("receiving_course_code")
                recv_title = parse_course_text(m.get("receiving_course_text", "")).get("course_title")
                recv_units = m.get("receiving_units")

                send_codes = extract_course_codes(m.get("sending_course_text", ""))
                send_titles = [parse_course_text(code).get("course_title") for code in send_codes]
                send_units = m.get("sending_units")

                articulation_status = m.get("articulation_status")

                # Requirement logic type inference (AND / OR / single)
                send_text_lower = (m.get("sending_course_text", "") or "").lower()
                if " and " in send_text_lower or "+" in send_text_lower:
                    requirement_type = "AND"
                elif " or " in send_text_lower or "/" in send_text_lower:
                    requirement_type = "OR"
                else:
                    requirement_type = "single"

                key = (recv_code or "", tuple(sorted(send_codes)), articulation_status)

                # Human-readable chunk content
                if send_codes:
                    smc_side = ", ".join(send_codes)
                else:
                    smc_side = "NO COURSE"
                chunk_text = (
                    f"{recv_code} ({recv_title}, {recv_units} units) at UCSD transfers from "
                    f"{smc_side} at Santa Monica College."
                )

                if key in course_map:
                    course_map[key]["metadata"]["applicable_majors"].add(meta.get("agreement_title", ""))
                else:
                    searchable_terms = [recv_code] + send_codes + [c.replace(" ", "") for c in ([recv_code] + send_codes if recv_code else send_codes)]

                    course_map[key] = {
                        "page_content": chunk_text,
                        "metadata": clean_metadata({
                            "chunk_type": "course_mapping",
                            "ucsd_course_code": recv_code,
                            "ucsd_course_name": recv_title,
                            "ucsd_units": recv_units,
                            "smc_course_codes": send_codes,
                            "smc_course_names": send_titles,
                            "smc_units": send_units,
                            "articulation_status": articulation_status,
                            "requirement_type": requirement_type,
                            "subject_area": _subject_area(recv_code),
                            "applicable_majors": {meta.get("agreement_title", "")},
                            "institutions": [meta.get("receiving_institution"), meta.get("sending_institution")],
                            "searchable_terms": searchable_terms,
                        }),
                    }

            continue  # Finished processing this requirement chunk

        # Unhandled chunk types – keep note
        warnings.append(f"Unhandled chunk type: {chunk_type_original}")

    # Finalise course-mapping chunks and convert *applicable_majors* sets → sorted lists
    course_chunks: List[Dict[str, Any]] = []
    for data in course_map.values():
        majors_list = sorted(data["metadata"].pop("applicable_majors"))
        data["metadata"]["applicable_majors"] = majors_list
        course_chunks.append(data)

    summary_header = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "majors_processed": len(majors_seen),
        "chunk_counts": {
            "course_mappings": len(course_chunks),
            "requirements": len(requirement_chunks),
            "program_info": len(program_chunks),
        },
        "warnings": warnings,
    }

    return {
        "course_mappings": course_chunks,
        "requirements": requirement_chunks,
        "program_info": program_chunks,
        "header": summary_header,
    }

if __name__ == "__main__":
    main() 