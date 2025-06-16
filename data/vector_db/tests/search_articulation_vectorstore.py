#!/usr/bin/env python3
"""Interactive search utility for the ASSIST articulation FAISS vector store.

Example usage:
    python search_articulation_vectorstore.py --vectorstore_path data/vector_db/vectorstores/assist_articulation_faiss \
        --model_name all-MiniLM-L6-v2 --k 5 --query "MATH 31 articulation"

If --query is omitted, the script opens a REPL for iterative searches.
"""

import argparse
import sys
from typing import List, Tuple, Optional, Dict
from pathlib import Path

from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DEFAULT_K = 5

###############################################################################
# Loading helpers
###############################################################################

def load_vectorstore(path: str, model_name: str) -> FAISS:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Vector store not found at: {p}")
    embeds = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.load_local(str(p), embeds, allow_dangerous_deserialization=True)


def load_vectorstores(root: Path, model_name: str, assist_only: bool = True) -> Dict[str, FAISS]:
    """Load one or many FAISS stores.

    If *root* is a directory that directly contains a FAISS index (faiss + pkl files), it is
    loaded as a single store. Otherwise, all sub-directories ending with "_faiss" are loaded.
    The returned dict maps store names (directory stem) → FAISS instance."""

    if (root / "index.faiss").exists() or any(root.glob("*.faiss")):
        # Single store directory
        return {root.name: load_vectorstore(str(root), model_name)}

    stores: Dict[str, FAISS] = {}
    for sub in root.iterdir():
        if not sub.is_dir() or not sub.name.endswith("_faiss"):
            continue

        if assist_only:
            if not sub.name.startswith("assist_artic_"):
                # Skip non‐articulation FAISS stores when assist_only is True
                continue

        try:
            stores[sub.name] = load_vectorstore(str(sub), model_name)
        except Exception as exc:
            print(f"[WARN] Could not load store {sub}: {exc}")

    if not stores:
        raise FileNotFoundError(f"No matching FAISS indexes found under {root}")
    return stores


def format_result(doc: Document, score: Optional[float] = None) -> str:
    meta = doc.metadata
    chunk_type = meta.get('chunk_type') or meta.get('type')
    header = f"[{chunk_type}] {meta.get('requirement_area') or meta.get('chunk_semantic_type') or meta.get('subject_area', '')}".strip()
    title = meta.get("agreement_title", "")
    preview = doc.page_content.replace("\n", " ")[:120] + ("…" if len(doc.page_content) > 120 else "")
    score_str = f" (score={score:.4f})" if score is not None else ""
    return f"{header} | {title}{score_str}\n  {preview}"

###############################################################################
# Search functions
###############################################################################

def run_search(vs: FAISS, query: str, k: int, with_scores: bool = False) -> None:
    if with_scores:
        results: List[Tuple[Document, float]] = vs.similarity_search_with_score(query, k=k)
        if not results:
            print("❌ No results found.")
            return
        for idx, (doc, score) in enumerate(results, 1):
            print(f"{idx}. {format_result(doc, score)}\n")
    else:
        docs = vs.similarity_search(query, k=k)
        if not docs:
            print("❌ No results found.")
            return
        for idx, doc in enumerate(docs, 1):
            print(f"{idx}. {format_result(doc)}\n")

def run_search_multi(stores: Dict[str, FAISS], query: str, k: int, with_scores: bool = False) -> None:
    """Search across multiple stores and aggregate results by score."""
    aggregate: List[Tuple[str, Document, float]] = []
    for name, vs in stores.items():
        for doc, score in vs.similarity_search_with_score(query, k=k):
            aggregate.append((name, doc, score))

    if not aggregate:
        print("❌ No results found across stores.")
        return

    aggregate.sort(key=lambda x: x[2])  # lower score = closer
    for idx, (store_name, doc, score) in enumerate(aggregate[:k], 1):
        print(f"{idx}. [{store_name}] {format_result(doc, score if with_scores else None)}\n")

###############################################################################
# CLI / REPL
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(description="Search one or multiple articulation FAISS vector stores.")
    parser.add_argument(
        "--vectorstore-path",
        default="data/vector_db/vectorstores",
        help="A FAISS index directory or a directory containing *_faiss subfolders.",
    )
    parser.add_argument(
        "--model-name",
        default="all-MiniLM-L6-v2",
        help="Embedding model name (must match build step).",
    )
    parser.add_argument("--k", type=int, default=DEFAULT_K, help="Number of top results to display (per store or aggregate).")
    parser.add_argument("--query", type=str, help="Single-shot query (skips interactive mode).")
    parser.add_argument("--scores", action="store_true", help="Display similarity scores.")
    parser.add_argument("--store", type=str, help="Name of a specific store to query when multiple are present.")
    parser.add_argument("--include-catalog", action="store_true", help="Include catalog (non-ASSIST) stores in search.")

    args = parser.parse_args()

    root = Path(args.vectorstore_path)
    try:
        stores = load_vectorstores(root, args.model_name, assist_only=not args.include_catalog)
    except Exception as exc:
        print(f"💥 Failed to load vectorstore(s): {exc}")
        sys.exit(1)

    if len(stores) == 1:
        vs = next(iter(stores.values()))
        print(f"✅ Loaded single store '{root.name}' with {vs.index.ntotal:,} embeddings\n")
    else:
        print("✅ Loaded stores:")
        for name, store in stores.items():
            print(f"  • {name}: {store.index.ntotal:,} embeddings")
        print()

    # Choose search function based on arguments
    def _search(query: str):
        if args.store and args.store in stores:
            run_search(stores[args.store], query, args.k, args.scores)
        elif len(stores) == 1:
            run_search(vs, query, args.k, args.scores)
        else:
            run_search_multi(stores, query, args.k, args.scores)

    if args.query:
        _search(args.query)
        return

    # Interactive loop
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
        _search(q)


if __name__ == "__main__":
    main() 