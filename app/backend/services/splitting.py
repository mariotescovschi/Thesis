"""Multi-floor split service: one sheet -> N cropped floors.

Highest-uncertainty task: the auto-detection is an intentionally simple,
documented heuristic (binarize + projection-profile gap split). It is always
backed by a manual-assist fallback (caller-supplied rectangles) so the user is
never blocked when the heuristic guesses wrong.

cv2 / numpy are imported lazily inside functions so this module imports cleanly
even where the native libs are missing; a clear ValidationError is raised at
call time instead.
"""
from pathlib import Path

import infra.store as store
from core.document import Project
from core.errors import NotFoundError, ValidationError

# bbox = [x, y, w, h] in image pixels
Bbox = list[int]

# Fraction of a row/column that must be foreground for it to count as "occupied".
_OCCUPIED_FRAC = 0.01


def _require_cv2():
    """Import cv2 + numpy lazily; surface a domain error if unavailable."""
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as e:  # native dep missing in this environment
        raise ValidationError(
            "Image processing is unavailable (opencv-python not installed). "
            "Provide manual_rects to split this sheet."
        ) from e
    return cv2, np


def _largest_gaps(profile, n_regions: int) -> list[int]:
    """Pick n_regions-1 split positions at the centres of the largest empty bands.

    `profile` is a 1-D occupancy mask (1 = occupied row/col, 0 = empty). We find
    interior runs of 0s, rank them by length, take the longest (n_regions-1) and
    split at each run's midpoint. Returns sorted split indices.
    """
    runs: list[tuple[int, int]] = []  # (length, midpoint)
    i = 0
    length = len(profile)
    while i < length:
        if profile[i] == 0:
            j = i
            while j < length and profile[j] == 0:
                j += 1
            # ignore empty margins at the very start/end — only interior gaps split
            if i > 0 and j < length:
                runs.append((j - i, (i + j) // 2))
            i = j
        else:
            i += 1
    runs.sort(reverse=True)
    splits = sorted(mid for _, mid in runs[: max(0, n_regions - 1)])
    return splits


def _content_bbox_in_strip(occ_cols, x0: int, x1: int) -> tuple[int, int]:
    """Tighten a strip horizontally to its occupied column range [start, end)."""
    start, end = x0, x1
    while start < end and occ_cols[start] == 0:
        start += 1
    while end > start and occ_cols[end - 1] == 0:
        end -= 1
    if start >= end:  # fully empty strip — keep original bounds
        return x0, x1
    return start, end


def detect_regions(
    image_path: str | Path,
    floor_count_hint: int | None,
    manual_rects: list[list[int]] | None,
) -> list[Bbox]:
    """Return per-floor bounding boxes [x, y, w, h] for a multi-floor sheet.

    manual_rects (manual-assist fallback) take precedence and are returned as-is.
    Otherwise: grayscale -> Otsu binarize -> projection profiles. We split along
    whichever axis has the cleaner empty band into `floor_count_hint or 2`
    regions and tighten each region to its content. Approximate by design.
    """
    if manual_rects:
        return [[int(v) for v in r] for r in manual_rects]

    cv2, np = _require_cv2()
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValidationError(f"Could not read image: {image_path}")

    h, w = img.shape[:2]
    n = floor_count_hint if floor_count_hint and floor_count_hint > 1 else 2

    # Otsu binarize; invert so plan strokes/fills become foreground (255).
    _, binary = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    fg = (binary > 0).astype(np.uint8)

    row_counts = fg.sum(axis=1)            # foreground px per row
    col_counts = fg.sum(axis=0)            # foreground px per col
    occ_rows = (row_counts >= w * _OCCUPIED_FRAC).astype(np.uint8)
    occ_cols = (col_counts >= h * _OCCUPIED_FRAC).astype(np.uint8)

    # Choose the split axis whose largest interior empty band is widest.
    def _best_gap(profile) -> int:
        best, i, length = 0, 0, len(profile)
        while i < length:
            if profile[i] == 0:
                j = i
                while j < length and profile[j] == 0:
                    j += 1
                if i > 0 and j < length:
                    best = max(best, j - i)
                i = j
            else:
                i += 1
        return best

    split_horizontally = _best_gap(occ_rows) >= _best_gap(occ_cols)

    if split_horizontally:
        cuts = _largest_gaps(occ_rows, n)
        bounds = [0, *cuts, h]
        regions: list[Bbox] = []
        for y0, y1 in zip(bounds, bounds[1:]):
            x0, x1 = _content_bbox_in_strip(occ_cols, 0, w)
            regions.append([int(x0), int(y0), int(x1 - x0), int(y1 - y0)])
    else:
        cuts = _largest_gaps(occ_cols, n)
        bounds = [0, *cuts, w]
        regions = []
        for x0, x1 in zip(bounds, bounds[1:]):
            y0, y1 = _content_bbox_in_strip(occ_rows, 0, h)
            regions.append([int(x0), int(y0), int(x1 - x0), int(y1 - y0)])

    # Drop degenerate slivers; never return empty (fall back to whole image).
    regions = [r for r in regions if r[2] > 1 and r[3] > 1]
    return regions or [[0, 0, w, h]]


def split_floor(
    pid: str, floor_id: str, manual_rects: list[list[int]] | None = None
) -> Project:
    """Crop the source floor sheet into N new pending floors. Returns the project.

    Reads the source image via the store, detects (or accepts) regions, crops
    each, and appends a new pending Floor per region. Semantics are NOT re-run
    here — the normal analyze flow handles each new floor.
    """
    src = store.input_path(pid, floor_id)            # raises NotFoundError if absent
    floor = store.get_floor(store.load_project(pid), floor_id)

    regions = detect_regions(src, floor.floor_count, manual_rects)
    if len(regions) < 2 and not manual_rects:
        raise ValidationError(
            "Could not detect multiple floors on this sheet. "
            "Provide manual_rects to split it manually."
        )

    cv2, np = _require_cv2()
    img = cv2.imread(str(src))
    if img is None:
        raise ValidationError(f"Could not read image: {src}")
    img_h, img_w = img.shape[:2]
    ext = Path(floor.filename).suffix.lower() or ".png"

    proj = store.load_project(pid)
    for idx, (x, y, w, h) in enumerate(regions, start=1):
        # Clamp the crop to the image so manual rects can't read out of bounds.
        x0 = max(0, min(int(x), img_w - 1))
        y0 = max(0, min(int(y), img_h - 1))
        x1 = max(x0 + 1, min(int(x) + int(w), img_w))
        y1 = max(y0 + 1, min(int(y) + int(h), img_h))
        crop = img[y0:y1, x0:x1]
        ok, buf = cv2.imencode(ext, crop)
        if not ok:
            raise ValidationError(f"Failed to encode crop for region {idx}")
        name = f"{floor.name} — part {idx}"
        proj = store.add_floor_from_bytes(
            pid, buf.tobytes(), f"{floor_id}_part{idx}{ext}", name
        )
    return proj
