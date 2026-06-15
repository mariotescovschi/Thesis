"""Scene text must expose every element id, including segments (the chat bug fix).

Previously walls/doors/windows showed only as counts (wall=3, door=2), so the model
could not target them by id even though the prompt asked it to use (id=...).
"""
from core.document import Element, Floor
from helpers.scene import build_scene, scene_to_text


def _floor() -> Floor:
    return Floor(
        id="fl", name="L0", width=400, height=400,
        elements=[
            Element(id="room_1", kind="room", type="kitchen", label="Kitchen",
                    polygon=[[0, 0], [200, 0], [200, 200], [0, 200]]),
            Element(id="wall_1", kind="wall",
                    polygon=[[0, 0], [400, 0], [400, 10], [0, 10]]),
            Element(id="door_1", kind="door",
                    polygon=[[50, 0], [90, 0], [90, 8], [50, 8]]),
        ],
    )


def test_every_segment_listed_with_id():
    text = scene_to_text(build_scene(_floor()))
    # Each segment id must appear so the model can target it.
    assert "id=wall_1" in text
    assert "id=door_1" in text
    # Rooms still carry their id too.
    assert "id=room_1" in text


def test_segment_lines_count_matches_segments():
    scene = build_scene(_floor())
    text = scene_to_text(scene)
    for seg in scene["segments"]:
        assert f"id={seg['id']}" in text
