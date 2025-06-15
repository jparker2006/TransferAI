import argparse
import json
import os
from typing import List

from tqdm import tqdm
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


###############################################################################
# Helpers
###############################################################################

def load_chunks(jsonl_path: str) -> List[Document]:
    """Load section chunks from *jsonl_path* into LangChain `Document`s."""
    docs: List[Document] = []
    total_lines = sum(1 for _ in open(jsonl_path, "r", encoding="utf-8"))

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, total=total_lines, desc="Reading section chunks"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                docs.append(Document(page_content=obj["page_content"], metadata=obj.get("metadata", {})))
            except Exception as exc:
                print(f"[WARN] Skipping malformed line: {exc}")
    return docs


def build_vectorstore(docs: List[Document], model_name: str) -> FAISS:
    """Create a FAISS vector store from *docs* using *model_name* embeddings."""
    embedder = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.from_documents(docs, embedder)


###############################################################################
# CLI
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(description="Build a FAISS vector store for section-level chunks.")
    parser.add_argument(
        "--chunks_file",
        default="data/vector_db/chunk_output/section_chunks.jsonl",
        help="Path to the JSONL file produced by generate_section_chunks.py",
    )
    parser.add_argument(
        "--model_name",
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model to use for embeddings.",
    )
    parser.add_argument(
        "--output_dir",
        default="data/vector_db/vectorstores/section_faiss",
        help="Directory to store the resulting FAISS index.",
    )

    args = parser.parse_args()

    if not os.path.isfile(args.chunks_file):
        raise FileNotFoundError(f"Chunks file not found: {args.chunks_file}")

    docs = load_chunks(args.chunks_file)
    print(f"✔ Loaded {len(docs):,} section chunks. Embedding …")

    vectorstore = build_vectorstore(docs, args.model_name)

    os.makedirs(args.output_dir, exist_ok=True)
    vectorstore.save_local(args.output_dir)

    print(f"\n✔ Section vector store saved to {args.output_dir}")


if __name__ == "__main__":
    main() 