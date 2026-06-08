# Semantic Evaluation — Qwen3-VL-8B Zero-Shot Ablation (n=50 CubiCasa val plans)

## Setup

Same model (Qwen3-VL-8B-Instruct), same GT (room types from `model.svg`), same 50 validation plans.
Only the **prompt** changes. Measures how much guidance improves room-type identification.

GT comparison: multiset matching on canonical room types (CANON mapping normalizes both
Qwen output and GT labels to a shared vocabulary: bedroom, living, kitchen, bath, etc.)

## Results

| prompt level | precision | recall | F1 | parse OK |
|---|---|---|---|---|
| level1_open | 0.214 | 0.208 | **0.211** | 50/50 |
| level2_guided | 0.425 | 0.478 | **0.450** | 48/50 |
| **level3_strict** | **0.543** | **0.453** | **0.494** | 50/50 |
| level4_hybrid | 0.415 | 0.487 | **0.449** | 50/50 |

**Winner: level3_strict (F1=0.494)**

## Prompt Descriptions

- **level1_open**: No context. "Analyze this floor plan, return JSON." Baseline — does the model understand floor plans at all?
- **level2_guided**: Finnish glossary (MH=bedroom, KPH=bathroom...) + hint that multiple storeys are drawn side by side. Tests: how much does domain context help?
- **level3_strict**: Glossary + exact JSON schema with floors, room types, positions, vertical circulation, adjacency graph. Tests: does forcing structure improve accuracy?
- **level4_hybrid**: Everything from level3 + injected output from our Mask2Former pipeline (detected rooms with areas + positions on a 3×3 grid + door-based adjacency graph). Tests: does pipeline geometry help the VLM on semantics?

## Key Findings

1. **Glossary is the single biggest factor** (level1→level2: +114% F1). Without Finnish abbreviation translations, Qwen can't read labels like MH, KPH, OH.
2. **Strict schema adds precision** (level2→level3: P jumps from 0.43 to 0.54). Forcing exact output format reduces hallucinated/spurious room types.
3. **Pipeline geometry does NOT help on room-type identification** (level4 ≈ level2). The Mask2Former graph (rooms + areas + adjacency) gives abstract letters (A, B, C) that Qwen cannot reliably map to visible labels. Room-type identification is fundamentally an OCR+translation task, not a spatial reasoning task.
4. **Pipeline geometry DOES help on geometry** (separate benchmark: IoU 0.89 vs Claude's 0.63). Each component wins at its own role — the thesis argument holds.

## Decision

**Use level3_strict** as the production prompt for the hybrid pipeline's semantic component.
It achieves the best F1 on room types while also producing adjacency graphs and floor structure
that the pipeline can use downstream.

## Experiments Chronology

1. Ran all 4 prompts on 50 val plans (Qwen3-VL-8B on Modal A100, ~65 min).
2. Initial results: level3=0.400, level4=0.374. Level4 underperformed — investigated.
3. Improved level4: added room positions (centroid → 3×3 grid label) + Finnish glossary. Re-ran level4 on all 50. Result: 0.373 → no improvement.
4. Analyzed per-type errors: discovered CANON mapping was too narrow (137 GT "other" rooms, 26 "draughtlobby", 33 "userdefined" had zero matches because Qwen used different synonyms).
5. Extended CANON mapping (added: technical closet→technical, entrance hall→entry, draughtlobby→entry, utility_room→utility, living_room→living, cellar→storage, changing room→sauna, etc.). Re-scored without re-running inference.
6. Final results: level3 jumped from 0.400 to **0.494** (+24%). Trend unchanged, level3 remains best.

## Claude vs Qwen3-VL-8B — Head-to-Head → moved to consolidated chapter

> **Archived / superseded.** The original head-to-head here used **Claude Opus 4.6**
> (semantic-only) and a micro-averaged F1, reporting a statistical tie (ΔF1 ≈ 0.011).
> That 4.6 run is now archived (`claude_preds_opus46_archive/`) and replaced by the
> **Claude Opus 4.8** monolithic run on the identical 50 val plans, scored with a
> **per-plan paired test**.
>
> **Updated result (see `../RESULTS.md` §5 and `stats.json`):** per-plan F1 Qwen
> 0.451 ± 0.224 vs Claude 4.8 0.520 ± 0.160; paired Wilcoxon **p = 0.012 (significant)**,
> bootstrap 95% CI [−0.116, −0.028] (excludes 0). The 8B does **not** tie the frontier
> model — it loses by a small but significant ~0.07 F1, mostly on recall. The thesis still
> holds: the 8B is close, cheap, and local, and the decisive hybrid win is on **geometry**,
> not semantics.
>
> Reproduce: `python3 eval_sem_headtohead.py && python3 stats.py`.
