"""Chat service: floor scene + user message -> answer text + validated edit commands.

Pipeline (Route → Service → Store; this is the Service layer, no I/O):
  build_scene(floor) → scene_to_text → prompt (with pins-in-context) →
  ollama_client.chat → parse JSON {"answer", "commands"} →
  resolve pin references to coordinates → validate each via EditCommandEnvelope →
  drop invalid silently.

The public `answer(project, floor, message, pin_ids)` signature is STABLE —
T12 (routes) depends on it. It never applies commands; it only proposes them.
"""
import json
from typing import Optional

import core.commands as cmds
import services.chat_loop as chat_loop
from core.document import Annotation, Floor, Project
from helpers.scene import (
    build_building_scene,
    build_scene,
    building_scene_to_text,
    denorm_delta,
    denorm_point,
    norm_params,
    norm_point,
    scene_to_text,
)

# Fields on a command that carry coordinates and may reference pins.
_POINT_FIELD = "polygon"      # list[[x, y], ...]
_SEGMENT_FIELD = "segment"    # [[x, y], [x, y]]

_SYSTEM = (
    "You are a floor-plan editing assistant. You answer the user's question "
    "about the plan AND, when they request a change, propose deterministic edit "
    "commands. Reply with STRICT JSON only: "
    '{"answer": "<short reply>", "commands": [<command>, ...]}. '
    "IMPORTANT: In your 'answer' text, always refer to rooms/elements by their "
    "human-readable NAME (label or type, e.g. 'kitchen', 'bedroom 1'), NEVER by "
    "their internal id. The user cannot see ids. "
    "Each command is an object with an \"op\" field from this vocabulary: "
    "set_label{element_id,label}, set_type{element_id,type}, "
    "set_area_m2{element_id,area_m2}, add_adjacency{from,to}, "
    "remove_adjacency{from,to}, delete_element{element_id}, "
    "merge_rooms{element_ids[]}, split_room{element_id,segment}, "
    "add_wall{segment,thickness?}, move_element{element_id,dx?,dy?,polygon?}, "
    "set_scale{scale_px_per_m}, add_annotation{x,y,name,note?}, "
    "update_annotation{id,name?,note?,x?,y?}, delete_annotation{id}. "
    "In commands, use the exact id shown as (id=...) in the SCENE. "
    "A segment is [[x1,y1],[x2,y2]]. All coordinates you output MUST use the "
    "SAME 0..1000 space as the SCENE (they are converted to image pixels "
    "server-side). To anchor a point on a pin, use {\"pin\":\"<pin name>\"} "
    "in place of an [x,y] pair and it will be resolved server-side. "
    "If no edit is needed, return an empty commands list."
)


def _pin_index(floor: Floor) -> dict[str, Annotation]:
    """Map both pin id and pin name -> Annotation for server-side resolution."""
    idx: dict[str, Annotation] = {}
    for a in floor.annotations:
        idx[a.id] = a
        if a.name:
            idx.setdefault(a.name, a)
    return idx


def _pins_in_context(
    floor: Floor, pin_ids: Optional[list[str]], p: tuple[float, float, float, float]
) -> str:
    """Resolve the user-selected pin_ids to a compact name/coords context block.

    Coords are shown in the SAME 0..1000 space as the scene so the model reasons
    in one consistent system; the {"pin":name} ref still resolves to pixels.
    """
    if not pin_ids:
        return ""
    idx = _pin_index(floor)
    lines = []
    for pid in pin_ids:
        a = idx.get(pid)
        if a is not None:
            nx, ny = norm_point(a.x, a.y, p)
            note = f" — {a.note}" if a.note else ""
            lines.append(f"- {a.name} (id={a.id}) @ [{nx}, {ny}]{note}")
    if not lines:
        return ""
    return "PINS IN CONTEXT (user selected these):\n" + "\n".join(lines)


def _building_context(project: Project, current_floor_id: str) -> str:
    """Compact cross-floor context for the floor-level chat (other floors + links).

    Only emitted for genuinely multi-floor projects so single-floor prompts stay
    lean. The current floor's full detail already comes from build_scene above.
    """
    if len(project.floors) <= 1 and not project.links:
        return ""
    scene = build_building_scene(project)
    others = [f["name"] for f in scene["floors"] if f["floor_id"] != current_floor_id]
    parts = []
    if others:
        parts.append("OTHER FLOORS IN BUILDING: " + ", ".join(others))
    if scene["links"]:
        parts.append(building_scene_to_text(scene).split("Links (")[-1].rstrip())
        parts[-1] = "CROSS-FLOOR LINKS (" + parts[-1]
    return "\n".join(parts)


