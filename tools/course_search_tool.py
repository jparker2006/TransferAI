from __future__ import annotations

"""TransferAI – Course Search Tool

StructuredTool that performs a keyword search across *all* Santa Monica College
courses using a two-stage hybrid retrieval strategy:

1. Sparse BM25 pass over the raw catalogue JSON files – returns the top-30
   candidate course documents.
2. Dense re-rank with FAISS (Sentence-Transformer embeddings) restricted to
   the BM25 candidate set.

The final response is the *top-k* courses sorted by dense similarity.

Dependencies
------------
• rank_bm25>=0.2.2
• langchain_huggingface
• langchain_community

The module defers heavy initialisation (BM25 construction, embedding model
loading, FAISS index deserialisation) until the *first* invocation to minimise
import overhead when the tool is present but unused in an agent prompt.
"""

from pathlib import Path
import json
import pickle
import sys
from functools import lru_cache
from typing import Dict, List, Optional
import heapq

import numpy as np
from langchain.docstore.document import Document
from langchain_core.tools import StructuredTool
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from pydantic import BaseModel, Field
from rank_bm25 import BM25Okapi

# ---------------------------------------------------------------------------
# Ensure project root importable when executed as standalone script ----------
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":  # pragma: no cover – CLI/pytest support
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Public Exceptions ----------------------------------------------------------
# ---------------------------------------------------------------------------


class SearchFailureError(RuntimeError):
    """Raised when the search pipeline cannot return any results."""


# ---------------------------------------------------------------------------
# Pydantic I/O Schemas -------------------------------------------------------
# ---------------------------------------------------------------------------


class CSIn(BaseModel):  # noqa: D401
    """Input parameters for :pyattr:`CourseSearchTool`."""

    query: str = Field(..., description="Free-text keyword search query.")
    top_k: int = Field(5, ge=1, le=20, description="Number of top courses to return (≤20).")


class CourseSearchResult(BaseModel):  # noqa: D401
    """One returned course hit from the hybrid search."""

    course_code: str
    course_id: Optional[str] = None
    program_name: str
    units: Optional[float] = None
    description_excerpt: str


class CSOut(BaseModel):  # noqa: D401
    """Wrapper holding the list of :class:`CourseSearchResult`."""

    results: List[CourseSearchResult]


# ---------------------------------------------------------------------------
# Constants & Paths ---------------------------------------------------------
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_CATALOG_DIR = _DATA_DIR / "SMC_catalog" / "parsed_programs"
_VECTORSTORE_DIR = _DATA_DIR / "vector_db" / "vectorstores" / "course_faiss"
_BM25_CACHE_PATH = _DATA_DIR / "vector_db" / "bm25_cache.pkl"

# Same embedding model used when building the FAISS store
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"

# ---------------------------------------------------------------------------
# In-memory caches (lightweight) --------------------------------------------
# ---------------------------------------------------------------------------

# Avoid recomputing embeddings for the same document between queries.
_DOC_EMB_CACHE: Dict[str, np.ndarray] = {}

