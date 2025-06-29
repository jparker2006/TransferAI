from __future__ import annotations

"""TransferAI – User Profile Tool

Retrieves complete user profile data for evaluation and testing purposes.
Given a user ID, returns the full JSON profile including courses, GPA, units, and schedule.

Example
-------
>>> from tools.user_profile_tool import UserProfileTool
>>> UserProfileTool.invoke({"user_id": "U01"})
{
  "id": "U01",
  "courses": [...],
  "units_completed": 29,
  "gpa": 3.37,
  "current_schedule": [...],
  "major_interest": "cse_computer_science_bs"
}
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import sys

# ---------------------------------------------------------------------------
# Ensure project root is importable when running as a standalone script
# ---------------------------------------------------------------------------

if __package__ is None or __package__ == "":
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

# Pydantic 2.x imports
from pydantic import BaseModel, Field, field_validator, ConfigDict

# LangChain import
from langchain_core.tools import StructuredTool

# ---------------------------------------------------------------------------
# Public Exceptions
# ---------------------------------------------------------------------------


class UserProfileNotFoundError(RuntimeError):
    """Raised when a user_id cannot be located in the profiles directory."""


# ---------------------------------------------------------------------------
# Pydantic models for user profile structure
# ---------------------------------------------------------------------------


class Course(BaseModel):
    """Individual course record with code and grade."""
    
    code: str
    grade: str


class ScheduleItem(BaseModel):
    """Current schedule item with course, days, and time."""
    
    code: str
    days: str
    time: str


class UserProfile(BaseModel):
    """Complete user profile data structure."""
    
    id: str
    courses: List[Course]
    units_completed: float
    gpa: float
    current_schedule: List[ScheduleItem]
    major_interest: str
    
    # Allow additional fields that might be added in the future
    model_config = ConfigDict(extra="allow")


# ---------------------------------------------------------------------------
# I/O schemas for LangChain StructuredTool
# ---------------------------------------------------------------------------


class UPIn(BaseModel):  # noqa: D401
    """Input schema – single required user ID parameter."""

    user_id: str = Field(..., description="User ID to look up (e.g., 'U01', 'U02')")
    
    @field_validator("user_id", mode="before")  # type: ignore[arg-type]
    def _normalize_user_id(cls, v: str) -> str:  # noqa: D401, N805
        """Normalize user ID to uppercase format."""
        return str(v).strip().upper()


class UPOut(UserProfile):  # noqa: D401
    """Output schema – inherits all UserProfile fields."""
    
    pass


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


_PROFILES_DIR = Path(__file__).resolve().parents[1] / "evals" / "user_profiles"
_PROFILES_CACHE: Optional[Dict[str, dict]] = None  # Lazy global cache


def _load_profiles() -> Dict[str, dict]:  # noqa: D401
    """Load all user profiles from JSON files, memoized for process lifetime."""
    global _PROFILES_CACHE  # noqa: PLW0603 – intentional module-level cache
    
    if _PROFILES_CACHE is not None:
        return _PROFILES_CACHE
    
    if not _PROFILES_DIR.exists():
        raise RuntimeError(f"User profiles directory not found: {_PROFILES_DIR}")
    
    profiles: Dict[str, dict] = {}
    
    for json_file in _PROFILES_DIR.glob("U*.json"):
        try:
            with json_file.open("r", encoding="utf-8") as fh:
                profile_data = json.load(fh)
                
            user_id = profile_data.get("id", "").upper()
            if user_id:
                profiles[user_id] = profile_data
                
        except Exception as exc:  # noqa: BLE001
            # Skip malformed files but continue loading others
            print(f"Warning: Failed to load {json_file}: {exc}")
            continue
    
    _PROFILES_CACHE = profiles
    return profiles


# ---------------------------------------------------------------------------
# Core lookup function
# ---------------------------------------------------------------------------


def _lookup_user_profile(*, user_id: str) -> Dict[str, Any]:  # noqa: D401
    """Lookup user_id in profiles directory and return complete profile data."""
    
    normalized_id = user_id.strip().upper()
    profiles = _load_profiles()
    
    if normalized_id not in profiles:
        available_ids = sorted(profiles.keys())
        raise UserProfileNotFoundError(
            f"User profile '{normalized_id}' not found. "
            f"Available profiles: {', '.join(available_ids)}"
        )
    
    raw_data = profiles[normalized_id]
    
    try:
        # Validate the profile structure
        profile = UserProfile(**raw_data)
    except Exception as exc:  # noqa: BLE001
        raise UserProfileNotFoundError(
            f"User profile '{normalized_id}' found but could not be validated: {exc}"
        ) from exc
    
    # Return plain dict for JSON serialization
    return profile.model_dump(mode="json", exclude_none=True)


# ---------------------------------------------------------------------------
# Public StructuredTool instance
# ---------------------------------------------------------------------------


UserProfileTool: StructuredTool = StructuredTool.from_function(
    func=_lookup_user_profile,
    name="user_profile",
    description=(
        "Retrieve complete user profile data including courses, GPA, units completed, "
        "current schedule, and major interest. Input: user_id (e.g., 'U01')."
    ),
    args_schema=UPIn,
    return_schema=UPOut,
)

# Explicitly set return schema for proper typing
object.__setattr__(UserProfileTool, "return_schema", UPOut)


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------


__all__ = ["UserProfileTool", "UserProfileNotFoundError"]


# ---------------------------------------------------------------------------
# Manual test / demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import json
    
    try:
        # Test with a known user
        profile = UserProfileTool.invoke({"user_id": "U01"})
        print("✅ Successfully retrieved U01 profile:")
        print(json.dumps(profile, indent=2))
        
        # Test with invalid user
        try:
            UserProfileTool.invoke({"user_id": "U99"})
        except UserProfileNotFoundError as err:
            print(f"\n✅ Correctly handled invalid user: {err}")
            
    except Exception as err:
        print(f"❌ Error: {err}") 