"""Merge geometry elements + Qwen semantics into one Floor Document (pure, deterministic)."""
from statistics import median

from core.document import Element, Floor, new_id
from helpers.geom import poly_area_px


def merge_document(base: Floor, width: int, height: int, geom_elements: list[dict],
                   semantics: dict) -> Floor:
    elements = [
        Element(id=new_id("el"), kind=ge["kind"], polygon=ge["polygon"], score=ge.get("score"))
        for ge in geom_elements
    ]

    # Assign semantic rooms onto geometry 'room' elements by order (heuristic for now).
    sem_rooms = semantics.get("rooms") or []
    room_els = [e for e in elements if e.kind == "room"]
    px_per_m: list[float] = []
    for el, room in zip(room_els, sem_rooms):
        el.label = room.get("label")
        el.type = room.get("type_en") or room.get("type")
        area_m2 = room.get("area_m2")
        if area_m2:
            el.area_m2 = area_m2
            px_per_m.append((poly_area_px(el.polygon) / area_m2) ** 0.5)

    return Floor(
        id=base.id,
        name=base.name,
        description=base.description,
        filename=base.filename,
        width=width,
        height=height,
        scale_px_per_m=round(median(px_per_m), 3) if px_per_m else None,
        status="done",
        elements=elements,
        adjacency=semantics.get("adjacency") or [],
        building_type=semantics.get("building_type"),
        floor_count=semantics.get("floor_count"),
        notes=semantics.get("notes"),
    )
