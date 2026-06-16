"""Pricing: estimate a floor's price from the derived index and explain it.

Pure compute over plain dicts (no I/O, no LLM): ridge regression gives the estimate
plus each feature's signed % contribution, kNN (cosine) surfaces comparable plans,
and the verdict compares the asking price to the estimate (over/under/fair at ±10%).
The route loads the index records and passes them in.
"""
from typing import Optional

import numpy as np

from helpers.features import feature_keys, to_vector

_RIDGE_LAMBDA = 1.0
_K = 5                 # comparables to surface
_VERDICT_MIN = 4       # need at least this many other priced plans for a verdict
_BAND = 0.10           # ±10% -> "fair"
_TOP_CONTRIB = 6


def _key(rec: dict) -> tuple:
    return (rec.get("project_id"), rec.get("floor_id"))


def _matrix(records: list[dict], keys: list[str]) -> np.ndarray:
    return np.array([to_vector(r.get("features", {}), keys) for r in records], dtype=float)


def _standardize(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=0)
    std = x.std(axis=0)
    std[std == 0] = 1.0
    return (x - mean) / std, mean, std


def _ridge_fit(xs: np.ndarray, y: np.ndarray) -> tuple[float, np.ndarray]:
    """Closed-form ridge with an unregularized intercept. Returns (intercept, coef)."""
    n = xs.shape[0]
    xi = np.hstack([np.ones((n, 1)), xs])
    reg = np.eye(xi.shape[1]) * _RIDGE_LAMBDA
    reg[0, 0] = 0.0
    w = np.linalg.solve(xi.T @ xi + reg, xi.T @ y)
    return float(w[0]), w[1:]


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


def _contributions(coef: np.ndarray, xt: np.ndarray, keys: list[str]) -> list[dict]:
    """Signed % contribution of each feature to the prediction (top |contrib|)."""
    contrib = coef * xt
    total = float(np.abs(contrib).sum()) or 1.0
    items = [
        {"feature": k, "pct": round(float(c) / total * 100.0, 1)}
        for k, c in zip(keys, contrib)
    ]
    items.sort(key=lambda d: abs(d["pct"]), reverse=True)
    return items[:_TOP_CONTRIB]


def _comparables(xs: np.ndarray, xt: np.ndarray, priced: list[dict]) -> list[dict]:
    sims = [(_cosine(xs[i], xt), i) for i in range(len(priced))]
    sims.sort(reverse=True)
    out = []
    for sim, i in sims[:_K]:
        r = priced[i]
        out.append({
            "project_id": r.get("project_id"),
            "floor_id": r.get("floor_id"),
            "project_name": r.get("project_name"),
            "floor_name": r.get("floor_name"),
            "price": r.get("price"),
            "similarity": round(sim, 3),
        })
    return out


def _verdict(price: Optional[float], estimate: float, sample_size: int) -> tuple[str, Optional[float]]:
    """Compare the asking price to the model estimate: over/under/fair at ±10%.

    A signed delta of +X% means the asking price is X% above what the model thinks
    the plan is worth (overpriced); negative means below (underpriced / a good deal).
    """
    if sample_size < _VERDICT_MIN or price is None or estimate <= 0:
        return "insufficient_data", None
    delta = (price - estimate) / estimate
    label = "overpriced" if delta > _BAND else "underpriced" if delta < -_BAND else "fair"
    return label, round(delta * 100.0, 1)


def estimate(target: dict, records: list[dict]) -> dict:
    """Estimate price for `target` (an index record) against all index `records`."""
    keys = feature_keys()
    priced = [r for r in records
              if r.get("price") is not None and _key(r) != _key(target)]
    if not priced:
        return {"available": False, "reason": "no priced plans to learn from yet",
                "currency": target.get("currency", "EUR"), "price": target.get("price")}

    x = _matrix(priced, keys)
    y = np.array([float(r["price"]) for r in priced], dtype=float)
    xs, mean, std = _standardize(x)
    intercept, coef = _ridge_fit(xs, y)

    xt = (np.array(to_vector(target.get("features", {}), keys), dtype=float) - mean) / std
    predicted = max(0.0, intercept + float(coef @ xt))
    comps = _comparables(xs, xt, priced)
    verdict, delta_pct = _verdict(target.get("price"), predicted, len(priced))

    return {
        "available": True,
        "currency": target.get("currency", "EUR"),
        "price": target.get("price"),
        "estimate": round(predicted, 2),
        "verdict": verdict,
        "delta_pct": delta_pct,
        "contributions": _contributions(coef, xt, keys),
        "comparables": comps,
        "sample_size": len(priced),
    }


# --- Orchestration (I/O): set prices in the manifest, keep the index in sync,
# and assemble the estimate for a concrete floor. The pure `estimate` above stays
# the testable core; these glue it to the store + derived index.
import infra.embeddings as _embeddings
import infra.index_store as _index_store
import infra.store as _store
from core.document import Project
from core.errors import NotFoundError


def _reindex_floor(proj: Project, floor_id: str) -> None:
    """Refresh one floor's index record (best-effort; embeddings may be offline)."""
    try:
        doc = _store.read_output(proj.id, floor_id)
    except NotFoundError:
        return
    doc.price = _store.get_floor(proj, floor_id).price
    try:
        rec = _index_store.build_record(proj, doc, embed=_embeddings.embed)
    except Exception:  # noqa: BLE001 embeddings offline -> index without a vector
        rec = _index_store.build_record(proj, doc)
    _index_store.upsert_floor(rec)


def set_project_price(pid: str, price: Optional[float], currency: Optional[str]) -> Project:
    """Set the project's asking price/currency in the manifest; resync the index."""
    proj = _store.load_project(pid)
    if price is not None:
        proj.price = price
    if currency:
        proj.currency = currency
    _store.save_manifest(proj)
    for f in proj.floors:                       # currency lives on the floor records
        if f.status == "done":
            _reindex_floor(proj, f.id)
    return proj


def set_floor_price(pid: str, floor_id: str, price: Optional[float]) -> Project:
    """Set one floor's asking price in the manifest; resync its index record."""
    proj = _store.load_project(pid)
    _store.get_floor(proj, floor_id).price = price   # raises NotFoundError if missing
    _store.save_manifest(proj)
    _reindex_floor(proj, floor_id)
    return proj


def estimate_floor(pid: str, floor_id: str) -> dict:
    """Estimate price for a floor against the whole index (404 if not analyzed)."""
    proj = _store.load_project(pid)
    doc = _store.read_output(pid, floor_id)          # 404 if not analyzed yet
    doc.price = _store.get_floor(proj, floor_id).price
    target = _index_store.build_record(proj, doc)
    return estimate(target, _index_store.all_records())
