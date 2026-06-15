"""Tests for the derived index store (temp FPS_ROOT, no real projects needed)."""
import importlib

import pytest


@pytest.fixture
def idx(tmp_path, monkeypatch):
    monkeypatch.setenv("FPS_ROOT", str(tmp_path))
    import infra.index_store as index_store
    importlib.reload(index_store)
    return index_store


def _rec(pid: str, fid: str, price=None) -> dict:
    return {"project_id": pid, "floor_id": fid, "price": price,
            "features": {"room_count": 2.0}, "embedding": None}


def test_upsert_then_all_records(idx):
    idx.upsert_floor(_rec("p1", "f1"))
    idx.upsert_floor(_rec("p1", "f2", price=100.0))
    recs = idx.all_records()
    assert len(recs) == 2


def test_upsert_replaces_same_key(idx):
    idx.upsert_floor(_rec("p1", "f1", price=50.0))
    idx.upsert_floor(_rec("p1", "f1", price=80.0))
    recs = idx.all_records()
    assert len(recs) == 1
    assert recs[0]["price"] == 80.0


def test_remove_project(idx):
    idx.upsert_floor(_rec("p1", "f1"))
    idx.upsert_floor(_rec("p2", "f1"))
    idx.remove_project("p1")
    recs = idx.all_records()
    assert {r["project_id"] for r in recs} == {"p2"}
