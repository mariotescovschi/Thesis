"""Manual JSON tool-loop for the chat service (kept separate to bound chat.py).

At each step the model replies with EITHER a tool call {"tool","args"} — which we
execute (read-only) and feed back — OR the final {"answer","commands"}. Capped at
3 tool calls, after which we force a tool-free final answer; one repair retry if
the final reply is not a JSON object. Pure orchestration: never applies edits.
"""
import json

import infra.ollama_client as ollama_client
import helpers.chat_tools as chat_tools
from core.document import Floor

_MAX_TOOL_ITERS = 3

# Appended to the chat system prompt so the model knows the loop protocol + tools.
TOOL_PROTOCOL = (
    "Before answering you MAY inspect the plan with read-only tools. To call a "
    'tool, reply with STRICT JSON {"tool": "<name>", "args": {...}} and nothing '
    "else; you will receive a TOOL RESULT and may call again (max 3 times). When "
    'ready, reply with the final {"answer", "commands"} JSON.\n'
    + chat_tools.TOOL_SPECS
)


def _tool_call(content: str):
    """If the reply is a tool call {"tool","args"}, return (name, args) else None."""
    try:
        data = json.loads(content)
    except (ValueError, TypeError):
        return None
    if isinstance(data, dict) and isinstance(data.get("tool"), str):
        args = data.get("args")
        return data["tool"], args if isinstance(args, dict) else {}
    return None


def _parses_to_obj(content: str) -> bool:
    try:
        return isinstance(json.loads(content), dict)
    except (ValueError, TypeError):
        return False


def _maybe_repair(messages: list[dict], content: str) -> str:
    """One repair retry if the final reply is not a JSON object."""
    if _parses_to_obj(content):
        return content
    messages.append({"role": "assistant", "content": content})
    messages.append({
        "role": "user",
        "content": 'Your reply was not valid JSON. Reply ONLY with '
                   '{"answer":"...","commands":[...]}.',
    })
    return ollama_client.chat(messages, json_format=True)


def run_loop(messages: list[dict], floor: Floor) -> str:
    """Drive the tool-loop and return the final raw JSON content string."""
    for _ in range(_MAX_TOOL_ITERS):
        content = ollama_client.chat(messages, json_format=True)
        call = _tool_call(content)
        if call is None:
            return _maybe_repair(messages, content)
        name, args = call
        result = chat_tools.run_tool(floor, name, args)
        messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": f"TOOL RESULT {name}: {json.dumps(result)}"})
    # Cap reached — force a final, tool-free answer.
    messages.append({
        "role": "user",
        "content": 'Now give your FINAL answer as JSON {"answer","commands"}; '
                   "do not call another tool.",
    })
    return _maybe_repair(messages, ollama_client.chat(messages, json_format=True))
