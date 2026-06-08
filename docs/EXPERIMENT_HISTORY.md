# Experiment History

Chronological record of all training runs, infrastructure decisions, and pivot points.
For thesis reference (methodology chapter, cost analysis, lessons learned).

---

## Phase 1: VLM-Direct (ABANDONED)

Goal: fine-tune Qwen3-VL to output structured JSON with polygon coordinates directly from floor plan images.

### Runs

**Run 1: Qwen3-VL-32B, QLoRA 4-bit r=64, A100 80GB (Prime Intellect)**

Reached step 264/421 twice before OOM on the same problematic large image during backward pass. Saved checkpoint at step 200 and uploaded to HuggingFace. Decided not to continue because even with reduced image resolution (1280 → 800px), the same sample caused OOM both times, the 32B model was too heavy for a single A100, and inference was painfully slow (~10 tok/s in 4-bit).

**Run 2 (inference only): testing the checkpoint-200**

The model learned JSON syntax and room-type vocabulary correctly. However, the polygon coordinates were wrong: they didn't correspond to actual room positions in the image. The model understands *what* is in the image but not *where* precisely. Generation was too slow for practical use (~10-15 min per image at max tokens).

**Run 3: Qwen3-VL-8B, full bf16 r=128, H200 141GB (Nebius)**

Switched to 8B to iterate faster and cheaper. Loss went from 6.81 to 3.37 over 404/633 steps, token accuracy reached 53%. Stopped manually at step 404 because the loss plateau suggested diminishing returns and we wanted to test inference quality before burning more compute. Checkpoint-400 uploaded to HuggingFace. Inference with this checkpoint produced degenerate output (infinite repetition of "GRAND BALLROOM" with same coordinates), confirming the model hadn't learned EOS properly due to sequence truncation during training.

**Run 4: Qwen3-VL-8B retrain on Modal A100**

Full retrain from scratch with simplified output (rooms + walls only) and max_length=8192 so the model could learn EOS. Got to step 200 with loss dropping nicely (7.7 → 3.5), then OOM during evaluation on a large val sample. The checkpoint was on disk but the container died before upload, so it was lost. At this point we'd spent ~$50 on VLM training with no usable geometry output, and the pattern was clear: VLMs learn the format but not the spatial precision.

**SageMaker attempts: 8 jobs, all failed on infra**

Tried L40S 48GB on SageMaker. Never got past the setup phase. Problems: nvidia/cuda base images don't guarantee GPU detection, PyTorch/CUDA/transformers version triangles are brutal, and small files over S3 sync are unusably slow. Burned ~$60 on CodeBuild iterations and failed jobs without a single training step completing.

**StarVector side-test (A6000 48GB, Prime Intellect)**

Tested `starvector-8b-im2svg` hoping an image-to-SVG model might produce vector traces of floor plans. It's trained on SVG-Stack (icons, logos) and produced completely hallucinatory output (Chinese template text, empty groups, zero correlation with the input). Dead end confirmed in under 2 hours.

### Why we pivoted

After ~$100 and multiple runs across 3 platforms, the conclusion was consistent: VLMs achieve high token accuracy (~91.5%) and learn the JSON vocabulary, but they *estimate* polygon positions through reasoning rather than perceiving them at pixel level. The coordinates are always wrong. FloorplanVLM (Feb 2026) reports VLM end-to-end with high IoU, but their training loop (SFT + GRPO, massive data) would cost far more than our budget allows.

The decision: a hybrid pipeline where each component handles what it's good at. Mask2Former for geometry (pixel-precise masks), VLM only for semantics (room types, labels, adjacency).

### Phase 1 costs

| Platform | Spent | Notes |
|----------|-------|-------|
| Prime Intellect | ~$20 | Training + inference + StarVector |
| Modal | ~$20 | Training attempts + zero-shot tests |
| AWS SageMaker | ~$60 | 8 failed jobs (all infra, no training) |
| **Total** | **~$100** | Majority on failed runs and environment learning |

---

## Phase 2: Mask2Former Training

Goal: train a dedicated segmentation model for pixel-precise floor plan geometry.

### Setup

- Hardware: Prime Intellect, 1x A100 80GB
- Dataset: CubiCasa5k, 4200 train images, 253994 annotations, 5 classes (room, wall, door, window, railing)
- Architecture: Mask2Former + Swin-B backbone (pretrained ImageNet-22K)
- Config: batch 2, max_size 1600px, AdamW lr=1e-4, cosine warmup, 20K iterations
- VRAM usage: ~34GB / 80GB. Speed: ~1.4s/iter, total ~7.8h

### Environment issues solved

- gcc-12 missing (needed for MSDeformAttn compilation)
- detectron2 symbol mismatch (had to rebuild from source for torch 2.4)
- MSDeformAttn required manual compilation with CUDA_HOME set
- Custom MaskMapper needed because default trainer didn't handle bitmask format
- OOM at batch 4 / 2048px, settled on batch 2 / 1600px

### Result

Training completed. `model_final.pth` produced and runs inference locally on CPU.

IoU on CubiCasa test split (n=50): room 0.889, wall 0.749, door 0.631, window 0.728, railing 0.272. Beats the CubiCasa CNN baseline on every class.

---

## Phase 3: Benchmarks (summary)

Full tables in `benchmarks/RESULTS.md`. Key conclusions:

- **Geometry**: Mask2Former dominates. Room IoU 0.889 vs Claude Opus 4.8 monolithic 0.672. Walls: 0.749 vs 0.248. The VLM produces a handful of coarse rectangles.
- **Semantics**: Claude 4.8 wins modestly (F1 0.520 vs Qwen 0.451, p=0.012) but at 6x the cost per image ($0.088 vs $0.014).
- **OOD generalization**: fine-tuned M2F still finds structure on unseen drawing styles (FloorPlanCAD). CNN baseline collapses on walls.
- **Prompt ablation**: Finnish glossary is the single biggest lever for semantic accuracy (+114% F1). Room-type ID is mostly OCR + translation.
- **Thesis argument**: the hybrid wins on geometry decisively, loses on semantics marginally, and costs 6x less. Division of labour justified.

---

## Infrastructure Lessons

1. Always use vendor DLCs (SageMaker Deep Learning Containers, etc.) instead of raw nvidia/cuda images. Driver/CUDA/PyTorch combos break silently.
2. Pin dependency versions in production. Bleeding-edge git installs break between runs.
3. Tar large datasets before upload. `aws s3 sync` with thousands of small files takes forever.
4. Disable evaluation during training if GPU memory is tight. A single large eval sample can OOM and kill the container.
5. Upload checkpoints to HuggingFace immediately after each save. Cloud pods lose all data on termination.
6. TRL 1.4 multimodal requires ALL message content as list-of-dicts (not strings). This caused multiple silent failures.

---

## Artifacts on HuggingFace

- `mariotescovschi/qwen3vl-floorplan-lora` (32B, checkpoint-200, partial)
- `mariotescovschi/qwen3vl-8b-floorplan-lora` (8B, checkpoint-400, partial)

Both are from Phase 1 and not used in the final pipeline, but preserved for reproducibility.
