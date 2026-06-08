"""Unit tests for the export service: DXF, SVG, JSON."""
import json

import pytest

import export
from document import Element, Floor


def _sample_floor() -> Floor:
    return Floor(
        id="fl_test",
        name="Test Floor",
        width=800,
        height=600,
        scale_px_per_m=100.0,
        elements=[
            Element(id="el_r1", kind="room", polygon=[[100, 100], [300, 100], [300, 300], [100, 300]], type="kitchen", label="K"),
            Element(id="el_w1", kind="wall", polygon=[[100, 100], [300, 100], [300, 110], [100, 110]]),
            Element(id="el_d1", kind="door", polygon=[[200, 100], [250, 100], [250, 110], [200, 110]]),
            Element(id="el_win1", kind="window", polygon=[[350, 200], [360, 200], [360, 300], [350, 300]]),
            Element(id="el_degenerate", kind="room", polygon=[[0, 0]]),  # degenerate: <3 points
        ],
    )


class TestJSON:
    def test_valid_json(self):
        out = export.to_json(_sample_floor())
        data = json.loads(out)
        assert data["id"] == "fl_test"
        assert len(data["elements"]) == 5

    def test_no_image_data(self):
        out = export.to_json(_sample_floor())
        assert "image" not in out.lower() or "image" in "raster_image" not in out


class TestSVG:
    def test_valid_svg_envelope(self):
        out = export.to_svg(_sample_floor())
        assert out.startswith("<svg")
        assert 'width="800"' in out
        assert 'height="600"' in out
        assert "</svg>" in out

    def test_contains_polygons(self):
        out = export.to_svg(_sample_floor())
        assert "<polygon" in out

    def test_room_label(self):
        out = export.to_svg(_sample_floor())
        assert "kitchen" in out  # room type rendered as label

    def test_no_image_element(self):
        out = export.to_svg(_sample_floor())
        assert "<image" not in out

    def test_degenerate_polygon_skipped(self):
        """Elements with <2 points should not produce broken SVG."""
        out = export.to_svg(_sample_floor())
        # Should not crash and polygon count = 4 (the 4 valid elements)
        assert out.count("<polygon") == 4


class TestDXF:
    def test_produces_bytes(self):
        out = export.to_dxf(_sample_floor())
        assert isinstance(out, bytes)
        assert len(out) > 0

    def test_contains_layer_names(self):
        out = export.to_dxf(_sample_floor()).decode("utf-8", errors="replace")
        assert "room" in out.lower()
        assert "wall" in out.lower()
        assert "door" in out.lower()

    def test_scaled_coordinates(self):
        """When scale is set, coordinates are in metres (< pixel values)."""
        floor = _sample_floor()
        out = export.to_dxf(floor).decode("utf-8", errors="replace")
        # Original max x is 360 px; at 100px/m that's 3.6m.
        # DXF should NOT have raw pixel coords for rooms; max should be ~3.6 range.
        # We verify by checking the DXF doesn't contain raw 300-range coords.
        # Better: parse it with ezdxf
        import ezdxf
        import io
        doc = ezdxf.read(io.StringIO(out))
        msp = doc.modelspace()
        polys = list(msp.query("LWPOLYLINE"))
        # At least 4 polylines (the degenerate one has <2 points, skipped)
        assert len(polys) == 4
        for poly in polys:
            for x, y, *_ in poly.get_points():
                # All coords should be in metres (max ~6m for 600px at 100px/m)
                assert abs(x) < 10, f"Expected metres, got {x}"
                assert abs(y) < 10, f"Expected metres, got {y}"

    def test_y_flip(self):
        """Y axis should be flipped (CAD = up-positive)."""
        import ezdxf
        import io
        floor = Floor(
            id="fl_yf",
            name="Y",
            width=100,
            height=200,
            elements=[Element(id="el_yf", kind="room", polygon=[[0, 0], [50, 0], [50, 50], [0, 50]])],
        )
        out = export.to_dxf(floor).decode("utf-8", errors="replace")
        doc = ezdxf.read(io.StringIO(out))
        poly = list(doc.modelspace().query("LWPOLYLINE"))[0]
        pts = list(poly.get_points())
        # Original point (0,0) with height=200 should become (0, 200) after flip
        ys = [p[1] for p in pts]
        assert max(ys) == 200.0  # top of the image (0) becomes height

    def test_no_scale(self):
        """Without scale, coords remain in pixels."""
        import ezdxf
        import io
        floor = Floor(
            id="fl_ns",
            name="NS",
            width=400,
            height=300,
            elements=[Element(id="el_ns", kind="wall", polygon=[[100, 100], [300, 100], [300, 110], [100, 110]])],
        )
        out = export.to_dxf(floor).decode("utf-8", errors="replace")
        doc = ezdxf.read(io.StringIO(out))
        poly = list(doc.modelspace().query("LWPOLYLINE"))[0]
        xs = [p[0] for p in poly.get_points()]
        assert max(xs) == 300.0  # pixel coords preserved
