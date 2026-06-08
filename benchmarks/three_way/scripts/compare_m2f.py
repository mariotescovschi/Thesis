#!/usr/bin/env python3
"""
Mask2Former predictions for the 3-way comparison.
Runs detectron2 on CPU, outputs JSON + SVG + overlay per plan.
"""
import os, sys, json, cv2, importlib.util
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parents[3]  # project root
_spec = importlib.util.spec_from_file_location(
    "m2f_infer", ROOT / "pipeline" / "mask2former_infer.py")
_inf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_inf)
setup_detectron2, CLASSES, SCORE_THRESH = _inf.setup_detectron2, _inf.CLASSES, _inf.SCORE_THRESH

IMAGES = Path.home() / "Desktop" / "floorplan_comparison"   # clean inputs
OUT = Path.home() / "Desktop" / "floorplan_results"         # our outputs
OUT.mkdir(exist_ok=True)
PLANS = ["plan_a", "plan_b", "plan_c"]
EPS_FRAC = 0.004          # Douglas-Peucker epsilon as fraction of contour perimeter
MIN_AREA = 80             # drop tiny specks

SVG_FILL = {              # by class
    "room": ("#cfe8d8", 0.55), "wall": ("#9aa0a6", 0.9), "door": ("#6f8fd6", 0.9),
    "window": ("#3fb6c9", 0.9), "railing": ("#b58fd0", 0.9),
}


def mask_to_polys(mask):
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polys = []
    for c in cnts:
        if cv2.contourArea(c) < MIN_AREA:
            continue
        eps = EPS_FRAC * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        if len(approx) >= 3:
            polys.append(approx.tolist())
    return polys


def to_json(instances):
    masks = instances.pred_masks.numpy()
    classes = instances.pred_classes.numpy()
    scores = instances.scores.numpy()
    out = {c: [] for c in CLASSES}
    for m, cid, sc in zip(masks, classes, scores):
        if sc < SCORE_THRESH:
            continue
        for poly in mask_to_polys(m):
            out[CLASSES[cid]].append({"score": round(float(sc), 3), "polygon": poly})
    return out


def render_svg(data, w, h):
    p = ['<?xml version="1.0" encoding="UTF-8"?>',
         f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
         f'viewBox="0 0 {w} {h}">',
         f'<rect width="{w}" height="{h}" fill="#1a1a1a"/>']
    for cls in ["room", "railing", "wall", "door", "window"]:  # paint order
        fill, op = SVG_FILL[cls]
        for obj in data.get(cls, []):
            pts = " ".join(f"{x},{y}" for x, y in obj["polygon"])
            stroke = "none" if cls == "room" else fill
            p.append(f'<polygon points="{pts}" fill="{fill}" fill-opacity="{op}" '
                     f'stroke="{stroke}" stroke-width="1"/>')
    p.append("</svg>")
    return "\n".join(p)


def overlay(img, data):
    """Draw masks semi-transparent over the real plan (the hybrid 'where')."""
    out = img.copy()
    bgr = {"room": (216, 232, 207), "wall": (166, 160, 154), "door": (214, 143, 111),
           "window": (201, 182, 63), "railing": (208, 143, 181)}
    for cls in ["room", "railing", "wall", "door", "window"]:
        layer = out.copy()
        for obj in data.get(cls, []):
            pts = np.array(obj["polygon"], np.int32).reshape(-1, 1, 2)
            cv2.fillPoly(layer, [pts], bgr[cls])
        a = 0.35 if cls == "room" else 0.55
        out = cv2.addWeighted(layer, a, out, 1 - a, 0)
    return out


def main():
    cfg, predictor = setup_detectron2()
    import torch
    for name in PLANS:
        img = cv2.imread(str(IMAGES / f"{name}.png"))
        h, w = img.shape[:2]
        with torch.no_grad():
            inst = predictor(img)["instances"].to("cpu")
        inst = inst[inst.scores >= SCORE_THRESH]
        data = to_json(inst)
        counts = {c: len(v) for c, v in data.items() if v}
        (OUT / f"{name}_m2f.json").write_text(json.dumps(data, indent=2))
        (OUT / f"{name}_m2f.svg").write_text(render_svg(data, w, h))
        cv2.imwrite(str(OUT / f"{name}_m2f_overlay.png"), overlay(img, data))
        print(f"{name}: {counts}")


if __name__ == "__main__":
    main()
