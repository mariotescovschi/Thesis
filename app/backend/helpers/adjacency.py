"""Derive adjacency edges from room geometry (rooms sharing a boundary)."""
from shapely.geometry import Polygon

from core.document import Floor

# Two rooms are adjacent if their polygons are within this distance (pixels).
_TOUCH_THRESHOLD = 5.0


def derive_adjacency(floor: Floor) -> list[dict]:
    """Return adjacency edge list [{"from": name, "to": name}] from geometry."""
    rooms = [(el, Polygon(el.polygon)) for el in floor.elements if el.kind == "room" and len(el.polygon) >= 3]
    edges: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for i, (el_a, poly_a) in enumerate(rooms):
        if not poly_a.is_valid:
            poly_a = poly_a.buffer(0)
        for j in range(i + 1, len(rooms)):
            el_b, poly_b = rooms[j]
            if not poly_b.is_valid:
                poly_b = poly_b.buffer(0)
            if poly_a.distance(poly_b) <= _TOUCH_THRESHOLD:
                name_a = el_a.label or el_a.type or el_a.id
                name_b = el_b.label or el_b.type or el_b.id
                key = (min(name_a, name_b), max(name_a, name_b))
                if key not in seen:
                    seen.add(key)
                    edges.append({"from": name_a, "to": name_b})
    return edges
