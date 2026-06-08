"""Edit-command engine: pure, deterministic `apply(floor, command) -> new Floor`.

One `EditCommand` (commands.py) is applied to a copy of a Floor Document and a NEW
Floor is returned — the input is never mutated. No I/O, no LLM. Geometry reuses
the shared pure helpers in geom.py.
"""
from typing import Optional

import core.commands as cmds
import helpers.editing_geom as eg
from core.document import Annotation, Element, Floor, new_id
from core.errors import NotFoundError, ValidationError
from helpers.geom import poly_area_px

IntPoly = list[list[int]]


# --- shared helpers ---------------------------------------------------------
def _area_m2(polygon: list[list[float]], scale: Optional[float]) -> Optional[float]:
    """Room area in m² from pixel polygon + scale; None when scale is unknown."""
    if scale and scale > 0:
        return round(poly_area_px(polygon) / (scale * scale), 2)
    return None


def _find_element(floor: Floor, eid: str) -> Element:
    for el in floor.elements:
        if el.id == eid:
            return el
    raise NotFoundError(f"element {eid!r} not found")


def _find_annotation(floor: Floor, aid: str) -> Annotation:
    for an in floor.annotations:
        if an.id == aid:
            return an
    raise NotFoundError(f"annotation {aid!r} not found")


# --- op handlers (each mutates the already-copied floor) --------------------
def _set_label(f: Floor, c: cmds.SetLabel) -> None:
    _find_element(f, c.element_id).label = c.label


def _set_type(f: Floor, c: cmds.SetType) -> None:
    _find_element(f, c.element_id).type = c.type


def _set_area(f: Floor, c: cmds.SetAreaM2) -> None:
    _find_element(f, c.element_id).area_m2 = c.area_m2


def _adj_eq(d: dict, a: str, b: str) -> bool:
    return {d.get("from"), d.get("to")} == {a, b}


def _add_adjacency(f: Floor, c: cmds.AddAdjacency) -> None:
    if not any(_adj_eq(d, c.from_, c.to) for d in f.adjacency):
        f.adjacency.append({"from": c.from_, "to": c.to})


def _remove_adjacency(f: Floor, c: cmds.RemoveAdjacency) -> None:
    f.adjacency = [d for d in f.adjacency if not _adj_eq(d, c.from_, c.to)]


def _delete_element(f: Floor, c: cmds.DeleteElement) -> None:
    f.elements = [el for el in f.elements if el.id != c.element_id]


def _merge_rooms(f: Floor, c: cmds.MergeRooms) -> None:
    if len(c.element_ids) < 2:
        raise ValidationError("merge_rooms needs at least two element ids")
    first = _find_element(f, c.element_ids[0])
    polys = [_find_element(f, eid).polygon for eid in c.element_ids]
    try:
        first.polygon = eg.round_poly(eg.union_polygons(polys))
    except ValueError as e:
        raise ValidationError(f"cannot merge rooms: {e}")
    first.area_m2 = _area_m2(first.polygon, f.scale_px_per_m)
    rest = set(c.element_ids[1:])
    f.elements = [el for el in f.elements if el.id not in rest]


def _split_room(f: Floor, c: cmds.SplitRoom) -> None:
    el = _find_element(f, c.element_id)
    try:
        pieces = eg.split_polygon(el.polygon, c.segment)
    except ValueError as e:
        raise ValidationError(f"cannot split room: {e}")
    if len(pieces) < 2:
        raise ValidationError("split segment does not cross the room polygon")
    out = [el.model_copy(deep=True, update={"id": new_id("el"), "polygon": eg.round_poly(piece)})
           for piece in pieces]
    for piece in out:
        piece.area_m2 = _area_m2(piece.polygon, f.scale_px_per_m)
    f.elements = [e for e in f.elements if e.id != c.element_id] + out


def _add_wall(f: Floor, c: cmds.AddWall) -> None:
    try:
        poly = eg.round_poly(eg.wall_polygon(c.segment, c.thickness))
    except ValueError as e:
        raise ValidationError(f"cannot add wall: {e}")
    f.elements.append(Element(id=new_id("el"), kind="wall", polygon=poly))


def _move_element(f: Floor, c: cmds.MoveElement) -> None:
    el = _find_element(f, c.element_id)
    if c.polygon is not None:
        el.polygon = eg.round_poly(c.polygon)
    else:
        el.polygon = eg.round_poly([[x + c.dx, y + c.dy] for x, y in el.polygon])
    if el.kind == "room":
        el.area_m2 = _area_m2(el.polygon, f.scale_px_per_m)


def _set_scale(f: Floor, c: cmds.SetScale) -> None:
    f.scale_px_per_m = c.scale_px_per_m
    for el in f.elements:
        if el.kind == "room":
            el.area_m2 = _area_m2(el.polygon, c.scale_px_per_m)


def _add_annotation(f: Floor, c: cmds.AddAnnotation) -> None:
    f.annotations.append(Annotation(id=new_id("pin"), x=c.x, y=c.y, name=c.name, note=c.note))


def _update_annotation(f: Floor, c: cmds.UpdateAnnotation) -> None:
    an = _find_annotation(f, c.id)
    for field in ("name", "note", "x", "y"):
        val = getattr(c, field)
        if val is not None:
            setattr(an, field, val)


def _delete_annotation(f: Floor, c: cmds.DeleteAnnotation) -> None:
    f.annotations = [a for a in f.annotations if a.id != c.id]


_DISPATCH = {
    "set_label": _set_label, "set_type": _set_type, "set_area_m2": _set_area,
    "add_adjacency": _add_adjacency, "remove_adjacency": _remove_adjacency,
    "delete_element": _delete_element, "merge_rooms": _merge_rooms,
    "split_room": _split_room, "add_wall": _add_wall, "move_element": _move_element,
    "set_scale": _set_scale, "add_annotation": _add_annotation,
    "update_annotation": _update_annotation, "delete_annotation": _delete_annotation,
}


def apply(floor: Floor, command: cmds.EditCommand) -> Floor:
    """Apply one EditCommand to a deep copy of `floor` and return the new Floor."""
    handler = _DISPATCH.get(command.op)
    if handler is None:
        raise ValidationError(f"unknown op {command.op!r}")
    result = floor.model_copy(deep=True)
    handler(result, command)
    return result
