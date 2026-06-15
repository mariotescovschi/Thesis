"""Pure deterministic polygon regularization for the post-analysis Normalize pass.

Three cumulative levels, gentle by design (it cleans up, it does not redraw):

- L1 (light):  per-element axis snap (near-H/V edges -> exact H/V), merge of
               near-duplicate and collinear vertices, drop sub-MIN_AREA slivers.
- L2 (medium): L1 + weld each room corner onto a nearby wall corner and weld
               nearby room corners together (the "corner between 4 walls" case)
               so adjacent rooms meet exactly.
- L3 (hard):   L2 + clip room-room overlaps (carve the shared area out of the
               smaller room) so neighbours tile instead of overlapping.

No I/O and no mutation of the input Floor. Returns only what changed so the
caller can express the diff as move_element / delete_element edit commands.
"""
import math
from dataclasses import dataclass, field

from core.document import Floor
from helpers.editing_geom import round_poly
from helpers.geom import poly_area_px
from helpers.normalize_cross import clip_overlaps, snap_tolerance, weld_rooms

IntPoly = list[list[int]]
FPoly = list[list[float]]

MIN_AREA = 80.0           # px^2; matches infra.geometry - below this is a speck
_ANGLE_TOL_DEG = 8.0      # an edge within this of H/V is snapped to exact H/V
_COLLINEAR_TOL_DEG = 6.0  # a vertex straighter than this is dropped
_DUP_DIST = 2.0           # px; consecutive vertices closer than this are merged


@dataclass
class NormalizedFloor:
    """Diff produced by a normalization pass (polygons in image pixels)."""
    changed: dict[str, IntPoly] = field(default_factory=dict)  # id -> new polygon
    dropped: list[str] = field(default_factory=list)           # ids to delete


def _dedupe(poly: FPoly) -> FPoly:
    out: FPoly = []
    for p in poly:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) > _DUP_DIST:
            out.append([p[0], p[1]])
    if len(out) > 1 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= _DUP_DIST:
        out.pop()
    return out


def _axis_snap(poly: FPoly) -> FPoly:
    """Snap near-H/V edges to exact H/V by averaging the shared coordinate of their
    endpoints (one pass; deliberately not a full rectilinearization)."""
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        if dx == 0 and dy == 0:
            continue
        ang = math.degrees(math.atan2(abs(dy), abs(dx)))
        if ang <= _ANGLE_TOL_DEG:          # near-horizontal -> share y
            a[1] = b[1] = (a[1] + b[1]) / 2.0
        elif ang >= 90 - _ANGLE_TOL_DEG:   # near-vertical -> share x
            a[0] = b[0] = (a[0] + b[0]) / 2.0
    return poly


def _drop_collinear(poly: FPoly) -> FPoly:
    n = len(poly)
    if n < 4:
        return poly
    keep: FPoly = []
    for i in range(n):
        prev, cur, nxt = poly[i - 1], poly[i], poly[(i + 1) % n]
        v1 = (cur[0] - prev[0], cur[1] - prev[1])
        v2 = (nxt[0] - cur[0], nxt[1] - cur[1])
        if math.hypot(*v1) == 0 or math.hypot(*v2) == 0:
            continue  # degenerate -> drop
        turn = math.degrees(abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                           v1[0] * v2[0] + v1[1] * v2[1])))
        if turn >= _COLLINEAR_TOL_DEG:
            keep.append(cur)
    return keep if len(keep) >= 3 else poly


def _regularize(poly: IntPoly) -> FPoly:
    """L1 pipeline for a single polygon (returns float coords)."""
    p = _dedupe([[float(x), float(y)] for x, y in poly])
    if len(p) < 3:
        return p
    return _drop_collinear(_axis_snap(p))


def normalize_floor(floor: Floor, level: int) -> NormalizedFloor:
    """Regularization diff for a floor at the given level (1..3). Pure: the input
    floor is never mutated."""
    if level not in (1, 2, 3):
        raise ValueError(f"normalization level must be 1, 2 or 3 (got {level})")
    result = NormalizedFloor()

    reg: dict[str, FPoly] = {}
    for el in floor.elements:
        p = _regularize(el.polygon)
        if len(p) < 3 or poly_area_px(p) < MIN_AREA:
            result.dropped.append(el.id)
        else:
            reg[el.id] = p

    rooms = {el.id: reg[el.id] for el in floor.elements
             if el.kind == "room" and el.id in reg}

    if level >= 2 and rooms:
        anchors = [(v[0], v[1]) for el in floor.elements
                   if el.kind == "wall" and el.id in reg for v in reg[el.id]]
        walls = [el.polygon for el in floor.elements if el.kind == "wall"]
        weld_rooms(rooms, anchors, snap_tolerance(walls, floor.width, floor.height))

    if level >= 3 and len(rooms) > 1:
        clipped = clip_overlaps(rooms, MIN_AREA)
        for rid in list(rooms):
            if rid not in clipped:
                rooms.pop(rid)
                result.dropped.append(rid)
        for rid, poly in clipped.items():
            rooms[rid] = _drop_collinear(_dedupe(poly))

    for el in floor.elements:
        if el.id in result.dropped:
            continue
        new_poly = rooms.get(el.id) or reg.get(el.id)
        if new_poly is None:
            continue
        rounded = round_poly(new_poly)
        if len(rounded) >= 3 and rounded != el.polygon:
            result.changed[el.id] = rounded
    return result