def _elements_in_context(floor: Floor, element_ids: Optional[list[str]]) -> str:
    """Summarize user-selected elements as a context block for the LLM."""
    if not element_ids:
        return ""
    lines = []
    for eid in element_ids:
        for el in floor.elements:
            if el.id == eid:
                name = el.label or el.type or el.kind
                lines.append(f"- {name} (id={el.id}) kind={el.kind} area_m2={el.area_m2}")
                break
    if not lines:
        return ""
    return "ELEMENTS IN CONTEXT (user selected these on canvas):\n" + "\n".join(lines)


def _build_prompt(
    project: Project, floor: Floor, message: str, pin_ids: Optional[list[str]],
    element_ids: Optional[list[str]] = None,
) -> str:
    scene_txt = scene_to_text(build_scene(floor))
    parts = [scene_txt]
    building = _building_context(project, floor.id)
    if building:
        parts.append(building)
    pins = _pins_in_context(floor, pin_ids, norm_params(floor))
    if pins:
        parts.append(pins)
    elements = _elements_in_context(floor, element_ids)
    if elements:
        parts.append(elements)
    parts.append(f"USER: {message}")
    return "\n\n".join(parts)


def _resolve_point(value, idx: dict[str, Annotation]):
    """Resolve a single point ref: {"pin": name} or "pin name" -> [x, y]."""
    if isinstance(value, dict) and "pin" in value:
        a = idx.get(str(value["pin"]))
        return [a.x, a.y] if a is not None else None
    if isinstance(value, str):
        a = idx.get(value)
        return [a.x, a.y] if a is not None else value
    return value


def _resolve_pins(raw: dict, idx: dict[str, Annotation]) -> dict:
    """Replace pin references inside segment/polygon fields with raw coordinates."""
    if not isinstance(raw, dict):
        return raw
    out = dict(raw)
    seg = out.get(_SEGMENT_FIELD)
    if isinstance(seg, list):
        resolved = [_resolve_point(pt, idx) for pt in seg]
        if all(isinstance(p, list) for p in resolved):
            out[_SEGMENT_FIELD] = resolved
    poly = out.get(_POINT_FIELD)
    if isinstance(poly, list):
        resolved = [_resolve_point(pt, idx) for pt in poly]
        if all(isinstance(p, list) for p in resolved):
            out[_POINT_FIELD] = resolved
    return out


def _denorm_point(pt, p: tuple[float, float, float, float]):
    """Convert a numeric [x, y] from 0..1000 to pixels; leave pin refs untouched."""
    if (
        isinstance(pt, list)
        and len(pt) == 2
        and all(isinstance(c, (int, float)) and not isinstance(c, bool) for c in pt)
    ):
        return denorm_point(pt[0], pt[1], p)
    return pt


def _denormalize(raw: dict, p: tuple[float, float, float, float]) -> dict:
    """Map a model command's 0..1000 coords to image pixels (the engine's space).

    Runs BEFORE pin resolution so {"pin":name} refs (resolved to pixels later) are
    not double-converted. Touches only the coordinate-bearing fields.
    """
    if not isinstance(raw, dict):
        return raw
    out = dict(raw)
    for field in (_SEGMENT_FIELD, _POINT_FIELD):
        v = out.get(field)
        if isinstance(v, list):
            out[field] = [_denorm_point(pt, p) for pt in v]
    x, y = out.get("x"), out.get("y")
    if isinstance(x, (int, float)) and not isinstance(x, bool) and isinstance(y, (int, float)) and not isinstance(y, bool):
        out["x"], out["y"] = denorm_point(x, y, p)
    if "dx" in out or "dy" in out:
        dx, dy = denorm_delta(out.get("dx") or 0.0, out.get("dy") or 0.0, p)
        if "dx" in out:
            out["dx"] = dx
        if "dy" in out:
            out["dy"] = dy
    return out


