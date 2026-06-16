# Benchmark Chapter: Image → Structured CAD

Consolidated evaluation of the floor-plan understanding pipeline. The thesis claim is a
**division of labour**: a dedicated segmentation model (Mask2Former) owns *geometry* (the
"where"), a vision-language model (Qwen3-VL-8B) owns *semantics* (the "what"), and the
hybrid of the two beats a monolithic frontier model (Claude Opus 4.8) that tries to do
both in one pass.

Every section labels its **dataset split** and **sample size (n)**. Two CubiCasa5k splits
appear and must not be conflated:

| split | file | used by |
|---|---|---|
| **test** | `experiments/mask2former_training/dataset/test.json` | Section 1 (training improvement) |
| **val** | `experiments/mask2former_training/dataset/val.json` | Section 2 (geometry monolithic), Section 4 (semantic ablation), Section 5 (semantic head-to-head) |

OOD plans (Section 3) come from FloorPlanCAD. All scripts referenced below are re-runnable
and their printed numbers reproduce the tables here.

---

## 1. Geometry: training improvement (CubiCasa **test**, n=50)

Does fine-tuning Mask2Former actually buy anything? Three models, identical 50 test plans,
pixel IoU vs RLE ground truth. `before` = same Swin-B architecture with COCO weights and
**zero** floor-plan training; `after` = our fine-tuned Mask2Former; `cnn` = the original
CubiCasa5k multi-task CNN baseline.

| model | IoU room | IoU wall | IoU door | IoU window | IoU railing |
|---|---|---|---|---|---|
| before (COCO, untrained) | 0.000 | 0.000 | 0.000 | 0.000 | 0.002 |
| **after (fine-tuned)** | **0.889** | **0.749** | **0.631** | **0.728** | **0.272** |
| cnn (CubiCasa baseline) | 0.772 | 0.711 | 0.551 | 0.686 | 0.252 |

Source: `before_after/results/RESULTS.md`.

The untrained model scores ~0 on every class (COCO categories do not transfer to
schematic line drawings). After fine-tuning it beats the established CubiCasa CNN on
**every** class. Training is justified.

---

## 2. Geometry: hybrid vs monolithic

Can a frontier VLM replace the segmentation model on pixel-precise geometry?

> **Split caveat:** the hybrid IoU comes from the CubiCasa test split (n=50) and the
> Claude IoU from the val split (n=50). Not the same 50 plans, but both are comparable
> single-family CubiCasa plans. The gap is large enough that the split difference doesn't
> change the conclusion.

| metric | Claude Opus 4.8 (val, n=50) | Hybrid pipeline (test, n=50) |
|---|---|---|
| IoU room | 0.672 ± 0.139 | 0.889 |
| IoU wall | 0.248 ± 0.102 | 0.749 |

Sources: `three_way/data/claude_geom_preds/RESULTS.md` (Claude, per-plan mean ± std via
`stats.py`); `before_after/results/RESULTS.md` (pipeline, `after`).

The gap is large and consistent: ~0.22 IoU on rooms and ~0.50 IoU on walls. Walls are the
clearest failure: Claude emits a handful of coarse rectangles (≈0.25 IoU) where the
segmentation model traces the actual wall skeleton (≈0.75). A VLM *estimates* polygons by
reasoning over the image; it does not perceive them pixel-precisely. **Geometry belongs to
the segmentation model**, and the gap is far too wide to be an artefact of the split
difference.

---

## 3. Generalization: out-of-distribution (FloorPlanCAD, n=3, qualitative)

How do the geometry models behave on a *completely different* drawing style (colored
Chinese CAD with dimensions and furniture, never seen in training)? FloorPlanCAD annotates
symbols on lines (not area polygons), so there is no comparable room-IoU ground truth; the
table reports **pixel coverage %** (how much each model paints), not accuracy. The real
signal is which model still finds structure.

| model | %room | %wall | %door | %window | %railing |
|---|---|---|---|---|---|
| before | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| **after** | **46.7** | **11.3** | **1.0** | 0.6 | 0.4 |
| cnn | 41.7 | 3.9 | 0.0 | 0.0 | 0.0 |

Source: `generalization/results/RESULTS.md`.

The fine-tuned model still recovers rooms (≈47%) and, crucially, keeps finding walls
(≈11%) where the CNN baseline collapses on walls (≈4%). Qualitative only (n=3), but the
fine-tuned model generalizes OOD better than the CNN baseline.

