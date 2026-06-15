"""Unit tests for the normalization service (Floor + level -> EditCommand[])."""
import pytest

import core.commands as cmds
import services.editing as editing
from core.document import Element, Floor
from services.normalization import propose_normalization


def _floor(elements: list[Element], width: int = 300, height: int = 300) -> Floor:
    return Floor(id="fl_1", name="L0", width=width, height=height, elements=elements)


def test_changed_element_becomes_move_with_polygon() -> None:
    # Tilted top edge -> the room is regularized -> a polygon-replace move_element.
    el = Element(id="r1", kind="room", polygon=[[0, 0], [200, 3], [200, 200], [0, 200]])
    out = propose_normalization(_floor([el]), 1)
    moves = [c for c in out if isinstance(c, cmds.MoveElement)]
    assert len(moves) == 1
    assert moves[0].element_id == "r1"
    assert moves[0].polygon is not None


def test_sliver_becomes_delete_element() -> None:
    big = Element(id="r1", kind="room", polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])
    speck = Element(id="w1", kind="wall", polygon=[[0, 0], [5, 0], [5, 5], [0, 5]])
    out = propose_normalization(_floor([big, speck]), 1)
    deletes = [c for c in out if isinstance(c, cmds.DeleteElement)]
    assert any(c.element_id == "w1" for c in deletes)


def test_commands_are_applicable_by_the_engine() -> None:
    el = Element(id="r1", kind="room", polygon=[[0, 0], [200, 3], [200, 200], [0, 200]])
    floor = _floor([el])
    out = propose_normalization(floor, 1)
    result = floor
    for command in out:
        result = editing.apply(result, command)  # must not raise
    assert result is not floor  # engine returned new floors (pure)


def test_invalid_level_propagates() -> None:
    floor = _floor([Element(id="r1", kind="room",
                            polygon=[[0, 0], [100, 0], [100, 100], [0, 100]])])
    with pytest.raises(ValueError):
        propose_normalization(floor, 5)
