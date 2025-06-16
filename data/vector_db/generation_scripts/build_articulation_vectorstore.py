import argparse
import json
from typing import List, Union
from pathlib import Path

from tqdm import tqdm
from langchain.docstore.document import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

###############################################################################
# Helpers
###############################################################################

def load_chunks(jsonl_path: Union[str, Path]) -> List[Document]:
    """Load articulation chunks from *jsonl_path* into LangChain `Document`s.

    Skips special header objects that contain an ``_metadata`` key."""
    docs: List[Document] = []
    jsonl_path = Path(jsonl_path)
    total_lines = sum(1 for _ in open(jsonl_path, "r", encoding="utf-8"))

    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in tqdm(f, total=total_lines, desc=f"Reading {jsonl_path.name}"):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                # Skip header metadata records
                if "_metadata" in obj:
                    continue
                docs.append(Document(page_content=obj["page_content"], metadata=obj.get("metadata", {})))
            except Exception as exc:
                print(f"[WARN] {jsonl_path.name}: skipping malformed line – {exc}")
    return docs


def build_vectorstore(docs: List[Document], model_name: str) -> FAISS:
    """Create a FAISS vector store from *docs* using *model_name* embeddings."""
    embedder = HuggingFaceEmbeddings(model_name=model_name)
    return FAISS.from_documents(docs, embedder)

###############################################################################
# CLI
###############################################################################

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build FAISS vector store(s) for articulation chunks (supports single or multi-vector JSONL files).",
    )
    parser.add_argument(
        "--input-path",
        default="data/vector_db/chunk_output",
        help="Path to a chunks .jsonl file OR a directory containing multiple chunk files.",
    )
    parser.add_argument(
        "--model-name",
        default="all-MiniLM-L6-v2",
        help="Sentence-transformers model for embeddings.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/vector_db/vectorstores",
        help="Directory to store resulting FAISS index(es). Subdirectories will be created per chunk file when input-path is a directory.",
    )

    args = parser.parse_args()

    in_path = Path(args.input_path)
    out_root = Path(args.output_dir)

    if in_path.is_file():
        docs = load_chunks(in_path)
        print(f"✔ Loaded {len(docs):,} chunks from {in_path.name}. Embedding …")

        vectorstore = build_vectorstore(docs, args.model_name)
        out_root.mkdir(parents=True, exist_ok=True)
        vectorstore.save_local(out_root)
        print(f"\n✔ Vector store saved to {out_root}")
    elif in_path.is_dir():
        jsonl_files = list(in_path.glob("*.jsonl"))
        if not jsonl_files:
            raise FileNotFoundError(f"No .jsonl files found in {in_path}")

        allowed_stems = {
            "course_mappings_chunks",
            "requirements_chunks",
            "program_info_chunks",
        }

        for jsonl_path in jsonl_files:
            if jsonl_path.stem not in allowed_stems:
                # Skip non-articulation chunk files (e.g., catalog course/section chunks)
                continue
            docs = load_chunks(jsonl_path)
            print(f"\n✔ Loaded {len(docs):,} chunks from {jsonl_path.name}. Embedding …")

            vectorstore = build_vectorstore(docs, args.model_name)

            stem = jsonl_path.stem
            if stem.endswith("_chunks"):
                stem = stem[: -len("_chunks")]

            # Add assist_artic_ prefix for known articulation chunk categories
            if stem in {"course_mappings", "requirements", "program_info"}:
                stem = f"assist_artic_{stem}"

            subdir = out_root / f"{stem}_faiss"
            subdir.mkdir(parents=True, exist_ok=True)
            vectorstore.save_local(subdir)
            print(f"✔ Vector store saved → {subdir}")
    else:
        raise FileNotFoundError(f"input-path not found: {in_path}")


if __name__ == "__main__":
    main() 