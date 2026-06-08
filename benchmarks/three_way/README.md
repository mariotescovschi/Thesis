# three_way benchmark

Hybrid pipeline (Mask2Former + Qwen3-VL-8B) vs monolithic Claude Opus 4.8 on CubiCasa val (n=50).

## Structure

```
three_way/
├── README.md
├── scripts/                        # all runnable code
│   ├── eval_sem_headtohead.py      # paired semantic F1 -> data/sem_headtohead.json
│   ├── stats.py                    # Wilcoxon + bootstrap -> data/stats.json
│   ├── eval_extra.py               # error analysis -> data/extra_results.json + results/EXTRA_RESULTS.md
│   ├── compare_m2f.py              # run Mask2Former on val split
│   ├── compare_qwen.py             # Qwen3-VL-8B semantic preds -> data/semantic_preds.json
│   ├── compare_eval.py             # IoU eval for Claude geometry preds
│   ├── extract_graphs.py           # topology graphs from CubiCasa -> data/graphs.json
│   ├── spatial_test.py             # pilot prompt ablation (n=3, early version)
│   ├── semantic_eval.py            # simple semantic eval (superseded by eval_sem_headtohead)
│   ├── run_claude_geom_bench.sh    # run Claude geometry predictions (skip-existing)
│   └── run_claude_batch.sh         # batch runner helper
├── results/                        # markdown write-ups (referenced by ../RESULTS.md)
│   ├── SEMANTIC_RESULTS.md         # prompt ablation detail (Section 4)
│   ├── EXTRA_RESULTS.md            # error analysis tables (Section 6)
│   └── COMPARISON_PROMPT.md        # the geometry prompt sent to Claude
└── data/                           # raw JSON + prediction files
    ├── sem_headtohead.json         # per-plan P/R/F1 (both models)
    ├── stats.json                  # Wilcoxon p-value + bootstrap CI
    ├── extra_results.json          # room counts, per-class IoU, per-type F1
    ├── semantic_preds.json         # Qwen predictions (all 50 val plans, all levels)
    ├── graphs.json                 # topology graphs from GT
    ├── claude_geom_preds/          # 50 Claude predictions (JSON + SVG overlays + RESULTS.md)
    ├── claude_geom_input/          # 50 PNG inputs (resized max 1400px)
    ├── vlm_pilot_tests/            # n=3 pilot test output
    └── claude_preds_opus46_archive/  # archived 4.6 run (provenance only)
```

## Reproduce

```bash
cd benchmarks/three_way/scripts
python3 eval_sem_headtohead.py   # -> ../data/sem_headtohead.json
python3 stats.py                 # -> ../data/stats.json
python3 eval_extra.py            # -> ../data/extra_results.json + ../results/EXTRA_RESULTS.md
bash run_claude_geom_bench.sh    # -> ../data/claude_geom_preds/RESULTS.md
```
