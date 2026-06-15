"""Pure Floor -> compact LLM-facing 'scene' description. No LLM calls, no I/O.

All coordinates are normalized into a 0..1000 space so raw pixels never leak
downstream. Centerlines for thin elements use the farthest-apart-vertices
approximation of the min-area-rect long axis (cheap, deterministic, no deps).
"""
from shapely.geometry import Polygon

from core.document import Floor
from helpers.geom import bbox, centroid, poly_area_px

_SEGMENT_KINDS = ("wall", "door", "window", "railing")
_NORM = 1000.0


def _norm_params(floor: Floor) -> tuple[float, float, float, float]:
    """Return (off_x, off_y, w, h) for normalization; fall back to global bbox."""
    if floor.width > 0 and floor.height > 0:
        return (0.0, 0.0, float(floor.width), float(floor.height))
    pts = [p for el in floor.elements for p in el.polygon]
    if not pts:
        return (0.0, 0.0, 1.0, 1.0)
    minx, miny, maxx, maxy = bbox(pts)
    return (minx, miny, max(maxx - minx, 1.0), max(maxy - miny, 1.0))


def _n(x: float, y: float, p: tuple[float, float, float, float]) -> list[int]:
    """Normalize a single point into the 0..1000 integer space."""
    off_x, off_y, w, h = p
    return [round((x - off_x) * _NORM / w), round((y - off_y) * _NORM / h)]


# --- public coordinate helpers ---------------------------------------------
# The scene presents everything in 0..1000 so raw pixels never leak to the model.
# Commands the model proposes therefore come back in 0..1000 too and MUST be
# converted to image pixels before the edit engine (which works in pixels) can
# apply them. These wrappers expose both directions for the chat service.
def norm_params(floor: Floor) -> tuple[float, float, float, float]:
    """Public alias for the (off_x, off_y, w, h) normalization params of a floor."""
    return _norm_params(floor)


def norm_point(x: float, y: float, p: tuple[float, float, float, float]) -> list[int]:
    """Pixels -> 0..1000 (for presenting pins consistently with the scene)."""
    return _n(x, y, p)


def denorm_point(x: float, y: float, p: tuple[float, float, float, float]) -> list[float]:
    """0..1000 -> image pixels (inverse of norm_point)."""
    off_x, off_y, w, h = p
    return [off_x + x * w / _NORM, off_y + y * h / _NORM]


def denorm_delta(dx: float, dy: float, p: tuple[float, float, float, float]) -> list[float]:
    """0..1000 delta -> pixel delta (no offset; for move_element dx/dy)."""
    _off_x, _off_y, w, h = p
    return [dx * w / _NORM, dy * h / _NORM]


def _farthest_pair(poly: list[list[int]]) -> tuple[list[float], list[float]]:
    """Fallback: the two farthest-apart vertices (degenerate / tiny polygons)."""
    best = (poly[0], poly[1])
    best_d = -1.0
    for i in range(len(poly)):
        for j in range(i + 1, len(poly)):
            d = (poly[i][0] - poly[j][0]) ** 2 + (poly[i][1] - poly[j][1]) ** 2
            if d > best_d:
                best_d, best = d, (poly[i], poly[j])
    a, b = best
    return ([float(a[0]), float(a[1])], [float(b[0]), float(b[1])])


def _mid(p: tuple, q: tuple) -> list[float]:
    return [(p[0] + q[0]) / 2.0, (p[1] + q[1]) / 2.0]


def _centerline(poly: list[list[int]]) -> tuple[list[float], list[float]]:
    """Long axis of the minimum rotated rectangle (true centerline of a thin shape)."""
    if len(poly) < 2:
        pt = poly[0] if poly else [0, 0]
        return ([float(pt[0]), float(pt[1])], [float(pt[0]), float(pt[1])])
    g = Polygon([(p[0], p[1]) for p in poly])
    if not g.is_valid:
        g = g.buffer(0)
    if g.area <= 0:
        return _farthest_pair(poly)
    rect = list(g.minimum_rotated_rectangle.exterior.coords)[:-1]  # 4 corners
    if len(rect) < 4:
        return _farthest_pair(poly)
    e0 = ((rect[0][0] - rect[1][0]) ** 2 + (rect[0][1] - rect[1][1]) ** 2) ** 0.5
    e1 = ((rect[1][0] - rect[2][0]) ** 2 + (rect[1][1] - rect[2][1]) ** 2) ** 0.5
    # Connect midpoints of the two SHORT edges → the long axis.
    if e0 >= e1:
        return (_mid(rect[1], rect[2]), _mid(rect[3], rect[0]))
    return (_mid(rect[0], rect[1]), _mid(rect[2], rect[3]))


def _room_key(el) -> str:
    return el.label or el.type or el.id


def _neighbors(key: str, adjacency: list[dict]) -> list[str]:
    """Labels adjacent to `key` from the adjacency edge list (deterministic order)."""
    out: list[str] = []
    for e in adjacency:
        if e.get("from") == key and e.get("to") not in out:
            out.append(e.get("to"))
        elif e.get("to") == key and e.get("from") not in out:
            out.append(e.get("from"))
    return out


