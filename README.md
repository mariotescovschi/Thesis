# Image → Structured CAD

A pipeline that takes floor plan images and produces structured CAD output through spatial understanding — not just segmentation, but full comprehension of elements, dimensions, and spatial relationships.

## Approach

Fine-tune **Qwen3-VL-32B** (QLoRA 4-bit) on the ResPlan dataset (17K floor plans with topological graphs) to generate structured JSON directly from images. The JSON is then converted to executable ForgeCAD code for validation and visualization.

Benchmark against generalist VLMs (GPT-4V, Claude, GLM-4.5V) used zero-shot to demonstrate the value of domain-specific fine-tuning on spatial understanding tasks.

## Pipeline

```
Image (floor plan) → Qwen3-VL fine-tuned → Structured JSON → ForgeCAD .forge.js → Validate & Render
```

## Current Status

**Phase 3** — Training in progress. Qwen3-VL-32B-Instruct fine-tuning running on Prime Intellect (1x A100 80GB). ~8h run, 421 steps, 3361 training samples from CubiCasa5k.

## Project Structure

```
training/
├── config.json              # Hyperparameters (QLoRA, LoRA, training)
├── requirements.txt         # Pinned dependencies (working versions)
├── prepare_data.py          # CubiCasa5k SVG → Qwen3-VL chat format
├── train.py                 # Main training script (QLoRA + SFTTrainer)
├── checkpoint.py            # Upload/download checkpoints to HuggingFace Hub
├── modal_train.py           # Modal.com serverless deployment
├── visualize.py             # Generate HTML training report
├── training_explained.html  # Full explainer (open in browser)
└── TRAINING_LOG.md          # Run log with all issues & fixes

studies/
├── papers/                  # 9 reference papers (LoRA, QLoRA, Qwen2-VL, SAM2, etc.)
└── lora_finetuning.md       # LoRA research summary

docs/
└── references.md            # All papers, tools, datasets index
```

## Training Strategy

Split training across platforms to use available credits:
1. **Prime Intellect** ($44 credits) — 1x A100 80GB @ $1.5/h
2. **Modal** ($30 credits) — 1x A100 80GB @ $2.5/h

Checkpoints saved to HuggingFace Hub between runs for seamless resume.

## Benchmarks

Round-trip fidelity: CAD ground truth → render as image → our pipeline → CAD output → compare.

Models compared:
- **Ours**: Qwen3-VL-32B + QLoRA (fine-tuned on ResPlan)
- GPT-4V / Claude (zero-shot)
- GLM-4.5V (zero-shot)
- SAM2 + OpenCV baseline (modular)

Metrics: IoU (walls), Chamfer Distance, Graph Edit Distance (topology), SSIG.

## Stack

- **Model**: Qwen3-VL-32B, QLoRA 4-bit NF4, LoRA r=64
- **Training data**: CubiCasa5k (5K), eval on FPBench-2K
- **Validation**: ForgeCAD CLI
- **Training**: HuggingFace Transformers + PEFT + TRL
- **Compute**: Prime Intellect + Modal (A100 80GB)
