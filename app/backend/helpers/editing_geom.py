"""Pure 2D polygon geometry for the edit engine, backed by shapely. No I/O.

Robust boolean/clip operations that handle concave polygons and disjoint
results correctly (unlike a hand-rolled convex-hull / half-plane clip):
- split_polygon: cut a polygon by the infinite line through a segment.
- union_polygons: merge polygons into their true union.
- wall_polygon: buffer a segment into a thin rectangle.
"""
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon
from shapely.ops import split as _split, unary_union

IntPoly = list[list[int]]
FloatPoly = list[list[float]]


def round_poly(poly: FloatPoly) -> IntPoly:
    return [[int(round(p[0])), int(round(p[1]))] for p in poly]


def _to_polygon(poly: FloatPoly) -> Polygon:
    g = Polygon([(p[0], p[1]) for p in poly])
    return g if g.is_valid else g.buffer(0)


def _ext_ring(geom: Polygon) -> FloatPoly:
    """Exterior ring without the duplicated closing vertex."""
    return [[c[0], c[1]] for c in geom.exterior.coords[:-1]]


def split_polygon(poly: FloatPoly, segment: list[list[float]],
                  min_area: float = 1.0) -> list[FloatPoly]:
    """Split `poly` by the infinite line through `segment`.

    Returns the exterior rings of every resulting piece (>= min_area). Handles
    concave polygons and cuts that yield more than two pieces.
    """
    base = _to_polygon(poly)
    (x1, y1), (x2, y2) = segment[0], segment[1]
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        raise ValueError("zero-length split segment")
    # Extend the segment to a line guaranteed to span the polygon.
    minx, miny, maxx, maxy = base.bounds
    reach = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5 + 1.0
    length = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / length, dy / length
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    line = LineString([(cx - ux * reach, cy - uy * reach),
                       (cx + ux * reach, cy + uy * reach)])
    result = _split(base, line)
    pieces = [g for g in result.geoms if isinstance(g, Polygon) and g.area >= min_area]
    return [_ext_ring(g) for g in pieces]


def union_polygons(polys: list[FloatPoly], min_area: float = 1.0) -> FloatPoly:
    """True union of polygons. If the result is disjoint, keep the largest part."""
    merged = unary_union([_to_polygon(p) for p in polys])
    if isinstance(merged, (MultiPolygon, GeometryCollection)):
        parts = [g for g in merged.geoms if isinstance(g, Polygon) and g.area >= min_area]
        if not parts:
            raise ValueError("union produced no polygon")
        merged = max(parts, key=lambda g: g.area)
    return _ext_ring(merged)


def wall_polygon(segment: list[list[float]], thickness: float) -> FloatPoly:
    """Buffer a segment into a thin rectangle (flat caps)."""
    (x1, y1), (x2, y2) = segment[0], segment[1]
    line = LineString([(x1, y1), (x2, y2)])
    if line.length == 0:
        raise ValueError("wall segment has zero length")
    buf = line.buffer(thickness / 2.0, cap_style="flat", join_style="mitre")
    return _ext_ring(buf)
