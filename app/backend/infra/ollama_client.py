"""Thin Ollama chat client. No business logic — just transport + clean errors.

POSTs to a local Ollama server (http://localhost:11434/api/chat). The model is
read from OLLAMA_MODEL (default 'gemma3'). Any transport failure (server down,
timeout, non-200, malformed body) is converted into a clean AppError so callers
never see a raw socket/ConnectionError. Mirrors semantics.py's degrade pattern.
"""
import os
from typing import Optional

import httpx

from core.errors import AppError

_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
_URL = f"{_HOST.rstrip('/')}/api/chat"
_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


def default_model() -> str:
    return os.environ.get("OLLAMA_MODEL", "gemma3")


def _think() -> Optional[bool]:
    """Thinking toggle for models that support it (e.g. gemma4).

    Returns None when OLLAMA_THINK is unset so the key is omitted entirely —
    passing `think` to a non-thinking model (e.g. gemma3) would error. Set
    OLLAMA_THINK=false to disable reasoning for faster, cleaner JSON output.
    """
    raw = os.environ.get("OLLAMA_THINK")
    if raw is None:
        return None
    return raw.lower() in ("1", "true", "yes", "on")


def chat(messages: list[dict], json_format: bool = True) -> str:
    """Send a chat request and return the assistant message content (a string).

    Raises AppError (502) on any connectivity / protocol failure so the route
    layer can surface a clean { error } envelope instead of a stack trace.
    """
    payload: dict = {
        "model": default_model(),
        "messages": messages,
        "stream": False,
    }
    if json_format:
        payload["format"] = "json"
    think = _think()
    if think is not None:
        payload["think"] = think
    try:
        resp = httpx.post(_URL, json=payload, timeout=_TIMEOUT)
    except httpx.ConnectError as exc:
        raise AppError(
            f"Ollama is not reachable at {_HOST}. Is it running? "
            f"(start with `ollama serve` and pull `{default_model()}`)."
        ) from exc
    except httpx.TimeoutException as exc:
        raise AppError(f"Ollama request timed out after {_TIMEOUT:g}s.") from exc
    except httpx.HTTPError as exc:
        raise AppError(f"Ollama request failed: {exc}") from exc

    if resp.status_code != 200:
        raise AppError(
            f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
    try:
        data = resp.json()
        return data["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError("Ollama returned an unexpected response shape.") from exc
