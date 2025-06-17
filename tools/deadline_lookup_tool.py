from __future__ import annotations

"""TransferAI – UC/SMC Deadline Lookup Tool

This module exposes a ``DeadlineLookupTool`` StructuredTool instance which can
answer natural-language queries about upcoming UC San Diego transfer
application deadlines *and* (in the near future) Santa Monica College academic
term dates.

The public contract is intentionally simple – callers supply an arbitrary text
``query`` and the tool returns a *JSON-serialisable* dictionary with two keys:

``matches``
    A chronologically-sorted list of deadline records pulled from the bundled
    JSON timelines.  Each record is a subset of the original schema plus a
    ``source_file`` key indicating the data source.

``query_interpretation``
    A short human-readable sentence describing how the query was interpreted
    (e.g. *"single date match for July 15"* or *"semantic search for 'fafsa'"*).

The implementation follows the hybrid retrieval specification provided in the
project brief:

1. **Explicit/relative date detection** via :pypi:`dateparser` – if the query
   contains any date tokens we try to resolve them to a *single* date or a
   date **range** (e.g. *"between May 1 – May 31"*, *"next week"*).  Matching
   events are selected by range-overlap.
2. **Semantic search** leveraging a Sentence-Transformer FAISS index (stored
   under ``data/vector_db/vectorstores/ucsd_transfer_timeline_faiss``).
   • We fetch the top-40 vector hits, then
   • re-rank them with BM25 scores over each event's ``searchable_text``, then
   • apply a RapidFuzz filter (token_set_ratio ≥ 75) to boost precision.
3. If the semantic stage yields fewer than three results we *fallback* to a
   pure BM25 search across **all** events.

Heavy objects (timeline data, FAISS index, embedding model, BM25 corpus) are
memoised with :pyfunc:`functools.lru_cache` so that subsequent invocations
incur negligible latency (important for unit-tests and chained tool calls).

Example
-------
>>> from tools.deadline_lookup_tool import DeadlineLookupTool
>>> DeadlineLookupTool.invoke({"query": "fafsa due"})
{'matches': [{'date': 'April 2', 'title': 'File Your FAFSA or California Dream Act Application', ...}],
 'query_interpretation': "semantic match for keyword 'fafsa'"}

Edge cases handled
------------------
* No recognised dates *and* no sufficiently similar semantic hits  → empty
  ``matches`` list with a friendly ``query_interpretation``.
* Queries resolving to **future** or **past** dates outside the timeline range
  simply return no matches – we do **not** attempt year inference yet (stretch).

The code purposefully avoids heavyweight dependencies other than the allowed
``faiss-cpu``, ``rank-bm25``, ``rapidfuzz`` and ``dateparser``.
"""

from pathlib import Path
import json
import logging
import re
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---------------------------------------------------------------------------
# StructuredTool import with graceful fallback if *langchain_core* is missing
# ---------------------------------------------------------------------------
try:
    from langchain_core.tools import StructuredTool  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – minimal local stub
    from typing import Callable

    class StructuredTool:  # type: ignore
        """Minimal fallback StructuredTool for CI environments without LangChain."""

        def __init__(self, *, func: Callable[..., Any], name: str, description: str, args_schema: Any, return_schema: Any):  # noqa: D401,E501
            self._func = func
            self.name = name
            self.description = description
            self.args_schema = args_schema
            self.return_schema = return_schema

        def __call__(self, **kwargs):  # noqa: D401
            return self._func(**kwargs)

        def invoke(self, inputs: Dict[str, Any]):  # noqa: D401
            return self._func(**inputs)

        @classmethod
        def from_function(cls, func: Callable[..., Any], name: str, description: str, args_schema: Any, return_schema: Any):  # noqa: D401,E501
            return cls(func=func, name=name, description=description, args_schema=args_schema, return_schema=return_schema)

# ---------------------------------------------------------------------------
# Optional heavy deps – only imported lazily inside cached loader
# ---------------------------------------------------------------------------
try:
    from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
    from langchain_community.vectorstores import FAISS  # type: ignore