# ---------------------------------------------------------------------------
# Internal helpers -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _build_bm25() -> tuple[BM25Okapi, List[Dict[str, str]]]:
    """Scan the programme JSON files building the BM25 index.

    Returns
    -------
    (bm25, meta_list)
        *bm25* – ready-to-query :class:`BM25Okapi` instance.
        *meta_list* – list where *meta_list[i]* is the metadata dict for the
        *i*-th document in the BM25 corpus.  Contains at least
        ``course_id``/``course_code``/``program_name``/``units``/``page_content``.
    """

    tokens_corpus: List[List[str]] = []
    meta_list: List[Dict[str, str]] = []

    if not _CATALOG_DIR.exists():
        raise RuntimeError(f"Catalogue directory not found: {_CATALOG_DIR}")

    for json_file in sorted(_CATALOG_DIR.glob("*.json")):
        try:
            with json_file.open("r", encoding="utf-8") as fh:
                program_data = json.load(fh)
        except Exception as exc:  # noqa: BLE001
            # Skip unreadable files; continue building index
            print(f"[WARN] Failed to parse {json_file}: {exc}")
            continue

        program_name = program_data.get("program_name", json_file.stem)
        for course in program_data.get("courses", []):
            course_code = (course.get("course_code") or "").strip()
            title = (course.get("course_title") or "").strip()
            description = (course.get("description") or "").strip()

            page_content = f"{course_code} {title} {description}".strip()
            if not page_content:
                continue  # Skip empty docs

            tokens_corpus.append(page_content.lower().split())
            meta_list.append(
                {
                    "course_id": course.get("course_id"),
                    "course_code": course_code,
                    "program_name": program_name,
                    "units": course.get("units"),
                    "page_content": page_content,
                }
            )

    if not tokens_corpus:
        raise RuntimeError("No courses found whilst building BM25 corpus")

    bm25 = BM25Okapi(tokens_corpus)
    return bm25, meta_list


@lru_cache(maxsize=1)
def _load_bm25() -> tuple[BM25Okapi, List[Dict[str, str]]]:
    """Return the memoised BM25 & metadata list, building (and caching) if needed."""

    if _BM25_CACHE_PATH.exists():
        try:
            with _BM25_CACHE_PATH.open("rb") as fh:
                bm25, meta_list = pickle.load(fh)
            return bm25, meta_list
        except Exception as exc:  # noqa: BLE001
            # Corrupted cache – rebuild afresh
            print(f"[WARN] Corrupted BM25 cache – rebuilding. ({exc})")

    bm25, meta_list = _build_bm25()

    # Persist cache directory if required
    try:
        _BM25_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _BM25_CACHE_PATH.open("wb") as fh:
            pickle.dump((bm25, meta_list), fh)
    except Exception as exc:  # noqa: BLE001
        # Non-fatal – cache is only an optimisation
        print(f"[WARN] Could not write BM25 cache: {exc}")

    return bm25, meta_list


@lru_cache(maxsize=1)
def _load_embedder() -> HuggingFaceEmbeddings:  # noqa: D401
    """Singleton embedding model – heavy to load, so cache for tool lifetime."""

    return HuggingFaceEmbeddings(model_name=_EMBED_MODEL_NAME)


@lru_cache(maxsize=1)
def _load_vectorstore() -> FAISS:  # noqa: D401
    """Load FAISS vector store once and memoise along with course-id map."""

    embeddings = _load_embedder()
    if not _VECTORSTORE_DIR.exists():
        raise RuntimeError(f"Vector store directory not found: {_VECTORSTORE_DIR}")

    vect = FAISS.load_local(
        str(_VECTORSTORE_DIR), embeddings, allow_dangerous_deserialization=True
    )

    # Build once and attach to vectorstore to avoid O(N) scans later.
    cid_map: Dict[str, Document] = {}
    for doc in vect.docstore._dict.values():  # type: ignore[attr-defined]
        cid = doc.metadata.get("course_id")
        if cid and cid not in cid_map:
            cid_map[cid] = doc

    # Attach as private attribute (non-breaking for external callers)
    setattr(vect, "_cid_map", cid_map)
    return vect


@lru_cache(maxsize=1)
def _course_id_to_doc() -> Dict[str, Document]:  # noqa: D401
    """Return memoised course-ID → :class:`Document` mapping."""

    vect = _load_vectorstore()
    return getattr(vect, "_cid_map")  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Core hybrid search ---------------------------------------------------------
# ---------------------------------------------------------------------------


