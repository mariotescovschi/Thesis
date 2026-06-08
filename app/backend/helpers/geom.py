"""Pure geometry helpers shared across services (merge, editing, scene). No I/O."""


def poly_area_px(poly: list[list[float]]) -> float:
    """Shoelace area of a polygon in pixel units."""
    n = len(poly)
    if n < 3:
        return 0.0
    s = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        s += x1 * y2 - x2 * y1
    return abs(s) / 2.0


def centroid(poly: list[list[float]]) -> tuple[float, float]:
    """Area-weighted centroid; falls back to vertex mean for degenerate polygons."""
    n = len(poly)
    if n == 0:
        return (0.0, 0.0)
    if n < 3:
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    a = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if a == 0:
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


def bbox(poly: list[list[float]]) -> tuple[float, float, float, float]:
    """Axis-aligned bounding box: (min_x, min_y, max_x, max_y)."""
    xs = [p[0] for p in poly]
    ys = [p[1] for p in poly]
    return (min(xs), min(ys), max(xs), max(ys))
