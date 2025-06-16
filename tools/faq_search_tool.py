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
from typing import List, Optional, Dict, Any
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

# ---------------------------------------------------------------------------
# Pydantic I/O Schemas -------------------------------------------------------
# ---------------------------------------------------------------------------


class FAQIn(BaseModel):  # noqa: D401
    """Input parameters for :pyattr:`FAQSearchTool`."""

    query: str = Field(..., description="Keyword, phrase, or natural-language question to search.")
    category: Optional[str] = Field(
        None,
        description="(Deprecated) Category hint – currently ignored by the search logic.",
    )


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
# Core search helper --------------------------------------------------------
# ---------------------------------------------------------------------------

def _similarity_search(query: str, category: Optional[str] | None = None) -> List[FAQMatch]:  # noqa: D401
    """Return the top similarity-based FAQ matches (category hint is ignored)."""

    vect = _load_vectorstore()

    # ------------------------------------------------------------------
    # 1. Raw semantic search -------------------------------------------
    # ------------------------------------------------------------------

    try:
        docs_and_scores = vect.similarity_search_with_score(query, k=_RAW_K)
    except Exception as exc:  # noqa: BLE001
        logger.error("Vectorstore search failed: %s", exc)
        return []

    matches: List[FAQMatch] = []

    for doc, dist in docs_and_scores:
        meta = doc.metadata or {}

        doc_cat = (meta.get("category") or "").strip()

        # Convert FAISS L2 distance into cosine similarity estimate if the
        # index was built with normalised vectors (common).  When in doubt,
        # provide 1-distance so that higher is better.
        similarity = 1.0 - float(dist) if dist is not None else None

        matches.append(
            FAQMatch(
                question=meta.get("question", ""),
                answer=meta.get("answer", doc.page_content),
                category=doc_cat or None,
                source=meta.get("source", meta.get("url")),
                score=round(similarity, 4) if similarity is not None else None,
            )
        )

        if len(matches) >= _TOP_K:
            break  # Stop once we have enough

    return matches


# ---------------------------------------------------------------------------
# Tool entry point ----------------------------------------------------------
# ---------------------------------------------------------------------------

def _search_faq(*, query: str, category: Optional[str] = None):  # type: ignore[override]
    """Public function exposed via :class:`StructuredTool`."""

    logger.info("FAQ search invoked | query='%s' | category='%s'", query, category)

    hits = _similarity_search(query=query, category=category)
    logger.info("FAQ search returned %d hit(s)", len(hits))

    return FAQOut(matches=hits).model_dump(mode="json")


FAQSearchTool: StructuredTool = StructuredTool.from_function(
    func=_search_faq,
    name="faq_search",
    description="Search across all SMC FAQ sources using semantic similarity only.",
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
    sample = {"query": "What happens if I miss a class?"}
    res = tool.invoke(sample)
    print(_json.dumps(res, indent=2, ensure_ascii=False))
