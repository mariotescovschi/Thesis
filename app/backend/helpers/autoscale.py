"""Estimate scale_px_per_m from door widths (heuristic).

Strategy: for each door element, compute the short side of its oriented bounding
box (= door opening width in pixels). Take the median, divide by assumed real
door width in meters. Fallback chain: doors → windows → None.
"""
from statistics import median

from shapely.geometry import Polygon

from core.document import Floor

ASSUMED_DOOR_M = 0.9     # typical interior door width
ASSUMED_WINDOW_M = 1.2   # typical window width (fallback)


def _short_side_px(poly: list[list[float]]) -> float | None:
    """Return the short side length of the minimum rotated rectangle."""
    if len(poly) < 3:
        return None
    g = Polygon(poly)
    if not g.is_valid:
        g = g.buffer(0)
    if g.area <= 0:
        return None
    rect = list(g.minimum_rotated_rectangle.exterior.coords)[:-1]
    if len(rect) < 4:
        return None
    e0 = ((rect[0][0] - rect[1][0]) ** 2 + (rect[0][1] - rect[1][1]) ** 2) ** 0.5
    e1 = ((rect[1][0] - rect[2][0]) ** 2 + (rect[1][1] - rect[2][1]) ** 2) ** 0.5
    return min(e0, e1)


def estimate_scale(floor: Floor) -> float | None:
    """Estimate scale_px_per_m from element geometry. Returns None if not enough data."""
    # Try doors first
    doors = [el for el in floor.elements if el.kind == "door"]
    widths = [w for el in doors if (w := _short_side_px(el.polygon)) is not None and w > 0]
    if len(widths) >= 1:
        return round(median(widths) / ASSUMED_DOOR_M, 2)

    # Fallback: windows
    windows = [el for el in floor.elements if el.kind == "window"]
    widths = [w for el in windows if (w := _short_side_px(el.polygon)) is not None and w > 0]
    if len(widths) >= 1:
        return round(median(widths) / ASSUMED_WINDOW_M, 2)

    return None
