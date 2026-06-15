"""Unit tests for the pure polygon regularization helper (helpers.normalize)."""
import pytest
from shapely.geometry import Polygon

from core.document import Element, Floor
from helpers.normalize import normalize_floor


def _floor(elements: list[Element], width: int = 300, height: int = 300) -> Floor:
    return Floor(id="fl_1", name="L0", width=width, height=height, elements=elements)


def _final(res, element: Element) -> list[list[int]]:
    """The element's polygon after normalization (changed if present, else original)."""
    return res.changed.get(element.id, element.polygon)


def test_invalid_level_raises() -> None:
    floor = _floor([Element(id="r1", kind="room",
                            polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])])
    for bad in (0, 4, -1):
        with pytest.raises(ValueError):
            normalize_floor(floor, bad)


def test_is_pure_no_mutation() -> None:
    poly = [[0, 0], [200, 3], [200, 200], [0, 200]]
    el = Element(id="r1", kind="room", polygon=poly)
    floor = _floor([el])
    snapshot = [list(p) for p in poly]
    normalize_floor(floor, 3)
    assert el.polygon == snapshot  # input untouched


def test_l1_axis_snaps_near_horizontal_edge() -> None:
    # Top edge tilts by 3px over 200px -> well within the angle tolerance.
    el = Element(id="r1", kind="room", polygon=[[0, 0], [200, 3], [200, 200], [0, 200]])
    res = normalize_floor(_floor([el]), 1)
    assert "r1" in res.changed
    out = res.changed["r1"]
    assert out[0][1] == out[1][1]  # the two top vertices now share a y (clean edge)


def test_l1_drops_sliver() -> None:
    big = Element(id="r1", kind="room", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])
    speck = Element(id="w1", kind="wall", polygon=[[0, 0], [5, 0], [5, 5], [0, 5]])  # area 25
    res = normalize_floor(_floor([big, speck]), 1)
    assert "w1" in res.dropped


def test_l1_drops_collinear_vertex() -> None:
    # Extra midpoint (100,0) sits on a straight edge -> removed.
    el = Element(id="r1", kind="room",
                 polygon=[[0, 0], [100, 0], [200, 0], [200, 200], [0, 200]])
    res = normalize_floor(_floor([el]), 1)
    assert "r1" in res.changed
    assert len(res.changed["r1"]) == 4
    assert [100, 0] not in res.changed["r1"]


def test_l2_welds_shared_corner() -> None:
    # Two rooms with a 4px gap between their adjacent corners; no walls -> the
    # corners should weld to a single shared point at level 2.
    a = Element(id="a", kind="room", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])
    b = Element(id="b", kind="room", polygon=[[104, 0], [200, 0], [200, 100], [104, 100]])
    res = normalize_floor(_floor([a, b], width=210, height=110), 2)
    a_out, b_out = _final(res, a), _final(res, b)
    # roomA's right corners now equal roomB's left corners.
    assert [102, 0] in a_out and [102, 0] in b_out
    assert [102, 100] in a_out and [102, 100] in b_out


def test_l2_welds_room_corner_to_wall() -> None:
    # A wall corner at (100,0); a room corner 3px off should snap onto it.
    wall = Element(id="w", kind="wall", polygon=[[100, 0], [110, 0], [110, 100], [100, 100]])
    room = Element(id="r", kind="room", polygon=[[0, 0], [97, 0], [97, 100], [0, 100]])
    res = normalize_floor(_floor([wall, room], width=200, height=120), 2)
    r_out = _final(res, room)
    assert [100, 0] in r_out  # welded onto the wall corner


def test_l3_removes_room_overlap() -> None:
    a = Element(id="a", kind="room", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])
    b = Element(id="b", kind="room", polygon=[[80, 0], [180, 0], [180, 100], [80, 100]])
    res = normalize_floor(_floor([a, b], width=200, height=120), 3)
    ga, gb = Polygon(_final(res, a)), Polygon(_final(res, b))
    assert ga.intersection(gb).area < 1.0  # overlap carved away


def test_l3_keeps_non_overlapping_rooms() -> None:
    a = Element(id="a", kind="room", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])
    b = Element(id="b", kind="room", polygon=[[120, 0], [200, 0], [200, 100], [120, 100]])
    res = normalize_floor(_floor([a, b], width=220, height=120), 3)
    # Distinct rooms (gap 20 > tol) survive and stay disjoint.
    assert "a" not in res.dropped and "b" not in res.dropped
    ga, gb = Polygon(_final(res, a)), Polygon(_final(res, b))
    assert ga.intersection(gb).area < 1.0
