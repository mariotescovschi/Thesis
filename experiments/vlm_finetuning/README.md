# VLM Fine-tuning Experiments (Archived)

Attempted direct VLM-based floor plan vectorization: predicting structured JSON coordinates from images.

## What was tried

### 1. QLoRA Fine-tuning (Qwen3-VL-8B)
- 4-bit NF4 quantization, LoRA r=64, 5 epochs on CubiCasa5k
- Training data: SVG annotations converted to JSON (rooms with polygon coordinates)
- Result: loss=0.25, token accuracy=91.5%
- Problem: model learned JSON syntax and room type vocabulary, but geometry was wrong (coordinates don't match actual room positions)

### 2. Zero-shot VLM (Qwen3-VL, GPT-4V, Claude)
- Excellent semantic understanding (room names, adjacency, building type)
- Cannot produce precise pixel coordinates
- Useful for classification, not geometry

### 3. CubiCasa5k CNN baseline (pretrained)
- Works in-distribution on CubiCasa test set
- Fails completely OOD on hotel floor plans (everything classified as Background)

## Conclusion

VLMs cannot reliably produce pixel-precise geometry from images. They understand *what* is in the image but not *where* precisely. This motivated the hybrid pipeline:
- Mask2Former for precise masks (geometry)
- VLM for semantic labeling (classification)

## Config (for reference, code deleted)

- Model: Qwen3-VL-32B (r=64) and Qwen3-VL-8B (r=128)
- QLoRA: 4-bit NF4, double-quant, bf16 compute
- LoRA: alpha = 2xr, dropout 0.05, target = all proj layers (q,k,v,o,gate,up,down)
- Training: lr 2e-4, cosine, warmup 3-5%, batch 1 x grad_accum 8-16

## Related files (elsewhere in project)

- `docs/EXPERIMENT_HISTORY.md` - full run-by-run history with costs and decisions
- `benchmarks/three_way/` - the 50-plan comparison (Mask2Former vs VLM zero-shot vs Claude monolithic)
