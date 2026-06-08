"""Analysis service (Service layer): sequential per floor: geometry -> semantics -> merge.

Geometry pulls torch/detectron2, so it is imported lazily here (keeps `import main` light).
Manifest is saved after each floor so the UI can observe progress.
"""
import infra.store as store
from core.document import Floor, Link, Project

# Room types/labels that indicate vertical circulation between floors.
_VERT_CIRCULATION = ("stair", "elevator", "lift", "escalator")


def _has_vertical_circulation(floor: Floor, semantics: dict | None = None) -> bool:
    """True if a floor has vertical circulation (Qwen field or a stair/lift room)."""
    if semantics and semantics.get("vertical_circulation"):
        return True
    for el in floor.elements:
        text = f"{el.type or ''} {el.label or ''}".lower()
        if any(k in text for k in _VERT_CIRCULATION):
            return True
    return False


def infer_links(floors: list[Floor]) -> list[Link]:
    """Infer vertical_circulation links between adjacent floors in stacking order.

    Two consecutive floors (as listed) that BOTH contain vertical circulation are
    assumed to connect via that circulation. Deterministic; safe for 0/1 floors.
    """
    links: list[Link] = []
    for lower, upper in zip(floors, floors[1:]):
        if _has_vertical_circulation(lower) and _has_vertical_circulation(upper):
            links.append(Link(
                type="vertical_circulation",
                from_floor=lower.id,
                to_floor=upper.id,
                via="stairs",
            ))
    return links


def analyze_project(pid: str) -> Project:
    proj = store.load_project(pid)
    pending = [f for f in proj.floors if f.status in ("pending", "error")]
    if not pending:
        return proj

    import infra.geometry as geometry  # heavy (torch/detectron2); load only when actually analyzing
    import services.semantics as semantics
    from services.merge import merge_document
    from helpers.autoscale import estimate_scale
    from helpers.adjacency import derive_adjacency

    analyzed: dict[str, Floor] = {}
    for floor in pending:
        print(f"[analyze] {floor.name} ({floor.id}): geometry...")
        floor.status = "running"
        store.save_manifest(proj)
        try:
            path = store.input_path(pid, floor.id)
            width, height, elements = geometry.analyze_image(path)
            print(f"[analyze] {floor.name}: semantics...")
            doc = merge_document(floor, width, height, elements, semantics.analyze_semantics(path))
            # Auto-estimate scale from door widths if not already set
            if not doc.scale_px_per_m:
                estimated = estimate_scale(doc)
                if estimated:
                    doc.scale_px_per_m = estimated
                    # Recompute room areas with new scale
                    from services.editing import _area_m2
                    for el in doc.elements:
                        if el.kind == "room":
                            el.area_m2 = _area_m2(el.polygon, doc.scale_px_per_m)
            # Auto-derive adjacency from geometry if empty
            if not doc.adjacency:
                doc.adjacency = derive_adjacency(doc)
            store.write_output(pid, floor.id, doc)
            analyzed[floor.id] = doc
            # Keep the manifest entry light (no polygons); the Document lives in output/.
            floor.width = doc.width
            floor.height = doc.height
            floor.scale_px_per_m = doc.scale_px_per_m
            floor.building_type = doc.building_type
            floor.floor_count = doc.floor_count
            floor.notes = doc.notes
            floor.status = "done"
            print(f"[analyze] {floor.name}: done")
        except Exception as exc:  # noqa: BLE001 surface failure per-floor, keep going
            floor.status = "error"
            floor.notes = str(exc)
            print(f"[analyze] {floor.name}: ERROR - {exc}")
        store.save_manifest(proj)

    _refresh_links(proj, analyzed)
    return proj


def _refresh_links(proj: Project, analyzed: dict[str, Floor]) -> None:
    """Recompute cross-floor links from full floor documents (best-effort)."""
    ordered: list[Floor] = []
    for f in proj.floors:
        doc = analyzed.get(f.id)
        if doc is None and f.status == "done":
            try:
                doc = store.read_output(proj.id, f.id)
            except Exception:  # noqa: BLE001 missing/unreadable output -> use light floor
                doc = None
        ordered.append(doc or f)
    proj.links = infer_links(ordered)
    store.save_manifest(proj)