---

## 4. Semantics: Qwen prompt ablation (CubiCasa **val**, n=50)

Same model (Qwen3-VL-8B-Instruct), same GT (`model.svg` room types), same 50 val plans,
only the **prompt** changes. Micro-averaged P/R/F1 over the aggregate type multiset.

| prompt level | precision | recall | F1 |
|---|---|---|---|
| level1_open | 0.214 | 0.208 | 0.211 |
| level2_guided | 0.425 | 0.478 | 0.450 |
| **level3_strict** | 0.543 | 0.453 | **0.494** |
| level4_hybrid | 0.415 | 0.487 | 0.449 |

Source: `three_way/results/SEMANTIC_RESULTS.md`.

Two findings: (1) the Finnish glossary is the single biggest lever (level1→level2, +114%
F1), since room-type ID is largely an OCR + translation task; (2) injecting pipeline geometry
(level4) does **not** help semantics because abstract region letters don't map to visible labels.
**level3_strict** is the production prompt.

---

## 5. Semantics: monolithic vs hybrid (CubiCasa **val**, n=50, paired)

A clean head-to-head on the **identical 50 val plans**: Qwen3-VL-8B (`level3_strict`,
semantics only) vs Claude Opus 4.8 (monolithic, geometry + semantics in one pass). Both
scored with the same CANON normalization, `outdoor` dropped from both predictions and GT.
Per-plan F1 arrays feed a paired test.

| model | per-plan F1 (mean ± std) | precision | recall |
|---|---|---|---|
| Qwen3-VL-8B (L3) | 0.451 ± 0.224 | 0.478 | 0.457 |
| **Claude Opus 4.8** | **0.520 ± 0.160** | 0.489 | 0.582 |

Paired statistics on the per-plan F1 delta (Qwen − Claude), n=50:

- mean delta = **−0.070** (Claude higher)
- Wilcoxon signed-rank **p = 0.012 → significant** at α=0.05
- bootstrap 95% CI = **[−0.116, −0.028]** → **excludes 0**

Sources: `three_way/data/sem_headtohead.json` (per-plan), `three_way/data/stats.json` (tests; scipy
Wilcoxon + 10k-sample percentile bootstrap, seed 42).

**Honest reading:** on this paired test the frontier monolithic model is **modestly but
significantly better** on semantic F1 (≈0.07, driven mainly by higher recall; Claude finds
more rooms). This corrects an earlier claim (made on n=3 qualitatively in
`COMPARISON_RESULTS.md`) that the 8B "ties" the
frontier model. It does not tie, it loses by a small, significant margin on semantics.

The thesis argument survives and is more nuanced: the 8B is **within ~0.07 F1** of a
frontier model on semantics while being small, cheap, and runnable locally, an acceptable
trade for the semantic role. The decisive win for the hybrid is **geometry** (Section 2), not
semantics.

---

## 6. Error analysis: counts, full geometry, per-type (CubiCasa **val**, n=50)

Three cheap analyses on the existing predictions (no re-runs). Full tables:
`three_way/results/EXTRA_RESULTS.md`; raw: `three_way/data/extra_results.json`. Reproduce:
`python3 three_way/scripts/eval_extra.py`.

**6A. Room-count: hallucination vs omission.** Predicted #rooms vs GT, split by direction.

| model | MAE | mean signed | over (halluc.) | under (missed) | exact % |
|---|---|---|---|---|---|
| Qwen3-VL-8B (L3) | 3.68 | −1.72 | 0.98 | 2.70 | 14% |
| Claude Opus 4.8 | 2.60 | +1.20 | 1.90 | 0.70 | 14% |

This explains the Section 5 recall gap mechanically: **Qwen under-counts** (omits ~1.7 rooms/plan,
conservative), **Claude over-counts** (hallucinates ~1.2 rooms/plan). Opposite failure
modes; Claude's higher recall is bought with more spurious rooms.

**6B. Per-class IoU on monolithic Claude (completes Section 2).** Same val/test split caveat.

| class | Claude 4.8 (val) | pipeline (test, ref) |
|---|---|---|
| room | 0.672 ± 0.139 | 0.889 |
| wall | 0.248 ± 0.102 | 0.749 |
| door | 0.079 ± 0.088 | 0.631 |
| window | 0.147 ± 0.123 | 0.728 |

Claude's geometry is weak on **every** class, not just walls. Doors/windows (small targets)
collapse to ≈0.08–0.15 IoU. Reinforces Section 2: geometry is not a VLM job.

