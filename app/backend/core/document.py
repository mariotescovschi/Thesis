"""FloorPlan Document: the single editable source of truth (geometry + semantics)."""
import uuid
from typing import Optional

from pydantic import BaseModel


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class Element(BaseModel):
    id: str
    kind: str                       # room | wall | door | window | railing
    polygon: list[list[int]]        # [[x, y], ...] in image pixels
    score: Optional[float] = None
    label: Optional[str] = None     # semantic (Qwen): e.g. "MH", "OH"
    type: Optional[str] = None      # english type: bedroom, kitchen, ...
    area_m2: Optional[float] = None


class Annotation(BaseModel):         # named pin / "checkpoint" dropped on the plan (Q4)
    id: str
    x: float                         # image pixels
    y: float
    name: str
    note: Optional[str] = None


class Floor(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    filename: str = ""              # on-disk name in input/ (the store locates files by this)
    width: int = 0
    height: int = 0
    scale_px_per_m: Optional[float] = None
    status: str = "pending"         # pending | running | done | error
    elements: list[Element] = []
    adjacency: list[dict] = []      # [{"from": label, "to": label}]
    annotations: list[Annotation] = []   # per-floor named pins, live in the editable overlay
    # Output-only semantic context (filled by merge in E4).
    building_type: Optional[str] = None
    floor_count: Optional[int] = None
    notes: Optional[str] = None


class Link(BaseModel):               # relationship between floors (multi-floor)
    type: str                        # e.g. vertical_circulation
    from_floor: str
    to_floor: str
    via: Optional[str] = None        # stairs | ...


class Project(BaseModel):
    id: str
    name: str = "Untitled"
    type: str = "analysis"
    created: str = ""                # ISO 8601
    floors: list[Floor] = []
    links: list[Link] = []
    chat: list[dict] = []            # [{"role": "...", "text": "..."}]


class ProjectSummary(BaseModel):     # lightweight list item (GET /projects)
    id: str
    name: str
    type: str
    created: str
    floor_count: int
