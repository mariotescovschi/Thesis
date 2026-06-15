"""Pure, read-only tools the chat tool-loop can call. No I/O, no LLM, no mutation.

Each tool takes the current Floor + a small args dict and returns a JSON-
serializable result. Coordinates are the SAME 0..1000 space as the scene
(helpers.scene) so the model reasons in one consistent system.
"""
import math
from typing import Optional

from core.document import Floor
from helpers.geom import centroid
from helpers.scene import build_scene, denorm_point, norm_params, norm_point, scene_to_text


def _name(el) -> str:
    return el.label or el.type or el.kind


def _match(el, q: str) -> bool:
    q = q.lower().strip()
    return any(f and q in f.lower() for f in (el.id, el.label, el.type, el.kind))


def _is_name(el, name: str) -> bool:
    name = name.lower().strip()
    return name in ((el.label or "").lower(), (el.type or "").lower(),
                    el.kind.lower(), el.id.lower())


def find_element(floor: Floor, description: str = "", **_) -> dict:
    """Elements whose id/label/type/kind contains `description` (case-insensitive)."""
    p = norm_params(floor)
    matches = []
    for el in floor.elements:
        if not description or _match(el, description):
            cx, cy = centroid(el.polygon)
            matches.append({"id": el.id, "name": _name(el), "kind": el.kind,
                            "type": el.type, "area_m2": el.area_m2,
                            "centroid": norm_point(cx, cy, p)})
    return {"matches": matches, "count": len(matches)}


def list_elements(floor: Floor, kind: Optional[str] = None, **_) -> dict:
    """All elements, optionally filtered by kind (room/wall/door/window/railing)."""
    out = [{"id": el.id, "name": _name(el), "kind": el.kind}
           for el in floor.elements if not kind or el.kind == kind]
    return {"elements": out, "count": len(out)}


def get_neighbors(floor: Floor, name: str = "", **_) -> dict:
    """Rooms adjacent to the room identified by `name` (label/type/id)."""
    target = next((el for el in floor.elements
                   if el.kind == "room" and _is_name(el, name)), None)
    if target is None:
        return {"error": f"no room matching '{name}'", "neighbors": []}
    key = target.label or target.type or target.id
    neighbors: list[str] = []
    for e in floor.adjacency:
        if e.get("from") == key and e.get("to") not in neighbors:
            neighbors.append(e.get("to"))
        elif e.get("to") == key and e.get("from") not in neighbors:
            neighbors.append(e.get("from"))
    return {"room": _name(target), "neighbors": [n for n in neighbors if n]}


def _resolve_px(floor: Floor, val, p) -> Optional[list]:
    """A point name or [x,y] (0..1000) -> pixel coords (for metric distances)."""
    if isinstance(val, str):
        el = next((e for e in floor.elements if _is_name(e, val)), None)
        return list(centroid(el.polygon)) if el else None
    if (isinstance(val, (list, tuple)) and len(val) == 2
            and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in val)):
        return denorm_point(val[0], val[1], p)
    return None


def measure(floor: Floor, a=None, b=None, **_) -> dict:
    """Distance between two points (0..1000) or two element names; px and meters."""
    p = norm_params(floor)
    pa, pb = _resolve_px(floor, a, p), _resolve_px(floor, b, p)
    if pa is None or pb is None:
        return {"error": "could not resolve both endpoints (use a name or [x,y])"}
    dist_px = math.dist(pa, pb)
    out = {"distance_px": round(dist_px, 1)}
    if floor.scale_px_per_m and floor.scale_px_per_m > 0:
        out["distance_m"] = round(dist_px / floor.scale_px_per_m, 2)
    return out


def get_scene(floor: Floor, **_) -> dict:
    """The full current scene text (rooms, segments with ids, pins)."""
    return {"scene": scene_to_text(build_scene(floor))}


_TOOLS = {
    "find_element": find_element,
    "list_elements": list_elements,
    "get_neighbors": get_neighbors,
    "measure": measure,
    "get_scene": get_scene,
}

TOOL_SPECS = (
    "AVAILABLE TOOLS (read-only; to call one, reply with "
    '{"tool": "<name>", "args": {...}}):\n'
    "- find_element{description}: elements whose name/type/kind/id matches.\n"
    "- list_elements{kind?}: all elements, optionally filtered by kind.\n"
    "- get_neighbors{name}: rooms adjacent to a room (by name).\n"
    "- measure{a,b}: distance between two points (0..1000) or two element "
    "names; returns px and meters.\n"
    "- get_scene{}: the full current scene text."
)


def run_tool(floor: Floor, name: str, args: Optional[dict]) -> dict:
    """Dispatch a tool call; returns {"error": ...} on unknown tool / bad args."""
    fn = _TOOLS.get(name)
    if fn is None:
        return {"error": f"unknown tool '{name}'. available: {', '.join(_TOOLS)}"}
    if args is not None and not isinstance(args, dict):
        return {"error": "args must be an object"}
    try:
        return fn(floor, **(args or {}))
    except TypeError as exc:
        return {"error": f"bad args for {name}: {exc}"}
