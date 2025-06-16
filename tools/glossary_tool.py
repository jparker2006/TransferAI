from __future__ import annotations

"""TransferAI – Glossary Search Tool

Hybrid BM25 + embedding search across the Transfer Term Glossary.

The glossary has been embedded into a FAISS vector store using OpenAI
embeddings (1536-D) and resides under:
```
TransferAI/data/vector_db/vectorstores/transfer_terms_faiss/
```

This tool exposes a single StructuredTool – *glossary_search* – that answers
"What does <term> mean?"-style queries returning the top-5 most relevant
entries.
"""

from pathlib import Path
import logging
from functools import lru_cache
from typing import List, Optional, Dict
import sys
import re
import json

from langchain_core.tools import StructuredTool
from langchain.docstore.document import Document
from pydantic import BaseModel, Field
from langchain_community.vectorstores import FAISS

# Hybrid lexical → semantic retrieval
from rank_bm25 import BM25Okapi
import numpy as np

# ---------------------------------------------------------------------------
# Ensure project root importable when executed directly ----------------------
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":  # pragma: no cover – CLI support
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

# Re-use embedder loader from the FAQ tool to avoid duplication
from tools.faq_search_tool import _load_embedder  # noqa: E402  – internal import

# ---------------------------------------------------------------------------
# Logging --------------------------------------------------------------------
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants ------------------------------------------------------------------
# ---------------------------------------------------------------------------

_VECTORSTORE_DIR = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "vector_db"
    / "vectorstores"
    / "transfer_terms_faiss"
)

_BM25_CANDIDATES = 25
_TOP_K = 5

# ---------------------------------------------------------------------------
# Pydantic Schemas -----------------------------------------------------------
# ---------------------------------------------------------------------------


class GlossaryIn(BaseModel):  # noqa: D401
    """Input parameters for :pyattr:`GlossaryTool`."""

    query: str = Field(..., description="Word, phrase, or question to look up in the glossary.")


class GlossaryMatch(BaseModel):  # noqa: D401
    """One glossary entry returned by the tool."""

    term: str
    definition: str
    category: Optional[str] = None
    context: Optional[str] = None
    score: Optional[float] = None  # Cosine similarity ∈ [0, 1]


class GlossaryOut(BaseModel):  # noqa: D401
    """Wrapper holding a list of :class:`GlossaryMatch`."""

    matches: List[GlossaryMatch]


# ---------------------------------------------------------------------------
# FAISS vectorstore loader ---------------------------------------------------
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_vectorstore() -> FAISS:  # noqa: D401
    """Load and memoise the glossary FAISS store."""

    if not _VECTORSTORE_DIR.exists():
        raise RuntimeError(f"Vectorstore directory not found: {_VECTORSTORE_DIR}")

    embeddings = _load_embedder()

    vect = FAISS.load_local(
        str(_VECTORSTORE_DIR), embeddings, allow_dangerous_deserialization=True
    )

    # Attach id → doc mapping for convenience
    id_map: Dict[int, Document] = {}
    for idx, doc in enumerate(vect.docstore._dict.values()):  # type: ignore[attr-defined]
        id_map[idx] = doc
    setattr(vect, "_id_map", id_map)
    return vect


# ---------------------------------------------------------------------------
# BM25 loader ----------------------------------------------------------------
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _load_bm25() -> tuple[List[Document], BM25Okapi]:  # noqa: D401
    """Construct (and cache) BM25 over all glossary docs."""

    vect = _load_vectorstore()
    docs: List[Document] = list(vect.docstore._dict.values())  # type: ignore[attr-defined]

    corpus_tokens: List[List[str]] = []
    for d in docs:
        meta = d.metadata or {}
        term = str(meta.get("term", "")).lower()
        aliases = " ".join(str(a).lower() for a in meta.get("aliases", []))

        combined = f"{term} {aliases} {d.page_content}".strip().lower()
        corpus_tokens.append(combined.split())

    bm25 = BM25Okapi(corpus_tokens)
    return docs, bm25