**6C. Per-type F1: where each model errs.** Aggregated over 50 plans (full table in
`EXTRA_RESULTS.md`). Highlights:

- Claude leads on most frequent types (bedroom 0.90 vs 0.77, bath 0.72 vs 0.55, study 0.80
  vs 0.22), consistent with its higher overall recall.
- **Claude fails `dining` entirely (F1 0.00 vs Qwen 0.51)**: it folds dining areas into
  living/hall, a systematic type confusion worth flagging.
- Both models score near-zero on the GT catch-all **`other`** (174 GT instances, recall
  ≈0.05): neither emits a generic "other" label, so this is largely a GT-vocabulary
  artefact (userdefined/undefined rooms) rather than a real perception failure, which is a caveat
  on the absolute F1 numbers in Sections 4/5.

---

## 7. Conclusion

| role | winner | evidence |
|---|---|---|
| Geometry (where) | **Mask2Former (hybrid)** | Section 2: IoU room 0.889 vs 0.672, wall 0.749 vs 0.248 (split caveat) |
| Semantics (what) | Claude 4.8 by ~0.07 F1 (significant); Qwen close | Section 5: 0.520 vs 0.451, p=0.012 |
| Training value | fine-tuned ≫ untrained, > CNN | Section 1: every class |
| OOD robustness | fine-tuned > CNN | Section 3: walls 11% vs 4% |
| Cost | **Hybrid ~6x cheaper** | $0.014 vs $0.088 per image (semantic pass) |

The monolithic frontier model **loses decisively on geometry** and **wins modestly on
semantics**. Because geometry is where the large, consistent gap lives, and because the
8B semantic model is cheap, local, and within a small margin, the hybrid design
(Mask2Former geometry + Qwen3-VL semantics) is the right architecture for a local,
single-user application. Each component is justified on the role it owns.

### Cost per image

Typical CubiCasa floor plan at benchmark resolution (~1400x1000 px):

| | Claude Opus 4.8 (API) | Qwen3-VL-8B (Modal A100) |
|---|---|---|
| Image tokens (input) | ~1,867 (w*h/750) | N/A (billed by GPU-second) |
| Prompt tokens (input) | ~800 | ~800 |
| Output tokens | ~3,000 (full JSON) | ~2,000 (semantics only) |
| **Cost per image** | **~$0.088** | **~$0.014** |

Pricing used: Claude Opus 4.8 at $5/MTok input, $25/MTok output. Qwen on Modal A100-80GB at $0.000463/s, ~30s per image.

At scale:

| volume | Claude Opus 4.8 | Hybrid (Qwen + Mask2Former) | savings |
|---|---|---|---|
| 50 plans (this benchmark) | $4.40 | $0.69 | 6x |
| 1,000 plans | $88 | $14 | 6x |
| 100,000 plans | **$8,800** | **$1,400** | 6x |

Mask2Former runs locally on CPU in ~2s per image (effectively free after the one-time training cost), while Claude would need to do geometry + semantics together in one expensive API call. The hybrid is both better at geometry and cheaper to run.

---

## Appendices (detail / raw)

- Section 1 per-plan IoU: `before_after/results/RESULTS.md` + overlays.
- Section 2 Claude per-plan IoU + F1: `three_way/data/claude_geom_preds/RESULTS.md` (+ `*.svg`).
- Section 3 OOD overlays: `generalization/results/`.
- Section 4 ablation detail + prompt descriptions: `three_way/results/SEMANTIC_RESULTS.md`.
- Section 5 per-plan arrays: `three_way/data/sem_headtohead.json`; tests: `three_way/data/stats.json`.
- Section 6 error analysis (counts / full per-class IoU / per-type F1): `three_way/results/EXTRA_RESULTS.md`,
  raw `three_way/data/extra_results.json`.

### Reproduce

```bash
cd benchmarks/three_way/scripts
python3 eval_sem_headtohead.py   # -> ../data/sem_headtohead.json (per-plan P/R/F1, both models)
python3 stats.py                 # -> ../data/stats.json (Wilcoxon + bootstrap; geometry descriptive)
python3 eval_extra.py            # -> ../results/EXTRA_RESULTS.md + ../data/extra_results.json (Section 6 A/B/C)
bash run_claude_geom_bench.sh    # monolithic geom (skip-existing) -> ../data/claude_geom_preds/RESULTS.md
```
