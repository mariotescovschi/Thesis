#!/usr/bin/env python3
"""
Paired semantic eval: Qwen3-VL-8B (level3_strict) vs Claude Opus 4.8 on identical
50 CubiCasa val plans. Outputs sem_headtohead.json for paired significance testing.
"""
import json
from pathlib import Path
from collections import Counter

from compare_eval import canon, load_gt_sem

HERE = Path(__file__).resolve().parent.parent
QWEN_LEVEL = "level3_strict"


def qwen_rooms(parsed):
    """Canonical room-type multiset from the Qwen level3 schema (None if parse failed)."""
    if not parsed:
        return None
    items = []
    for fl in parsed.get("floors", []):
        items += fl.get("rooms", [])
    items += parsed.get("rooms", [])  # flat fallback
    out = Counter()
    for r in items:
        t = canon(r if isinstance(r, str)
                  else (r.get("type_en") or r.get("label") or r.get("label_original")))
        if t != "outdoor":
            out[t] += 1
    return out


def claude_rooms(data):
    """Canonical room-type multiset from the Claude monolithic schema."""
    out = Counter()
    for r in data.get("rooms", []):
        t = canon(r.get("type_en") or r.get("label", ""))
        if t != "outdoor":
            out[t] += 1
    return out


def prf(pred, gt):
    """Precision/recall/F1 of a predicted multiset against a GT multiset."""
    tp = sum((pred & gt).values())
    pr_n = sum(pred.values())
    gt_n = sum(gt.values())
    p = tp / pr_n if pr_n else 0.0
    r = tp / gt_n if gt_n else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def main():
    qwen_preds = json.load(open(HERE / "data" / "semantic_preds.json"))
    geom_dir = HERE / "data" / "claude_geom_preds"

    ids = sorted(set(qwen_preds) & {p.stem for p in geom_dir.glob("*.json")})
    per_plan = {}
    for sid in ids:
        gt = load_gt_sem(sid)
        qp = qwen_rooms(qwen_preds[sid].get(QWEN_LEVEL))
        cp = claude_rooms(json.load(open(geom_dir / f"{sid}.json")))
        per_plan[sid] = {
            "gt_rooms": sum(gt.values()),
            "qwen": dict(zip(("precision", "recall", "f1"), prf(qp, gt))) if qp is not None else None,
            "claude": dict(zip(("precision", "recall", "f1"), prf(cp, gt))),
        }

    # per-plan F1 arrays aligned by plan (only plans where Qwen parsed)
    paired_ids = [s for s in ids if per_plan[s]["qwen"] is not None]
    qwen_f1 = [per_plan[s]["qwen"]["f1"] for s in paired_ids]
    claude_f1 = [per_plan[s]["claude"]["f1"] for s in paired_ids]

    def mean(xs):
        return sum(xs) / len(xs) if xs else 0.0

    out = {
        "level": QWEN_LEVEL,
        "n_plans": len(ids),
        "n_paired": len(paired_ids),
        "paired_ids": paired_ids,
        "qwen_f1": qwen_f1,
        "claude_f1": claude_f1,
        "per_plan": per_plan,
        "means": {
            "qwen_f1": mean(qwen_f1),
            "claude_f1": mean(claude_f1),
            "qwen_precision": mean([per_plan[s]["qwen"]["precision"] for s in paired_ids]),
            "qwen_recall": mean([per_plan[s]["qwen"]["recall"] for s in paired_ids]),
            "claude_precision": mean([per_plan[s]["claude"]["precision"] for s in paired_ids]),
            "claude_recall": mean([per_plan[s]["claude"]["recall"] for s in paired_ids]),
        },
    }
    (HERE / "data" / "sem_headtohead.json").write_text(json.dumps(out, indent=2) + "\n")

    print(f"n_plans={out['n_plans']} n_paired={out['n_paired']}")
    print(f"Qwen   L3  mean per-plan F1 = {out['means']['qwen_f1']:.3f} "
          f"(P={out['means']['qwen_precision']:.3f} R={out['means']['qwen_recall']:.3f})")
    print(f"Claude 4.8 mean per-plan F1 = {out['means']['claude_f1']:.3f} "
          f"(P={out['means']['claude_precision']:.3f} R={out['means']['claude_recall']:.3f})")
    print(f"-> {HERE / 'sem_headtohead.json'}")


if __name__ == "__main__":
    main()