def _build_rooms(floor: Floor, p: tuple[float, float, float, float]) -> list[dict]:
    rooms = [el for el in floor.elements if el.kind == "room"]
    # % of the whole plan area (width*height), matching the canvas/Understanding
    # panel. Fall back to the sum of room areas only for degenerate (0-size) plans.
    plan_area = float(floor.width * floor.height)
    total_area = plan_area if plan_area > 0 else (
        sum(poly_area_px(el.polygon) for el in rooms) or 1.0
    )
    out: list[dict] = []
    for el in rooms:
        cx, cy = centroid(el.polygon)
        minx, miny, maxx, maxy = bbox(el.polygon)
        key = _room_key(el)
        out.append({
            "id": el.id,
            "name": el.label or el.type or el.id,
            "type": el.type,
            "area_m2": el.area_m2,
            "area_approx_pct": round(poly_area_px(el.polygon) / total_area * 100, 1),
            "centroid": _n(cx, cy, p),
            "bbox": _n(minx, miny, p) + _n(maxx, maxy, p),
            "neighbors": _neighbors(key, floor.adjacency),
        })
    return out


def _build_segments(floor: Floor, p: tuple[float, float, float, float]) -> list[dict]:
    out: list[dict] = []
    for el in floor.elements:
        if el.kind not in _SEGMENT_KINDS:
            continue
        start, end = _centerline(el.polygon)
        entry: dict = {
            "id": el.id,
            "kind": el.kind,
            "start": _n(start[0], start[1], p),
            "end": _n(end[0], end[1], p),
        }
        # Add metric dimensions when scale is known
        if floor.scale_px_per_m and floor.scale_px_per_m > 0:
            length_px = ((start[0] - end[0]) ** 2 + (start[1] - end[1]) ** 2) ** 0.5
            entry["length_m"] = round(length_px / floor.scale_px_per_m, 2)
            # Thickness = short side of oriented bbox
            if len(el.polygon) >= 3:
                g = Polygon([(pt[0], pt[1]) for pt in el.polygon])
                if g.is_valid and g.area > 0:
                    rect = list(g.minimum_rotated_rectangle.exterior.coords)[:-1]
                    if len(rect) >= 4:
                        e0 = ((rect[0][0] - rect[1][0]) ** 2 + (rect[0][1] - rect[1][1]) ** 2) ** 0.5
                        e1 = ((rect[1][0] - rect[2][0]) ** 2 + (rect[1][1] - rect[2][1]) ** 2) ** 0.5
                        entry["thickness_m"] = round(min(e0, e1) / floor.scale_px_per_m, 2)
        out.append(entry)
    return out


def build_scene(floor: Floor) -> dict:
    """Turn a Floor into a compact, normalized scene dict for the LLM."""
    p = _norm_params(floor)
    return {
        "rooms": _build_rooms(floor, p),
        "segments": _build_segments(floor, p),
        "adjacency": floor.adjacency,
        "pins": [
            {"id": a.id, "name": a.name, **dict(zip(("x", "y"), _n(a.x, a.y, p))), "note": a.note}
            for a in floor.annotations
        ],
        "scale_px_per_m": floor.scale_px_per_m,
        "coord_space": "normalized_0_1000",
    }


def _room_line(r: dict) -> str:
    area = f"{r['area_m2']:.2f}m2" if r["area_m2"] is not None else f"~{r['area_approx_pct']}%"
    nb = ", ".join(n for n in r["neighbors"] if n) or "none"
    return (
        f"- {r['name']} [{r['type'] or 'unknown'}] (id={r['id']}) {area} "
        f"@ {r['centroid']} | neighbors: {nb}"
    )


def _segment_line(s: dict) -> str:
    """One line per segment so the model can target it by id (was: counts only)."""
    dims = ""
    if "length_m" in s:
        dims = f" {s['length_m']}m"
        if "thickness_m" in s:
            dims += f" x{s['thickness_m']}m"
    return f"- {s['kind']} (id={s['id']}) {s['start']}->{s['end']}{dims}"


def scene_to_text(scene: dict) -> str:
    """Deterministic, compact human-readable summary for a text prompt."""
    lines = [f"SCENE (coords {scene['coord_space']}, scale_px_per_m={scene['scale_px_per_m']})"]
    lines.append(f"Rooms ({len(scene['rooms'])}):")
    lines.extend(_room_line(r) for r in scene["rooms"])
    kinds: dict[str, int] = {}
    for s in scene["segments"]:
        kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
    seg_breakdown = ", ".join(f"{k}={kinds[k]}" for k in sorted(kinds)) or "none"
    lines.append(f"Segments ({len(scene['segments'])}): {seg_breakdown}")
    lines.extend(_segment_line(s) for s in scene["segments"])
    lines.append(f"Pins ({len(scene['pins'])}):")
    lines.extend(f"- {pin['name']} @ [{pin['x']}, {pin['y']}]" for pin in scene["pins"])
    return "\n".join(lines)


# Building-level (multi-floor) scene helpers live in their own module to keep
# this file within length limits; re-exported here so `scene.build_building_scene`
# stays the public entry point.
from helpers.building_scene import build_building_scene, building_scene_to_text  # noqa: E402,F401
