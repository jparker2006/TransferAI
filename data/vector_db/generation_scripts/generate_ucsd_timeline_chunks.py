import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
import re

CHAR_LIMIT = 650
OVERLAP_SENT = 1

TIMELINE_FILE_DEFAULT = "data/UCSD_transfer_timeline/ucsd_transfer_application_timeline.json"
OUTPUT_FILE_DEFAULT = "data/vector_db/chunk_output/ucsd_transfer_timeline_chunks.jsonl"


def sent_split(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def split_text(text: str) -> List[str]:
    sents = sent_split(text)
    if not sents:
        return [text.strip()]
    chunks: List[str] = []
    buf: List[str] = []
    current = 0
    for s in sents:
        if current + len(s) + 1 > CHAR_LIMIT and buf:
            chunks.append(" ".join(buf).strip())
            overlap = buf[-OVERLAP_SENT:]
            buf = overlap.copy()
            current = sum(len(x) + 1 for x in buf)
        buf.append(s)
        current += len(s) + 1
    if buf:
        chunks.append(" ".join(buf).strip())
    return chunks or [text.strip()]


def build_page_content(header: str, desc: str, bullets: List[str]) -> str:
    content = header
    if desc:
        content += f"\n{desc.strip()}"
    if bullets:
        bullet_lines = "\n".join([f"• {b.strip()}" for b in bullets])
        content += f"\n{bullet_lines}"
    return content.strip()


def build_chunks(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    meta_global = data.get("metadata", {})
    institution = meta_global.get("institution")
    url = meta_global.get("url")
    academic_year = meta_global.get("academic_year")

    all_chunks: List[Dict[str, Any]] = []

    # 1. timeline events
    for ev in data.get("timeline", []):
        header = f"{ev.get('date')} – {ev.get('title')}"
        text_blocks = split_text(ev.get("description", ""))
        total = len(text_blocks)
        for idx, txt in enumerate(text_blocks, 1):
            page_content = build_page_content(header, txt, ev.get("bullet_points", []) if idx == total else [])
            meta = {
                "chunk_type": "timeline_event",
                "event_id": ev.get("id"),
                "date": ev.get("date"),
                "title": ev.get("title"),
                "category": ev.get("category"),
                "priority": ev.get("priority"),
                "institution": institution,
                "url": url,
                "academic_year": academic_year,
                "chunk_index": idx,
                "total_chunks": total,
                "keywords": ev.get("keywords") if idx == 1 else None,
            }
            meta = {k: v for k, v in meta.items() if v not in (None, [], "")}
            all_chunks.append({"page_content": page_content, "metadata": meta})

    # 2. summary key deadlines
    for kd in data.get("summary", {}).get("key_deadlines", []):
        content = f"KEY DEADLINE – {kd.get('date')}: {kd.get('title')}\n{kd.get('description', '')}"
        meta = {
            "chunk_type": "key_deadline",
            "date": kd.get("date"),
            "title": kd.get("title"),
            "category": kd.get("category"),
            "institution": institution,
            "academic_year": academic_year,
        }
        all_chunks.append({"page_content": content.strip(), "metadata": meta})

    # 3. important links (acts as reference chunks)
    for link in data.get("summary", {}).get("important_links", []):
        content = f"LINK: {link.get('text')} – {link.get('url')}\nContext: {link.get('context')} ({link.get('date')})"
        meta = {
            "chunk_type": "important_link",
            "title": link.get("text"),
            "url": link.get("url"),
            "context": link.get("context"),
            "date": link.get("date"),
            "institution": institution,
            "academic_year": academic_year,
        }
        all_chunks.append({"page_content": content.strip(), "metadata": meta})

    # 4. priority actions (could duplicate key deadlines, but provide urgency tag)
    for act in data.get("summary", {}).get("priority_actions", []):
        content = f"PRIORITY ACTION – {act.get('date')}: {act.get('title')}"
        meta = {
            "chunk_type": "priority_action",
            "date": act.get("date"),
            "title": act.get("title"),
            "category": act.get("category"),
            "priority": act.get("priority"),
            "institution": institution,
            "academic_year": academic_year,
        }
        all_chunks.append({"page_content": content.strip(), "metadata": meta})

    return all_chunks


def write_jsonl(chunks: List[Dict[str, Any]], outfile: Path):
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with outfile.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Generate vector-ready chunks from UCSD transfer timeline JSON.")
    parser.add_argument("--input-file", default=TIMELINE_FILE_DEFAULT, help="Path to UCSD timeline JSON.")
    parser.add_argument("--output-file", default=OUTPUT_FILE_DEFAULT, help="Destination JSONL file.")
    args = parser.parse_args()

    data = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
    chunks = build_chunks(data)
    write_jsonl(chunks, Path(args.output_file))
    print(f"✔ Generated {len(chunks):,} timeline chunks → {args.output_file}")


if __name__ == "__main__":
    main() 