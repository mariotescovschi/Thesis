"""Ollama text-embedding client (nomic-embed-text). Transport only — any failure
becomes a clean AppError so callers surface a tidy { error } envelope instead of a
stack trace (mirrors infra/ollama_client). Prereq: `ollama pull nomic-embed-text`.
"""
import os

import httpx

from core.errors import AppError

_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
_URL = f"{_HOST.rstrip('/')}/api/embeddings"
_TIMEOUT = float(os.environ.get("OLLAMA_TIMEOUT", "120"))


def default_model() -> str:
    return os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")


def embed(text: str) -> list[float]:
    """Embed a single text into a float vector. Raises AppError (502) on failure."""
    payload = {"model": default_model(), "prompt": text}
    try:
        resp = httpx.post(_URL, json=payload, timeout=_TIMEOUT)
    except httpx.ConnectError as exc:
        raise AppError(
            f"Ollama is not reachable at {_HOST}. Is it running? "
            f"(start with `ollama serve` and pull `{default_model()}`)."
        ) from exc
    except httpx.TimeoutException as exc:
        raise AppError(f"Ollama embedding timed out after {_TIMEOUT:g}s.") from exc
    except httpx.HTTPError as exc:
        raise AppError(f"Ollama embedding failed: {exc}") from exc

    if resp.status_code != 200:
        raise AppError(f"Ollama returned HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        vec = resp.json()["embedding"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AppError("Ollama returned an unexpected embedding shape.") from exc
    if not isinstance(vec, list) or not vec:
        raise AppError("Ollama returned an empty embedding.")
    return [float(x) for x in vec]


def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed several texts (sequential; the local server is single-host)."""
    return [embed(t) for t in texts]
