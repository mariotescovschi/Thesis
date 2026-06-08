"""Local project-folder store. The folder + project.json IS the database (rules §9).

Only this module touches the filesystem. Swap it later for a server-backed store.
"""
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from core.document import Project, ProjectSummary, Floor, new_id
from core.errors import NotFoundError, ValidationError


def projects_root() -> Path:
    root = Path(os.environ.get("FPS_ROOT", Path.home() / "MappaProjects")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "project"


def project_dir(pid: str) -> Path:
    d = projects_root() / pid
    if not d.is_dir():
        raise NotFoundError(f"Project '{pid}' not found")
    return d


def input_dir(pid: str) -> Path:
    d = project_dir(pid) / "input"
    d.mkdir(exist_ok=True)
    return d


def output_dir(pid: str) -> Path:
    d = project_dir(pid) / "output"
    d.mkdir(exist_ok=True)
    return d


def save_manifest(proj: Project) -> None:
    (project_dir(proj.id) / "project.json").write_text(proj.model_dump_json(indent=2))


def create_project(name: str, type: str = "analysis", location: str | None = None) -> Project:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Project name is required")
    # `location` is accepted for forward-compat; M0 always places under PROJECTS_ROOT
    # so list/load stay index-free. A real save-location lands with the desktop shell.
    root = projects_root()
    slug = pid = _slug(name)
    i = 2
    while (root / pid).exists():
        pid = f"{slug}-{i}"
        i += 1
    (root / pid / "input").mkdir(parents=True)
    proj = Project(
        id=pid, name=name, type=type, created=datetime.now(timezone.utc).isoformat()
    )
    (root / pid / "project.json").write_text(proj.model_dump_json(indent=2))
    return proj


def load_project(pid: str) -> Project:
    path = project_dir(pid) / "project.json"
    if not path.is_file():
        raise NotFoundError(f"Project '{pid}' not found")
    return Project.model_validate_json(path.read_text())


def list_projects() -> list[ProjectSummary]:
    out: list[ProjectSummary] = []
    for d in projects_root().iterdir():
        manifest = d / "project.json"
        if manifest.is_file():
            p = Project.model_validate_json(manifest.read_text())
            out.append(
                ProjectSummary(
                    id=p.id, name=p.name, type=p.type, created=p.created, floor_count=len(p.floors)
                )
            )
    out.sort(key=lambda s: s.created, reverse=True)
    return out


def get_floor(proj: Project, floor_id: str) -> Floor:
    for f in proj.floors:
        if f.id == floor_id:
            return f
    raise NotFoundError(f"Floor '{floor_id}' not found")


def append_chat(pid: str, role: str, text: str) -> Project:
    """Append one chat turn to the manifest history and persist. Returns the project."""
    proj = load_project(pid)
    proj.chat.append({"role": role, "text": text})
    save_manifest(proj)
    return proj


def add_floors(pid: str, items: list[dict]) -> Project:
    """items: [{ 'bytes': b'...', 'orig': 'plan.png', 'name': str, 'description': str|None }]."""
    proj = load_project(pid)
    in_dir = input_dir(pid)
    for it in items:
        fid = new_id("floor")
        ext = Path(it.get("orig", "")).suffix.lower() or ".png"
        disk = f"{fid}{ext}"
        (in_dir / disk).write_bytes(it["bytes"])
        proj.floors.append(
            Floor(
                id=fid,
                name=it["name"],
                description=it.get("description"),
                filename=disk,
                status="pending",
            )
        )
    save_manifest(proj)
    return proj


def add_floor_from_bytes(
    pid: str, data: bytes, orig: str, name: str, description: str | None = None
) -> Project:
    """Write a single (e.g. cropped) input file + append a pending Floor.

    Thin wrapper over `add_floors` so multi-floor splitting reuses one I/O path.
    """
    return add_floors(pid, [{"bytes": data, "orig": orig, "name": name, "description": description}])


def input_path(pid: str, floor_id: str) -> Path:
    floor = get_floor(load_project(pid), floor_id)
    p = input_dir(pid) / floor.filename
    if not floor.filename or not p.is_file():
        raise NotFoundError("Floor image not found")
    return p


def write_output(pid: str, floor_id: str, document: Floor) -> None:
    (output_dir(pid) / f"{floor_id}.json").write_text(document.model_dump_json(indent=2))


def overlay_path(pid: str, floor_id: str) -> Path:
    """Editable overlay: all user + chat edits land here (base + overlay model, Q1=C)."""
    return output_dir(pid) / f"{floor_id}.edited.json"


def has_overlay(pid: str, floor_id: str) -> bool:
    return overlay_path(pid, floor_id).is_file()


def write_overlay(pid: str, floor_id: str, document: Floor) -> None:
    overlay_path(pid, floor_id).write_text(document.model_dump_json(indent=2))


def delete_overlay(pid: str, floor_id: str) -> bool:
    """Revert to the pipeline original. Returns True if an overlay was removed."""
    p = overlay_path(pid, floor_id)
    if p.is_file():
        p.unlink()
        return True
    return False


def read_base_output(pid: str, floor_id: str) -> Floor:
    """The immutable pipeline output, ignoring any overlay."""
    p = output_dir(pid) / f"{floor_id}.json"
    if not p.is_file():
        raise NotFoundError("Output not available. Analyze this floor first")
    return Floor.model_validate_json(p.read_text())


def read_output(pid: str, floor_id: str) -> Floor:
    """Prefer the editable overlay; fall back to the pipeline base."""
    ov = overlay_path(pid, floor_id)
    if ov.is_file():
        return Floor.model_validate_json(ov.read_text())
    return read_base_output(pid, floor_id)
