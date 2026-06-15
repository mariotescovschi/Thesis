"""Tests for the ridge + kNN pricing service (synthetic index records)."""
from services.pricing import estimate


def _rec(pid: str, area: float, rooms: float, price=None) -> dict:
    return {
        "project_id": pid, "floor_id": "f1",
        "project_name": pid, "floor_name": "L0",
        "price": price, "currency": "EUR",
        "features": {"total_area_m2": area, "room_count": rooms},
    }


def _priced_dataset() -> list[dict]:
    # Price ~ 1000 * area, six priced comparables.
    return [_rec(f"p{i}", area=a, rooms=a / 20, price=1000.0 * a)
            for i, a in enumerate([40, 50, 60, 70, 80, 90])]


def test_no_priced_data_is_unavailable():
    target = _rec("t", area=55, rooms=3)
    res = estimate(target, [target])
    assert res["available"] is False


def test_estimate_tracks_area():
    records = _priced_dataset()
    small = estimate(_rec("t", area=45, rooms=2), records)
    big = estimate(_rec("t", area=85, rooms=4), records)
    assert small["available"] and big["available"]
    assert big["estimate"] > small["estimate"]


def test_verdict_and_comparables_with_enough_data():
    records = _priced_dataset()
    # Target priced far above the ~1000*area trend -> overpriced.
    target = _rec("t", area=60, rooms=3, price=200_000.0)
    res = estimate(target, records)
    assert res["verdict"] == "overpriced"
    assert len(res["comparables"]) == 5
    assert res["contributions"]


def test_verdict_insufficient_when_few_priced():
    records = [_rec("p0", 50, 2, price=50_000.0), _rec("p1", 60, 3, price=60_000.0)]
    res = estimate(_rec("t", 55, 2, price=55_000.0), records)
    assert res["verdict"] == "insufficient_data"
