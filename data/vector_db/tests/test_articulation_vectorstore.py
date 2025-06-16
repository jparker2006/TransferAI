#!/usr/bin/env python3
"""
Test suite for the ASSIST articulation FAISS vector store.

Validates that the index can be loaded, queried, and that key metadata fields
are present for downstream transfer-planning tasks.
"""

import argparse
import os
import sys
from typing import List

from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

###############################################################################
# Helpers
###############################################################################

def load_vectorstore(path: str, model_name: str) -> FAISS:
    """Load a FAISS vector store from *path* using *model_name* embeddings."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Vector store not found at: {path}")

    embeds = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.load_local(path, embeds, allow_dangerous_deserialization=True)


def pretty_doc(doc: Document) -> str:
    meta = doc.metadata
    kind = meta.get("type")
    area = meta.get("requirement_area") or meta.get("chunk_semantic_type")
    return f"[{kind}] {area} → {doc.page_content[:80].replace('\n', ' ')}…"

###############################################################################
# Tests
###############################################################################

def smoke_test_queries(vs: FAISS) -> None:
    """Run a few representative queries and print top-3 results."""
    queries: List[str] = [
        "lower division major requirements biology",
        "IGETC GE area 4 social science",
        "No Course Articulated policy",
        "MATH 31 articulation",
    ]

    for q in queries:
        print(f"\n🔍 Query: {q}")
        docs = vs.similarity_search(q, k=3)
        for i, d in enumerate(docs, 1):
            print(f"  {i}. {pretty_doc(d)}")


def metadata_integrity_check(vs: FAISS) -> None:
    """Ensure essential metadata fields exist across a sample."""
    sample = vs.similarity_search("transfer", k=50)
    required_keys = {"source_url", "academic_year", "type", "chunk_semantic_type"}
    missing_counts = {k: 0 for k in required_keys}

    for doc in sample:
        meta = doc.metadata
        for key in required_keys:
            if key not in meta:
                missing_counts[key] += 1

    for key, cnt in missing_counts.items():
        if cnt > 0:
            print(f"⚠️  {cnt}/{len(sample)} docs missing '{key}' metadata field")
        else:
            print(f"✅ All sample docs contain '{key}'")

###############################################################################
# CLI
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(description="Test the articulation FAISS vector store.")
    parser.add_argument(
        "--vectorstore_path",
        default="data/vector_db/vectorstores/articulation_faiss",
        help="Directory containing the FAISS index.",
    )
    parser.add_argument(
        "--model_name",
        default="all-MiniLM-L6-v2",
        help="Embedding model name (must match builder).",
    )

    args = parser.parse_args()

    try:
        vs = load_vectorstore(args.vectorstore_path, args.model_name)
        print(f"✅ Vector store loaded ({vs.index.ntotal:,} embeddings)")

        smoke_test_queries(vs)
        metadata_integrity_check(vs)

        print("\n🎉 Articulation vector store tests completed successfully.")
    except Exception as exc:
        print(f"❌ Test suite failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main() 