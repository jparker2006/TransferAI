import argparse
from pathlib import Path
from typing import List, Union, Dict
import json
import fnmatch

from tqdm import tqdm
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

###############################################################################
# Helpers
###############################################################################

def load_chunks(jsonl_path: Union[str, Path]) -> List[Document]:
    """Load JSONL chunks, skipping optional header lines starting with {'_metadata': …}."""
    p = Path(jsonl_path)
    docs: List[Document] = []
    total = sum(1 for _ in p.open("r", encoding="utf-8"))
    with p.open("r", encoding="utf-8") as f:
        for line in tqdm(f, total=total, desc=f"Reading {p.name}"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if "_metadata" in obj:
                    continue  # header
                docs.append(Document(page_content=obj["page_content"], metadata=obj.get("metadata", {})))
            except Exception as exc:
                print(f"[WARN] {p.name}: skipping malformed line – {exc}")
    return docs


def build_vectorstore(docs: List[Document], model_name: str) -> FAISS:
    """Embed *docs* with *model_name* and return FAISS store."""
    embedder = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.from_documents(docs, embedder)


def matches_patterns(name: str, patterns: List[str]) -> bool:
    return any(fnmatch.fnmatch(name, pat) for pat in patterns)

###############################################################################
# CLI
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(description="Build FAISS vector store(s) from any chunk JSONL files.")
    parser.add_argument("--input-path", default="data/vector_db/chunk_output", help="JSONL file or directory containing JSONL chunks.")
    parser.add_argument("--model-name", default="all-MiniLM-L6-v2", help="Sentence-transformers model used for embeddings.")
    parser.add_argument("--output-dir", default="data/vector_db/vectorstores", help="Directory where FAISS index folders will be written.")
    parser.add_argument("--include", nargs="*", default=["*.jsonl"], help="Glob pattern(s) of files to include when --input-path is a directory.")
    parser.add_argument("--exclude", nargs="*", default=[], help="Glob pattern(s) to exclude.")

    args = parser.parse_args()

    in_path = Path(args.input_path)
    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    # Helper to derive subdir name from file stem
    def stem_to_dir(stem: str) -> str:
        s = stem
        if s.endswith("_chunks"):
            s = s[: -len("_chunks")]
        # Articulation naming convention
        if s in {"course_mappings", "requirements", "program_info"}:
            s = f"assist_artic_{s}"
        return f"{s}_faiss"

    if in_path.is_file():
        docs = load_chunks(in_path)
        print(f"✔ Loaded {len(docs):,} chunks from {in_path.name}. Embedding …")
        store = build_vectorstore(docs, args.model_name)
        store.save_local(out_root)
        print(f"✔ Vector store saved → {out_root}")
        return

    # Directory mode
    if not in_path.is_dir():
        raise FileNotFoundError(f"input-path not found: {in_path}")

    jsonl_files = [p for p in in_path.glob("*.jsonl") if matches_patterns(p.name, args.include) and not matches_patterns(p.name, args.exclude)]
    if not jsonl_files:
        raise FileNotFoundError("No JSONL chunk files matched include/exclude patterns.")

    for path in jsonl_files:
        docs = load_chunks(path)
        if not docs:
            print(f"[WARN] {path.name}: no valid chunks – skipping.")
            continue
        print(f"\n✔ Loaded {len(docs):,} chunks from {path.name}. Embedding …")
        store = build_vectorstore(docs, args.model_name)
        subdir = out_root / stem_to_dir(path.stem)
        subdir.mkdir(parents=True, exist_ok=True)
        store.save_local(subdir)
        print(f"✔ Vector store saved → {subdir}")


if __name__ == "__main__":
    main() 