#!/usr/bin/env python3
"""OOD generalization: same 3 models on FloorPlanCAD (completely different style).
Qualitative only (no comparable GT). Reports pixel coverage per class.
"""
import importlib.util
from pathlib import Path
import numpy as np, cv2

ROOT = Path(__file__).resolve().parents[2]
PLANS = ROOT / "benchmarks/generalization/floorplancad"
COCO_W = "https://dl.fbaipublicfiles.com/maskformer/mask2former/coco/instance/maskformer2_swin_base_IN21k_384_bs16_50ep/model_final_83d103.pkl"
OUT = ROOT / "benchmarks/generalization/results"
CLASSES = ["room", "wall", "door", "window", "railing"]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cnn = _load("cnn_infer", ROOT / "pipeline/cubicasa_cnn_infer.py")
m2f = _load("m2f_infer", ROOT / "pipeline/mask2former_infer.py")


def m2f_masks(predictor, img, shape):
    out = predictor(img)["instances"].to("cpu")
    out = out[out.scores >= 0.5]
    masks = {c: np.zeros(shape, bool) for c in CLASSES}
    for m, c in zip(out.pred_masks.numpy(), out.pred_classes.numpy()):
        masks[CLASSES[c]] |= m.astype(bool)
    return masks


def main():
    plans = sorted(PLANS.glob("*.png"))
    OUT.mkdir(parents=True, exist_ok=True)
    print("Loading models...")
    _, pred_after = m2f.setup_detectron2()
    _, pred_before = m2f.setup_detectron2(weights=COCO_W)
    cnn_model = cnn.load_model()

    rows = []
    for p in plans:
        img = cv2.imread(str(p))
        shape = img.shape[:2]
        tot = shape[0] * shape[1]
        preds = {
            "before": m2f_masks(pred_before, img, shape),
            "after": m2f_masks(pred_after, img, shape),
            "cnn": cnn.predict(cnn_model, img),
        }
        for model, masks in preds.items():
            cv2.imwrite(str(OUT / f"{p.stem}_{model}.png"), cnn.overlay_side_by_side(img, masks))
            cov = {c: 100 * masks[c].sum() / tot for c in CLASSES}
            rows.append((p.stem, model, cov))
            print(f"{p.stem} {model:7} " + " ".join(f"{c}={cov[c]:.1f}%" for c in CLASSES), flush=True)

    hdr = "| plan | model | " + " | ".join(f"%{c}" for c in CLASSES) + " |\n"
    hdr += "|------|-------|" + "|".join(["------"] * len(CLASSES)) + "|\n"
    body = "".join(f"| {pid} | {m} | " + " | ".join(f"{cov[c]:.1f}" for c in CLASSES) + " |\n"
                   for pid, m, cov in rows)
    means = "".join(f"| **MEAN** | **{model}** | "
                    + " | ".join(f"**{np.mean([cov[c] for pid, mm, cov in rows if mm == model]):.1f}**"
                                 for c in CLASSES) + " |\n"
                    for model in ["before", "after", "cnn"])
    (OUT / "RESULTS.md").write_text(
        "# Generalizare (OOD): FloorPlanCAD\n\n"
        "Aceleasi 3 modele ca before_after, pe stil complet diferit (CAD colorat chinezesc cu cote/mobilier).\n\n"
        "**Calitativ.** FloorPlanCAD adnoteaza simboluri pe linii (semantic-id), NU poligoane de camera "
        "=> NU exista GT comparabil pentru IoU room. Tabelul de mai jos = ACOPERIRE pixeli per clasa "
        "(cat picteaza fiecare model), NU acuratete. Semnalul principal sunt overlay-urile: cine gaseste "
        "structura pe un desen nevazut la antrenare, cine se prabuseste.\n\n"
        "Overlay: original STANGA | predictie DREAPTA. Culori: room=verde, wall=rosu, door=albastru, "
        "window=galben, railing=mov.\n\n" + hdr + body + "\n" + hdr + means)
    print(f"\nDone -> {OUT}/  ({len(plans)*3} overlays + RESULTS.md)")


if __name__ == "__main__":
    main()
