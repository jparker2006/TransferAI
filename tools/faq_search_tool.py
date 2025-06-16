from __future__ import annotations

"""TransferAI – FAQ Search Tool

LangChain ``StructuredTool`` that performs a semantic similarity search across
all Santa Monica College FAQ documents (Counseling, International Education,
Online Learning).

The FAQ corpus has been embedded and indexed into a FAISS vector store located
at:
```
TransferAI/data/vector_db/vectorstores/smc_faq_faiss/
```

The vector store was created with OpenAI embeddings (1536-D).  At runtime we
lazily load the FAISS index together with the matching embedder and expose a
simple keyword / natural-language search interface.
"""

from pathlib import Path
import logging
from functools import lru_cache
from typing import List, Optional, Dict
import sys

from langchain_core.tools import StructuredTool
from langchain.docstore.document import Document
from pydantic import BaseModel, Field

# Prefer OpenAI embeddings (guaranteed dimension match with the stored index).
# Fallback to a local HuggingFace model if the OpenAI SDK / API key is
# unavailable so unit-tests can still run offline.
try:
    from langchain_openai import OpenAIEmbeddings as _OpenAIEmbeddings  # type: ignore
except Exception:  # noqa: BLE001
    _OpenAIEmbeddings = None  # type: ignore

try:
    from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
except Exception:  # noqa: BLE001
    HuggingFaceEmbeddings = None  # type: ignore

from langchain_community.vectorstores import FAISS

# Hybrid lexical → semantic retrieval
from rank_bm25 import BM25Okapi
import numpy as np

# ---------------------------------------------------------------------------
# Ensure project root importable when executed directly ----------------------
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":  # pragma: no cover – CLI/pytest support
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------------
# Logging -------------------------------------------------------------------
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Paths ---------------------------------------------------------
# ---------------------------------------------------------------------------

_VECTORSTORE_DIR = Path(__file__).resolve().parents[1] / "data" / "vector_db" / "vectorstores" / "smc_faq_faiss"

# Number of raw hits fetched before optional category filtering – should be
# higher than the final number returned so that category filters do not empty
# the result list too aggressively.
_RAW_K = 10

# Publicly exposed maximum results
_TOP_K = 5

# How many BM25 docs to re-rank via embeddings
_BM25_CANDIDATES = 20

# ---------------------------------------------------------------------------
# Pydantic I/O Schemas -------------------------------------------------------
# ---------------------------------------------------------------------------


class FAQIn(BaseModel):  # noqa: D401
    """Input parameters for :pyattr:`FAQSearchTool`."""

    query: str = Field(..., description="Keyword, phrase, or natural-language question to search.")


class FAQMatch(BaseModel):  # noqa: D401
    """One FAQ hit returned by the tool."""

    question: str
    answer: str
    category: Optional[str] = None
    source: Optional[str] = None
    score: Optional[float] = None  # Cosine similarity in [0, 1] if available


class FAQOut(BaseModel):  # noqa: D401
    """Wrapper holding the list of :class:`FAQMatch`."""

    matches: List[FAQMatch]


# ---------------------------------------------------------------------------
# Embedding & VectorStore loaders ------------------------------------------
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_embedder():  # noqa: D401
    """Return a memoised embedding model instance.

    Order of preference:
    1. ``OpenAIEmbeddings`` – ensures dimensional compatibility (1536-D) with
       the stored index.  Requires *OPENAI_API_KEY* environment variable.
    2. ``HuggingFaceEmbeddings`` – lightweight local model (384-D).  **Only**
       used if OpenAI embeddings cannot be instantiated.  Will raise if the
       resulting dimension is incompatible with the FAISS index.
    """

    if _OpenAIEmbeddings is not None:
        try:
            return _OpenAIEmbeddings()
        except Exception as exc:  # noqa: BLE001
            logger.debug("OpenAIEmbeddings unavailable – falling back (%s)", exc)

    if HuggingFaceEmbeddings is None:
        raise RuntimeError("No viable embedding backend found (OpenAI or HF).")

    # The same model used elsewhere in the project
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _load_vectorstore() -> FAISS:  # noqa: D401
    """Load and memoise the FAISS vector store from disk."""

    if not _VECTORSTORE_DIR.exists():
        raise RuntimeError(f"Vectorstore directory not found: {_VECTORSTORE_DIR}")

    embeddings = _load_embedder()

    vect = FAISS.load_local(
        str(_VECTORSTORE_DIR), embeddings, allow_dangerous_deserialization=True
    )

    # Attach convenience mapping: doc_id -> Document for quick lookup
    id_map: Dict[int, Document] = {}
    for idx, doc in enumerate(vect.docstore._dict.values()):  # type: ignore[attr-defined]
        id_map[idx] = doc
    setattr(vect, "_id_map", id_map)
    return vect


