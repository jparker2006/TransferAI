#!/usr/bin/env python3
"""Quick CLI/REPL to query the transfer‐terms vector store.

Example usage:
    python search_transfer_terms_vectorstore.py --query "What is articulation?" --scores

Run with no --query for an interactive prompt.
"""

import argparse
from pathlib import Path
import sys
from typing import List, Tuple, Optional

from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DEFAULT_STORE_DIR = "data/vector_db/vectorstores/transfer_terms_faiss"
DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_K = 5

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_vectorstore(path: Path, model_name: str) -> FAISS:
    if not path.exists():
        raise FileNotFoundError(f"Vector store not found at {path}")
    embeds = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.load_local(str(path), embeds, allow_dangerous_deserialization=True)


def format_doc(doc: Document, score: Optional[float] = None) -> str:
    meta = doc.metadata
    term = meta.get("term")
    cat = meta.get("category")
    header = f"{term} [{cat}]"
    score_txt = f" (score={score:.4f})" if score is not None else ""
    preview = doc.page_content.replace("\n", " ")[:100]
    return f"{header}{score_txt}\n  {preview}…"


def run_search(vs: FAISS, query: str, k: int, show_scores: bool):
    if show_scores:
        results: List[Tuple[Document, float]] = vs.similarity_search_with_score(query, k=k)
        if not results:
            print("❌ No results found.")
            return
        for i, (doc, score) in enumerate(results, 1):
            print(f"{i}. {format_doc(doc, score)}\n")
    else:
        docs = vs.similarity_search(query, k=k)
        if not docs:
            print("❌ No results found.")
            return
        for i, doc in enumerate(docs, 1):
            print(f"{i}. {format_doc(doc)}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Search the transfer terms vector store.")
    parser.add_argument("--vectorstore-path", default=DEFAULT_STORE_DIR, help="Path to transfer_terms_faiss directory.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL, help="Embedding model (must match build step).")
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="Top K results to return.")
    parser.add_argument("--query", type=str, help="One-off query (skip REPL).")
    parser.add_argument("--scores", action="store_true", help="Show similarity scores.")
    args = parser.parse_args()

    try:
        vs = load_vectorstore(Path(args.vectorstore_path), args.model_name)
    except Exception as exc:
        print(f"💥 Failed to load vectorstore: {exc}")
        sys.exit(1)

    print(f"✅ Loaded vector store with {vs.index.ntotal:,} embeddings\n")

    if args.query:
        run_search(vs, args.query, args.k, args.scores)
        return

    print("Enter your queries (type 'exit' to quit):")
    while True:
        try:
            q = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break
        if q.lower() in {"exit", "quit", "q"}:
            print("👋 Goodbye!")
            break
        if not q:
            continue
        run_search(vs, q, args.k, args.scores)


if __name__ == "__main__":
    main() 