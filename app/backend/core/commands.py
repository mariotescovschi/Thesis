"""EditCommand schema: the deterministic edit vocabulary (Q6=C).

Both manual canvas edits and chat-proposed edits speak this language. The engine
(editing.py, Task 2) applies one command to a Floor Document and returns a new one.
Commands reference element ids, segments, and pins — never raw model state.

Coordinates are image pixels unless noted. Segments are [[x1, y1], [x2, y2]].
"""
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

Point = list[float]      # [x, y] in image pixels
Segment = list[Point]    # [[x1, y1], [x2, y2]]


class _Cmd(BaseModel):
    # allow both "from" (JSON) and "from_" (Python) on adjacency commands
    model_config = ConfigDict(populate_by_name=True)


# --- Semantic edits ---------------------------------------------------------
class SetLabel(_Cmd):
    op: Literal["set_label"]
    element_id: str
    label: str


class SetType(_Cmd):
    op: Literal["set_type"]
    element_id: str
    type: str


class SetAreaM2(_Cmd):
    op: Literal["set_area_m2"]
    element_id: str
    area_m2: float


class AddAdjacency(_Cmd):
    op: Literal["add_adjacency"]
    from_: str = Field(alias="from")     # room label
    to: str


class RemoveAdjacency(_Cmd):
    op: Literal["remove_adjacency"]
    from_: str = Field(alias="from")
    to: str


# --- Geometry edits ---------------------------------------------------------
class DeleteElement(_Cmd):
    op: Literal["delete_element"]
    element_id: str


class MergeRooms(_Cmd):
    op: Literal["merge_rooms"]
    element_ids: list[str]               # >= 2; merged into the first id


class SplitRoom(_Cmd):
    op: Literal["split_room"]
    element_id: str
    segment: Segment                     # cut line crossing the room polygon


class AddWall(_Cmd):
    op: Literal["add_wall"]
    segment: Segment
    thickness: float = 6.0               # px; buffered to a thin polygon


class MoveElement(_Cmd):
    op: Literal["move_element"]
    element_id: str
    dx: float = 0.0                      # translate by (dx, dy) ...
    dy: float = 0.0
    polygon: Optional[list[list[float]]] = None   # ... or replace polygon outright (vertex edit)


class SetScale(_Cmd):
    op: Literal["set_scale"]
    scale_px_per_m: float                # = pixel_length / meters from calibration


# --- Annotations (pins) -----------------------------------------------------
class AddAnnotation(_Cmd):
    op: Literal["add_annotation"]
    x: float
    y: float
    name: str
    note: Optional[str] = None


class UpdateAnnotation(_Cmd):
    op: Literal["update_annotation"]
    id: str
    name: Optional[str] = None
    note: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None


class DeleteAnnotation(_Cmd):
    op: Literal["delete_annotation"]
    id: str


EditCommand = Annotated[
    Union[
        SetLabel,
        SetType,
        SetAreaM2,
        AddAdjacency,
        RemoveAdjacency,
        DeleteElement,
        MergeRooms,
        SplitRoom,
        AddWall,
        MoveElement,
        SetScale,
        AddAnnotation,
        UpdateAnnotation,
        DeleteAnnotation,
    ],
    Field(discriminator="op"),
]


class EditCommandEnvelope(BaseModel):
    """Wrapper so a route body can validate a single command via Pydantic discriminator."""
    command: EditCommand
