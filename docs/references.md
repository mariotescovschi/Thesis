# References & Resources

All studies, papers, articles, and tools relevant to the project.

## Papers — Floor Plan Understanding

| Paper | Date | What it does | URL |
|-------|------|-------------|-----|
| FloorplanVLM | Feb 2026 | VLM E2E, 92.5% IoU, SFT+GRPO, pixels-to-sequence | https://arxiv.org/abs/2602.xxxxx |
| FloorplanQA | 2025 | Benchmark: spatial reasoning Q&A on floor plans, 16K questions | https://arxiv.org/abs/2501.xxxxx |
| VLMs Can Parse Floor Plans | Sep 2024 | Tests GPT-4V zero-shot on floor plans | https://arxiv.org/abs/2409.xxxxx |
| DPSS (Dual-Pathway Symbol Spotter) | 2025 | Fusion of visual + CAD primitives, SOTA on FloorPlanCAD | — |
| LLM-Guided Agentic Parsing | Apr 2026 | Multi-agent pipeline → knowledge graph from plans | — |
| ASAMPS (SAM2 for architecture) | 2025 | SAM2 adapted for wall thickness + architectural symbols | — |

## Papers — LoRA & Fine-Tuning

| Paper | Date | Key Finding | URL |
|-------|------|-------------|-----|
| Learning Rate Matters: Vanilla LoRA Suffices | Feb 2026 | LR is most important; all variants perform same when tuned | https://arxiv.org/html/2602.04998v1 |
| QLoRA: Efficient Finetuning of Quantized LLMs | 2023 | 4-bit quantization + LoRA, minimal quality loss | https://github.com/artidoro/qlora |
| LoRA: Low-Rank Adaptation | 2022 | Original LoRA paper | https://arxiv.org/abs/2106.09685 |

## Papers — Spatial Reasoning & VLMs

| Paper | Date | Key Finding | URL |
|-------|------|-------------|-----|
| ADAPTVIS | 2025 | Training-free attention steering for spatial tasks, +50pp on VSR | — |
| GRAID-SFT | 2025 | Fine-tuning on geometric data fixes spatial reasoning in small VLMs | — |
| Visual Spatial Reasoning (VSR) | 2022 | Benchmark for spatial relation classification | — |
| SpatialBench | 2025 | 3D spatial reasoning benchmark for VLMs | — |

## Tutorials & Articles

| Title | Source | Relevance | URL |
|-------|--------|-----------|-----|
| Fine-Tuning Qwen3-VL 8B | DataCamp | Same model, same task type (image→structured) | https://www.datacamp.com/tutorial/fine-tuning-qwen3-vl-8b |
| LoRA Insights from Hundreds of Experiments | Lightning AI | Hyperparameter recommendations | https://lightning.ai/pages/community/lora-insights/ |
| Master LoRA and QLoRA (2026 guide) | letsdatascience.com | Complete practical guide | https://letsdatascience.com/blog/fine-tuning-llms-with-lora-and-qlora-complete-guide |
| How to Fine-Tune Qwen3-VL on Your Own Dataset | Datature | End-to-end guide | https://datature.io/blog/how-to-fine-tune-qwen3-vl-on-your-own-dataset |

## Datasets

| Dataset | Size | What it offers | URL |
|---------|------|---------------|-----|
| ResPlan | 17K | Residential plans + topological graph (JSON) | HuggingFace (TBD) |
| ArchCAD-400k | 413K chunks | Commercial/hospitals, 30 categories, auto-annotated | — |
| FloorPlanCAD | 15K | Vector SVG + raster, 30 categories | https://floorplancad.github.io/ |
| CubiCasa5k | 5K | 80+ categories, polygon annotations | https://github.com/CubiCasa/CubiCasa5k |
| FPBench-2K | 2K | Non-Manhattan layouts, VLM benchmark | — |
| FloorplanQA | 16K questions | Spatial reasoning Q&A | — |

## Tools

| Tool | What it does | URL |
|------|-------------|-----|
| ForgeCAD | Parametric CAD from JS code, CLI validate/render/export | https://github.com/nicholasgasior/forgecad |
| HuggingFace PEFT | LoRA/QLoRA implementation | https://github.com/huggingface/peft |
| TRL (Transformer RL) | SFTTrainer for VLM fine-tuning | https://github.com/huggingface/trl |
| Unsloth | 2x faster LoRA training | https://github.com/unslothai/unsloth |

## Models

| Model | Size | License | Role in project |
|-------|------|---------|-----------------|
| Qwen3-VL-32B | 32B dense | Apache 2.0 | Fine-tune target (main) |
| Qwen3-VL-7B | 7B dense | Apache 2.0 | Dev/iteration (fast) |
| InternVL3-7B | 7B | MIT | Fallback if Qwen fails |
| GLM-4.5V | 106B MoE | MIT | Zero-shot comparison |
| GPT-4V | — | Proprietary | Zero-shot comparison |
| Claude | — | Proprietary | Zero-shot comparison |
