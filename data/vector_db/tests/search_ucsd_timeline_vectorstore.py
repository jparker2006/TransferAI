#!/usr/bin/env python3
"""Interactive / CLI search for the UCSD transfer-timeline vector store.

Example:
    python search_ucsd_timeline_vectorstore.py --query "deadline to accept offer" --scores
"""

import argparse
from pathlib import Path
import sys
from typing import List, Tuple, Optional

from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DEFAULT_STORE = "data/vector_db/vectorstores/ucsd_transfer_timeline_faiss"
DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_K = 5


def load_store(path: Path, model: str) -> FAISS:
    if not path.exists():
        raise FileNotFoundError(f"Vector store not found: {path}")
    embedder = HuggingFaceEmbeddings(model_name=model)
    return FAISS.load_local(str(path), embedder, allow_dangerous_deserialization=True)


def fmt(doc: Document, score: Optional[float] = None) -> str:
    meta = doc.metadata
    label = meta.get("chunk_type")
    date = meta.get("date")
    title = meta.get("title")
    score_txt = f" (score={score:.4f})" if score is not None else ""
    preview = doc.page_content.replace("\n", " ")[:120]
    return f"[{label}] {date} – {title}{score_txt}\n  {preview}…"


def run_query(vs: FAISS, q: str, k: int, with_scores: bool):
    if with_scores:
        results: List[Tuple[Document, float]] = vs.similarity_search_with_score(q, k=k)
        if not results:
            print("❌ No results.")
            return
        for i, (d, s) in enumerate(results, 1):
            print(f"{i}. {fmt(d, s)}\n")
    else:
        docs = vs.similarity_search(q, k=k)
        if not docs:
            print("❌ No results.")
            return
        for i, d in enumerate(docs, 1):
            print(f"{i}. {fmt(d)}\n")


def main():
    p = argparse.ArgumentParser(description="Search UCSD transfer timeline vectorstore")
    p.add_argument("--vectorstore-path", default=DEFAULT_STORE)
    p.add_argument("--model-name", default=DEFAULT_MODEL)
    p.add_argument("--k", type=int, default=DEFAULT_K)
    p.add_argument("--query", type=str)
    p.add_argument("--scores", action="store_true")
    args = p.parse_args()

    try:
        store = load_store(Path(args.vectorstore_path), args.model_name)
        print(f"✅ Loaded store with {store.index.ntotal:,} embeddings\n")
    except Exception as e:
        print(f"💥 {e}")
        sys.exit(1)

    if args.query:
        run_query(store, args.query, args.k, args.scores)
        return

    print("Enter queries (exit to quit):")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Bye")
            break
        if q.lower() in {"exit", "quit", "q"}:
            print("👋 Bye")
            break
        if q:
            run_query(store, q, args.k, args.scores)


if __name__ == "__main__":
    main() 