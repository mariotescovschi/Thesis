#!/usr/bin/env python3
"""
Prompt ablation eval: 4 prompt levels on Qwen3-VL-8B vs GT (model.svg).
Outputs SEMANTIC_RESULTS.md.
"""
import json
from pathlib import Path
from collections import Counter
from compare_eval import canon, load_gt_sem

HERE = Path(__file__).resolve().parent.parent
LEVELS = ["level1_open", "level2_guided", "level3_strict", "level4_hybrid"]
preds = json.load(open(HERE / "data" / "semantic_preds.json"))


def rooms_of(parsed):
    """Canonical room-type multiset from any of the 3 schemas (None if parse failed)."""
    if not parsed:
        return None
    items = []
    for fl in parsed.get("floors", []):
        items += fl.get("rooms", [])
    items += parsed.get("rooms", [])  # flat fallback
    out = Counter()
    for r in items:
        t = canon(r if isinstance(r, str) else (r.get("type_en") or r.get("label") or r.get("label_original")))
        if t != "outdoor":
            out[t] += 1
    return out


def prf(tp, pred, gt):
    p = tp / pred if pred else 0.0
    r = tp / gt if gt else 0.0
    return p, r, (2 * p * r / (p + r) if (p + r) else 0.0)


rows = []
for lvl in LEVELS:
    tp = pr = g = ok = 0
    for sid, rec in preds.items():
        gt = load_gt_sem(sid)
        g += sum(gt.values())
        pred = rooms_of(rec.get(lvl))
        if pred is None:
            continue
        ok += 1
        tp += sum((pred & gt).values()); pr += sum(pred.values())
    P, R, F = prf(tp, pr, g)
    rows.append((lvl, P, R, F, ok))
    print(f"{lvl:14} P={P:.3f} R={R:.3f} F1={F:.3f} (parse OK {ok}/{len(preds)})")

md = [f"# Eval semantic: ablation pe 3 niveluri de prompt (Qwen3-VL-8B zero-shot, n={len(preds)})\n",
      "Acelasi model, acelasi GT (`model.svg`); difera DOAR prompt-ul. Arata cat adauga fiecare "
      "nivel de ghidare. Potrivire pe multiset de tipuri canonice de camera (CANON din compare_eval.py).\n",
      "| nivel prompt | precision | recall | F1 | parse OK |", "|---|---|---|---|---|"]
md += [f"| {l} | {p:.3f} | {r:.3f} | **{f:.3f}** | {o}/{len(preds)} |" for l, p, r, f, o in rows]
(HERE / "results" / "SEMANTIC_RESULTS.md").write_text("\n".join(md) + "\n")
print(f"-> {HERE/'SEMANTIC_RESULTS.md'}")
