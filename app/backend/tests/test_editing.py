"""Unit tests for the pure edit-command engine (editing.apply)."""
import commands as cmds
import editing
import pytest
from document import Element, Floor
from errors import NotFoundError, ValidationError


def _square_floor(scale=None) -> Floor:
    return Floor(
        id="fl_1",
        name="L0",
        scale_px_per_m=scale,
        elements=[Element(id="el_1", kind="room", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])],
    )


def test_apply_is_pure() -> None:
    floor = _square_floor()
    out = editing.apply(floor, cmds.SetLabel(op="set_label", element_id="el_1", label="MH"))
    assert out is not floor
    assert floor.elements[0].label is None  # input untouched
    assert out.elements[0].label == "MH"


def test_set_label_missing_raises() -> None:
    with pytest.raises(NotFoundError):
        editing.apply(_square_floor(), cmds.SetLabel(op="set_label", element_id="nope", label="X"))


def test_set_scale_recomputes_area() -> None:
    out = editing.apply(_square_floor(), cmds.SetScale(op="set_scale", scale_px_per_m=10.0))
    # 100x100 px square at 10 px/m -> 10m x 10m -> 100 m²
    assert out.elements[0].area_m2 == pytest.approx(100.0)


def test_add_wall_appends_wall_element() -> None:
    out = editing.apply(_square_floor(), cmds.AddWall(op="add_wall", segment=[[0, 0], [100, 0]], thickness=6.0))
    walls = [e for e in out.elements if e.kind == "wall"]
    assert len(walls) == 1
    assert len(walls[0].polygon) == 4


def test_split_room_yields_two_polygons() -> None:
    out = editing.apply(
        _square_floor(scale=10.0),
        cmds.SplitRoom(op="split_room", element_id="el_1", segment=[[50, 0], [50, 100]]),
    )
    rooms = [e for e in out.elements if e.kind == "room"]
    assert len(rooms) == 2
    assert all(len(r.polygon) >= 3 for r in rooms)
    assert "el_1" not in {r.id for r in rooms}
    # each half is 50x100 px @10px/m -> 50 m²
    assert all(r.area_m2 == pytest.approx(50.0) for r in rooms)


def test_split_room_non_crossing_raises() -> None:
    with pytest.raises(ValidationError):
        editing.apply(
            _square_floor(),
            cmds.SplitRoom(op="split_room", element_id="el_1", segment=[[200, 0], [200, 100]]),
        )


def test_add_then_delete_annotation() -> None:
    added = editing.apply(
        _square_floor(),
        cmds.AddAnnotation(op="add_annotation", x=10.0, y=20.0, name="entry"),
    )
    assert len(added.annotations) == 1
    pin_id = added.annotations[0].id
    assert pin_id.startswith("pin_")

    removed = editing.apply(added, cmds.DeleteAnnotation(op="delete_annotation", id=pin_id))
    assert removed.annotations == []
