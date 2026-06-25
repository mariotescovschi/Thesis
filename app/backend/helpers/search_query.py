"""Pure ranking over index records: hard numeric filters + keyword matching + semantic cosine.

No I/O, no LLM. services/search.py extracts the filters + keywords + query embedding
and calls rank(); this stays deterministic and testable over plain record dicts.
"""
import math
from typing import Optional, TypedDict


class Filters(TypedDict, total=False):
    area_min: float
    area_max: float
    price_min: float
    price_max: float
    bedrooms: float        # minimum number of bedrooms
    rooms_min: float       # minimum total rooms
    building_type: str


def _feat(rec: dict, key: str, default: float = 0.0) -> float:
    return float(rec.get("features", {}).get(key, default))


def _passes(rec: dict, f: dict) -> bool:
    area = _feat(rec, "total_area_m2")
    if "area_min" in f and area < f["area_min"]:
        return False
    if "area_max" in f and area > f["area_max"]:
        return False
    price = rec.get("price")
    if "price_max" in f and (price is None or price > f["price_max"]):
        return False
    if "price_min" in f and (price is None or price < f["price_min"]):
        return False
    if "bedrooms" in f and _feat(rec, "count_bedroom") < f["bedrooms"]:
        return False
    if "rooms_min" in f and _feat(rec, "room_count") < f["rooms_min"]:
        return False
    if "windows_min" in f and _feat(rec, "window_count") < f["windows_min"]:
        return False
    if "doors_min" in f and _feat(rec, "door_count") < f["doors_min"]:
        return False
    if "building_type" in f and _feat(rec, f"building_{f['building_type']}") < 1.0:
        return False
    return True


def _keyword_match(rec: dict, keywords: list[str]) -> list[str]:
    """Return which keywords appear in the record's description."""
    desc = (rec.get("description") or "").lower()
    return [kw for kw in keywords if kw in desc]


def filter_records(records: list[dict], f: dict) -> list[dict]:
    return [r for r in records if _passes(r, f)]


def cosine(a: Optional[list], b: Optional[list]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _public(rec: dict, score: float, match: str, matched_keywords: list[str]) -> dict:
    return {
        "project_id": rec.get("project_id"),
        "floor_id": rec.get("floor_id"),
        "project_name": rec.get("project_name"),
        "floor_name": rec.get("floor_name"),
        "price": rec.get("price"),
        "currency": rec.get("currency", "EUR"),
        "description": rec.get("description"),
        "score": round(score, 4),
        "match": match,
        "matched_keywords": matched_keywords,
    }


def rank(
    records: list[dict],
    query_embedding: Optional[list[float]] = None,
    filters: Optional[dict] = None,
    keywords: Optional[list[str]] = None,
    top_k: int = 20,
) -> list[dict]:
    """Filter records by hard constraints, then order them.

    Records matching ALL keywords are marked "exact"; the rest are "semantic".
    Exact matches come first, sorted by score; semantic matches follow.
    """
    kept = filter_records(records, filters or {})
    kws = keywords or []
    results: list[dict] = []
    for r in kept:
        score = cosine(query_embedding, r.get("embedding")) if query_embedding else 0.0
        matched = _keyword_match(r, kws) if kws else []
        match_type = "exact" if kws and len(matched) == len(kws) else "semantic"
        results.append(_public(r, score, match_type, matched))

    # Exact matches first, then semantic; within each group sort by score desc
    results.sort(key=lambda d: (0 if d["match"] == "exact" else 1, -d["score"]))
    return results[:top_k]