def _hybrid_search(query: str, top_k: int) -> List[CourseSearchResult]:  # noqa: D401
    """BM25 filter + dense re-rank returning the *top_k* results."""

    bm25, meta_list = _load_bm25()

    # ------------------------------------------------------------------
    # Stage 1 – Sparse BM25 filter (top-40 docs) ------------------------
    # ------------------------------------------------------------------

    # Cheap, reusable tokenisation
    query_tokens = query.lower().split()

    # Faster top-N retrieval (avoids full score array creation)
    candidate_indices = bm25.get_top_n(query_tokens, list(range(len(meta_list))), n=40)

    if not candidate_indices:
        return []

    candidate_meta = [meta_list[i] for i in candidate_indices]

    # ------------------------------------------------------------------
    # Stage 2 – Dense similarity (cosine distance) ---------------------
    # ------------------------------------------------------------------

    embedder = _load_embedder()
    query_vec = np.asarray(embedder.embed_query(query), dtype=np.float32)
    q_norm = np.linalg.norm(query_vec)

    course_docs_map = _course_id_to_doc()

    doc_ids: List[str] = []
    doc_vecs_list: List[np.ndarray] = []

    for meta in candidate_meta:
        cid = meta.get("course_id")
        if not cid or cid not in course_docs_map:
            continue

        doc_ids.append(cid)

        # Fetch from cache or compute embedding
        if cid in _DOC_EMB_CACHE:
            doc_vecs_list.append(_DOC_EMB_CACHE[cid])
        else:
            vec = np.asarray(embedder.embed_documents([course_docs_map[cid].page_content])[0], dtype=np.float32)
            _DOC_EMB_CACHE[cid] = vec
            doc_vecs_list.append(vec)

    if not doc_vecs_list:
        return []

    doc_vecs = np.vstack(doc_vecs_list)
    doc_norms = np.linalg.norm(doc_vecs, axis=1)

    # Cosine similarity → distance
    similarities = (doc_vecs @ query_vec) / (doc_norms * q_norm + 1e-10)
    distances = 1.0 - similarities  # Lower is closer per spec

    # ------------------------------------------------------------------
    # Select *top_k* smallest distances efficiently --------------------
    # ------------------------------------------------------------------

    if len(distances) > top_k:
        top_indices = np.argpartition(distances, top_k)[:top_k]
        top_indices = top_indices[np.argsort(distances[top_indices])]  # sort by actual dist
    else:
        top_indices = np.argsort(distances)

    results: List[CourseSearchResult] = []
    for idx in top_indices:
        cid = doc_ids[idx]
        doc = course_docs_map[cid]
        meta = doc.metadata

        excerpt = doc.page_content[:120].rstrip()
        if len(doc.page_content) > 120:
            excerpt += "…"

        results.append(
            CourseSearchResult(
                course_code=meta.get("course_code", "UNKNOWN"),
                course_id=meta.get("course_id"),
                program_name=meta.get("program_name", "UNKNOWN"),
                units=meta.get("units"),
                description_excerpt=excerpt,
            )
        )

    return results


# ---------------------------------------------------------------------------
# LangChain wrapper ----------------------------------------------------------
# ---------------------------------------------------------------------------


def _search_courses(*, query: str, top_k: int = 5):  # type: ignore[override]
    """Public function exposed via StructuredTool."""

    hits = _hybrid_search(query=query, top_k=top_k)
    if not hits:
        raise SearchFailureError("No courses matched the given query.")

    return CSOut(results=hits).model_dump(mode="json")


CourseSearchTool: StructuredTool = StructuredTool.from_function(
    func=_search_courses,
    name="course_search",
    description=(
        "Hybrid BM25 + dense semantic search across all Santa Monica College courses. "
        "Returns the top-k most relevant courses with basic metadata."
    ),
    args_schema=CSIn,
    return_schema=CSOut,
)

# Public exports ------------------------------------------------------------

__all__ = [
    "CourseSearchTool",
    "SearchFailureError",
    "CourseSearchResult",
]

# ---------------------------------------------------------------------------
# Manual testing helper ------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover – manual debug run
    import json as _json

    res = CourseSearchTool.invoke({"query": "Introductory chemistry", "top_k": 5})
    print(_json.dumps(res, indent=2, ensure_ascii=False))
