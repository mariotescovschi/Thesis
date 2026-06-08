# Extra Benchmarks (A, B, C) — CubiCasa val, n=50

Reuses existing predictions (Qwen L3 + Claude Opus 4.8 monolithic). No re-runs.
Reproduce: `python3 eval_extra.py`.

## A. Room-count accuracy

Predicted number of rooms vs GT, split into over-prediction (hallucinated) and omission (missed). MAE = mean absolute count error.

| model | MAE | mean signed | mean over (halluc.) | mean under (missed) | exact-match % |
|---|---|---|---|---|---|
| Qwen3-VL-8B (L3) | 3.68 | -1.72 | 0.98 | 2.70 | 14% |
| Claude Opus 4.8 | 2.60 | +1.20 | 1.90 | 0.70 | 14% |

A positive *mean signed* means the model emits more rooms than exist (Claude's higher recall in §5 comes with more hallucinated rooms).

## B. Per-class IoU — monolithic Claude (completes §2)

> Split caveat: Claude on **val** (n=50); pipeline reference on **test** (n=50). Not identical plans — descriptive only.

| class | Claude 4.8 (val) | Hybrid pipeline (test, ref) |
|---|---|---|
| room | 0.672 ± 0.139 | 0.889 |
| wall | 0.248 ± 0.102 | 0.749 |
| door | 0.079 ± 0.088 | 0.631 |
| window | 0.147 ± 0.123 | 0.728 |
| railing | n/a (Claude emits none) | 0.272 |

Claude's geometry is weak across **all** classes, not just walls — doors/windows are tiny targets it cannot place pixel-precisely.

## C. Per-type F1 — where each model errs (by room type)

Aggregated true/false positives/negatives per canonical room type across 50 plans, sorted by GT frequency. Shows *which* types each model confuses.

### Qwen3-VL-8B (L3)

| type | GT | F1 | precision | recall |
|---|---|---|---|---|
| other | 174 | 0.098 | 1.000 | 0.052 |
| bedroom | 107 | 0.765 | 0.921 | 0.654 |
| bath | 51 | 0.545 | 0.649 | 0.471 |
| living | 42 | 0.824 | 0.814 | 0.833 |
| kitchen | 38 | 0.816 | 0.816 | 0.816 |
| entry | 34 | 0.694 | 0.658 | 0.735 |
| storage | 23 | 0.750 | 0.720 | 0.783 |
| dining | 14 | 0.514 | 0.429 | 0.643 |
| technical | 10 | 0.316 | 0.214 | 0.600 |
| garage | 10 | 0.333 | 0.375 | 0.300 |
| study | 8 | 0.222 | 1.000 | 0.125 |
| alcove | 3 | 0.571 | 0.500 | 0.667 |
| hall | 2 | 0.222 | 0.125 | 1.000 |
| elevated | 2 | 0.000 | 0.000 | 0.000 |
| recreationroom | 1 | 0.000 | 0.000 | 0.000 |

### Claude Opus 4.8

| type | GT | F1 | precision | recall |
|---|---|---|---|---|
| other | 174 | 0.045 | 1.000 | 0.023 |
| bedroom | 107 | 0.898 | 0.856 | 0.944 |
| bath | 51 | 0.721 | 0.667 | 0.784 |
| living | 42 | 0.866 | 0.764 | 1.000 |
| kitchen | 38 | 0.814 | 0.729 | 0.921 |
| entry | 34 | 0.571 | 0.512 | 0.647 |
| storage | 23 | 0.807 | 0.676 | 1.000 |
| dining | 14 | 0.000 | 0.000 | 0.000 |
| technical | 10 | 0.435 | 0.278 | 1.000 |
| garage | 10 | 0.706 | 0.857 | 0.600 |
| study | 8 | 0.800 | 0.857 | 0.750 |
| alcove | 3 | 0.800 | 1.000 | 0.667 |
| hall | 2 | 0.211 | 0.118 | 1.000 |
| elevated | 2 | 0.000 | 0.000 | 0.000 |
| recreationroom | 1 | 0.000 | 0.000 | 0.000 |

