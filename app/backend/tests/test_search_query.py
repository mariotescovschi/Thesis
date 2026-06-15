"""Tests for the pure search ranking (filters + cosine)."""
from helpers.search_query import cosine, filter_records, rank


def _rec(pid, area, price, bedrooms=1, bt="apartment", emb=None):
    return {
        "project_id": pid, "floor_id": "f1",
        "project_name": pid, "floor_name": "L0",
        "price": price, "currency": "EUR", "description": pid, "embedding": emb,
        "features": {
            "total_area_m2": area, "room_count": bedrooms + 2,
            "count_bedroom": float(bedrooms), f"building_{bt}": 1.0,
        },
    }


def _dataset():
    return [
        _rec("a", area=40, price=80_000, bedrooms=1),
        _rec("b", area=70, price=150_000, bedrooms=2),
        _rec("c", area=110, price=300_000, bedrooms=3, bt="house"),
    ]


def test_filter_by_area_and_price():
    kept = filter_records(_dataset(), {"area_min": 60, "price_max": 200_000})
    assert {r["project_id"] for r in kept} == {"b"}


def test_filter_by_bedrooms_and_type():
    kept = filter_records(_dataset(), {"bedrooms": 3, "building_type": "house"})
    assert {r["project_id"] for r in kept} == {"c"}


def test_cosine_ranks_more_similar_first():
    records = [
        _rec("near", 50, 100_000, emb=[1.0, 0.0]),
        _rec("far", 50, 100_000, emb=[0.0, 1.0]),
    ]
    results = rank(records, query_embedding=[0.9, 0.1])
    assert results[0]["project_id"] == "near"


def test_no_embedding_falls_back_to_price_order():
    results = rank(_dataset(), query_embedding=None)
    prices = [r["price"] for r in results]
    assert prices == sorted(prices)


def test_cosine_handles_empty():
    assert cosine(None, [1.0]) == 0.0
    assert cosine([1.0, 2.0], [1.0]) == 0.0
