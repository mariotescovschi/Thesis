"""Pure ranking over index records: hard numeric filters + semantic cosine score.

No I/O, no LLM. services/search.py extracts the filters + query embedding and calls
rank(); this stays deterministic and testable over plain record dicts.
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
    if "building_type" in f and _feat(rec, f"building_{f['building_type']}") < 1.0:
        return False
    return True


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


def _public(rec: dict, score: float) -> dict:
    return {
        "project_id": rec.get("project_id"),
        "floor_id": rec.get("floor_id"),
        "project_name": rec.get("project_name"),
        "floor_name": rec.get("floor_name"),
        "price": rec.get("price"),
        "currency": rec.get("currency", "EUR"),
        "description": rec.get("description"),
        "score": round(score, 4),
    }


def rank(
    records: list[dict],
    query_embedding: Optional[list[float]] = None,
    filters: Optional[dict] = None,
    top_k: int = 20,
) -> list[dict]:
    """Filter records by hard constraints, then order them.

    With a query embedding, rank by semantic cosine similarity; without one
    (embeddings offline / empty query), fall back to a stable price-ascending order.
    """
    kept = filter_records(records, filters or {})
    results = [
        _public(r, cosine(query_embedding, r.get("embedding")) if query_embedding else 0.0)
        for r in kept
    ]
    if query_embedding:
        results.sort(key=lambda d: d["score"], reverse=True)
    else:
        results.sort(key=lambda d: (d["price"] is None, d["price"] or 0.0, d["project_name"] or ""))
    return results[:top_k]