except Exception:  # noqa: BLE001
    # Unit-test / minimal environment – semantic search will degrade gracefully
    HuggingFaceEmbeddings = None  # type: ignore[assignment]
    FAISS = None  # type: ignore

# ---------------------------------------------------------------------------
# Optional dependency: rapidfuzz – fallback to difflib if unavailable
# ---------------------------------------------------------------------------
try:
    from rapidfuzz import fuzz  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import difflib

    class _FuzzStub:  # noqa: D401 – minimal subset
        @staticmethod
        def token_set_ratio(a: str, b: str) -> int:  # noqa: D401
            return int(difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio() * 100)

    fuzz = _FuzzStub()  # type: ignore

# ---------------------------------------------------------------------------
# Optional dependency: rank_bm25 – provide no-op stub if unavailable
# ---------------------------------------------------------------------------
try:
    from rank_bm25 import BM25Okapi  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    class BM25Okapi:  # type: ignore
        def __init__(self, corpus):  # noqa: D401
            self._corpus_len = len(corpus)

        def get_scores(self, query_tokens):  # noqa: D401
            # Return uniform scores so that downstream logic still works.
            return [0.0] * self._corpus_len

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------

_ROOT = Path(__file__).resolve().parents[1]
_DEADLINE_DIRS: Tuple[Path, ...] = (
    _ROOT / "data" / "deadlines",  # primary location (future-proof)
    _ROOT / "data" / "UCSD_transfer_timeline",  # current repo location
)
_VECTORSTORE_PATH = (
    _ROOT
    / "data"
    / "vector_db"
    / "vectorstores"
    / "ucsd_transfer_timeline_faiss"
)
_VECTOR_MODEL_NAME = "all-MiniLM-L6-v2"

