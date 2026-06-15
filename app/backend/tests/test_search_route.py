"""Route test for /search with the LLM + embeddings mocked (offline, deterministic)."""
import json
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("FPS_ROOT", tempfile.mkdtemp(prefix="mappa_search_"))
    import main
    return TestClient(main.app)


def _seed():
    import infra.index_store as index_store
    for pid, area, price, beds in [("a", 40, 80_000, 1), ("b", 75, 160_000, 2), ("c", 120, 320_000, 3)]:
        index_store.upsert_floor({
            "project_id": pid, "floor_id": "f1", "project_name": pid, "floor_name": "L0",
            "price": price, "currency": "EUR", "description": f"{beds}-bed", "embedding": None,
            "features": {"total_area_m2": area, "room_count": beds + 2,
                         "count_bedroom": float(beds), "building_apartment": 1.0},
        })


def test_search_applies_llm_filters(client, monkeypatch):
    import infra.ollama_client as ollama_client
    import infra.embeddings as embeddings
    _seed()
    monkeypatch.setattr(ollama_client, "chat", lambda *a, **k: json.dumps({"price_max": 200000}))
    monkeypatch.setattr(embeddings, "embed", lambda t: (_ for _ in ()).throw(RuntimeError("offline")))

    r = client.post("/search", json={"query": "apartments under 200k"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["filters"]["price_max"] == 200000
    assert data["semantic"] is False
    assert {x["project_id"] for x in data["results"]} == {"a", "b"}


def test_search_degrades_when_llm_offline(client, monkeypatch):
    import infra.ollama_client as ollama_client
    import infra.embeddings as embeddings
    _seed()

    def _boom(*a, **k):
        raise RuntimeError("offline")

    monkeypatch.setattr(ollama_client, "chat", _boom)
    monkeypatch.setattr(embeddings, "embed", _boom)

    r = client.post("/search", json={"query": "anything"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["filters"] == {}
    assert len(data["results"]) == 3  # no filters -> all plans
