"""Chat route: ask a question / request edits about a floor.

The route validates the request, loads the project + floor via the store, and
delegates to the chat service (chat.answer). The service proposes — but never
applies — edit commands. Both the user message and the assistant answer are
appended to the manifest chat history (store.append_chat) so the conversation
persists across reloads.
"""
from fastapi import APIRouter
from pydantic import BaseModel

import services.chat as chat
import infra.store as store
from core.errors import NotFoundError

router = APIRouter()


class ChatRequest(BaseModel):
    floor_id: str
    message: str
    pin_ids: list[str] = []
    element_ids: list[str] = []
    history: list[dict] = []


@router.post("/projects/{pid}/chat")
def post_chat(pid: str, body: ChatRequest) -> dict:
    """Answer a chat message about a floor and return proposed (unapplied) edits."""
    project = store.load_project(pid)                 # 404 if project missing
    store.get_floor(project, body.floor_id)           # 404 if floor missing

    # Manifest floors are LIGHT (no polygons/rooms/pins) — the full editable
    # Document lives in output/ (overlay-aware). Hydrate the target floor and the
    # other done floors so the scene the LLM reasons over matches the canvas.
    floor = store.read_output(pid, body.floor_id)     # 404 if not analyzed yet
    for i, f in enumerate(project.floors):
        if f.status == "done":
            try:
                project.floors[i] = store.read_output(pid, f.id)
            except NotFoundError:
                pass

    result = chat.answer(project, floor, body.message, body.pin_ids, body.history, body.element_ids)

    store.append_chat(pid, "user", body.message)
    store.append_chat(pid, "assistant", result["answer"])

    return {
        "data": {
            "answer": result["answer"],
            "proposed_commands": result["commands"],
            "rejected_commands": result.get("rejected", []),
        }
    }
