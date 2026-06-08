# Archived — Claude Opus 4.6 semantic-only predictions (n=50)

These are the **superseded** Claude Opus 4.6 predictions from the original semantic
head-to-head (room types only, no geometry). They are kept for provenance but are **not**
part of the consolidated benchmark.

**Why archived:** the 4.6 semantic-only run was replaced by the Claude Opus 4.8
*monolithic* run (`../claude_geom_preds/`), which produces geometry (polygons) **and**
semantics (room types) in one pass. The consolidated benchmark (`../../RESULTS.md`) uses
only the 4.8 model so the geometry and semantic head-to-head come from the same model and
the same run.

- Original 4.6 semantic head-to-head: F1 ≈ 0.495 (micro, n=50), reported in an earlier
  draft of `../SEMANTIC_RESULTS.md`.
- Current head-to-head uses 4.8 (`sem_headtohead.json`): Qwen L3 vs Claude 4.8 on the
  identical 50 val plans, per-plan F1 with a paired significance test (`stats.py`).

Raw files are preserved here; nothing was deleted.
