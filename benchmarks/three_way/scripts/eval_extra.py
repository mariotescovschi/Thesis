#!/usr/bin/env python3
"""
Extra benchmarks (A, B, C) on 50 CubiCasa val plans, reusing existing predictions.
A: Room-count accuracy (hallucination vs omission)
B: Per-class IoU on monolithic Claude
C: Per-type F1 by room type
Outputs extra_results.json + EXTRA_RESULTS.md.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from compare_eval import canon, load_gt_sem, load_gt_geom, raster, iou

HERE = Path(__file__).resolve().parent.parent
QWEN_LEVEL = "level3_strict"

# Hybrid pipeline per-class IoU on the CubiCasa TEST split (from before_after).
PIPELINE_TEST = {"room": 0.889, "wall": 0.749, "door": 0.631, "window": 0.728, "railing": 0.272}


# ---------- shared room-type extractors (canonical multisets, outdoor dropped) ----------
def qwen_rooms(parsed):
    if not parsed:
        return None
    items = []
    for fl in parsed.get("floors", []):
        items += fl.get("rooms", [])
    items += parsed.get("rooms", [])
    out = Counter()
    for r in items:
        t = canon(r if isinstance(r, str)
                  else (r.get("type_en") or r.get("label") or r.get("label_original")))
        if t != "outdoor":
            out[t] += 1
    return out


def claude_rooms(data):
    out = Counter()
    for r in data.get("rooms", []):
        t = canon(r.get("type_en") or r.get("label", ""))
        if t != "outdoor":
            out[t] += 1
    return out


def load_inputs():
    qwen_preds = json.load(open(HERE / "data" / "semantic_preds.json"))
    geom_dir = HERE / "data" / "claude_geom_preds"
    ids = sorted(set(qwen_preds) & {p.stem for p in geom_dir.glob("*.json")})
    gt_sem = {s: load_gt_sem(s) for s in ids}
    qwen = {s: qwen_rooms(qwen_preds[s].get(QWEN_LEVEL)) for s in ids}
    claude = {s: claude_rooms(json.load(open(geom_dir / f"{s}.json"))) for s in ids}
    return ids, gt_sem, qwen, claude


# ---------- A. Room-count accuracy ----------
def bench_a(ids, gt_sem, qwen, claude):
    def per_model(pred):
        diffs, over, under, signed = [], [], [], []
        for s in ids:
            if pred[s] is None:
                continue
            p, g = sum(pred[s].values()), sum(gt_sem[s].values())
            d = p - g
            signed.append(d)
            diffs.append(abs(d))
            over.append(max(d, 0))
            under.append(max(-d, 0))
        return {
            "n": len(diffs),
            "mae": float(np.mean(diffs)),
            "mean_signed": float(np.mean(signed)),
            "mean_over": float(np.mean(over)),
            "mean_under": float(np.mean(under)),
            "exact_match_pct": float(100 * np.mean([d == 0 for d in signed])),
        }
    return {"qwen": per_model(qwen), "claude": per_model(claude)}


# ---------- B. Per-class IoU on monolithic Claude ----------
def bench_b(ids):
    geom_dir = HERE / "data" / "claude_geom_preds"
    acc = defaultdict(list)  # class -> [iou per plan]
    poly_key = {"room": "rooms", "wall": "walls", "door": "doors", "window": "windows"}
    for s in ids:
        data = json.load(open(geom_dir / f"{s}.json"))
        sz = data.get("image_size")
        src = (sz["width"], sz["height"]) if sz else None
        gt_size, gt_masks, _ = load_gt_geom(s)  # gt_size = (W, H)
        for cls, key in poly_key.items():
            polys = [o["polygon"] for o in data.get(key, []) if o.get("polygon")]
            pred_mask = raster(polys, gt_masks[cls].shape, src, gt_size)
            val = iou(pred_mask, gt_masks[cls])
            if val == val:  # drop NaN (empty GT class on this plan)
                acc[cls].append(val)
    return {cls: {"mean": float(np.mean(v)), "std": float(np.std(v, ddof=1)), "n": len(v)}
            for cls, v in acc.items()}


# ---------- C. Per-type F1 ----------
def bench_c(ids, gt_sem, pred):
    tp = Counter(); fp = Counter(); fn = Counter(); gt_tot = Counter()
    for s in ids:
        if pred[s] is None:
            continue
        p, g = pred[s], gt_sem[s]
        types = set(p) | set(g)
        for t in types:
            tp[t] += min(p[t], g[t])
            fp[t] += max(p[t] - g[t], 0)
            fn[t] += max(g[t] - p[t], 0)
        for t, c in g.items():
            gt_tot[t] += c
    rows = {}
    for t in sorted(gt_tot, key=lambda x: -gt_tot[x]):
        pr = tp[t] / (tp[t] + fp[t]) if (tp[t] + fp[t]) else 0.0
        rc = tp[t] / (tp[t] + fn[t]) if (tp[t] + fn[t]) else 0.0
        f1 = 2 * pr * rc / (pr + rc) if (pr + rc) else 0.0
        rows[t] = {"gt": int(gt_tot[t]), "tp": int(tp[t]), "fp": int(fp[t]),
                   "fn": int(fn[t]), "precision": pr, "recall": rc, "f1": f1}
    return rows


# ---------- report ----------
def write_md(a, b, c_qwen, c_claude):
    L = ["# Extra Benchmarks (A, B, C): CubiCasa val, n=50",
         "",
         "Reuses existing predictions (Qwen L3 + Claude Opus 4.8 monolithic). No re-runs.",
         "Reproduce: `python3 eval_extra.py`.", ""]

    L += ["## A. Room-count accuracy",
          "",
          "Predicted number of rooms vs GT, split into over-prediction (hallucinated) and "
          "omission (missed). MAE = mean absolute count error.", "",
          "| model | MAE | mean signed | mean over (halluc.) | mean under (missed) | exact-match % |",
          "|---|---|---|---|---|---|"]
    for m, r in (("Qwen3-VL-8B (L3)", a["qwen"]), ("Claude Opus 4.8", a["claude"])):
        L.append(f"| {m} | {r['mae']:.2f} | {r['mean_signed']:+.2f} | {r['mean_over']:.2f} "
                 f"| {r['mean_under']:.2f} | {r['exact_match_pct']:.0f}% |")
    L += ["",
          "A positive *mean signed* means the model emits more rooms than exist (Claude's "
          "higher recall in Section 5 comes with more hallucinated rooms).", ""]

    L += ["## B. Per-class IoU: monolithic Claude (completes Section 2)",
          "",
          "> Split caveat: Claude on **val** (n=50); pipeline reference on **test** (n=50). "
          "Not identical plans, descriptive only.", "",
          "| class | Claude 4.8 (val) | Hybrid pipeline (test, ref) |",
          "|---|---|---|"]
    for cls in ("room", "wall", "door", "window"):
        cv = b.get(cls)
        cell = f"{cv['mean']:.3f} ± {cv['std']:.3f}" if cv else "n/a"
        L.append(f"| {cls} | {cell} | {PIPELINE_TEST[cls]:.3f} |")
    L.append(f"| railing | n/a (Claude emits none) | {PIPELINE_TEST['railing']:.3f} |")
    L += ["",
          "Claude's geometry is weak across **all** classes, not just walls. Doors/windows "
          "are tiny targets it cannot place pixel-precisely.", ""]

    L += ["## C. Per-type F1: where each model errs (by room type)",
          "",
          "Aggregated true/false positives/negatives per canonical room type across 50 plans, "
          "sorted by GT frequency. Shows *which* types each model confuses.", ""]
    for title, rows in (("Qwen3-VL-8B (L3)", c_qwen), ("Claude Opus 4.8", c_claude)):
        L += [f"### {title}", "",
              "| type | GT | F1 | precision | recall |",
              "|---|---|---|---|---|"]
        for t, r in rows.items():
            L.append(f"| {t} | {r['gt']} | {r['f1']:.3f} | {r['precision']:.3f} | {r['recall']:.3f} |")
        L.append("")

    (HERE / "results" / "EXTRA_RESULTS.md").write_text("\n".join(L) + "\n")


def main():
    ids, gt_sem, qwen, claude = load_inputs()
    a = bench_a(ids, gt_sem, qwen, claude)
    b = bench_b(ids)
    c_qwen = bench_c(ids, gt_sem, qwen)
    c_claude = bench_c(ids, gt_sem, claude)

    out = {"n": len(ids), "A_room_count": a, "B_per_class_iou_claude_val": b,
           "C_per_type_f1": {"qwen": c_qwen, "claude": c_claude}}
    (HERE / "data" / "extra_results.json").write_text(json.dumps(out, indent=2) + "\n")
    write_md(a, b, c_qwen, c_claude)

    print("A. room-count MAE  Qwen={:.2f}  Claude={:.2f}".format(a["qwen"]["mae"], a["claude"]["mae"]))
    print("   over (halluc.)  Qwen={:.2f}  Claude={:.2f}".format(a["qwen"]["mean_over"], a["claude"]["mean_over"]))
    print("B. Claude val IoU  " + "  ".join(f"{k}={v['mean']:.3f}" for k, v in b.items()))
    print("C. per-type F1 computed for {} Qwen types, {} Claude types".format(len(c_qwen), len(c_claude)))
    print(f"-> {HERE / 'extra_results.json'}\n-> {HERE / 'EXTRA_RESULTS.md'}")


if __name__ == "__main__":
    main()