# ---------------------------------------------------------------------------
# BM25 loader ---------------------------------------------------------------
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_bm25() -> tuple[List[Document], BM25Okapi]:  # noqa: D401
    """Build and cache a BM25 index over the entire FAQ corpus (tiny)."""

    vect = _load_vectorstore()
    docs: List[Document] = list(vect.docstore._dict.values())  # type: ignore[attr-defined]
    corpus_tokens = [d.page_content.lower().split() for d in docs]
    bm25 = BM25Okapi(corpus_tokens)
    return docs, bm25


# ---------------------------------------------------------------------------
# Hybrid search helper ------------------------------------------------------
# ---------------------------------------------------------------------------


def _hybrid_search(query: str) -> List[FAQMatch]:  # noqa: D401
    """BM25 lexical pre-filter followed by semantic re-ranking."""

    # ------------------------- 1) BM25 filter -------------------------
    docs, bm25 = _load_bm25()
    tokens = query.lower().split()
    bm25_scores = bm25.get_scores(tokens)  # ndarray[float]

    # Indices of top-N BM25 docs (descending score)
    top_idx = np.argsort(bm25_scores)[::-1][: _BM25_CANDIDATES]

    if len(top_idx) == 0:
        return []

    cand_docs = [docs[i] for i in top_idx]

    # ------------------------- 2) Semantic rank ------------------------
    embedder = _load_embedder()
    q_vec = np.asarray(embedder.embed_query(query), dtype=np.float32)
    cand_vecs = np.asarray(
        embedder.embed_documents([d.page_content for d in cand_docs]), dtype=np.float32
    )

    # Cosine similarities
    q_vec /= np.linalg.norm(q_vec) + 1e-10
    cand_vecs /= np.linalg.norm(cand_vecs, axis=1, keepdims=True) + 1e-10
    sims = cand_vecs @ q_vec  # shape (num_cand,)

    # ------------------------- 3) Assemble results --------------------
    ranked_idx = np.argsort(sims)[::-1][: _TOP_K]

    matches: List[FAQMatch] = []
    for idx in ranked_idx:
        doc = cand_docs[idx]
        sim = sims[idx]
        meta = doc.metadata or {}

        matches.append(
            FAQMatch(
                question=meta.get("question", ""),
                answer=meta.get("answer", doc.page_content),
                category=(meta.get("category") or "").strip() or None,
                source=meta.get("source", meta.get("url")),
                score=round(float(sim), 4),
            )
        )

    return matches


# ---------------------------------------------------------------------------
# Tool entry point ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _search_faq(*, query: str):  # type: ignore[override]
    """Public function exposed via :class:`StructuredTool`."""

    logger.info("FAQ search invoked | query='%s'", query)

    hits = _hybrid_search(query=query)
    logger.info("FAQ search returned %d hit(s)", len(hits))

    return FAQOut(matches=hits).model_dump(mode="json")


FAQSearchTool: StructuredTool = StructuredTool.from_function(
    func=_search_faq,
    name="faq_search",
    description="Hybrid BM25 + embedding search across SMC FAQ corpus.",
    args_schema=FAQIn,
    return_schema=FAQOut,
)

__all__ = ["FAQSearchTool"]

# ---------------------------------------------------------------------------
# Manual testing helper ------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover – manual debug run
    import json as _json

    tool = FAQSearchTool
    sample = {"query": "academic probation"}
    res = tool.invoke(sample)
    print(_json.dumps(res, indent=2, ensure_ascii=False))
