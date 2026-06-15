"""Route tests for pricing: set price (project/floor) + floor estimate."""
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("FPS_ROOT", tempfile.mkdtemp(prefix="mappa_price_"))
    import main
    import infra.embeddings as embeddings
    # Keep tests offline + deterministic: force the no-embedding index path.
    monkeypatch.setattr(embeddings, "embed", lambda text: (_ for _ in ()).throw(RuntimeError("offline")))
    return TestClient(main.app)


def _project_with_floor(price=None):
    import infra.store as store
    from core.document import Element, Floor

    proj = store.create_project("House")
    floor = Floor(
        id="fl1", name="L0", width=300, height=300, status="done", price=price,
        building_type="apartment",
        elements=[Element(id="r1", kind="room", type="living", area_m2=30.0,
                          polygon=[[0, 0], [200, 0], [200, 200], [0, 200]])],
    )
    proj.floors.append(floor)
    store.save_manifest(proj)
    store.write_output(proj.id, floor.id, floor)
    return proj.id, floor.id


def _seed_priced(n=6):
    import infra.index_store as index_store
    for i in range(n):
        area = 40 + i * 10
        index_store.upsert_floor({
            "project_id": f"seed{i}", "floor_id": "f1",
            "project_name": f"seed{i}", "floor_name": "L0",
            "price": 1000.0 * area, "currency": "EUR",
            "features": {"total_area_m2": area, "room_count": 2}, "embedding": None,
        })


def test_patch_floor_price_persists(client):
    pid, fid = _project_with_floor()
    r = client.patch(f"/projects/{pid}/floors/{fid}/price", json={"price": 90000})
    assert r.status_code == 200
    floor = next(f for f in r.json()["data"]["floors"] if f["id"] == fid)
    assert floor["price"] == 90000


def test_patch_project_price_and_currency(client):
    pid, _ = _project_with_floor()
    r = client.patch(f"/projects/{pid}/price", json={"price": 250000, "currency": "USD"})
    assert r.status_code == 200
    assert r.json()["data"]["currency"] == "USD"


def test_negative_price_is_400(client):
    pid, fid = _project_with_floor()
    r = client.patch(f"/projects/{pid}/floors/{fid}/price", json={"price": -5})
    assert r.status_code == 400


def test_estimate_available_with_priced_comparables(client):
    pid, fid = _project_with_floor()
    _seed_priced()
    r = client.get(f"/projects/{pid}/floors/{fid}/price/estimate")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["available"] is True
    assert data["estimate"] > 0


def test_estimate_missing_floor_is_404(client):
    pid, _ = _project_with_floor()
    r = client.get(f"/projects/{pid}/floors/nope/price/estimate")
    assert r.status_code == 404
