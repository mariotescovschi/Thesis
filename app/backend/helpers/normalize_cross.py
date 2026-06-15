"""Cross-element normalization: weld room corners + clip room overlaps.

Split out of helpers/normalize.py to keep each module within the helper length
budget (mirrors the scene.py / building_scene.py split). Pure, shapely-backed,
no I/O.
"""
import math

from shapely.geometry import Polygon

from helpers.geom import poly_area_px

FPoly = list[list[float]]
Point = tuple[float, float]


def _short_side(poly: list[list[int]]) -> float | None:
    """Short side of the minimum rotated rectangle (≈ wall thickness)."""
    if len(poly) < 3:
        return None
    g = Polygon([(p[0], p[1]) for p in poly])
    if not g.is_valid:
        g = g.buffer(0)
    if g.area <= 0:
        return None
    rect = list(g.minimum_rotated_rectangle.exterior.coords)[:-1]
    if len(rect) < 4:
        return None
    return min(math.dist(rect[0], rect[1]), math.dist(rect[1], rect[2]))


def snap_tolerance(walls: list[list[list[int]]], width: int, height: int) -> float:
    """Welding tolerance: a wall thickness when walls exist, else ~1% of the plan
    diagonal. Conservative so we weld real corners, not genuinely distinct ones."""
    ths = sorted(t for w in walls for t in (_short_side(w),) if t)
    if ths:
        return max(6.0, ths[len(ths) // 2])
    return max(6.0, math.hypot(width or 1, height or 1) * 0.01)


def weld_rooms(rooms: dict[str, FPoly], anchors: list[Point], tol: float) -> None:
    """In place: snap each room vertex to a nearby wall anchor (fixed) or, failing
    that, to a shared cluster mean so adjacent room corners coincide exactly."""
    seeds = [[a[0], a[1]] for a in anchors]
    fixed = [True] * len(seeds)
    members: list[list[list[float]]] = [[] for _ in seeds]
    for poly in rooms.values():
        for v in poly:
            bi, bd = -1, tol
            for ci, c in enumerate(seeds):
                d = math.hypot(v[0] - c[0], v[1] - c[1])
                if d <= bd:
                    bd, bi = d, ci
            if bi == -1:
                seeds.append([v[0], v[1]])
                fixed.append(False)
                members.append([v])
            else:
                members[bi].append(v)
                if not fixed[bi]:
                    m = members[bi]
                    seeds[bi] = [sum(x[0] for x in m) / len(m),
                                 sum(x[1] for x in m) / len(m)]
    for c, m in zip(seeds, members):
        for v in m:
            v[0], v[1] = c[0], c[1]


def _shp(poly: FPoly) -> Polygon:
    g = Polygon([(p[0], p[1]) for p in poly])
    return g if g.is_valid else g.buffer(0)


def _largest_ring(geom) -> FPoly | None:
    """Exterior ring (no closing vertex) of the largest polygon part, or None."""
    if geom.is_empty:
        return None
    if geom.geom_type == "Polygon":
        polys = [geom]
    elif geom.geom_type in ("MultiPolygon", "GeometryCollection"):
        polys = [g for g in geom.geoms if g.geom_type == "Polygon" and g.area > 0]
    else:
        return None
    if not polys:
        return None
    g = max(polys, key=lambda p: p.area)
    return [[c[0], c[1]] for c in g.exterior.coords[:-1]]


def clip_overlaps(rooms: dict[str, FPoly], min_area: float) -> dict[str, FPoly]:
    """Carve overlapping area out of the smaller room so neighbours tile. Larger
    rooms keep their shape; rooms that vanish are absent from the result."""
    polys = {rid: _shp(p) for rid, p in rooms.items()}
    order = sorted(polys, key=lambda r: polys[r].area, reverse=True)
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            big, small = polys[order[i]], polys[order[j]]
            if big.is_empty or small.is_empty or not big.intersects(small):
                continue
            if big.intersection(small).area > 1.0:
                polys[order[j]] = small.difference(big)
    out: dict[str, FPoly] = {}
    for rid, g in polys.items():
        ring = _largest_ring(g)
        if ring and poly_area_px(ring) >= min_area:
            out[rid] = ring
    return out
