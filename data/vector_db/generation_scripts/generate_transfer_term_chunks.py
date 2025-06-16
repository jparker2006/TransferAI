import argparse
import json
from pathlib import Path
from typing import Dict, List, Any
import re
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHAR_MAX = 500  # hard cap per chunk
OVERLAP_SENTENCES = 1  # sentence overlap when splitting long definitions

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def split_sentences(text: str) -> List[str]:
    """Very simple sentence splitter preserving punctuation."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def split_definition(term: str, definition: str) -> List[str]:
    """Split a potentially long definition into chunks <= CHAR_MAX with overlap."""
    sentences = split_sentences(definition)
    if not sentences:
        return [definition.strip()]

    chunks: List[str] = []
    buf: List[str] = []
    current_len = 0

    for sent in sentences:
        if current_len + len(sent) + 1 > CHAR_MAX and buf:
            chunks.append(" ".join(buf).strip())
            # add overlap
            buf = sentences[max(0, len(chunks)*(len(buf)) - OVERLAP_SENTENCES):][:OVERLAP_SENTENCES]
            current_len = sum(len(s) + 1 for s in buf)
        buf.append(sent)
        current_len += len(sent) + 1

    if buf:
        chunks.append(" ".join(buf).strip())

    return chunks or [definition.strip()]


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def build_chunks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    glossary = data.get("college_transfer_terms", {})
    for category_key, category_val in glossary.items():
        cat_desc = category_val.get("category_description", "")
        terms_container = category_val.get("terms", {})
        # Some categories have nested subcategories like credentials_and_degree_types -> terms
        if not terms_container and category_val:
            # fallback: nested keys (e.g., credentials_and_degree_types has terms under it)
            terms_container = category_val
        for term, info in terms_container.items():
            definition = info.get("definition", "").strip()
            context = info.get("context", "").strip()

            if not definition:
                continue

            def_chunks = split_definition(term, definition)
            total = len(def_chunks)
            for idx, text in enumerate(def_chunks, 1):
                page_content = f"{term}: {text}"
                if context and idx == total:  # append context only to last chunk
                    page_content += f" Context: {context}"

                meta = {
                    "chunk_type": "transfer_term",
                    "term": term,
                    "category": category_key,
                    "chunk_index": idx,
                    "total_chunks": total,
                }
                chunks.append({"page_content": page_content, "metadata": meta})

    return chunks


def write_jsonl(chunks: List[Dict[str, Any]], outfile: Path):
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate chunks from transfer terms glossary JSON.")
    parser.add_argument(
        "--input-file",
        default="data/transfer_term_glossary/transfer_terms.json",
        help="Path to transfer_terms.json file.",
    )
    parser.add_argument(
        "--output-file",
        default="data/vector_db/chunk_output/transfer_terms_chunks.jsonl",
        help="Destination JSONL for chunks.",
    )
    args = parser.parse_args()

    data = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    chunks = build_chunks(data)
    write_jsonl(chunks, Path(args.output_file))

    print(f"✔ Generated {len(chunks):,} transfer term chunks → {args.output_file}")


if __name__ == "__main__":
    main() 