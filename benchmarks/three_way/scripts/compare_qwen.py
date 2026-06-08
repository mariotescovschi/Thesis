"""
Qwen3-VL-8B semantic predictions on Modal A100.
Reads floor plan images, outputs room types/adjacency/structure as JSON.
Run: modal run compare_qwen.py
"""
import modal, os, io, re, json

app = modal.App("qwen-compare")
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch", "torchvision", "accelerate", "Pillow", "qwen-vl-utils", "transformers==4.57.6",
)

DESKTOP = os.path.expanduser("~/Desktop/floorplan_comparison")
PLANS = ["plan_a", "plan_b", "plan_c"]

PROMPT = (
    "You are an expert architect analyzing a residential floor plan image. Room labels "
    "are Finnish abbreviations. Glossary: MH=bedroom, OH/AH=living room, "
    "K/KT/KEITTIO=kitchen, RUOKAILU=dining, KPH/PH/PESUH=bathroom, WC=toilet, "
    "ET=entry hall, AULA=hall/landing, S/SAUNA=sauna, PUKUH=changing room, "
    "VH/KHH=utility, TK/TEKN=technical, VAR/VARASTO=storage, AUTOTALLI=garage, "
    "PARVEKE=balcony, TERASSI=terrace, KELLARI=cellar, ALK/ALKOVI=alcove, "
    "KIRJ=library/study, K+R=kitchen+dining.\n\n"
    "Describe the SEMANTICS ONLY. Do NOT output pixel coordinates or polygons. "
    "Return STRICT JSON, no prose:\n"
    "{\n"
    '  "building_type": "...",\n'
    '  "floor_count": <int>,\n'
    '  "rooms": [{"label": "<as written>", "type_en": "...", "area_m2": <number or null>}],\n'
    '  "adjacency": [{"from": "<label>", "to": "<label>"}],\n'
    '  "vertical_circulation": "stairs|none|...",\n'
    '  "notes": "1-3 sentences describing the overall layout and how spaces relate"\n'
    "}\n"
    "Read the labels and m2-areas exactly as written. Return valid JSON only."
)


@app.function(image=image, gpu="A100", timeout=3600)
def run(samples: list[dict]):
    from transformers import AutoModelForImageTextToText, AutoProcessor
    from PIL import Image
    import torch

    model_id = "Qwen/Qwen3-VL-8B-Instruct"
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, dtype=torch.bfloat16, device_map="auto").eval()
    processor = AutoProcessor.from_pretrained(
        model_id, min_pixels=256 * 28 * 28, max_pixels=2048 * 28 * 28)

    out = {}
    for s in samples:
        img = Image.open(io.BytesIO(s["bytes"])).convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img}, {"type": "text", "text": PROMPT}]}]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt").to(model.device)
        with torch.no_grad():
            o = model.generate(**inputs, max_new_tokens=2048,
                               do_sample=False, repetition_penalty=1.05)
        out[s["id"]] = processor.decode(o[0][inputs["input_ids"].shape[-1]:],
                                        skip_special_tokens=True)
        print(f"done {s['id']}")
    return out


def _extract(text):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    s = (m.group(1) if m else text).strip()
    try:
        return json.loads(s)
    except Exception:
        return None


@app.local_entrypoint()
def main():
    payload = []
    for name in PLANS:
        with open(os.path.join(DESKTOP, f"{name}.png"), "rb") as f:
            payload.append({"id": name, "bytes": f.read()})
    res = run.remote(payload)
    for name in PLANS:
        parsed = _extract(res[name])
        with open(os.path.join(DESKTOP, f"{name}_qwen_semantic.json"), "w") as f:
            json.dump({"raw": res[name], "parsed": parsed}, f, indent=2, ensure_ascii=False)
        n = len(parsed.get("rooms", [])) if parsed else "PARSE_FAIL"
        print(f"{name}: rooms={n}")


@app.local_entrypoint()
def batch(n: int = 50):
    """Qwen semantic on N val images (those with GT model.svg). Run: modal run compare_qwen.py::batch --n 50"""
    import json
    from pathlib import Path
    val = json.load(open(Path(__file__).resolve().parent.parents[3]
                         / "experiments/mask2former_training/dataset/val.json"))
    cubi = Path.home() / "Downloads" / "cubicasa5k" / "high_quality_architectural"
    ids = []
    for i in val["images"]:
        fn = i["file_name"]
        if "high_quality_architectural/" in fn:
            sid = fn.split("high_quality_architectural/")[1].split("/")[0]
            if (cubi / sid / "model.svg").exists() and (cubi / sid / "F1_scaled.png").exists():
                ids.append(sid)
    ids = ids[:n]
    payload = [{"id": sid, "bytes": (cubi / sid / "F1_scaled.png").read_bytes()} for sid in ids]
    res = run.remote(payload)
    out = {sid: {"raw": res[sid], "parsed": _extract(res[sid])} for sid in ids}
    dst = Path(__file__).resolve().parent.parent / "data" / "semantic_preds.json"
    json.dump(out, open(dst, "w"), indent=2, ensure_ascii=False)
    ok = sum(1 for v in out.values() if v["parsed"])
    print(f"saved {dst} | {ok}/{len(ids)} parsed OK")
