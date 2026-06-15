"""Edit routes: apply one EditCommand to the overlay, or revert to the base.

Edits never touch the immutable pipeline output (`{floor_id}.json`); they read
the current Document (overlay-preferred), apply the command via the pure engine,
and write the result to the overlay (`{floor_id}.edited.json`). Revert simply
deletes the overlay so the next read falls back to the pipeline base (Q1=C).
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field

import services.editing as editing
import services.normalization as normalization
import infra.store as store
from core.commands import EditCommand, EditCommandEnvelope
from core.document import Floor

router = APIRouter()


class BatchBody(BaseModel):
    commands: list[EditCommand]


class NormalizeBody(BaseModel):
    level: int = Field(ge=1, le=3, description="1 = light, 2 = medium, 3 = hard")


@router.patch("/projects/{pid}/output/{floor_id}")
def apply_edit(pid: str, floor_id: str, body: EditCommandEnvelope) -> dict[str, Floor]:
    """Apply one edit command and persist it to the overlay; return the new Document."""
    current = store.read_output(pid, floor_id)          # 404 if never analyzed
    updated = editing.apply(current, body.command)      # pure; raises on bad command
    store.write_overlay(pid, floor_id, updated)
    return {"data": updated}


@router.post("/projects/{pid}/output/{floor_id}/batch")
def apply_edits(pid: str, floor_id: str, body: BatchBody) -> dict[str, Floor]:
    """Apply several commands atomically: all succeed and persist once, or none do.

    Used for chat-proposed edit sets so a later failing command (e.g. one that
    references an element an earlier command deleted) never leaves a half-applied,
    broken document on disk.
    """
    updated = store.read_output(pid, floor_id)          # 404 if never analyzed
    for command in body.commands:
        updated = editing.apply(updated, command)       # raises -> nothing written
    store.write_overlay(pid, floor_id, updated)
    return {"data": updated}


@router.post("/projects/{pid}/output/{floor_id}/normalize")
def normalize(pid: str, floor_id: str, body: NormalizeBody) -> dict:
    """Propose regularization edits for the current Document WITHOUT persisting.

    Returns move_element/delete_element commands so the client can preview them
    (amber ghost) and apply via the batch endpoint — the base/overlay are untouched
    until the user accepts. Levels: 1 light, 2 medium, 3 hard.
    """
    current = store.read_output(pid, floor_id)          # 404 if never analyzed
    commands = normalization.propose_normalization(current, body.level)
    return {"data": {"commands": commands}}


@router.delete("/projects/{pid}/output/{floor_id}/edits")
def revert_edits(pid: str, floor_id: str) -> dict[str, Floor]:
    """Discard all overlay edits and return the pipeline original."""
    store.delete_overlay(pid, floor_id)
    return {"data": store.read_base_output(pid, floor_id)}


@router.post("/projects/{pid}/output/{floor_id}/autoscale")
def autoscale(pid: str, floor_id: str) -> dict[str, Floor]:
    """Re-estimate scale_px_per_m from door/window widths and recompute areas."""
    from helpers.autoscale import estimate_scale
    current = store.read_output(pid, floor_id)
    estimated = estimate_scale(current)
    if estimated is None:
        from core.errors import ValidationError
        raise ValidationError("Cannot estimate scale: no doors or windows found")
    current.scale_px_per_m = estimated
    for el in current.elements:
        if el.kind == "room":
            current.area_m2 = None  # force recompute
            from services.editing import _area_m2
            el.area_m2 = _area_m2(el.polygon, current.scale_px_per_m)
    store.write_overlay(pid, floor_id, current)
    return {"data": current}


@router.post("/projects/{pid}/output/{floor_id}/adjacency/derive")
def derive_adjacency_route(pid: str, floor_id: str) -> dict[str, Floor]:
    """Re-derive adjacency from room geometry and persist."""
    from helpers.adjacency import derive_adjacency
    current = store.read_output(pid, floor_id)
    current.adjacency = derive_adjacency(current)
    store.write_overlay(pid, floor_id, current)
    return {"data": current}
