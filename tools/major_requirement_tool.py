from __future__ import annotations

# Standard library imports
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Third-party imports
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Optional LangChain dependency – provide a lightweight fallback when absent.
# ---------------------------------------------------------------------------

try:
    # Real import when LangChain is available
    from langchain.tools import StructuredTool  # type: ignore
except ImportError:  # pragma: no cover

    class StructuredTool:  # type: ignore
        """Minimal stub replicating the subset of StructuredTool used here."""

        def __init__(self, *args, **kwargs):  # noqa: D401
            self.name = kwargs.get("name", "major_requirement_tool")

        @classmethod
        def from_function(cls, **kwargs):  # noqa: D401
            return cls()

# ---------------------------------------------------------------------------
# Constants (these can be monkey-patched in the unit-tests)
# ---------------------------------------------------------------------------

# NOTE: The ASSIST folder was renamed a few times in the repository's history.
# We defensively try both spellings (with and without the trailing "s").
try:
    _PACKAGE_ROOT = Path(__file__).resolve().parents[1]
except NameError:
    # Fallback when __file__ is not available (e.g., exec() context)
    _PACKAGE_ROOT = Path.cwd()

_ASSIST_CANDIDATE_DIRS: Tuple[Path, ...] = (
    _PACKAGE_ROOT
    / "data"
    / "assist_articulation_v2"
    / "rag_output"
    / "santa_monica_college"
    / "university_of_california_san_diego",
    _PACKAGE_ROOT
    / "data"
    / "assist_articulations_v2"  # legacy plural form
    / "rag_output"
    / "santa_monica_college"
    / "university_of_california_san_diego",
)

# Resolved at runtime to the first path that exists on disk.
ASSIST_ROOT: Path = next((d for d in _ASSIST_CANDIDATE_DIRS if d.exists()), _ASSIST_CANDIDATE_DIRS[0])

UCSD_PREP_PATH: Path = _PACKAGE_ROOT / "data" / "UCSD_transfer_major_prep" / "ucsd_transfer_majors.json"

# ---------------------------------------------------------------------------
# Pydantic result schema
# ---------------------------------------------------------------------------


class MajorRequirementResult(BaseModel):
    """Return payload for MajorRequirementTool."""

    major_name: str = Field(..., description="Normalised major name that was matched")
    assist_articulation: Optional[str] = Field(
        None, description="ASSIST articulation text between SMC and UCSD, if any"
    )
    ucsd_transfer_prep: Optional[str] = Field(
        None, description="Official UCSD transfer preparation text, if any"
    )
    notes: str = Field(..., description="Summary of what data was found or missing")

    class Config:
        # Allow arbitrary large text fields
        arbitrary_types_allowed = True


# ---------------------------------------------------------------------------
# Helpers – normalisation & slugification
# ---------------------------------------------------------------------------

_DEGREE_MARKER_RE = re.compile(
    r"\b((b\.?a\.?|b\.?s\.?)|ba|bs|phd|ma|m\.?s\.?)\b", re.IGNORECASE
)

_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _normalise(text: str) -> str:
    """Normalise a major string for matching (lower, strip, remove degree labels)."""

    if not text:
        return ""
    text = text.lower().strip()

    # Remove anything within parentheses, e.g. "Physics (B.S.)" -> "Physics"
    text = re.sub(r"\(.*?\)", "", text)
    # Remove degree markers such as "bs", "b.s.", etc.
    text = _DEGREE_MARKER_RE.sub("", text)
    # Collapse whitespace -> single space
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


def _slugify(text: str) -> str:
    """Create a slug suitable for filename/key comparisons."""

    norm = _normalise(text)
    # Replace non-alpha-numeric characters with underscores and collapse
    slug = _NON_ALNUM_RE.sub("_", norm)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


# ---------------------------------------------------------------------------
# Cached catalogue loaders
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _assist_file_catalogue() -> List[Path]:
    """Return list of all *.json files under ASSIST_ROOT (cached)."""

    if not ASSIST_ROOT.exists():
        return []
    return sorted(ASSIST_ROOT.glob("**/*.json"))


@lru_cache(maxsize=1)
def _ucsd_transfer_prep_catalogue() -> Dict[str, dict]:
    """Return mapping of slug -> major JSON entry from the UCSD prep file."""

    if not UCSD_PREP_PATH.exists():
        return {}

    try:
        with UCSD_PREP_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError:
        return {}

    majors_mapping: Dict[str, dict] = {}

    # Handle different shapes
    if isinstance(data, dict):
        # Newer format: {"majors": {...}}
        if "majors" in data and isinstance(data["majors"], dict):
            iterable = data["majors"].values()
        else:
            iterable = data.values()
    elif isinstance(data, list):
        iterable = data
    else:
        iterable = []

    for entry in iterable:
        if not isinstance(entry, dict):
            continue
        name_source = entry.get("major_name") or entry.get("name") or ""
        slug = _slugify(name_source)
        majors_mapping[slug] = entry

    return majors_mapping


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_text_from_assist_json(path: Path) -> str:
    """Return articulation text from an ASSIST JSON file (best-effort)."""

    try:
        with path.open(encoding="utf-8") as fh:
            obj = json.load(fh)
    except Exception as exc:  # pragma: no cover – corrupt file
        return f"<Failed to read JSON from {path.name}: {exc}>"

    for key in ("articulation_text", "body", "text", "requirements"):
        if key in obj:
            val = obj[key]
            if isinstance(val, str):
                return val
            try:
                return json.dumps(val, indent=2)
            except TypeError:
                # Non-serialisable – fallback to str()
                return str(val)

    # Fallback to entire JSON pretty-printed
    try:
        return json.dumps(obj, indent=2)
    except TypeError:  # pragma: no cover
        return str(obj)


