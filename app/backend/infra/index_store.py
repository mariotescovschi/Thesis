"""Derived cross-project index (`_index.json` under MappaProjects/).

A CACHE only: every record is reconstructible from the project.json manifests via
rebuild(), so the index is never a second source of truth (no sync, no migrations).
Lives beside store.py as the second I/O module — but strictly for this derived cache.
"""
import json
from pathlib import Path
from typing import Callable, Optional

import infra.store as store
from core.document import Floor, Project
from core.errors import NotFoundError
from helpers.features import describe_floor, floor_features

_INDEX_NAME = "_index.json"
Embed = Callable[[str], list[float]]


def _index_path() -> Path:
    return store.projects_root() / _INDEX_NAME


def _load() -> dict:
    p = _index_path()
    if not p.is_file():
        return {"records": []}
    try:
        data = json.loads(p.read_text())
    except (ValueError, OSError):
        return {"records": []}
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        return {"records": []}
    return data


def _save(data: dict) -> None:
    _index_path().write_text(json.dumps(data, indent=2))


def _key(record: dict) -> tuple:
    return (record.get("project_id"), record.get("floor_id"))


def build_record(proj: Project, floor: Floor, embed: Optional[Embed] = None) -> dict:
    """Build one index record from a project + a hydrated (output) floor.

    `embed` (optional) turns the floor description into a semantic vector; omitted
    during a filter-only rebuild or when embeddings are unavailable.
    """
    desc = describe_floor(floor)
    return {
        "project_id": proj.id,
        "floor_id": floor.id,
        "project_name": proj.name,
        "floor_name": floor.name,
        "price": floor.price,
        "currency": proj.currency,
        "features": floor_features(floor),
        "description": desc,
        "embedding": embed(desc) if embed else None,
    }


def upsert_floor(record: dict) -> None:
    """Insert or replace the record for (project_id, floor_id)."""
    data = _load()
    k = _key(record)
    data["records"] = [r for r in data["records"] if _key(r) != k]
    data["records"].append(record)
    _save(data)


def all_records() -> list[dict]:
    """All index records (cache); lazily rebuilds from manifests if missing."""
    if not _index_path().is_file():
        rebuild()
    return _load()["records"]


def remove_project(project_id: str) -> None:
    """Drop all records for a project (e.g. on delete)."""
    data = _load()
    data["records"] = [r for r in data["records"] if r.get("project_id") != project_id]
    _save(data)


def rebuild(embed: Optional[Embed] = None) -> int:
    """Rebuild the whole index from project manifests. Returns the record count.

    Only analyzed ('done') floors with a readable output Document are indexed.
    Without `embed`, records carry no vector (filter-only search still works).
    """
    records: list[dict] = []
    for summary in store.list_projects():
        proj = store.load_project(summary.id)
        for f in proj.floors:
            if f.status != "done":
                continue
            try:
                floor = store.read_output(proj.id, f.id)
            except NotFoundError:
                continue
            floor.price = f.price   # price lives in the manifest, not the output doc
            records.append(build_record(proj, floor, embed))
    _save({"records": records})
    return len(records)
