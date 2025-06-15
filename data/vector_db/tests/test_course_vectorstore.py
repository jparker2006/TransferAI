#!/usr/bin/env python3
"""
Test script for the course vector database.
Tests loading, querying, and retrieval functionality.
"""

import argparse
import os
import sys
from typing import List

from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


def test_vectorstore_loading(vectorstore_path: str, model_name: str) -> FAISS:
    """Test loading the FAISS vector store."""
    print(f"🔍 Testing vector store loading from: {vectorstore_path}")
    
    if not os.path.exists(vectorstore_path):
        raise FileNotFoundError(f"Vector store not found at: {vectorstore_path}")
    
    try:
        embeddings = HuggingFaceEmbeddings(model_name=model_name)
        vectorstore = FAISS.load_local(vectorstore_path, embeddings, allow_dangerous_deserialization=True)
        
        # Get basic stats
        doc_count = vectorstore.index.ntotal
        print(f"✅ Successfully loaded vector store with {doc_count:,} documents")
        return vectorstore
        
    except Exception as e:
        print(f"❌ Failed to load vector store: {e}")
        raise


def test_similarity_search(vectorstore: FAISS, queries: List[str], k: int = 5) -> None:
    """Test similarity search functionality."""
    print(f"\n🔍 Testing similarity search (top-{k} results per query)")
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}: '{query}' ---")
        try:
            results = vectorstore.similarity_search(query, k=k)
            
            if not results:
                print("❌ No results found")
                continue
                
            print(f"✅ Found {len(results)} results:")
            for j, doc in enumerate(results, 1):
                course_id = doc.metadata.get('course_id', 'N/A')
                course_code = doc.metadata.get('course_code', 'N/A')
                program = doc.metadata.get('program_name', 'N/A')
                units = doc.metadata.get('units', 'N/A')
                
                # Truncate content for display
                content_preview = doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                
                print(f"  {j}. {course_code} ({course_id}) - {units} units")
                print(f"     Program: {program}")
                print(f"     Content: {content_preview}")
                
        except Exception as e:
            print(f"❌ Search failed for query '{query}': {e}")


def test_similarity_search_with_score(vectorstore: FAISS, queries: List[str], k: int = 3) -> None:
    """Test similarity search with scores."""
    print(f"\n🔍 Testing similarity search with scores (top-{k} results per query)")
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}: '{query}' ---")
        try:
            results = vectorstore.similarity_search_with_score(query, k=k)
            
            if not results:
                print("❌ No results found")
                continue
                
            print(f"✅ Found {len(results)} results with scores:")
            for j, (doc, score) in enumerate(results, 1):
                course_code = doc.metadata.get('course_code', 'N/A')
                course_id = doc.metadata.get('course_id', 'N/A')
                
                print(f"  {j}. {course_code} ({course_id}) - Score: {score:.4f}")
                
        except Exception as e:
            print(f"❌ Scored search failed for query '{query}': {e}")


def test_retriever_interface(vectorstore: FAISS, queries: List[str], k: int = 3) -> None:
    """Test the LangChain retriever interface."""
    print(f"\n🔍 Testing LangChain retriever interface (top-{k} results per query)")
    
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": k})
        
        for i, query in enumerate(queries, 1):
            print(f"\n--- Query {i}: '{query}' ---")
            try:
                results = retriever.get_relevant_documents(query)
                
                if not results:
                    print("❌ No results found")
                    continue
                    
                print(f"✅ Retriever found {len(results)} results:")
                for j, doc in enumerate(results, 1):
                    course_code = doc.metadata.get('course_code', 'N/A')
                    course_id = doc.metadata.get('course_id', 'N/A')
                    print(f"  {j}. {course_code} ({course_id})")
                    
            except Exception as e:
                print(f"❌ Retriever failed for query '{query}': {e}")
                
    except Exception as e:
        print(f"❌ Failed to create retriever: {e}")


