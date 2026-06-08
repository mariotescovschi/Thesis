"""Routes: multi-floor split. Wired via include_router by the app entrypoint."""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

import services.splitting as splitting
from core.document import Project

router = APIRouter()


class SplitRequest(BaseModel):
    # Manual-assist fallback: caller-supplied [x, y, w, h] rectangles. When
    # absent, the service auto-detects floor regions heuristically.
    manual_rects: Optional[list[list[int]]] = None


@router.post("/projects/{pid}/floors/{floor_id}/split")
def split_floor(pid: str, floor_id: str, body: SplitRequest) -> dict[str, Project]:
    proj = splitting.split_floor(pid, floor_id, body.manual_rects)
    return {"data": proj}
