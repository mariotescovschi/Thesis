"""Building-level (cross-floor) chat service. No I/O; sibling of chat.answer().

Spans the whole project instead of one floor. Building chat is advisory and
navigational — it answers questions about floors, their stacking, and the
vertical-circulation links between them — so it never proposes edit commands
(edits are inherently floor-scoped and applied via the floor-level pipeline).
"""
import json
from typing import Optional

import infra.ollama_client as ollama_client
from helpers.building_scene import build_building_scene, building_scene_to_text
from core.document import Project

_SYSTEM_BUILDING = (
    "You are a floor-plan assistant answering questions about a MULTI-FLOOR "
    "building: its floors, their stacking order, the rooms on each floor, and "
    "the vertical-circulation links between floors. Use the BUILDING scene to "
    "reason about cross-floor relationships (what sits above/below what, how "
    "floors connect). Reply with STRICT JSON only: "
    '{"answer": "<short reply>"}. '
    "Building-level chat is advisory and does NOT emit edit commands — edits are "
    "made per floor. Be concise and reference floors by name."
)


def answer_building(
    project: Project,
    message: str,
    pin_ids: Optional[list[str]] = None,
) -> dict:
    """Answer a building-level (cross-floor) chat message.

    Sibling of `chat.answer()` — it spans all floors instead of one. Returns
    {"answer": str, "commands": []}: building chat is informational/navigational,
    so it never proposes edit commands. `pin_ids` is accepted for signature
    symmetry but unused at building level.
    """
    scene_txt = building_scene_to_text(build_building_scene(project))
    prompt = f"{scene_txt}\n\nUSER: {message}"
    messages = [
        {"role": "system", "content": _SYSTEM_BUILDING},
        {"role": "user", "content": prompt},
    ]
    content = ollama_client.chat(messages, json_format=True)
    try:
        data = json.loads(content)
        answer_text = (
            str(data.get("answer", "")).strip()
            if isinstance(data, dict) else content.strip()
        )
    except (ValueError, TypeError):
        answer_text = content.strip()
    return {"answer": answer_text, "commands": []}
