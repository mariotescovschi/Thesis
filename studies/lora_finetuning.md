# LoRA Fine-Tuning: Research & Best Practices

## Key Papers

### 1. "Learning Rate Matters: Vanilla LoRA May Suffice" (Feb 2026, ICML)
- **URL:** https://arxiv.org/html/2602.04998v1
- **Finding:** All LoRA variants (PiSSA, MiLoRA, DoRA, Init[AB]) achieve similar peak performance (within 1-2%) when learning rate is properly tuned
- **Critical:** Learning rate is THE most important hyperparameter. More important than rank, batch size, or LoRA variant choice.
- **Tested on:** Qwen3-0.6B, Gemma-3-1B, Llama-2-7B
- **Recommendation:** Use vanilla LoRA with proper LR tuning. No need for fancy variants.
- **LR search range:** 1e-5 to 1e-3 (log scale, 4 values per order of magnitude)
- **Alpha:** Set alpha = r (scaling factor γ=1) works well

### 2. "Finetuning LLMs with LoRA and QLoRA: Insights from Hundreds of Experiments" (Lightning AI, Sebastian Raschka)
- **URL:** https://lightning.ai/pages/community/lora-insights/
- **Best config:** r=256, alpha=512 (alpha = 2x rank) on Llama-2-7B
- **Key findings:**
  - QLoRA saves ~6GB VRAM with ~30% slower training
  - Cosine annealing scheduler helps
  - AdamW vs SGD: negligible difference for LoRA
  - Multiple epochs can HURT — 1 epoch often sufficient
  - Enable LoRA on ALL layers (q,k,v,o,gate,up,down) for best results
  - r=8 default is too small
  - Very large r (512+) didn't converge

### 3. "Fine-Tuning Qwen3-VL 8B: A Step-by-Step Guide" (DataCamp, Jan 2026)
- **URL:** https://www.datacamp.com/tutorial/fine-tuning-qwen3-vl-8b
- **Task:** Electronic schematic diagrams → component extraction
- **Setup:** RunPod A100 80GB, transformers 5.0.0rc1 + trl + peft + flash-attn
- **Config used:** r=16, alpha=32, lr=1e-4, 1 epoch, batch 2 + grad_accum 4
- **Result:** Clear improvement over zero-shot. Model stopped hallucinating.
- **Relevant because:** Same model family (Qwen3-VL), same task type (image → structured output)

## Hyperparameter Reference Table

| Parameter | Safe Default | Optimal Range | Notes |
|-----------|-------------|---------------|-------|
| rank (r) | 64 | 16-256 | Higher = more expressive, more VRAM |
| alpha | 2 * r | r to 2r | Rule of thumb confirmed by multiple studies |
| learning_rate | 2e-4 | 5e-5 to 5e-4 | MOST IMPORTANT. Sweep this first. |
| dropout | 0.05 | 0-0.1 | Can skip for small datasets |
| epochs | 1 | 1-3 | More can degrade performance |
| batch_size (effective) | 16 | 8-128 | Less critical than LR |
| warmup | 3% of steps | 3-10% | Cosine scheduler recommended |
| target_modules | all linear | q,k,v,o,gate,up,down | All layers > just attention |
| weight_decay | 0.01 | 0-0.1 | Standard |
| max_grad_norm | 1.0 | 0.5-2.0 | Stability |

## VRAM Estimates

| Model | QLoRA 4-bit Training (r=64) | Hardware Needed |
|-------|----------------------------|-----------------|
| Qwen3-VL-2B | ~12GB | RTX 3090 / 4070 |
| Qwen3-VL-7B | ~24GB | RTX 4090 / A100 40GB |
| Qwen3-VL-32B | ~48-60GB | A100 80GB |

## For Our Project (Qwen3-VL-32B + ResPlan 17K)

**Recommended starting config:**
```
r=64, alpha=128, lr=2e-4, 1 epoch, cosine scheduler
QLoRA 4-bit NF4, flash attention 2, gradient checkpointing
All linear layers, batch 2 + grad_accum 8 (effective 16)
A100 80GB, estimated ~40-60h training, ~100-150€
```

**LR sweep plan:** 5e-5, 1e-4, 2e-4, 5e-4 (pick best on validation set)
