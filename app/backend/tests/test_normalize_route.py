"""Route tests for the normalize endpoint (proposes commands, never persists)."""
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("FPS_ROOT", tempfile.mkdtemp(prefix="mappa_test_"))
    import main
    return TestClient(main.app)


def _project_with_output():
    import infra.store as store
    from core.document import Element, Floor

    proj = store.create_project("Norm House")
    fid = "fl_test"
    floor = Floor(
        id=fid, name="L0", width=300, height=300,
        elements=[Element(id="r1", kind="room",
                          polygon=[[0, 0], [200, 3], [200, 200], [0, 200]])],
    )
    store.write_output(proj.id, fid, floor)
    return proj.id, fid


def test_normalize_returns_commands_without_persisting(client):
    import infra.store as store
    pid, fid = _project_with_output()
    r = client.post(f"/projects/{pid}/output/{fid}/normalize", json={"level": 1})
    assert r.status_code == 200
    commands = r.json()["data"]["commands"]
    assert any(c["op"] == "move_element" for c in commands)
    assert not store.has_overlay(pid, fid)  # preview only — base/overlay untouched


def test_normalize_bad_level_is_400(client):
    pid, fid = _project_with_output()
    r = client.post(f"/projects/{pid}/output/{fid}/normalize", json={"level": 9})
    assert r.status_code == 400


def test_normalize_missing_floor_is_404(client):
    import infra.store as store
    proj = store.create_project("Empty")
    r = client.post(f"/projects/{proj.id}/output/nope/normalize", json={"level": 1})
    assert r.status_code == 404