def _extract_text_from_ucsd_entry(entry: dict) -> str:
    """Convert UCSD transfer prep entry dict to a human-readable string."""

    for key in ("text", "body", "requirements"):
        if key in entry and isinstance(entry[key], str):
            return entry[key]

    # Otherwise stringify the entire dict (pretty printed)
    try:
        return json.dumps(entry, indent=2)
    except TypeError:
        return str(entry)


# ---------------------------------------------------------------------------
# Core lookup logic
# ---------------------------------------------------------------------------


def _lookup_assist(major_slug: str) -> Tuple[Optional[str], List[str]]:
    """Return (text, notes) for ASSIST lookup."""

    matches = [p for p in _assist_file_catalogue() if major_slug == _slugify(p.stem)]

    # Fallback fuzzy containment search if no exact hit
    if not matches:
        matches = [p for p in _assist_file_catalogue() if major_slug in _slugify(p.stem)]

    notes: List[str] = []
    if not matches:
        notes.append(f"No ASSIST articulation found for '{major_slug}'.")
        return None, notes

    if len(matches) > 1:
        notes.append(
            f"Multiple ASSIST files matched '{major_slug}'. Using '{matches[0].name}'."
        )

    articulation_text = _extract_text_from_assist_json(matches[0])
    return articulation_text, notes


def _lookup_ucsd_prep(major_slug: str) -> Tuple[Optional[str], List[str]]:
    """Return (text, notes) for UCSD transfer prep lookup."""

    catalogue = _ucsd_transfer_prep_catalogue()
    notes: List[str] = []
    if not catalogue:
        notes.append("UCSD transfer prep catalogue is empty or missing.")
        return None, notes

    if major_slug in catalogue:
        return _extract_text_from_ucsd_entry(catalogue[major_slug]), notes

    # Fuzzy containment search
    fuzzy_hits = [slug for slug in catalogue if major_slug in slug or slug in major_slug]
    if not fuzzy_hits:
        notes.append(f"No UCSD transfer preparation found for '{major_slug}'.")
        return None, notes

    fuzzy_hits.sort()
    if len(fuzzy_hits) > 1:
        notes.append(
            f"Multiple UCSD majors matched '{major_slug}'. Using '{fuzzy_hits[0]}' entry."
        )
    chosen_slug = fuzzy_hits[0]
    return _extract_text_from_ucsd_entry(catalogue[chosen_slug]), notes


# ---------------------------------------------------------------------------
# Public callable
# ---------------------------------------------------------------------------


def major_requirement_tool(major_name: str) -> MajorRequirementResult:  # noqa: D401
    """Fetch transfer-prep & articulation information for a UCSD major.

    Parameters
    ----------
    major_name:
        A UC San Diego major name (any reasonable formatting).

    Returns
    -------
    MajorRequirementResult
        Structured result payload containing texts and diagnostic notes.

    Raises
    ------
    ValueError
        If the major cannot be found in either source.
    """

    if not major_name or not major_name.strip():
        raise ValueError("major_name must be a non-empty string")

    major_slug = _slugify(major_name)

    assist_text, assist_notes = _lookup_assist(major_slug)
    prep_text, prep_notes = _lookup_ucsd_prep(major_slug)

    if not assist_text and not prep_text:
        # Compile notes before raising so caller can log them if desired.
        combined_notes = "\n".join(assist_notes + prep_notes)
        raise ValueError(
            f"Major '{major_name}' not found in either source. Details:\n{combined_notes}"
        )

    result_notes = "\n".join(assist_notes + prep_notes) or "Lookup successful."

    return MajorRequirementResult(
        major_name=_normalise(major_name),
        assist_articulation=assist_text,
        ucsd_transfer_prep=prep_text,
        notes=result_notes,
    )


# ---------------------------------------------------------------------------
# LangChain StructuredTool wrapper (optional)
# ---------------------------------------------------------------------------


# Even if the real LangChain is not installed, the stub defined above will allow
# importing `MajorRequirementTool` without crashing. Downstream applications
# can choose to ignore the wrapper if not using LangChain.

MajorRequirementTool: StructuredTool = StructuredTool.from_function(
    name="major_requirement_tool",
    description="Return ASSIST articulation and UCSD transfer-prep text for a given UC San Diego major.",
    func=major_requirement_tool,
    args_schema=None,
    return_direct=True,
)

if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json as _json
    import sys

    parser = argparse.ArgumentParser(description="CLI wrapper around MajorRequirementTool")
    parser.add_argument("--major", required=True, help="Major name to analyze, e.g. 'Mathematics'")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    args = parser.parse_args()

    try:
        result = major_requirement_tool(args.major)
        output = result.model_dump(mode="json")
        
        if args.pretty:
            print(_json.dumps(output, indent=2))
        else:
            print(_json.dumps(output))
            
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
