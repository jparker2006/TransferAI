from __future__ import annotations

"""Unit tests for DeadlineLookupTool.

The tests deliberately avoid loading the heavy FAISS vector store by targeting
queries that are resolvable via date parsing or simple lexical matching.  This
keeps runtime under the 3-second CI budget while still exercising the critical
branches of the hybrid retrieval logic.
"""

import sys
from pathlib import Path
import os

import pytest

# Ensure project root importability -------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Skip heavy vectorstore during unit tests ------------------------------------------------
os.environ["TRANSFERAI_SKIP_VECTORSTORE"] = "1"

from tools.deadline_lookup_tool import DeadlineLookupTool  # noqa: E402

TOOL = DeadlineLookupTool  # singleton


# -----------------------------------------------------------------------------
# 1. Exact title lookup ---------------------------------------------------------
# -----------------------------------------------------------------------------

def test_exact_title_lookup() -> None:  # noqa: D401
    query = "Deadline to Accept UC San Diego's Offer of Admission"
    result = TOOL.invoke({"query": query})

    assert result["matches"], "No matches returned for exact title query"
    first = result["matches"][0]
    assert first["date"] == "June 1"
    assert "Accept UC San Diego" in first["title"]


# -----------------------------------------------------------------------------
# 2. Explicit date lookup -------------------------------------------------------
# -----------------------------------------------------------------------------


def test_single_date_lookup() -> None:  # noqa: D401
    result = TOOL.invoke({"query": "July 15"})
    titles = {m["title"] for m in result["matches"]}
    assert "AP and IB Exam Results Due" in titles


# -----------------------------------------------------------------------------
# 3. Date range lookup ----------------------------------------------------------
# -----------------------------------------------------------------------------


def test_date_range_lookup() -> None:  # noqa: D401
    result = TOOL.invoke({"query": "deadlines between May 1-May 31"})
    dates = {m["date"] for m in result["matches"]}
    # Expect May 9 and May 15 events in range
    assert "May 9" in dates and "May 15" in dates, "Range query missed expected events"


# -----------------------------------------------------------------------------
# 4. Fuzzy / semantic lookup ----------------------------------------------------
# -----------------------------------------------------------------------------


def test_fuzzy_query_lookup() -> None:  # noqa: D401
    result = TOOL.invoke({"query": "fafsa due"})
    assert result["matches"], "No matches for fuzzy 'fafsa' query"
    # April 2 event should be among the first results
    assert any(
        "FAFSA" in match["title"] and match["date"] == "April 2" for match in result["matches"]
    ), "FAFSA deadline not found" 