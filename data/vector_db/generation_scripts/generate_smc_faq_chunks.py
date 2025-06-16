import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Union
import re
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHAR_LIMIT = 600  # Maximum char length per chunk
OVERLAP_SENTENCES = 1  # Overlap between chunks for long answers

FAQ_DIR_DEFAULT = "data/SMC_FAQs"
OUTPUT_FILE_DEFAULT = "data/vector_db/chunk_output/smc_faq_chunks.jsonl"

# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def sent_split(text: str) -> List[str]:
    """Plain-regex sentence splitter (keeps punctuation)."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def split_answer(answer: str) -> List[str]:
    sentences = sent_split(answer)
    if not sentences:
        return [answer.strip()]

    chunks: List[str] = []
    buf: List[str] = []
    current_len = 0

    for s in sentences:
        if current_len + len(s) + 1 > CHAR_LIMIT and buf:
            chunks.append(" ".join(buf).strip())
            # create overlap
            overlap = sentences[max(0, len(chunks) - 1):len(chunks) - 1 + OVERLAP_SENTENCES]
            buf = overlap.copy()
            current_len = sum(len(x) + 1 for x in buf)
        buf.append(s)
        current_len += len(s) + 1

    if buf:
        chunks.append(" ".join(buf).strip())

    return chunks or [answer.strip()]

# ---------------------------------------------------------------------------
# Chunk builder
# ---------------------------------------------------------------------------

def build_chunks(json_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(json_path.read_text(encoding="utf-8"))

    meta_global = data.get("metadata", {})
    source_title = meta_global.get("title") or meta_global.get("source")
    source_type = meta_global.get("page_type") or "counseling"
    institution = meta_global.get("institution")
    url = meta_global.get("url")

    chunks: List[Dict[str, Any]] = []

    for faq in data.get("faqs", []):
        question = faq.get("question", "").strip()
        answer = faq.get("answer", "").strip()
        category = faq.get("category")
        faq_id = faq.get("id")
        keywords = faq.get("keywords", [])

        answer_chunks = split_answer(answer)
        total = len(answer_chunks)
        for idx, ans_part in enumerate(answer_chunks, 1):
            page_content = f"Q: {question}\nA: {ans_part}"
            meta = {
                "chunk_type": "faq",
                "faq_source": source_type,
                "source_title": source_title,
                "institution": institution,
                "url": url,
                "faq_id": faq_id,
                "category": category,
                "keywords": keywords if idx == 1 else None,  # include only first chunk
                "chunk_index": idx,
                "total_chunks": total,
            }
            meta = {k: v for k, v in meta.items() if v not in (None, [], "")}
            chunks.append({"page_content": page_content, "metadata": meta})

    return chunks

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def write_jsonl(chunks: List[Dict[str, Any]], outfile: Path) -> None:
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate vector-ready chunks from SMC FAQ JSON files.")
    parser.add_argument("--input-dir", default=FAQ_DIR_DEFAULT, help="Directory containing *_faq_rag.json files.")
    parser.add_argument("--output-file", default=OUTPUT_FILE_DEFAULT, help="Destination JSONL file for chunks.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    files = sorted(input_dir.glob("*_faq_rag.json"))
    if not files:
        raise FileNotFoundError(f"No *_faq_rag.json files found in {input_dir}")

    all_chunks: List[Dict[str, Any]] = []
    for fp in files:
        print(f"Processing {fp.name} …")
        all_chunks.extend(build_chunks(fp))

    write_jsonl(all_chunks, Path(args.output_file))
    print(f"✔ Generated {len(all_chunks):,} FAQ chunks → {args.output_file}")


if __name__ == "__main__":
    main() 