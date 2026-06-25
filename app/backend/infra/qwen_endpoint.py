"""Modal web endpoint for Qwen3-VL-8B semantic analysis.

Deploy:  modal deploy app/backend/qwen_endpoint.py
Test:    curl -X POST <url> -H "Content-Type: application/json" -d '{"image":"<base64>"}'
"""
import modal

app = modal.App("qwen-floorplan-semantics")
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch", "torchvision", "accelerate", "Pillow", "qwen-vl-utils",
    "transformers==4.57.6", "fastapi[standard]",
)

PROMPT = (
    "You are an expert architect analyzing a residential floor plan image. Room labels "
    "are Finnish abbreviations. Glossary: MH=bedroom, OH/AH=living room, "
    "K/KT/KEITTIO=kitchen, RUOKAILU=dining, KPH/PH/PESUH=bathroom, WC=toilet, "
    "ET=entry hall, AULA=hall/landing, S/SAUNA=sauna, PUKUH=changing room, "
    "VH/KHH=utility, TK/TEKN=technical, VAR/VARASTO=storage, AUTOTALLI=garage, "
    "PARVEKE=balcony, TERASSI=terrace, KELLARI=cellar, ALK/ALKOVI=alcove, "
    "KIRJ=library/study, K+R=kitchen+dining.\n\n"
    "Set \"type_en\" to EXACTLY ONE value from this controlled vocabulary, picking the "
    "closest match: bedroom, kitchen, living, dining, bathroom, hall, sauna, utility, "
    "technical, storage, garage, balcony, office. If nothing fits, use \"other\". "
    "Use lowercase, exactly as listed.\n\n"
    "Describe the SEMANTICS ONLY. Do NOT output pixel coordinates or polygons. "
    "Return STRICT JSON, no prose:\n"
    "{\n"
    '  "building_type": "...",\n'
    '  "floor_count": <int>,\n'
    '  "rooms": [{"label": "<as written>", "type_en": "<controlled vocabulary>", "area_m2": <number or null>}],\n'
    '  "adjacency": [{"from": "<label>", "to": "<label>"}],\n'
    '  "vertical_circulation": "stairs|none|...",\n'
    '  "notes": "2-4 sentences: overall layout character, open-plan areas (rooms sharing doors or lacking separating walls), natural light level (many windows = bright/luminous), connectivity (rooms reachable from a single hub), flow between spaces"\n'
    "}\n"
    "Read the labels and m2-areas exactly as written. Return valid JSON only."
)


@app.cls(image=image, gpu="A100", scaledown_window=120)
class Model:
    @modal.enter()
    def load(self):
        from transformers import AutoModelForImageTextToText, AutoProcessor
        import torch

        model_id = "Qwen/Qwen3-VL-8B-Instruct"
        self.model = AutoModelForImageTextToText.from_pretrained(
            model_id, dtype=torch.bfloat16, device_map="auto"
        ).eval()
        self.processor = AutoProcessor.from_pretrained(
            model_id, min_pixels=256 * 28 * 28, max_pixels=2048 * 28 * 28
        )

    @modal.fastapi_endpoint(method="POST")
    def analyze(self, request: dict):
        import base64, io, json, re
        from PIL import Image
        import torch

        img = Image.open(io.BytesIO(base64.b64decode(request["image"]))).convert("RGB")
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img}, {"type": "text", "text": PROMPT}
        ]}]
        inputs = self.processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt"
        ).to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs, max_new_tokens=2048, do_sample=False, repetition_penalty=1.05
            )
        raw = self.processor.decode(
            out[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True
        )
        # Extract JSON from possible markdown fences
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        text = (m.group(1) if m else raw).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": raw, "error": "parse_failed"}
