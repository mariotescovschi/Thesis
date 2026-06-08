"""Export routes: download a floor as DXF / SVG / JSON."""
from fastapi import APIRouter, Query
from fastapi.responses import Response

import infra.store as store
import services.export as export
from core.errors import ValidationError

router = APIRouter()

# fmt -> (media type, file extension, encoder)
_FORMATS = {
    "json": ("application/json", "json"),
    "svg": ("image/svg+xml", "svg"),
    "dxf": ("application/dxf", "dxf"),
}


@router.get("/projects/{pid}/export/{floor_id}")
def export_floor(pid: str, floor_id: str, fmt: str = Query("json")) -> Response:
    if fmt not in _FORMATS:
        raise ValidationError(f"Unsupported export format: {fmt!r}. Use dxf, svg or json")

    floor = store.read_output(pid, floor_id)
    media_type, ext = _FORMATS[fmt]

    if fmt == "dxf":
        content: bytes | str = export.to_dxf(floor)
    elif fmt == "svg":
        content = export.to_svg(floor)
    else:
        content = export.to_json(floor)

    headers = {"Content-Disposition": f'attachment; filename="{floor_id}.{ext}"'}
    return Response(content=content, media_type=media_type, headers=headers)
