"""Geometry: local Mask2Former (detectron2) -> simplified polygons.

Reuses pipeline/mask2former_infer.py (setup_detectron2, CLASSES) and the
Douglas-Peucker polygonization from benchmarks/three_way/compare_m2f.py.
Runs on CPU (the HAS_CUDA_MSDA patch handles the fallback). Predictor is
loaded lazily on first call (model load is heavy).
"""
import importlib.util
from pathlib import Path
import cv2
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[3]  # app/backend/infra/ -> project root

_spec = importlib.util.spec_from_file_location(
    "m2f_infer", ROOT / "pipeline" / "mask2former_infer.py")
_inf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inf)
CLASSES = _inf.CLASSES
SCORE_THRESH = _inf.SCORE_THRESH

EPS_FRAC = 0.004   # Douglas-Peucker epsilon as fraction of contour perimeter
MIN_AREA = 80      # drop tiny specks

_predictor = None


def _predictor_once():
    global _predictor
    if _predictor is None:
        _, _predictor = _inf.setup_detectron2()
    return _predictor


def _mask_to_polys(mask):
    cnts, _ = cv2.findContours(
        mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cnts:
        if cv2.contourArea(c) < MIN_AREA:
            continue
        eps = EPS_FRAC * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        if len(approx) >= 3:
            polys.append(approx.tolist())
    return polys


def analyze_image(path):
    """Return (width, height, [{"kind","polygon","score"}, ...])."""
    img = cv2.imread(str(path))
    h, w = img.shape[:2]
    with torch.no_grad():
        inst = _predictor_once()(img)["instances"].to("cpu")
    inst = inst[inst.scores >= SCORE_THRESH]
    masks = inst.pred_masks.numpy()
    classes = inst.pred_classes.numpy()
    scores = inst.scores.numpy()
    elements = []
    for m, cid, sc in zip(masks, classes, scores):
        for poly in _mask_to_polys(m):
            elements.append({
                "kind": CLASSES[int(cid)],
                "polygon": poly,
                "score": round(float(sc), 3),
            })
    return w, h, elements
