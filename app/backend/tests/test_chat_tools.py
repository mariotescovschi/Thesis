"""Tests for the pure, read-only chat tools."""
from core.document import Element, Floor
from helpers.chat_tools import run_tool


def _floor() -> Floor:
    return Floor(
        id="fl", name="L0", width=1000, height=1000, scale_px_per_m=100.0,
        adjacency=[{"from": "Kitchen", "to": "Hall"}],
        elements=[
            Element(id="room_k", kind="room", type="kitchen", label="Kitchen",
                    polygon=[[0, 0], [200, 0], [200, 200], [0, 200]]),
            Element(id="room_h", kind="room", type="hall", label="Hall",
                    polygon=[[200, 0], [400, 0], [400, 200], [200, 200]]),
            Element(id="wall_1", kind="wall",
                    polygon=[[0, 0], [400, 0], [400, 10], [0, 10]]),
        ],
    )


def test_find_element_by_substring():
    res = run_tool(_floor(), "find_element", {"description": "kitch"})
    assert res["count"] == 1
    assert res["matches"][0]["id"] == "room_k"


def test_list_elements_filtered_by_kind():
    res = run_tool(_floor(), "list_elements", {"kind": "room"})
    assert res["count"] == 2
    assert {e["id"] for e in res["elements"]} == {"room_k", "room_h"}


def test_get_neighbors_resolves_by_name():
    res = run_tool(_floor(), "get_neighbors", {"name": "Kitchen"})
    assert res["neighbors"] == ["Hall"]


def test_measure_between_named_rooms_returns_meters():
    res = run_tool(_floor(), "measure", {"a": "Kitchen", "b": "Hall"})
    assert "distance_px" in res and "distance_m" in res
    assert res["distance_m"] > 0


def test_get_scene_includes_segment_ids():
    res = run_tool(_floor(), "get_scene", {})
    assert "id=wall_1" in res["scene"]


def test_unknown_tool_returns_error():
    res = run_tool(_floor(), "nope", {})
    assert "error" in res
