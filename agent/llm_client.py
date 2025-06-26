from __future__ import annotations

"""Lightweight OpenAI ChatCompletion wrapper used by the executor.

This module keeps **all OpenAI-specific code** isolated so that the rest of the
codebase (including unit-tests) can be executed without importing the heavy
`openai` package or requiring an API key.  The public helper :pyfunc:`chat` is
what other modules should call.

The implementation supports both the **new 1.x SDK** (``openai.OpenAI``) and the
legacy 0.x interface (``openai.ChatCompletion``) to maximise compatibility.
"""

from pathlib import Path
import os
import sys
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment handling ------------------------------------------------------
# ---------------------------------------------------------------------------

# Attempt to load a local .env if present.  This is a *no-op* when the file
# does not exist which preserves offline-testability.
load_dotenv()  # silently loads variables from .env into os.environ

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not _OPENAI_API_KEY:
    # Delay the hard failure until *first* call so that unit tests that monkey-
    # patch :func:`chat` can run without the key.
    _MISSING_KEY_MSG = (
        "OPENAI_API_KEY is not set.  Create a .env file (see .env.example) or "
        "export it in your shell environment."
    )
else:
    _MISSING_KEY_MSG = None


# ---------------------------------------------------------------------------
# Helper – choose implementation based on SDK version -----------------------
# ---------------------------------------------------------------------------

def _get_chat_fn():  # noqa: D401 – simple factory
    """Return an internal function that wraps `ChatCompletion.create`.

    The returned callable has signature ``(model, messages, temperature)`` and
    must return *content* (``str``) of the first choice.
    """

    try:
        import openai  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover – only hits if dep missing
        raise ImportError(
            "The 'openai' package is required for LLM execution.\n"
            "Install it via `pip install openai` or run tests with the client "
            "mocked (see agent/tests/test_llm.py)."
        ) from exc

    # ------------------------------------------------------------------
    # 1. New 1.x style (client.chat.completions.create) -----------------
    # ------------------------------------------------------------------
    if hasattr(openai, "OpenAI"):
        client = openai.OpenAI(api_key=_OPENAI_API_KEY)  # type: ignore[attr-defined]

        def _chat_v1(model: str, messages: list[dict[str, str]], temperature: float):  # noqa: D401
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content  # type: ignore[index]

        return _chat_v1

    # ------------------------------------------------------------------
    # 2. Legacy 0.x style (openai.ChatCompletion.create) ----------------
    # ------------------------------------------------------------------
    if hasattr(openai, "ChatCompletion"):
        # Explicitly set key on global module for old SDK
        openai.api_key = _OPENAI_API_KEY  # type: ignore[attr-defined]

        def _chat_v0(model: str, messages: list[dict[str, str]], temperature: float):  # noqa: D401
            resp = openai.ChatCompletion.create(  # type: ignore[attr-defined]
                model=model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content  # type: ignore[index]

        return _chat_v0

    # If neither interface found, raise
    raise RuntimeError(
        "Unsupported 'openai' package version – neither 1.x (OpenAI) nor 0.x "
        "(ChatCompletion) API detected."
    )


# Lazily initialise the concrete chat implementation to avoid import overhead
# when *not* used.
_chat_impl = None  # type: ignore


def chat(
    instructions: str,
    context: Optional[Dict[str, Any]] = None,
    *,
    model: str = "gpt-4o",
    temperature: float = 0.4,
) -> str:
    """Return an assistant response by calling OpenAI ChatCompletion.

    This tiny wrapper handles: loading the API key from ``.env``, choosing the
    correct SDK version, and blending *context* into the user message.

    The function is *sync* and intentionally minimal.  For advanced features
    (streaming, tools, functions) we would expose a richer API.
    """

    # Fail fast on missing key (but allow unit tests to monkey-patch).
    if _MISSING_KEY_MSG is not None:
        raise RuntimeError(_MISSING_KEY_MSG)

    global _chat_impl  # pylint: disable=global-statement
    if _chat_impl is None:
        _chat_impl = _get_chat_fn()

    # Construct the messages for ChatCompletion
    system_prompt = (
        "You are Admitr's composer. Blend the provided tool outputs into a "
        "concise, actionable reply for the student."
    )

    user_msg = instructions.strip()
    if context:
        user_msg += "\n\n# Context\n" + str(context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_msg},
    ]

    return _chat_impl(model, messages, temperature).strip() 