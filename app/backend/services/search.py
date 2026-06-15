"""Search service: natural-language query over the derived plan index.

The LLM turns the query into structured numeric filters; the query is embedded for
semantic ranking; helpers.search_query.rank() does the deterministic filter + rank.
Degrades to filter-only (and unranked) when Ollama / embeddings are unavailable —
search must never hard-fail just because a model is offline.
"""
import json
from typing import Optional

import infra.embeddings as embeddings
import infra.index_store as index_store
import infra.ollama_client as ollama_client
from helpers.search_query import rank

_SYSTEM = (
    "Extract structured real-estate search filters from the user's query. Reply "
    "with STRICT JSON only, using any of these OPTIONAL keys: "
    '{"area_min","area_max","price_min","price_max","bedrooms","rooms_min",'
    '"building_type"}. Areas are in m2; prices numeric; bedrooms/rooms_min integers; '
    "building_type one of apartment|house|office|commercial. Omit keys you cannot "
    "confidently infer. Return {} if none apply."
)
_NUMERIC = {"area_min", "area_max", "price_min", "price_max", "bedrooms", "rooms_min"}


def _extract_filters(query: str) -> dict:
    """Ask the LLM for structured filters; return {} on any failure (degrade)."""
    try:
        content = ollama_client.chat(
            [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": query}],
            json_format=True,
        )
        data = json.loads(content)
    except Exception:  # noqa: BLE001 LLM/JSON failure -> filter-free search
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict = {}
    for k, v in data.items():
        if k in _NUMERIC and isinstance(v, (int, float)) and not isinstance(v, bool):
            out[k] = float(v)
        elif k == "building_type" and isinstance(v, str) and v.strip():
            out[k] = v.strip().lower()
    return out


def _embed_query(query: str) -> Optional[list[float]]:
    try:
        return embeddings.embed(query)
    except Exception:  # noqa: BLE001 embeddings offline -> filter-only ranking
        return None


def search(query: str, top_k: int = 20) -> dict:
    """Run a natural-language search over all indexed plans."""
    query = (query or "").strip()
    records = index_store.all_records()
    if not query:
        return {"query": query, "filters": {}, "semantic": False,
                "results": rank(records, None, {}, top_k)}
    filters = _extract_filters(query)
    q_emb = _embed_query(query)
    return {
        "query": query,
        "filters": filters,
        "semantic": q_emb is not None,
        "results": rank(records, q_emb, filters, top_k),
    }