# Priority ordering used for secondary sort (chronological first)
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _parse_event_date_range(date_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Attempt to convert **arbitrary** timeline ``date`` strings into
    concrete ``(start, end)`` datetime objects.  The function is **best-effort** –
    for ill-formed values we return ``(None, None)`` which signals to callers
    that the entry should *always* be considered a match in semantic mode
    (date-based filters must check for ``None`` start/end).
    """

    # Normalise whitespace and remove leading qualifiers ("By", "On", etc.)
    cleaned = date_str.strip()
    cleaned = re.sub(r"^By\s+", "", cleaned, flags=re.I)

    # ------------------------------------------------------------------
    # Simple single-date cases – e.g. "July 15", "April 2"
    # ------------------------------------------------------------------
    single = dateparser.parse(cleaned, settings={"PREFER_DAY_OF_MONTH": "first"})
    if single and "-" not in cleaned:
        return single, single

    # ------------------------------------------------------------------
    # Date ranges – detect the separator "-" or "to"
    # ------------------------------------------------------------------
    # Examples: "October 1 - December 2", "May 1 to May 31"
    match = re.match(r"(.*?)\s*(?:-|to)\s*(.*)", cleaned, flags=re.I)
    if match:
        start_raw, end_raw = match.groups()
        start_dt = dateparser.parse(start_raw.strip())
        end_dt = dateparser.parse(end_raw.strip())
        return start_dt, end_dt

    # Month-only values like "October" – treat entire month
    month_only = dateparser.parse(cleaned, settings={"PREFER_DAY_OF_MONTH": "first"})
    if month_only and month_only.day == 1 and " " not in cleaned:
        # compute end of month by adding one month then subtracting a day
        next_month = month_only.replace(day=28) + timedelta(days=4)
        end_of_month = next_month - timedelta(days=next_month.day)
        return month_only, end_of_month

    # Fallback – unknown format
    return None, None


@lru_cache(maxsize=1)
def _load_timeline_events() -> List[Dict[str, Any]]:
    """Load **all** timeline JSON files into a flat list of event dicts.

    The returned objects are *augmented* with helper keys:
    ``start_dt``, ``end_dt`` and ``source_file``.
    """

    events: List[Dict[str, Any]] = []

    for folder in _DEADLINE_DIRS:
        if not folder.exists():
            continue
        for json_file in folder.glob("*.json"):
            try:
                with json_file.open("r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed loading %s: %s", json_file, exc)
                continue

            for item in data.get("timeline", []):
                start_dt, end_dt = _parse_event_date_range(item.get("date", ""))
                item["start_dt"] = start_dt
                item["end_dt"] = end_dt
                item["source_file"] = json_file.name
                events.append(item)

    if not events:
        raise RuntimeError("No timeline JSON files found in configured directories")

    return events


# ---------------------------------------------------------------------------
# Semantic search helpers – wrapped in lru_cache to avoid repeated heavy loads
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_vectorstore():  # noqa: D401
    """Load the FAISS vector store if present; return *None* on failure.

    Gracefully handles missing files or optional dependencies so that date/BM25
    queries can still function in constrained environments (e.g. CI).
    """

    import os

    # CI / unit-test shortcut -------------------------------------------------
    if os.environ.get("TRANSFERAI_SKIP_VECTORSTORE") == "1":
        logger.info("Vectorstore loading skipped via TRANSFERAI_SKIP_VECTORSTORE=1")
        return None

    if not _VECTORSTORE_PATH.exists():
        logger.info("Vector store not found – semantic search disabled (path=%s)", _VECTORSTORE_PATH)
        return None

    if HuggingFaceEmbeddings is None or FAISS is None:
        logger.info("LangChain FAISS/HF dependencies unavailable – semantic search disabled")
        return None

    try:
        embedder = HuggingFaceEmbeddings(model_name=_VECTOR_MODEL_NAME)
        store = FAISS.load_local(
            str(_VECTORSTORE_PATH), embedder, allow_dangerous_deserialization=True
        )
        return store
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to load vectorstore: %s", exc)
        return None


# ---------------------------------------------------------------------------
# BM25 helper – we build corpus from searchable_text across events
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _build_bm25() -> Tuple[BM25Okapi, List[Dict[str, Any]]]:
    events = _load_timeline_events()
    tokenised_corpus: List[List[str]] = []
    for ev in events:
        text = (ev.get("searchable_text") or "")
        tokens = re.findall(r"\w+", text.lower())
        tokenised_corpus.append(tokens)
    bm25 = BM25Okapi(tokenised_corpus)
    return bm25, events


# ---------------------------------------------------------------------------
# Query interpretation helpers
# ---------------------------------------------------------------------------

def _extract_explicit_dates(query: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Return (start, end) if query contains explicit/relative date tokens.

    If multiple dates are found and the wording includes *between* or a dash,
    the smallest and largest dates are returned.  For single date queries the
    same value is returned for start and end.
    """

    dates_found: List[Tuple[str, datetime]] = search_dates(query, settings={"RELATIVE_BASE": datetime.now()}) or []
    if not dates_found:
        return None, None

    dts = [dt for _span, dt in dates_found]
    dts.sort()

    # Heuristic: if query says "between" or contains "-" treat as range
    if re.search(r"\bbetween\b|\bfrom\b|\-", query, flags=re.I) and len(dts) >= 2:
        return dts[0], dts[-1]

    # Relative words like "next week" may produce two dates (start/end).  If
    # the delta between min/max is <= 14 days we still treat as range.
    if len(dts) >= 2 and (dts[-1] - dts[0]).days <= 14:
        return dts[0], dts[-1]

    # Fallback – single date
    return dts[0], dts[0]


# ---------------------------------------------------------------------------
# Core search functions
# ---------------------------------------------------------------------------

def _date_based_search(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    events = _load_timeline_events()
    matches: List[Dict[str, Any]] = []
    for ev in events:
        s_dt: Optional[datetime] = ev.get("start_dt")
        e_dt: Optional[datetime] = ev.get("end_dt")
        if s_dt is None or e_dt is None:
            # Unknown dates – ignore for date queries
            continue
        if s_dt <= end and e_dt >= start:
            matches.append(ev)
    return matches


def _semantic_search(query: str) -> List[Dict[str, Any]]:
    """Return top candidate events for *query* using the hybrid pipeline."""

    store = _load_vectorstore()
    events = _load_timeline_events()

    # ---------------------------------------------------------------
    # Stage 1 – FAISS semantic search (if available)
    # ---------------------------------------------------------------
    candidate_idxs: List[int] = []
    if store is not None:
        try:
            docs = store.similarity_search(query, k=40)
            # Extract original index stored in doc.metadata["id"] if present,
            # else fall back to linear index by matching title/dates.
            meta_ids = [d.metadata.get("orig_index") for d in docs]
            if all(m is not None for m in meta_ids):
                candidate_idxs = [int(m) for m in meta_ids]  # type: ignore[arg-type]
            else:
                # Fallback – brute force match by (title, date)
                doc_keys = {(d.metadata.get("title"), d.metadata.get("date")) for d in docs}
                for i, ev in enumerate(events):
                    if (ev.get("title"), ev.get("date")) in doc_keys:
                        candidate_idxs.append(i)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vectorstore search failed: %s", exc)

    # If FAISS unavailable fall back to all indices (still filtered later)
    if not candidate_idxs:
        candidate_idxs = list(range(len(events)))

    # ---------------------------------------------------------------
    # Stage 2 – BM25 re-ranking
    # ---------------------------------------------------------------
    bm25, _ = _build_bm25()
    tokenised_query = re.findall(r"\w+", query.lower())

    scores = bm25.get_scores(tokenised_query)
    # Compose tuples (idx, bm25_score)
    scored_candidates = [(idx, scores[idx]) for idx in candidate_idxs]

    # ---------------------------------------------------------------
    # Stage 3 – RapidFuzz filter (≥ 75)
    # ---------------------------------------------------------------
    filtered: List[Tuple[int, float]] = []
    for idx, score in scored_candidates:
        ev = events[idx]
        ratio = fuzz.token_set_ratio(query, ev.get("searchable_text", ""))
        if ratio >= 75:
            filtered.append((idx, score))

    # Fallback to pure BM25 only if **no** hits survived the RapidFuzz filter.
    if not filtered:
        logger.debug("Hybrid retrieval yielded 0 hits – falling back to pure BM25")
        filtered = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:10]  # take top-10

    # Sort by BM25 descending
    filtered.sort(key=lambda x: x[1], reverse=True)

    matched_events = [events[idx] for idx, _sc in filtered]
    return matched_events


# ---------------------------------------------------------------------------
# Utility – final sort and projection
# ---------------------------------------------------------------------------

def _prepare_output(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Chronological sort primary
    def key(ev: Dict[str, Any]):
        s_dt: Optional[datetime] = ev.get("start_dt")
        if s_dt is None:
            # put unknown dates at end
            s_dt = datetime.max
        priority = _PRIORITY_RANK.get(ev.get("priority", "medium"), 1)
        return s_dt, priority

    sorted_events = sorted(events, key=key)

    output: List[Dict[str, Any]] = []
    for ev in sorted_events:
        output.append(
            {
                "date": ev.get("date"),
                "title": ev.get("title"),
                "description": ev.get("description"),
                "category": ev.get("category"),
                "source_file": ev.get("source_file"),
            }
        )
    return output


# ---------------------------------------------------------------------------
# LangChain StructuredTool adapter
# ---------------------------------------------------------------------------


def _lookup_deadline(*, query: str) -> Dict[str, Any]:  # noqa: D401
    query = query.strip()

    # 1. Date / relative date detection -----------------------------------
    start_dt, end_dt = _extract_explicit_dates(query)

    if start_dt is not None and end_dt is not None:
        matches = _date_based_search(start_dt, end_dt)
        interpretation = (
            f"date range {start_dt.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')}"
            if start_dt != end_dt
            else f"single date match for {start_dt.strftime('%Y-%m-%d')}"
        )
    else:
        # 2. Hybrid semantic search -------------------------------------
        matches = _semantic_search(query)
        interpretation = f"semantic search for '{query}'"

        # If any match title closely matches query (>= 90 ratio) keep only those
        high_title_matches = [
            ev for ev in matches if fuzz.token_set_ratio(query, ev.get("title", "")) >= 90
        ]
        if high_title_matches:
            matches = high_title_matches

    if not matches:
        return {"matches": [], "query_interpretation": "no deadlines found"}

    return {"matches": _prepare_output(matches), "query_interpretation": interpretation}


# Input/Output Pydantic schemas --------------------------------------------

from pydantic import BaseModel, Field  # noqa: E402 – local import after docstring


class DLIn(BaseModel):  # noqa: D401
    """Input schema – single required text query."""

    query: str = Field(..., description="Natural-language search query")


class _Match(BaseModel):
    date: str
    title: str
    description: Optional[str] = None
    category: str
    source_file: str


class DLOut(BaseModel):  # noqa: D401
    matches: List[_Match]
    query_interpretation: str


# Public StructuredTool instance
DeadlineLookupTool: StructuredTool = StructuredTool.from_function(
    func=_lookup_deadline,
    name="deadline_lookup",
    description="Return UC application or Santa Monica College term deadlines. Input: query.",
    args_schema=DLIn,
    return_schema=DLOut,
)

object.__setattr__(DeadlineLookupTool, "return_schema", DLOut)


# ---------------------------------------------------------------------------
# Optional dependency: *dateparser* – fall back to a lightweight stub if absent
# ---------------------------------------------------------------------------
try:
    import dateparser  # type: ignore
    from dateparser.search import search_dates  # type: ignore
except ModuleNotFoundError:  # pragma: no cover – stub for minimal CI env
    # ---------------------------------------------------------------------
    # Lightweight fallback using python-dateutil so that unit-tests which
    # exercise only a handful of fixed dates (e.g. "July 15") still pass in
    # environments where *dateparser* is not installed.  The fallback is **not**
    # feature-complete – it handles only explicit "<Month> <DD>" patterns and
    # ignores relative phrases ("next week", etc.).
    # ---------------------------------------------------------------------
    from dateutil import parser as _dt_parser  # type: ignore

    _MONTH_PATTERN = re.compile(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}",
        flags=re.I,
    )

    def _fallback_parse(text: str, *, settings: Optional[dict] = None):  # type: ignore[override]
        try:
            return _dt_parser.parse(text, fuzzy=True, dayfirst=False)
        except Exception:  # noqa: BLE001
            return None

    def _fallback_search_dates(query: str, *, settings: Optional[dict] = None):  # type: ignore[override]
        results: List[Tuple[str, datetime]] = []
        for match in _MONTH_PATTERN.finditer(query):
            span = match.group(0)
            dt = _fallback_parse(span)
            if dt:
                results.append((span, dt))
        return results or None

    class _DateParserStub:  # noqa: D401 – minimal interface shim
        @staticmethod
        def parse(text: str, settings: Optional[dict] = None):  # type: ignore[override]
            return _fallback_parse(text, settings=settings)

    dateparser = _DateParserStub()  # type: ignore
    search_dates = _fallback_search_dates  # type: ignore


# ---------------------------------------------------------------------------
# CLI helper – run with `python -m tools.deadline_lookup_tool --query "..."`
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import json as _json

    parser = argparse.ArgumentParser(description="CLI wrapper around DeadlineLookupTool")
    parser.add_argument("--query", required=True, help="Natural-language query, e.g. 'July 15 deadlines'")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    result = DeadlineLookupTool.invoke({"query": args.query})

    if args.pretty:
        print(_json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(_json.dumps(result, ensure_ascii=False))



