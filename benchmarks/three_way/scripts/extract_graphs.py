#!/usr/bin/env python3
"""
Extract adjacency graphs from Mask2Former predictions on val plans.
Rasterizes rooms/doors, derives which rooms each door connects, outputs graphs.json.
"""
import json, sys, importlib.util, numpy as np, cv2
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parents[2]
HERE = Path(__file__).resolve().parent.parent
CUBI = Path.home() / "Downloads" / "cubicasa5k" / "high_quality_architectural"

# load m2f module
spec = importlib.util.spec_from_file_location("m2f", ROOT / "pipeline" / "mask2former_infer.py")
m2f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m2f)

CLASSES = ["room", "wall", "door", "window", "railing"]
DST = HERE / "data" / "graphs.json"


def get_val_ids(n=50):
    val = json.load(open(ROOT / "experiments/mask2former_training/dataset/val.json"))
    ids = []
    for i in val["images"]:
        fn = i["file_name"]
        if "high_quality_architectural/" in fn:
            sid = fn.split("high_quality_architectural/")[1].split("/")[0]
            if (CUBI / sid / "F1_scaled.png").exists():
                ids.append(sid)
    return ids[:n]


def m2f_predict(predictor, img):
    """Run m2f, return per-class list of polygons with scores."""
    from detectron2.structures import Instances
    out = predictor(img)["instances"]
    result = {c: [] for c in CLASSES}
    for i in range(len(out)):
        score = out.scores[i].item()
        if score < 0.5:
            continue
        cls = CLASSES[out.pred_classes[i].item()]
        mask = out.pred_masks[i].cpu().numpy().astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            if len(c) >= 3:
                result[cls].append({"score": round(score, 3), "polygon": c.squeeze().tolist()})
    return result


def build_graph(preds, H, W):
    """From m2f predictions, build adjacency graph."""
    # rasterize rooms
    room_map = np.zeros((H, W), np.int32)
    for i, r in enumerate(preds["room"], 1):
        pts = np.array(r["polygon"], np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(room_map, [pts], i)

    total_px = H * W
    rooms = []
    for i in range(1, len(preds["room"]) + 1):
        mask = (room_map == i)
        area = int(mask.sum())
        if area == 0:
            continue
        ys, xs = np.where(mask)
        cx, cy = float(xs.mean()) / W, float(ys.mean()) / H
        # 3x3 grid position
        col = "left" if cx < 0.33 else ("right" if cx > 0.66 else "center")
        row = "top" if cy < 0.33 else ("bottom" if cy > 0.66 else "middle")
        pos = f"{row}-{col}" if row != "middle" else col
        rooms.append({"id": i, "area_pct": round(100 * area / total_px, 1), "position": pos})
    rooms.sort(key=lambda x: -x["area_pct"])

    # adjacency via doors
    adj = set()
    for door in preds["door"]:
        mask = np.zeros((H, W), np.uint8)
        pts = np.array(door["polygon"], np.int32).reshape(-1, 1, 2)
        cv2.fillPoly(mask, [pts], 1)
        mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
        touching = set(int(x) for x in room_map[mask > 0]) - {0}
        if len(touching) >= 2:
            t = sorted(touching)
            for i in range(len(t)):
                for j in range(i + 1, len(t)):
                    adj.add((t[i], t[j]))

    return {
        "rooms": rooms,
        "adjacency": [{"a": a, "b": b} for a, b in sorted(adj)],
        "n_doors": len(preds["door"]),
        "n_windows": len(preds["window"]),
    }


def graph_to_text(g):
    """Convert graph dict to natural language context for level4 prompt."""
    # filter out tiny fragments (< 1% area)
    real_rooms = [r for r in g["rooms"] if r["area_pct"] >= 1.0]
    real_ids = {r["id"] for r in real_rooms}
    real_adj = [e for e in g["adjacency"] if e["a"] in real_ids and e["b"] in real_ids]
    lines = [f"DETECTED STRUCTURE ({len(real_rooms)} rooms, {g['n_doors']} doors, {g['n_windows']} windows):"]
    lines.append("Rooms by area (largest first):")
    labels = {}
    for i, r in enumerate(real_rooms):
        lbl = chr(65 + i)  # A, B, C...
        labels[r["id"]] = lbl
        lines.append(f"  {lbl}: {r['area_pct']}% of plan area, located {r.get('position','unknown')}")
    lines.append("Connections (rooms sharing a door):")
    if real_adj:
        for e in real_adj:
            la, lb = labels.get(e["a"], "?"), labels.get(e["b"], "?")
            lines.append(f"  {la} <-> {lb}")
    else:
        lines.append("  (none detected)")
    return "\n".join(lines)


def main():
    ids = get_val_ids(50)
    # skip already done
    existing = json.load(open(DST)) if DST.exists() else {}
    todo = [s for s in ids if s not in existing]
    if not todo:
        print(f"All {len(ids)} graphs already in {DST}")
        return

    print(f"Extracting graphs: {len(todo)} remaining (of {len(ids)})")
    predictor = m2f.setup_detectron2()[1]  # (cfg, predictor)

    for idx, sid in enumerate(todo):
        img = cv2.imread(str(CUBI / sid / "F1_scaled.png"))
        H, W = img.shape[:2]
        preds = m2f_predict(predictor, img)
        g = build_graph(preds, H, W)
        g["text"] = graph_to_text(g)
        existing[sid] = g
        if (idx + 1) % 10 == 0 or idx == len(todo) - 1:
            json.dump(existing, open(DST, "w"), indent=2)
            print(f"  [{idx+1}/{len(todo)}] saved ({len(existing)} total)")

    print(f"Done -> {DST} ({len(existing)} plans)")


if __name__ == "__main__":
    main()
