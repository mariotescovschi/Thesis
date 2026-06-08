"""Building-level (multi-floor) scene: pure, coordinate-free. No LLM calls, no I/O.

A coarse view of the whole project — the stacking order of floors, a compact
room list per floor, and the cross-floor links — so the building-level chat can
reason about vertical relationships (e.g. "what is directly below the kitchen?")
without per-floor pixel detail. The per-floor pixel scene lives in scene.py.
"""
from core.document import Floor, Project


def _floor_rooms(floor: Floor) -> list[dict]:
    """Compact, coordinate-free room list for a floor (robust to empty floors)."""
    return [
        {"id": el.id, "name": el.label or el.type or el.id, "type": el.type}
        for el in floor.elements
        if el.kind == "room"
    ]


def build_building_scene(project: Project) -> dict:
    """Whole-project scene: stacking order, per-floor rooms, and cross-floor links.

    `stacking` follows project.floors order (index 0 = first/lowest in the list).
    No coordinates are emitted; this is the topological/vertical view of the
    building. Floors without loaded elements still appear (with an empty room
    list) so the stacking stays complete.
    """
    floors = project.floors
    building_type = next((f.building_type for f in floors if f.building_type), None)
    stacking = [
        {"index": i, "floor_id": f.id, "name": f.name, "room_count": len(_floor_rooms(f))}
        for i, f in enumerate(floors)
    ]
    return {
        "project_id": project.id,
        "name": project.name,
        "building_type": building_type,
        "floor_count": len(floors),
        "stacking": stacking,
        "floors": [
            {"floor_id": f.id, "name": f.name, "rooms": _floor_rooms(f)}
            for f in floors
        ],
        "links": [
            {"type": l.type, "from_floor": l.from_floor, "to_floor": l.to_floor, "via": l.via}
            for l in project.links
        ],
        "coord_space": "building_level",
    }


def _floor_name(scene: dict, floor_id: str) -> str:
    for f in scene["floors"]:
        if f["floor_id"] == floor_id:
            return f["name"]
    return floor_id


def building_scene_to_text(scene: dict) -> str:
    """Deterministic, compact human-readable summary of the whole building."""
    bt = scene["building_type"] or "unknown"
    lines = [f"BUILDING '{scene['name']}' [{bt}] — {scene['floor_count']} floor(s)"]
    lines.append("Stacking (bottom->top as listed):")
    for s in scene["stacking"]:
        lines.append(f"- [{s['index']}] {s['name']} (id={s['floor_id']}): {s['room_count']} room(s)")
    for f in scene["floors"]:
        names = ", ".join(r["name"] for r in f["rooms"]) or "none"
        lines.append(f"Floor '{f['name']}' rooms: {names}")
    lines.append(f"Links ({len(scene['links'])}):")
    if scene["links"]:
        for l in scene["links"]:
            via = f" via {l['via']}" if l["via"] else ""
            lines.append(
                f"- {l['type']}: {_floor_name(scene, l['from_floor'])} "
                f"<-> {_floor_name(scene, l['to_floor'])}{via}"
            )
    else:
        lines.append("- none")
    return "\n".join(lines)
