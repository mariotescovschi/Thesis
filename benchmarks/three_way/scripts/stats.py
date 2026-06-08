#!/usr/bin/env python3
"""
Statistical tests on the benchmark results.
Semantics: Wilcoxon signed-rank + bootstrap CI on paired per-plan F1 delta.
Geometry: descriptive stats (different splits, no paired test).
Outputs stats.json.
"""
import json
import re
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats

HERE = Path(__file__).resolve().parent.parent
RNG = np.random.default_rng(42)
N_BOOT = 10000

# Hybrid pipeline geometry on the CubiCasa TEST split (from benchmarks/before_after).
PIPELINE_TEST_IOU = {"room": 0.889, "wall": 0.749}


def bootstrap_ci(delta, n_boot=N_BOOT, alpha=0.05):
    """Percentile bootstrap CI for the mean of a paired delta array."""
    delta = np.asarray(delta, float)
    n = len(delta)
    boot_means = np.array([RNG.choice(delta, size=n, replace=True).mean()
                           for _ in range(n_boot)])
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def semantics():
    d = json.load(open(HERE / "data" / "sem_headtohead.json"))
    qwen = np.array(d["qwen_f1"], float)
    claude = np.array(d["claude_f1"], float)
    delta = qwen - claude  # >0 => Qwen better

    # Wilcoxon needs at least one non-zero difference.
    try:
        w_stat, p = scipy_stats.wilcoxon(qwen, claude)
        w_stat, p = float(w_stat), float(p)
    except ValueError:
        w_stat, p = float("nan"), float("nan")

    ci = bootstrap_ci(delta)
    out = {
        "n": int(len(delta)),
        "qwen_mean": float(qwen.mean()), "qwen_std": float(qwen.std(ddof=1)),
        "claude_mean": float(claude.mean()), "claude_std": float(claude.std(ddof=1)),
        "delta_mean": float(delta.mean()),
        "wilcoxon_stat": w_stat, "wilcoxon_p": p,
        "bootstrap_ci_95": ci,
        "significant_at_0.05": bool(p == p and p < 0.05),  # p==p guards NaN
        "ci_excludes_zero": bool(ci[0] > 0 or ci[1] < 0),
    }
    return out


def parse_geom_per_plan():
    """Read per-plan room/wall IoU from claude_geom_preds/RESULTS.md table."""
    txt = (HERE / "data" / "claude_geom_preds" / "RESULTS.md").read_text()
    rooms, walls = [], []
    for line in txt.splitlines():
        m = re.match(r"\|\s*(\d+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|", line)
        if m:
            rooms.append(float(m.group(2)))
            walls.append(float(m.group(3)))
    return np.array(rooms), np.array(walls)


def geometry():
    rooms, walls = parse_geom_per_plan()
    return {
        "n_claude_val": int(len(rooms)),
        "claude_val_room_iou": {"mean": float(rooms.mean()), "std": float(rooms.std(ddof=1))},
        "claude_val_wall_iou": {"mean": float(walls.mean()), "std": float(walls.std(ddof=1))},
        "pipeline_test_room_iou_mean": PIPELINE_TEST_IOU["room"],
        "pipeline_test_wall_iou_mean": PIPELINE_TEST_IOU["wall"],
        "note": ("Claude on val split, pipeline on test split -> NOT identical plans. "
                 "Descriptive only; no paired test."),
    }


def main():
    sem = semantics()
    geo = geometry()
    report = {"semantics": sem, "geometry": geo}
    (HERE / "data" / "stats.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"Semantics: Qwen F1={sem['qwen_mean']:.3f}±{sem['qwen_std']:.3f}, "
          f"Claude F1={sem['claude_mean']:.3f}±{sem['claude_std']:.3f}")
    print(f"  delta={sem['delta_mean']:+.3f}, Wilcoxon p={sem['wilcoxon_p']:.4f}, "
          f"CI=[{sem['bootstrap_ci_95'][0]:+.3f}, {sem['bootstrap_ci_95'][1]:+.3f}]")
    print(f"Geometry: Claude room={geo['claude_val_room_iou']['mean']:.3f}, "
          f"wall={geo['claude_val_wall_iou']['mean']:.3f} (val) | "
          f"Pipeline room={geo['pipeline_test_room_iou_mean']}, "
          f"wall={geo['pipeline_test_wall_iou_mean']} (test)")
    print(f"-> stats.json")


if __name__ == "__main__":
    main()