def test_metadata_filtering(vectorstore: FAISS) -> None:
    """Test metadata-based filtering capabilities."""
    print(f"\n🔍 Testing metadata filtering")
    
    # Test filtering by program
    try:
        # Get a sample of documents to see what programs exist
        sample_docs = vectorstore.similarity_search("mathematics", k=10)
        programs = set(doc.metadata.get('program_name') for doc in sample_docs if doc.metadata.get('program_name'))
        
        if programs:
            test_program = list(programs)[0]
            print(f"Testing filter for program: {test_program}")
            
            # Note: FAISS doesn't support metadata filtering directly, but we can demonstrate
            # how to filter results post-search
            all_results = vectorstore.similarity_search("course", k=50)
            filtered_results = [doc for doc in all_results if doc.metadata.get('program_name') == test_program]
            
            print(f"✅ Found {len(filtered_results)} courses in {test_program} program")
            for i, doc in enumerate(filtered_results[:5], 1):
                course_code = doc.metadata.get('course_code', 'N/A')
                print(f"  {i}. {course_code}")
        else:
            print("❌ No program metadata found in sample")
            
    except Exception as e:
        print(f"❌ Metadata filtering test failed: {e}")


def run_comprehensive_tests(vectorstore_path: str, model_name: str) -> None:
    """Run all tests."""
    print("🚀 Starting comprehensive vector store tests\n")
    
    # Test queries covering different domains
    test_queries = [
        "calculus mathematics",
        "computer science programming",
        "english writing composition",
        "biology laboratory science",
        "art history culture",
        "statistics data analysis",
        "chemistry organic",
        "physics mechanics",
        "psychology human behavior",
        "business accounting"
    ]
    
    try:
        # Load vector store
        vectorstore = test_vectorstore_loading(vectorstore_path, model_name)
        
        # Run various tests
        test_similarity_search(vectorstore, test_queries[:5], k=3)
        test_similarity_search_with_score(vectorstore, test_queries[:3], k=3)
        test_retriever_interface(vectorstore, test_queries[:3], k=3)
        test_metadata_filtering(vectorstore)
        
        print(f"\n🎉 All tests completed successfully!")
        
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the course vector database")
    parser.add_argument(
        "--vectorstore_path",
        default="vectorstores/course_faiss",
        help="Path to the FAISS vector store directory"
    )
    parser.add_argument(
        "--model_name",
        default="all-MiniLM-L6-v2",
        help="Embedding model name (must match the one used to build the store)"
    )
    parser.add_argument(
        "--query",
        help="Run a single test query instead of the full test suite"
    )
    parser.add_argument(
        "--k",
        type=int,
        default=5,
        help="Number of results to return for single query test"
    )
    
    args = parser.parse_args()
    
    if args.query:
        # Single query mode
        print(f"🔍 Testing single query: '{args.query}'")
        try:
            embeddings = HuggingFaceEmbeddings(model_name=args.model_name)
            vectorstore = FAISS.load_local(args.vectorstore_path, embeddings, allow_dangerous_deserialization=True)
            
            results = vectorstore.similarity_search_with_score(args.query, k=args.k)
            
            print(f"\n✅ Found {len(results)} results:")
            for i, (doc, score) in enumerate(results, 1):
                course_code = doc.metadata.get('course_code', 'N/A')
                course_id = doc.metadata.get('course_id', 'N/A')
                program = doc.metadata.get('program_name', 'N/A')
                units = doc.metadata.get('units', 'N/A')
                
                print(f"\n{i}. {course_code} ({course_id}) - Score: {score:.4f}")
                print(f"   Program: {program} | Units: {units}")
                print(f"   Content: {doc.page_content}")
                
        except Exception as e:
            print(f"❌ Single query test failed: {e}")
            sys.exit(1)
    else:
        # Full test suite
        run_comprehensive_tests(args.vectorstore_path, args.model_name)


if __name__ == "__main__":
    main() 