#!/usr/bin/env python3
"""Before/After + CNN on CubiCasa test split.
3 models, 5 classes, overlays + IoU vs GT.
Run: python3 run_before_after.py (NUM env var for plan count)
"""
import os, sys, json, importlib.util
from pathlib import Path
from collections import defaultdict
import numpy as np, cv2, torch
from pycocotools import mask as maskUtils

ROOT = Path(__file__).resolve().parents[2]
IMAGES = Path(os.environ.get("CUBICASA_ROOT", os.path.expanduser("~/Downloads/cubicasa5k")))
TEST_JSON = ROOT / "experiments/mask2former_training/dataset/test.json"
COCO_W = "https://dl.fbaipublicfiles.com/maskformer/mask2former/coco/instance/maskformer2_swin_base_IN21k_384_bs16_50ep/model_final_83d103.pkl"
OUT = ROOT / "benchmarks/before_after/results"
NUM = int(os.environ.get("NUM", "5"))
CLASSES = ["room", "wall", "door", "window", "railing"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cnn = _load("cnn_infer", ROOT / "pipeline/cubicasa_cnn_infer.py")
m2f = _load("m2f_infer", ROOT / "pipeline/mask2former_infer.py")


def iou(a, b):
    u = np.logical_or(a, b).sum()
    return np.logical_and(a, b).sum() / u if u else float("nan")


def gt_masks(anns, cats, iid, shape):
    masks = {c: np.zeros(shape, bool) for c in CLASSES}
    for a in anns:
        if a["image_id"] != iid:
            continue
        rle = a["segmentation"]
        if isinstance(rle["counts"], str):
            rle = {"size": rle["size"], "counts": rle["counts"].encode()}
        masks[cats[a["category_id"]]] |= maskUtils.decode(rle).astype(bool)
    return masks


def m2f_masks(predictor, img, shape):
    out = predictor(img)["instances"].to("cpu")
    out = out[out.scores >= 0.5]
    masks = {c: np.zeros(shape, bool) for c in CLASSES}
    for m, c in zip(out.pred_masks.numpy(), out.pred_classes.numpy()):
        masks[CLASSES[c]] |= m.astype(bool)
    return masks


def main():
    d = json.load(open(TEST_JSON))
    cats = {c["id"]: c["name"] for c in d["categories"]}
    imgs = [i for i in d["images"] if (IMAGES / i["file_name"]).exists()][:NUM]
    OUT.mkdir(parents=True, exist_ok=True)

    print("Loading models...")
    _, pred_after = m2f.setup_detectron2()
    _, pred_before = m2f.setup_detectron2(weights=COCO_W)
    cnn_model = cnn.load_model()

    rows, agg = [], defaultdict(lambda: defaultdict(list))
    save_n = int(os.environ.get("SAVE_OVERLAYS", "8"))
    for n, info in enumerate(imgs):
        sid = info["file_name"].split("/")[-2]
        img = cv2.imread(str(IMAGES / info["file_name"]))
        shape = img.shape[:2]
        gt = gt_masks(d["annotations"], cats, info["id"], shape)
        preds = {
            "before": m2f_masks(pred_before, img, shape),
            "after": m2f_masks(pred_after, img, shape),
            "cnn": cnn.predict(cnn_model, img),
        }
        for model, masks in preds.items():
            if n < save_n:
                cv2.imwrite(str(OUT / f"{sid}_{model}.png"), cnn.overlay_side_by_side(img, masks))
            ious = {c: iou(masks[c], gt[c]) for c in CLASSES}
            for c in CLASSES:
                agg[model][c].append(ious[c])
            rows.append((sid, model, ious))
            print(f"{sid} {model:7} " + " ".join(f"{c}={ious[c]:.3f}" for c in CLASSES), flush=True)

    # markdown
    hdr = "| plan | model | " + " | ".join(f"IoU {c}" for c in CLASSES) + " |\n"
    hdr += "|------|-------|" + "|".join(["------"] * len(CLASSES)) + "|\n"
    shown = [r for r in rows if r[0] in {s for s, _, _ in rows[:save_n * 3]}]
    body = "".join(f"| {sid} | {m} | " + " | ".join(f"{io[c]:.3f}" for c in CLASSES) + " |\n"
                   for sid, m, io in shown)
    means = "".join(f"| **MEAN** | **{m}** | "
                    + " | ".join(f"**{np.nanmean(agg[m][c]):.3f}**" for c in CLASSES) + " |\n"
                    for m in ["before", "after", "cnn"])
    (OUT / "RESULTS.md").write_text(
        f"# Before/After + CNN: CubiCasa (n={len(imgs)})\n\n"
        "original LEFT | prediction RIGHT. IoU pixel vs GT (RLE).\n"
        "Culori: room=verde, wall=roșu, door=albastru, window=galben, railing=mov.\n\n"
        + hdr + body + "\n" + hdr + means)
    print(f"\nDone -> {OUT}/  (RESULTS.md + {min(save_n, len(imgs))*3} overlays, IoU on all {len(imgs)})")


if __name__ == "__main__":
    main()
