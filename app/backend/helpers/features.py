"""Pure feature extraction: a Floor Document -> a deterministic numeric feature
vector + a short text description (for embeddings). No I/O, no LLM, no mutation —
same input always yields the same output. Used by the index, pricing and search.
"""
from typing import Optional

from core.document import Floor
from helpers.geom import bbox, poly_area_px

# Fixed taxonomies keep the vector layout stable across floors/projects so the
# index, ridge and kNN all speak the same column order.
ROOM_TYPES = (
    "bedroom", "kitchen", "bathroom", "living", "hall",
    "balcony", "storage", "office",
)
BUILDING_TYPES = ("apartment", "house", "office", "commercial")


def _room_area(el) -> float:
    """Room area in m² when known, else polygon area in px (consistent per floor)."""
    if el.area_m2 is not None:
        return float(el.area_m2)
    return poly_area_px(el.polygon)


def _compactness(rooms: list) -> float:
    """Total room area / bounding-box area of all rooms (0..1). 0 when undefinable."""
    if not rooms:
        return 0.0
    xs0, ys0, xs1, ys1 = [], [], [], []
    for el in rooms:
        x0, y0, x1, y1 = bbox(el.polygon)
        xs0.append(x0); ys0.append(y0); xs1.append(x1); ys1.append(y1)
    bb = (max(xs1) - min(xs0)) * (max(ys1) - min(ys0))
    if bb <= 0:
        return 0.0
    total_px = sum(poly_area_px(el.polygon) for el in rooms)
    return round(min(total_px / bb, 1.0), 4)


def floor_features(floor: Floor) -> dict[str, float]:
    """Deterministic numeric features describing a floor's layout."""
    rooms = [e for e in floor.elements if e.kind == "room"]
    doors = sum(1 for e in floor.elements if e.kind == "door")
    windows = sum(1 for e in floor.elements if e.kind == "window")
    walls = sum(1 for e in floor.elements if e.kind == "wall")
    total_area = sum(float(e.area_m2) for e in rooms if e.area_m2 is not None)

    feats: dict[str, float] = {
        "room_count": float(len(rooms)),
        "total_area_m2": round(total_area, 2),
        "door_count": float(doors),
        "window_count": float(windows),
        "wall_count": float(walls),
        "adjacency_density": round(len(floor.adjacency) / len(rooms), 4) if rooms else 0.0,
        "compactness": _compactness(rooms),
        "floor_count": float(floor.floor_count or 1),
    }

    # Area share per room type (fractions of total room area; sums to ≤ 1).
    areas = [(e.type or "", _room_area(e)) for e in rooms]
    denom = sum(a for _, a in areas) or 1.0
    for t in ROOM_TYPES:
        share = sum(a for typ, a in areas if typ == t) / denom
        feats[f"area_frac_{t}"] = round(share, 4)

    bt = (floor.building_type or "").lower()
    for t in BUILDING_TYPES:
        feats[f"building_{t}"] = 1.0 if bt == t else 0.0

    return feats


def feature_keys() -> list[str]:
    """Stable, ordered list of feature names (the vector layout)."""
    keys = [
        "room_count", "total_area_m2", "door_count", "window_count",
        "wall_count", "adjacency_density", "compactness", "floor_count",
    ]
    keys += [f"area_frac_{t}" for t in ROOM_TYPES]
    keys += [f"building_{t}" for t in BUILDING_TYPES]
    return keys


def to_vector(feats: dict[str, float], keys: Optional[list[str]] = None) -> list[float]:
    """Flatten a feature dict to a vector in the canonical key order."""
    ks = keys or feature_keys()
    return [float(feats.get(k, 0.0)) for k in ks]


def describe_floor(floor: Floor) -> str:
    """Short natural-language description of a floor, for embedding."""
    f = floor_features(floor)
    rooms = [e for e in floor.elements if e.kind == "room"]
    types = sorted({e.type for e in rooms if e.type})
    bt = floor.building_type or "unspecified type"
    parts = [
        f"{int(f['room_count'])}-room {bt} floor",
        f"total area {f['total_area_m2']:.0f} m2" if f["total_area_m2"] else "area unknown",
    ]
    if types:
        parts.append("rooms: " + ", ".join(types))
    parts.append(f"{int(f['door_count'])} doors, {int(f['window_count'])} windows")
    return "; ".join(parts)
