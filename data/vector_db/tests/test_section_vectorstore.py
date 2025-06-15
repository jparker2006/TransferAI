#!/usr/bin/env python3
"""
Test script for the section-level vector database.
Mirrors functionality of ``test_course_vectorstore.py`` but tailored to
section metadata (days, time_range, location, instructor, etc.).

Usage examples:

    # Full test suite
    python data/vector_db/tests/test_section_vectorstore.py

    # Single ad-hoc query
    python data/vector_db/tests/test_section_vectorstore.py \
        --query "Calculus morning section" --k 8
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
    """Load a FAISS vector store at *path* using *model_name* for embeddings."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Vector store not found at: {path}")

    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.load_local(path, embeddings, allow_dangerous_deserialization=True)


###############################################################################
# Test routines – largely copy-pasted/adapted from course tests
###############################################################################

def test_similarity_search(vs: FAISS, queries: List[str], k: int = 5) -> None:
    print(f"\n🔍 Similarity search (top-{k})")
    for i, q in enumerate(queries, 1):
        print(f"\n--- Query {i}: '{q}' ---")
        try:
            res = vs.similarity_search(q, k=k)
            if not res:
                print("❌ No results found")
                continue
            print(f"✅ {len(res)} results:")
            for j, doc in enumerate(res, 1):
                code = doc.metadata.get("course_code", "N/A")
                sec = doc.metadata.get("section_number", "N/A")
                location = doc.metadata.get("location", "N/A")
                instr = doc.metadata.get("instructor", "N/A")
                preview = (doc.page_content[:100] + "…") if len(doc.page_content) > 100 else doc.page_content
                print(f"  {j}. {code}-{sec} at {location} w/ {instr}")
                print(f"     {preview}")
        except Exception as e:
            print(f"❌ Search failed: {e}")


def test_similarity_search_with_score(vs: FAISS, queries: List[str], k: int = 3) -> None:
    print(f"\n🔍 Similarity search with scores (top-{k})")
    for i, q in enumerate(queries, 1):
        print(f"\n--- Query {i}: '{q}' ---")
        try:
            res = vs.similarity_search_with_score(q, k=k)
            if not res:
                print("❌ No results")
                continue
            for j, (doc, score) in enumerate(res, 1):
                code = doc.metadata.get("course_code", "N/A")
                sec = doc.metadata.get("section_number", "N/A")
                print(f"  {j}. {code}-{sec} score={score:.4f}")
        except Exception as e:
            print(f"❌ Failed: {e}")


def test_retriever_interface(vs: FAISS, queries: List[str], k: int = 3) -> None:
    print("\n🔍 Retriever interface tests")
    retriever = vs.as_retriever(search_kwargs={"k": k})
    for i, q in enumerate(queries, 1):
        print(f"\n--- Query {i}: '{q}' ---")
        try:
            docs = retriever.get_relevant_documents(q)
            print(f"✅ Retrieved {len(docs)} docs")
        except Exception as e:
            print(f"❌ Retriever error: {e}")


###############################################################################
# Main entry
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(description="Test the section-level vector database")
    parser.add_argument(
        "--vectorstore_path",
        default="data/vector_db/vectorstores/section_faiss",
        help="Path to the FAISS vector store directory",
    )
    parser.add_argument(
        "--model_name",
        default="all-MiniLM-L6-v2",
        help="Embedding model name used to build the store",
    )
    parser.add_argument("--query", help="Run a single query instead of the full suite")
    parser.add_argument("--k", type=int, default=5, help="Number of results to return")

    args = parser.parse_args()

    try:
        vs = load_vectorstore(args.vectorstore_path, args.model_name)
        print(f"✅ Loaded vector store with {vs.index.ntotal:,} embeddings\n")
    except Exception as e:
        print(f"💥 Failed to load vector store: {e}")
        sys.exit(1)

    if args.query:
        test_similarity_search(vs, [args.query], k=args.k)
        test_similarity_search_with_score(vs, [args.query], k=args.k)
    else:
        test_queries = [
            "calculus morning section",
            "online psychology lecture",
            "evening computer science lab",
            "instructor smith classroom",
            "weekend art history",
        ]
        test_similarity_search(vs, test_queries, k=5)
        test_similarity_search_with_score(vs, test_queries[:3], k=3)
        test_retriever_interface(vs, test_queries[:3], k=3)
        print("\n🎉 Section vector store tests complete")


if __name__ == "__main__":
    main() 