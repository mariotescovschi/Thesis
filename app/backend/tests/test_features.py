"""Tests for pure floor feature extraction."""
from core.document import Element, Floor
from helpers.features import describe_floor, feature_keys, floor_features, to_vector


def _floor() -> Floor:
    return Floor(
        id="fl", name="L0", width=1000, height=1000, building_type="apartment",
        adjacency=[{"from": "Kitchen", "to": "Living"}],
        elements=[
            Element(id="r1", kind="room", type="kitchen", label="Kitchen",
                    area_m2=10.0, polygon=[[0, 0], [100, 0], [100, 100], [0, 100]]),
            Element(id="r2", kind="room", type="living", label="Living",
                    area_m2=30.0, polygon=[[100, 0], [300, 0], [300, 100], [100, 100]]),
            Element(id="d1", kind="door", polygon=[[95, 40], [105, 40], [105, 60], [95, 60]]),
            Element(id="w1", kind="wall", polygon=[[0, 0], [300, 0], [300, 5], [0, 5]]),
        ],
    )


def test_features_basic_counts():
    f = floor_features(_floor())
    assert f["room_count"] == 2.0
    assert f["door_count"] == 1.0
    assert f["wall_count"] == 1.0
    assert f["total_area_m2"] == 40.0
    assert f["building_apartment"] == 1.0
    assert f["building_house"] == 0.0


def test_area_fractions_sum_to_one_when_areas_known():
    f = floor_features(_floor())
    total = sum(v for k, v in f.items() if k.startswith("area_frac_"))
    assert abs(total - 1.0) < 1e-6
    assert f["area_frac_living"] > f["area_frac_kitchen"]


def test_to_vector_matches_key_order():
    f = floor_features(_floor())
    vec = to_vector(f)
    assert len(vec) == len(feature_keys())


def test_describe_floor_mentions_rooms():
    desc = describe_floor(_floor())
    assert "2-room" in desc
    assert "apartment" in desc