def _element_index(floor: Floor) -> dict[str, str]:
    """Map id/label/type -> a real element id so the model can reference rooms by
    their readable name. Ids are authoritative; labels/types fill in (first match)."""
    eidx: dict[str, str] = {el.id: el.id for el in floor.elements}
    for el in floor.elements:
        if el.label:
            eidx.setdefault(el.label, el.id)
    for el in floor.elements:
        if el.type:
            eidx.setdefault(el.type, el.id)
    return eidx


def _resolve_element_refs(raw: dict, eidx: dict[str, str]) -> dict:
    """Rewrite element_id / element_ids from a name/label to a real element id."""
    if not isinstance(raw, dict):
        return raw
    out = dict(raw)
    eid = out.get("element_id")
    if isinstance(eid, str) and eid in eidx:
        out["element_id"] = eidx[eid]
    eids = out.get("element_ids")
    if isinstance(eids, list):
        out["element_ids"] = [eidx.get(e, e) if isinstance(e, str) else e for e in eids]
    return out


def _reason(exc: Exception) -> str:
    """A short, single-line reason for surfacing a rejected command to the user."""
    return " ".join(str(exc).split())[:200] or exc.__class__.__name__


def _validate(
    raw: dict,
    idx: dict[str, Annotation],
    eidx: dict[str, str],
    p: tuple[float, float, float, float],
) -> tuple[Optional[cmds.EditCommand], Optional[str]]:
    """Denormalize coords, resolve element + pin refs, then validate.

    Returns (command, None) on success or (None, reason) so the caller can tell
    the user WHY an edit was dropped instead of silently discarding it.
    """
    try:
        resolved = _resolve_pins(_resolve_element_refs(_denormalize(raw, p), eidx), idx)
        return cmds.EditCommandEnvelope(command=resolved).command, None
    except Exception as exc:
        return None, _reason(exc)


def _parse_commands(content: str, floor: Floor) -> tuple[str, list, list]:
    """Parse the model's JSON reply into (answer_text, validated, rejected).

    `rejected` is a list of {"command", "reason"} so invalid edits surface in the
    UI with an explanation instead of disappearing (the old silent-drop).
    """
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        # Model ignored the JSON contract — treat the whole reply as the answer.
        return (content.strip(), [], [])
    if not isinstance(data, dict):
        return (content.strip(), [], [])
    answer_text = str(data.get("answer", "")).strip()
    raw_cmds = data.get("commands", [])
    if not isinstance(raw_cmds, list):
        return (answer_text, [], [])
    idx = _pin_index(floor)
    eidx = _element_index(floor)
    p = norm_params(floor)
    validated: list = []
    rejected: list = []
    for r in raw_cmds:
        cmd, reason = _validate(r, idx, eidx, p)
        if cmd is not None:
            validated.append(cmd)
        else:
            rejected.append({"command": r, "reason": reason})
    return (answer_text, validated, rejected)


def answer(
    project: Project,
    floor: Floor,
    message: str,
    pin_ids: Optional[list[str]] = None,
    history: Optional[list[dict]] = None,
    element_ids: Optional[list[str]] = None,
) -> dict:
    """Answer a chat message about a floor, proposing validated edit commands.

    Returns {"answer": str, "commands": list[EditCommand], "rejected": list}.
    The model may first call read-only tools (chat_loop) to inspect the plan;
    commands are schema-validated and pin-resolved but NOT applied. Invalid
    commands come back in `rejected` with a reason (no more silent-drop).
    """
    prompt = _build_prompt(project, floor, message, pin_ids, element_ids)
    system = _SYSTEM + "\n" + chat_loop.TOOL_PROTOCOL
    messages = [{"role": "system", "content": system}]
    # Include last N history turns for multi-turn context (capped at 8)
    if history:
        for turn in history[-8:]:
            role = turn.get("role", "user")
            text = turn.get("text", "")
            if role in ("user", "assistant") and text:
                messages.append({"role": role, "content": text})
    messages.append({"role": "user", "content": prompt})
    content = chat_loop.run_loop(messages, floor)
    answer_text, validated, rejected = _parse_commands(content, floor)
    return {"answer": answer_text, "commands": validated, "rejected": rejected}


# Building-level (cross-floor) chat lives in its own module to keep this file
# within length limits; re-exported so `chat.answer_building` stays available.
from services.chat_building import answer_building  # noqa: E402,F401
