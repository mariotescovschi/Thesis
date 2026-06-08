#!/usr/bin/env python3
"""
Evaluate hybrid comparison against CubiCasa GT.
Geometry: Mask2Former masks vs GT masks (pixel IoU).
Semantics: Qwen/Claude room types vs GT room labels (type recall).
Shared utilities (canon, load_gt_*, raster, iou) used by other eval scripts.
"""
import json, os, re
from pathlib import Path
from collections import Counter
import numpy as np, cv2
from pycocotools import mask as maskUtils

ROOT = Path(__file__).resolve().parent.parents[3]  # project root
RES = Path.home() / "Desktop" / "floorplan_results"
CUBI = Path.home() / "Downloads" / "cubicasa5k" / "high_quality_architectural"
PLAN2ID = {"plan_a": "1654", "plan_b": "5748", "plan_c": "3015"}
CLASSES = ["room", "wall", "door", "window", "railing"]

# normalize room type strings to a canonical token for semantic matching
CANON = {
    "bedroom": "bedroom", "mh": "bedroom",
    "living room": "living", "livingroom": "living", "living_room": "living", "oh": "living", "ah": "living",
    "library": "study", "study/library": "study", "study": "study", "library/study": "study", "kirj": "study",
    "office": "study",
    "kitchen": "kitchen", "kitchen+dining": "kitchen", "kt": "kitchen", "k": "kitchen",
    "dining": "dining", "dining room": "dining",
    "bath": "bath", "bathroom": "bath", "kph": "bath", "ph": "bath",
    "toilet": "toilet", "wc": "toilet",
    "entry": "entry", "entry hall": "entry", "entry_hall": "entry", "entrance hall": "entry",
    "et": "entry", "draughtlobby": "entry",
    "storage": "storage", "var": "storage", "cellar": "storage",
    "utility": "utility", "utility room": "utility", "utility_room": "utility",
    "technical": "technical", "technicalroom": "technical", "technical room": "technical",
    "technical closet": "technical",
    "hall/landing": "hall", "hall": "hall", "aula": "hall", "corridor": "hall",
    "alcove": "alcove", "alk": "alcove",
    "sauna": "sauna", "s": "sauna",
    "changing room": "sauna", "pukuh": "sauna",
    "garage": "garage", "autotalli": "garage", "carport": "garage",
    "balcony": "outdoor", "terrace": "outdoor", "parveke": "outdoor",
    "outdoor": "outdoor", "yard": "outdoor",
    "workshop": "other", "fireplace room": "other", "bedroom/workshop": "other",
    "attic": "other", "room": "other", "undefined": "other", "userdefined": "other",
    "dressingroom": "other",
}


def canon(s):
    return CANON.get(str(s).strip().lower(), str(s).strip().lower())


def load_gt_geom(sample_id):
    d = json.load(open(ROOT / "experiments/mask2former_training/dataset/val.json"))
    cats = {c["id"]: c["name"] for c in d["categories"]}
    iid = next(i["id"] for i in d["images"] if f"/{sample_id}/" in i["file_name"])
    info = next(i for i in d["images"] if i["id"] == iid)
    H, W = info["height"], info["width"]
    masks = {c: np.zeros((H, W), np.uint8) for c in CLASSES}
    counts = Counter()
    for a in d["annotations"]:
        if a["image_id"] != iid:
            continue
        cls = cats[a["category_id"]]
        counts[cls] += 1
        rle = a["segmentation"]
        if isinstance(rle["counts"], str):
            rle = {"size": rle["size"], "counts": rle["counts"].encode()}
        masks[cls] |= maskUtils.decode(rle).astype(np.uint8)
    return (W, H), masks, counts


def load_gt_sem(sample_id):
    svg = (CUBI / sample_id / "model.svg").read_text()
    rooms = re.findall(r'class="Space (\w+)"', svg)
    return Counter(canon(r) for r in rooms if canon(r) != "outdoor")


def raster(polys, shape, src=None, dst=None):
    m = np.zeros(shape, np.uint8)
    sx = dst[0] / src[0] if src and dst else 1
    sy = dst[1] / src[1] if src and dst else 1
    for poly in polys:
        pts = np.array([[x * sx, y * sy] for x, y in poly], np.int32).reshape(-1, 1, 2)
        if len(pts) >= 3:
            cv2.fillPoly(m, [pts], 1)
    return m


def iou(a, b):
    u = np.logical_or(a, b).sum()
    return np.logical_and(a, b).sum() / u if u else float("nan")


def geom_eval(plan, method, gt_size, gt_masks, gt_counts):
    f = RES / f"{plan}_{method}.json"
    if not f.exists():
        return
    data = json.load(open(f))
    src = None
    if method == "m2f":
        polys = {c: [o["polygon"] for o in data.get(c, [])] for c in CLASSES}
        cnt = {c: len(polys[c]) for c in CLASSES}
    else:  # claude geometry: parsed schema with rooms/walls polygons
        p = data.get("parsed", data)
        if not p:
            print(f"  [{method:7}] geometry: PARSE FAIL"); return
        sz = p.get("image_size")
        src = (sz["width"], sz["height"]) if sz else None
        polys = {"room": [r["polygon"] for r in p.get("rooms", []) if r.get("polygon")],
                 "wall": [w["polygon"] for w in p.get("walls", []) if w.get("polygon")]}
        cnt = {"room": len(p.get("rooms", [])), "wall": len(p.get("walls", [])),
               "door": len(p.get("doors", [])), "window": len(p.get("windows", []))}
    ri = iou(raster(polys.get("room", []), gt_masks["room"].shape, src, gt_size), gt_masks["room"])
    wi = iou(raster(polys.get("wall", []), gt_masks["wall"].shape, src, gt_size), gt_masks["wall"])
    cd = " ".join(f"{c}={cnt.get(c,0)}/{gt_counts[c]}" for c in CLASSES)
    print(f"  [{method:7}] GEOM  IoU room={ri:.3f} wall={wi:.3f} | counts {cd}")


def sem_eval(plan, method, gt_sem):
    # qwen file name differs
    cand = [f"{plan}_qwen_semantic.json"] if method == "qwen" else [f"{plan}_{method}.json"]
    f = next((RES / c for c in cand if (RES / c).exists()), None)
    if not f:
        return
    raw = json.load(open(f))
    p = raw.get("parsed", raw) if isinstance(raw, dict) else None
    if not p or "rooms" not in p:
        print(f"  [{method:7}] SEM   PARSE FAIL"); return
    pred = Counter(canon(r.get("type_en") or r.get("label")) for r in p.get("rooms", []))
    matched = sum((pred & gt_sem).values())
    total = sum(gt_sem.values())
    extra = sum((pred - gt_sem).values())
    fc = p.get("floor_count")
    print(f"  [{method:7}] SEM   room-type recall={matched}/{total} "
          f"({100*matched/total:.0f}%), spurious={extra}, floors={fc}")


def main():
    for plan, sid in PLAN2ID.items():
        gt_size, gt_masks, gt_counts = load_gt_geom(sid)
        gt_sem = load_gt_sem(sid)
        print(f"\n{'='*60}\n{plan} (id {sid}, {gt_size[0]}x{gt_size[1]})")
        print(f"  GT geom counts: {dict(gt_counts)}")
        print(f"  GT room types : {dict(gt_sem)}")
        geom_eval(plan, "m2f", gt_size, gt_masks, gt_counts)
        sem_eval(plan, "qwen", gt_sem)
        geom_eval(plan, "claude", gt_size, gt_masks, gt_counts)
        sem_eval(plan, "claude", gt_sem)


if __name__ == "__main__":
    main()
