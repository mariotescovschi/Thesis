"""Tests for merging geometry + semantics into a Floor Document."""
from core.document import Floor
from services.merge import merge_document


def _base() -> Floor:
    return Floor(id="fl", name="L0", filename="f.png", width=10, height=10)


def _room(x: float) -> dict:
    return {"kind": "room", "polygon": [[x, 0], [x + 10, 0], [x + 10, 10], [x, 10]]}


def test_merge_normalizes_types_and_defaults_unmatched_to_other():
    geom = [_room(0), _room(20), _room(40)]  # three geometry rooms (over-segmented)
    semantics = {
        "rooms": [
            {"label": "MH", "type_en": "Bedroom", "area_m2": 12.0},
            {"label": "OH", "type_en": "living room", "area_m2": 20.0},
        ],
    }
    floor = merge_document(_base(), 100, 100, geom, semantics)
    rooms = [e for e in floor.elements if e.kind == "room"]
    assert rooms[0].type == "bedroom"     # normalized
    assert rooms[1].type == "living"      # alias normalized
    assert rooms[2].type == "other"       # unmatched geometry room, not None
    assert all(r.type is not None for r in rooms)
