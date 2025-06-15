#!/usr/bin/env python3
"""
Quick inspection script for vector store metadata structure.
"""

import os
import pickle
import json
from pathlib import Path

def inspect_vectorstore_metadata(vectorstore_path: str):
    """Inspect the metadata structure of the vector store."""
    print(f"🔍 Inspecting vector store at: {vectorstore_path}")
    
    # Check if vector store exists
    if not os.path.exists(vectorstore_path):
        print(f"❌ Vector store not found at: {vectorstore_path}")
        return
    
    # Try to load the index file to get basic info
    index_path = os.path.join(vectorstore_path, "index.faiss")
    if os.path.exists(index_path):
        file_size = os.path.getsize(index_path) / (1024 * 1024)  # MB
        print(f"📊 Index file size: {file_size:.2f} MB")
    
    # Try to load the docstore pickle to examine metadata
    docstore_path = os.path.join(vectorstore_path, "index.pkl")
    if os.path.exists(docstore_path):
        try:
            with open(docstore_path, 'rb') as f:
                docstore_data = pickle.load(f)
            
            print(f"📊 Docstore type: {type(docstore_data)}")
            
            # If it's a dictionary, examine its structure
            if hasattr(docstore_data, 'docstore') and hasattr(docstore_data.docstore, '_dict'):
                docs = docstore_data.docstore._dict
                print(f"📊 Total documents: {len(docs)}")
                
                # Sample a few documents to examine metadata
                sample_docs = list(docs.values())[:5]
                
                print(f"\n📋 Sample Document Metadata:")
                for i, doc in enumerate(sample_docs, 1):
                    print(f"\n--- Document {i} ---")
                    print(f"Metadata keys: {list(doc.metadata.keys())}")
                    print(f"Content length: {len(doc.page_content)}")
                    
                    # Show metadata values
                    for key, value in doc.metadata.items():
                        if isinstance(value, str) and len(value) > 50:
                            print(f"  {key}: {value[:50]}...")
                        else:
                            print(f"  {key}: {value}")
                
                # Analyze metadata consistency
                print(f"\n📊 Metadata Field Analysis:")
                all_keys = set()
                key_counts = {}
                
                for doc in docs.values():
                    doc_keys = set(doc.metadata.keys())
                    all_keys.update(doc_keys)
                    
                    for key in doc_keys:
                        key_counts[key] = key_counts.get(key, 0) + 1
                
                print(f"Total unique metadata keys: {len(all_keys)}")
                print(f"Key frequency:")
                for key in sorted(all_keys):
                    percentage = (key_counts.get(key, 0) / len(docs)) * 100
                    print(f"  {key}: {key_counts.get(key, 0)}/{len(docs)} ({percentage:.1f}%)")
                    
        except Exception as e:
            print(f"❌ Error reading docstore: {e}")
    
    else:
        print(f"❌ Docstore file not found at: {docstore_path}")

if __name__ == "__main__":
    vectorstore_path = "vectorstores/course_faiss"
    inspect_vectorstore_metadata(vectorstore_path) 