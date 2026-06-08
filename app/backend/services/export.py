"""Export service: a Floor Document -> JSON / SVG / DXF. Pure (no filesystem I/O)."""
import io
import xml.sax.saxutils as xml

import ezdxf

from core.document import Floor, Element
from helpers.geom import centroid

# Per-kind SVG style: (stroke, fill, stroke_width). Rooms are translucent fills,
# walls solid, doors/windows visually distinct.
_SVG_STYLE: dict[str, tuple[str, str, float]] = {
    "room": ("#2563eb", "rgba(37,99,235,0.18)", 1.5),
    "wall": ("#111827", "#111827", 1.0),
    "door": ("#f59e0b", "rgba(245,158,11,0.35)", 1.5),
    "window": ("#10b981", "rgba(16,185,129,0.35)", 1.5),
    "railing": ("#a855f7", "none", 1.5),
}
_SVG_FALLBACK = ("#6b7280", "rgba(107,114,128,0.15)", 1.0)

# Per-kind DXF AutoCAD Color Index (ACI) for the layer.
_DXF_ACI: dict[str, int] = {
    "room": 5,      # blue
    "wall": 7,      # white/black (default)
    "door": 2,      # yellow
    "window": 3,    # green
    "railing": 6,   # magenta
}
_DXF_ACI_FALLBACK = 8   # grey


def to_json(floor: Floor) -> str:
    """Raw Document JSON, pretty-printed."""
    return floor.model_dump_json(indent=2)


def _points_attr(poly: list[list[int]]) -> str:
    return " ".join(f"{p[0]},{p[1]}" for p in poly)


def _element_svg(el: Element) -> str:
    if len(el.polygon) < 2:
        return ""
    stroke, fill, width = _SVG_STYLE.get(el.kind, _SVG_FALLBACK)
    parts = [
        f'<polygon points="{_points_attr(el.polygon)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{width}" />'
    ]
    # Label rooms with their semantic type + area at the centroid.
    if el.kind == "room" and (el.type or el.label) and len(el.polygon) >= 3:
        cx, cy = centroid(el.polygon)
        label = xml.escape(el.type or el.label or "")
        if el.area_m2 is not None:
            label += f" ({el.area_m2:.2f}m²)"
        parts.append(
            f'<text x="{cx:.1f}" y="{cy:.1f}" font-family="sans-serif" '
            f'font-size="12" fill="{stroke}" text-anchor="middle" '
            f'dominant-baseline="middle">{label}</text>'
        )
    return "".join(parts)


def to_svg(floor: Floor) -> str:
    """SVG sized to the floor, one shape per element, rooms labelled by type."""
    w = floor.width or 1000
    h = floor.height or 1000
    body = "".join(_element_svg(el) for el in floor.elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">{body}</svg>'
    )


def to_dxf(floor: Floor) -> bytes:
    """DXF: each element polygon as a closed LWPOLYLINE on a per-kind layer.

    Coordinates are scaled px -> metres when ``scale_px_per_m`` is set, otherwise
    kept in pixel units. The image Y axis (down-positive) is flipped to the CAD
    convention (up-positive) so the drawing opens upright in a CAD viewer.
    """
    scale = floor.scale_px_per_m if floor.scale_px_per_m else None
    height = float(floor.height or 0)

    doc = ezdxf.new(setup=True)
    msp = doc.modelspace()

    for el in floor.elements:
        if len(el.polygon) < 3:
            continue
        if el.kind not in doc.layers:
            aci = _DXF_ACI.get(el.kind, _DXF_ACI_FALLBACK)
            doc.layers.add(name=el.kind, color=aci)
        pts: list[tuple[float, float]] = []
        for x, y in el.polygon:
            fx, fy = float(x), height - float(y)
            if scale:
                fx, fy = fx / scale, fy / scale
            pts.append((fx, fy))
        msp.add_lwpolyline(pts, close=True, dxfattribs={"layer": el.kind})

    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode(doc.output_encoding)
