"""Normalization service: turn a regularization diff into proposed edit commands.

Pure (Floor + level in -> EditCommand[] out). Persists nothing; the route returns
the commands for preview and the existing batch endpoint applies them (overlay),
so normalization reuses the whole preview / Apply / undo pipeline.
"""
import core.commands as cmds
from core.document import Floor
from helpers.normalize import normalize_floor


def propose_normalization(floor: Floor, level: int) -> list[cmds.EditCommand]:
    """Regularize `floor` at `level` (1..3) and express the diff as edit commands:
    move_element (polygon replace) for changed elements, delete_element for slivers.
    Raises ValueError for an out-of-range level (surfaced by the route as 400)."""
    diff = normalize_floor(floor, level)
    commands: list[cmds.EditCommand] = []
    for eid, polygon in diff.changed.items():
        commands.append(cmds.MoveElement(
            op="move_element",
            element_id=eid,
            polygon=[[float(x), float(y)] for x, y in polygon],
        ))
    for eid in diff.dropped:
        commands.append(cmds.DeleteElement(op="delete_element", element_id=eid))
    return commands
