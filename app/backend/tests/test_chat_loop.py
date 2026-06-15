"""Tool-loop + rejected-commands tests for the chat service (Ollama mocked)."""
import json

import infra.ollama_client as ollama_client
import services.chat as chat
from core.document import Element, Floor, Project


def _floor() -> Floor:
    return Floor(
        id="fl", name="L0", width=1000, height=1000,
        elements=[Element(id="room_k", kind="room", type="kitchen", label="Kitchen",
                          polygon=[[0, 0], [200, 0], [200, 200], [0, 200]])],
    )


def _project(floor: Floor) -> Project:
    return Project(id="p1", name="P", floors=[floor])


def _script(monkeypatch, responses: list[str]):
    """Make ollama_client.chat return the given responses in order."""
    seq = list(responses)
    monkeypatch.setattr(ollama_client, "chat", lambda *a, **k: seq.pop(0))
    return seq


def test_loop_runs_tool_then_finalizes(monkeypatch):
    floor = _floor()
    seq = _script(monkeypatch, [
        json.dumps({"tool": "list_elements", "args": {}}),
        json.dumps({"answer": "There is 1 room.", "commands": []}),
    ])
    res = chat.answer(_project(floor), floor, "how many rooms?")
    assert res["answer"] == "There is 1 room."
    assert seq == []  # tool call + final both consumed


def test_invalid_command_is_rejected_with_reason(monkeypatch):
    floor = _floor()
    _script(monkeypatch, [json.dumps({"answer": "ok", "commands": [{"op": "set_label"}]})])
    res = chat.answer(_project(floor), floor, "rename it")
    assert res["commands"] == []
    assert len(res["rejected"]) == 1
    assert res["rejected"][0]["reason"]


def test_loop_caps_at_three_tools(monkeypatch):
    floor = _floor()
    tool = json.dumps({"tool": "get_scene", "args": {}})
    seq = _script(monkeypatch, [tool, tool, tool, json.dumps({"answer": "done", "commands": []})])
    res = chat.answer(_project(floor), floor, "x")
    assert res["answer"] == "done"
    assert seq == []  # exactly 3 tool calls + 1 forced final


def test_repair_retry_on_bad_json(monkeypatch):
    floor = _floor()
    seq = _script(monkeypatch, ["not json at all", json.dumps({"answer": "fixed", "commands": []})])
    res = chat.answer(_project(floor), floor, "x")
    assert res["answer"] == "fixed"
    assert seq == []
