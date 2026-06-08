"""Integration tests for the route layer (export + multi-floor split) via TestClient.

FPS_ROOT is redirected to a temp dir so the filesystem store never touches the
real projects folder.
"""
import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="mappa_test_")
    monkeypatch.setenv("FPS_ROOT", tmp)
    import main
    return TestClient(main.app)


def _make_project(with_output: bool = True):
    import store
    from document import Element, Floor

    proj = store.create_project("Test House")
    floor_id = "fl_test"
    if with_output:
        floor = Floor(
            id=floor_id, name="L0", width=500, height=500, scale_px_per_m=100.0,
            elements=[
                Element(id="el_1", kind="room",
                        polygon=[[0, 0], [200, 0], [200, 200], [0, 200]], type="kitchen"),
                Element(id="el_2", kind="wall",
                        polygon=[[0, 0], [10, 0], [10, 200], [0, 200]]),
            ],
        )
        store.write_output(proj.id, floor_id, floor)
    return proj.id, floor_id


def test_export_svg(client):
    pid, fid = _make_project()
    r = client.get(f"/projects/{pid}/export/{fid}", params={"fmt": "svg"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text
    assert f'filename="{fid}.svg"' in r.headers["content-disposition"]


def test_export_json(client):
    pid, fid = _make_project()
    r = client.get(f"/projects/{pid}/export/{fid}", params={"fmt": "json"})
    assert r.status_code == 200
    assert r.json()["elements"][0]["type"] == "kitchen"


def test_export_dxf(client):
    pid, fid = _make_project()
    r = client.get(f"/projects/{pid}/export/{fid}", params={"fmt": "dxf"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/dxf")
    assert len(r.content) > 100


def test_export_bad_format_is_400(client):
    pid, fid = _make_project()
    r = client.get(f"/projects/{pid}/export/{fid}", params={"fmt": "pdf"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


def test_export_no_output_is_404(client):
    pid, fid = _make_project(with_output=False)
    r = client.get(f"/projects/{pid}/export/{fid}", params={"fmt": "json"})
    assert r.status_code == 404


def test_split_multi_floor(client):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    import store

    # synthetic vertical 2-up sheet: two content blocks with an empty band between.
    img = np.full((400, 300), 255, np.uint8)
    img[20:180, 40:260] = 0
    img[260:380, 40:260] = 0
    ok, buf = cv2.imencode(".png", img)
    assert ok

    proj = store.create_project("Two Up")
    proj = store.add_floor_from_bytes(proj.id, buf.tobytes(), "sheet.png", "Sheet")
    src_floor_id = proj.floors[0].id

    r = client.post(f"/projects/{proj.id}/floors/{src_floor_id}/split", json={})
    assert r.status_code == 200
    floors = r.json()["data"]["floors"]
    assert len(floors) >= 3  # original + 2 split parts


def test_split_manual_rects(client):
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    import store

    img = np.full((400, 300), 255, np.uint8)
    ok, buf = cv2.imencode(".png", img)
    proj = store.create_project("Manual Split")
    proj = store.add_floor_from_bytes(proj.id, buf.tobytes(), "sheet.png", "Sheet")
    fid = proj.floors[0].id

    body = {"manual_rects": [[0, 0, 150, 400], [150, 0, 150, 400]]}
    r = client.post(f"/projects/{proj.id}/floors/{fid}/split", json=body)
    assert r.status_code == 200
    assert len(r.json()["data"]["floors"]) == 3


def test_patch_apply_edit_writes_overlay(client):
    import store
    pid, fid = _make_project()
    body = {"command": {"op": "set_type", "element_id": "el_1", "type": "bedroom"}}
    r = client.patch(f"/projects/{pid}/output/{fid}", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["elements"][0]["type"] == "bedroom"
    assert store.has_overlay(pid, fid)
    # base output is untouched
    assert store.read_base_output(pid, fid).elements[0].type == "kitchen"


def test_patch_bad_command_is_400(client):
    pid, fid = _make_project()
    r = client.patch(f"/projects/{pid}/output/{fid}", json={"command": {"op": "nonsense"}})
    assert r.status_code == 400


def test_delete_reverts_to_base(client):
    import store
    pid, fid = _make_project()
    client.patch(f"/projects/{pid}/output/{fid}",
                 json={"command": {"op": "set_type", "element_id": "el_1", "type": "bedroom"}})
    r = client.delete(f"/projects/{pid}/output/{fid}/edits")
    assert r.status_code == 200
    assert r.json()["data"]["elements"][0]["type"] == "kitchen"
    assert not store.has_overlay(pid, fid)


def test_split_room_via_patch_persists(client):
    pid, fid = _make_project()
    body = {"command": {"op": "split_room", "element_id": "el_1",
                        "segment": [[100, 0], [100, 200]]}}
    r = client.patch(f"/projects/{pid}/output/{fid}", json=body)
    assert r.status_code == 200
    rooms = [e for e in r.json()["data"]["elements"] if e["kind"] == "room"]
    assert len(rooms) == 2