# ---------------------------------------------------------------------------
# Alias map builder ---------------------------------------------------------
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _build_alias_map() -> Dict[str, str]:  # noqa: D401
    """Scan glossary data building a lowercase {alias -> canonical_term} map."""

    alias_map: Dict[str, str] = {}

    json_path = (
        Path(__file__).resolve().parents[1] / "data" / "transfer_terms.json"
    )

    docs: List[Document]
    if json_path.exists():
        try:
            with json_path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
            docs = [Document(page_content=item.get("definition", ""), metadata=item) for item in raw]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to parse glossary JSON – falling back to FAISS (%s)", exc)
            docs = list(_load_vectorstore().docstore._dict.values())  # type: ignore[attr-defined]
    else:
        docs = list(_load_vectorstore().docstore._dict.values())  # type: ignore[attr-defined]

    for d in docs:
        meta = d.metadata or {}
        term = str(meta.get("term", "")).strip()
        if not term:
            continue

        term_lc = term.lower()

        # 1) explicit aliases list
        for alias in meta.get("aliases", []):
            alias_map[str(alias).strip().lower()] = term_lc

        # 2) parenthetical acronym at end
        m = re.search(r"\(([^)]+)\)$", term)
        if m:
            candidate = m.group(1).strip()
            if 2 <= len(candidate) <= 10:
                alias_map[candidate.lower()] = term_lc

        # 3) slash-separated alt labels (only first split for pairs)
        if "/" in term:
            parts = [p.strip() for p in term.split("/")]
            if len(parts) == 2:
                alias_map[parts[0].lower()] = parts[1].lower()
                alias_map[parts[1].lower()] = parts[0].lower()

        # 4) generated acronym from initials
        words = re.findall(r"[A-Za-z]+", term)
        if len(words) >= 2:
            acronym = "".join(w[0] for w in words).upper()
            if 2 <= len(acronym) <= 6 and acronym.lower() != term_lc:
                alias_map[acronym.lower()] = term_lc

    # Fallback hard-coded examples if nothing extracted
    if not alias_map:
        alias_map.update(
            {
                "prereq": "prerequisite",
                "tag": "transfer admission guarantee",
                "igetc": "intersegmental general education transfer curriculum",
            }
        )

    logger.info("Glossary alias map built (%d entries)", len(alias_map))
    return alias_map


# Build once at import time (memoised function ensures cheap subsequent calls)
_ALIAS: Dict[str, str] = _build_alias_map()


def _expand_aliases(tokens: List[str]) -> List[str]:  # noqa: D401
    """Return *tokens* plus expansions based on the alias map."""

    expanded: List[str] = []
    for t in tokens:
        t_lc = t.lower()
        expanded.append(t_lc)
        if t_lc in _ALIAS:
            expanded.extend(re.findall(r"[a-z0-9]+", _ALIAS[t_lc]))
    return expanded


# ---------------------------------------------------------------------------
# Hybrid search --------------------------------------------------------------
# ---------------------------------------------------------------------------


def _hybrid_search(query: str) -> List[GlossaryMatch]:  # noqa: D401
    """Perform BM25 → embedding hybrid search returning top‐k entries with alias support."""

    # Replace query if it's an exact alias for a canonical term
    query_lc = query.strip().lower()
    effective_query = _ALIAS.get(query_lc, query)

    # 1) BM25 lexical filter with token expansion
    docs, bm25 = _load_bm25()
    tokens = _expand_aliases(effective_query.lower().split())
    scores = bm25.get_scores(tokens)

    cand_idx = np.argsort(scores)[::-1][: _BM25_CANDIDATES]
    if len(cand_idx) == 0:
        return []

    cand_docs = [docs[i] for i in cand_idx]

    # 2) Semantic re-rank
    embedder = _load_embedder()
    enrich_texts = []
    for d in cand_docs:
        m = d.metadata or {}
        term = str(m.get("term", ""))
        aliases = " ".join(str(a) for a in m.get("aliases", []))
        enrich_texts.append(f"{term} {aliases} {d.page_content}".strip())

    doc_vecs = np.asarray(embedder.embed_documents(enrich_texts), dtype=np.float32)

    q_vec = np.asarray(embedder.embed_query(effective_query), dtype=np.float32)
    q_vec /= np.linalg.norm(q_vec) + 1e-10
    doc_vecs /= np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-10

    sims = doc_vecs @ q_vec  # shape (N,)

    top_idx = np.argsort(sims)[::-1][: _TOP_K]

    matches: List[GlossaryMatch] = []
    for i in top_idx:
        doc = cand_docs[i]
        sim = sims[i]
        meta = doc.metadata or {}

        matches.append(
            GlossaryMatch(
                term=meta.get("term", doc.page_content[:50]),
                definition=meta.get("definition", doc.page_content),
                category=meta.get("category"),
                context=meta.get("context"),
                score=round(float(sim), 4),
            )
        )

    return matches


# ---------------------------------------------------------------------------
# Tool entry point -----------------------------------------------------------
# ---------------------------------------------------------------------------


def _lookup_glossary(*, query: str):  # type: ignore[override]
    """Public wrapper exposed via StructuredTool."""

    hits = _hybrid_search(query=query)
    logger.info("Glossary search | query='%s' | hits=%d", query, len(hits))
    return GlossaryOut(matches=hits).model_dump(mode="json")


GlossaryTool: StructuredTool = StructuredTool.from_function(
    func=_lookup_glossary,
    name="glossary_search",
    description="Hybrid BM25 + embedding search over transfer-term glossary.",
    args_schema=GlossaryIn,
    return_schema=GlossaryOut,
)

__all__ = ["GlossaryTool"]

# ---------------------------------------------------------------------------
# Manual CLI test ------------------------------------------------------------
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover – manual debug run
    import json as _json

    sample = {"query": "GPA"}
    print(_json.dumps(GlossaryTool.invoke(sample), indent=2, ensure_ascii=False))
