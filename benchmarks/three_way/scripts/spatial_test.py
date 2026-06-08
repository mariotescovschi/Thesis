"""
VLM spatial-understanding test on Qwen3-VL-8B (zero-shot, Modal A100).

Runs 3 prompt levels on multi-floor CubiCasa floor plans to probe how much
the model understands on its own vs. with guidance vs. with a strict schema.

  Level 1 (open)    : no context, free-form JSON. Does it find the floors itself?
  Level 2 (guided)  : we say it's a Finnish single-family house with several
                      storeys side-by-side + a Finnish glossary.
  Level 3 (strict)  : exact schema incl. vertical circulation + adjacency graph.

Output (local): vlm_tests/<sample>/{F1_scaled.png, level1_open.json,
                level2_guided.json, level3_strict.json}

Run:  modal run spatial_test.py
"""
import modal, os, io, re, json, shutil

app = modal.App("qwen-spatial-test")

image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "torch", "torchvision", "accelerate", "Pillow",
    "qwen-vl-utils", "transformers==4.57.6",
)

# ---- chosen multi-floor test samples (CubiCasa test split) ----
CUBI = "/Users/mariotescovschi/Downloads/cubicasa5k/high_quality_architectural"
SAMPLES = ["9223", "2085", "5135"]

GLOSSARY = (
    "MH=bedroom, OH=living room, K/KEITTIO=kitchen, RUOKAILUTILA/RUOKATILA=dining, "
    "KPH/PESUH=bathroom, WC=toilet, ET=entry hall, AULA=hall/landing, S/SAUNA=sauna, "
    "PUKUH=changing room, VH/KHH=utility room, TK=technical closet, "
    "VARASTO/VARAS=storage, AUTOTALLI=garage, PARVEKE=balcony, TERASSI=terrace, "
    "KELLARI=cellar, KATTILAHUONE=boiler room, TAKKAHUONE=fireplace room, "
    "VESIVARAAJA=water heater, ALKOVI=alcove, HALLI=hall. "
    "Floor labels: KELLARIKERROS=basement floor, (I/II) KERROS / KRS=storey, "
    "VINTTIKERROS=attic floor, POHJA=plan."
)

PROMPTS = {
    "level1_open": (
        "You are given a floor plan drawing. With no extra context, analyze it "
        "and return ONLY a JSON object:\n"
        '{"building_type": "...", "num_floors": <int>, '
        '"floors": [{"floor_label": "...", "rooms": ["..."]}], '
        '"observations": ["..."]}\n'
        "Return valid JSON only, no prose."
    ),
    "level2_guided": (
        "This drawing is a single-family RESIDENTIAL house. The SAME sheet contains "
        "MULTIPLE FLOOR LEVELS drawn side by side \u2014 each separate sub-drawing is "
        "one storey of the same house. Room labels are Finnish abbreviations.\n"
        f"Finnish glossary: {GLOSSARY}\n\n"
        "Identify each storey and its rooms. Return ONLY JSON:\n"
        '{"building_type": "...", "num_floors": <int>, '
        '"floors": [{"floor_label_original": "...", "floor_role": '
        '"basement|ground|upper|attic", "rooms": [{"label_original": "...", '
        '"type_en": "..."}]}], "notes": ["..."]}\n'
        "Return valid JSON only, no prose."
    ),
    "level3_strict": (
        "This is one drawing sheet of a single-family Finnish house showing several "
        "storeys side by side. Labels are Finnish abbreviations.\n"
        f"Finnish glossary: {GLOSSARY}\n\n"
        "Extract a STRICT structured representation. For every storey list its rooms "
        "with a coarse relative position. Identify vertical circulation (staircases "
        "that connect storeys). For the main/ground storey give a room adjacency list "
        "(which rooms are directly connected by a door or opening). Return ONLY JSON "
        "matching exactly:\n"
        "{\n"
        '  "building_type": "single_family_house",\n'
        '  "floors": [{"level_index": <int, 0=lowest>, "floor_label_original": "...",\n'
        '    "floor_role": "basement|ground|upper|attic",\n'
        '    "rooms": [{"label": "...", "type_en": "...", '
        '"position": "top-left|top|top-right|left|center|right|bottom-left|bottom|bottom-right"}]}],\n'
        '  "vertical_connections": [{"via": "staircase", "connects_levels": [<int>, <int>]}],\n'
        '  "ground_floor_adjacency": [{"from": "...", "to": "...", "via": "door|opening"}]\n'
        "}\n"
        "Return valid JSON only, no prose."
    ),
}

# level4: glossary (level2) + strict schema (level3) + pipeline-extracted geometry as context
LEVEL4_TEMPLATE = (
    "This is one drawing sheet of a single-family Finnish house showing several "
    "storeys side by side. Labels are Finnish abbreviations.\n"
    f"Finnish glossary: {GLOSSARY}\n\n"
    "An automated segmentation pipeline has already analyzed this floor plan and "
    "detected the following geometric structure:\n\n"
    "{graph_context}\n\n"
    "Using BOTH the image AND the detected structure above:\n"
    "1. Match each detected room (A, B, C...) to the label visible in the image at that position.\n"
    "2. Identify room types using the glossary.\n"
    "3. Confirm or correct the detected connections.\n"
    "4. Identify floors and vertical circulation.\n\n"
    "Return ONLY JSON matching exactly:\n"
    "{{\n"
    '  "building_type": "single_family_house",\n'
    '  "floors": [{{"level_index": <int, 0=lowest>, "floor_label_original": "...",\n'
    '    "floor_role": "basement|ground|upper|attic",\n'
    '    "rooms": [{{"label": "...", "type_en": "...", "detected_id": "<A|B|C|...or null>"}}]}}],\n'
    '  "vertical_connections": [{{"via": "staircase", "connects_levels": [<int>, <int>]}}],\n'
    '  "ground_floor_adjacency": [{{"from": "...", "to": "...", "via": "door|opening"}}]\n'
    "}}\n"
    "Return valid JSON only, no prose."
)


@app.function(image=image, gpu="A100", timeout=6000)
def run_all(samples: list[dict]):
    from transformers import AutoModelForImageTextToText, AutoProcessor
    from PIL import Image
    import torch

    model_id = "Qwen/Qwen3-VL-8B-Instruct"
    model = AutoModelForImageTextToText.from_pretrained(
        model_id, dtype=torch.bfloat16, device_map="auto"
    ).eval()
    processor = AutoProcessor.from_pretrained(
        model_id, min_pixels=256 * 28 * 28, max_pixels=3072 * 28 * 28
    )

    def generate(img, prompt):
        messages = [{"role": "user", "content": [
            {"type": "image", "image": img},
            {"type": "text", "text": prompt},
        ]}]
        inputs = processor.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_dict=True, return_tensors="pt",
        ).to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=4096,
                                 do_sample=False, repetition_penalty=1.05)
        return processor.decode(out[0][inputs["input_ids"].shape[-1]:],
                                skip_special_tokens=True)

    results = {}
    for s in samples:
        img = Image.open(io.BytesIO(s["bytes"])).convert("RGB")
        if s.get("only_level4"):
            res = {}
        else:
            res = {name: generate(img, p) for name, p in PROMPTS.items()}
        # level4: inject pipeline graph context if provided
        if s.get("graph_context"):
            l4_prompt = LEVEL4_TEMPLATE.format(graph_context=s["graph_context"])
            res["level4_hybrid"] = generate(img, l4_prompt)
        results[s["id"]] = res
        print(f"done {s['id']}")
        yield s["id"], results[s["id"]]


def _extract_json(text):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    s = (m.group(1) if m else text).strip()
    try:
        return json.loads(s)
    except Exception:
        return None


@app.local_entrypoint()
def main():
    out_root = os.path.join(os.path.dirname(__file__), "..", "data", "vlm_pilot_tests")
    payload = []
    for sid in SAMPLES:
        path = os.path.join(CUBI, sid, "F1_scaled.png")
        with open(path, "rb") as f:
            payload.append({"id": sid, "bytes": f.read()})

    results = dict(run_all.remote_gen(payload))

    for sid in SAMPLES:
        d = os.path.join(out_root, sid)
        os.makedirs(d, exist_ok=True)
        shutil.copy(os.path.join(CUBI, sid, "F1_scaled.png"),
                    os.path.join(d, "F1_scaled.png"))
        for name, text in results[sid].items():
            with open(os.path.join(d, f"{name}.json"), "w") as f:
                json.dump({"prompt": PROMPTS[name], "raw": text,
                           "parsed": _extract_json(text)}, f, indent=2,
                          ensure_ascii=False)
        print(f"saved {d}")


@app.local_entrypoint()
def batch(n: int = 50):
    """All 4 prompts on N val images. Needs graphs.json from extract_graphs.py.
    Run: modal run spatial_test.py::batch --n 50"""
    from pathlib import Path
    root = Path(__file__).resolve().parent.parents[4]
    val = json.load(open(root / "experiments/mask2former_training/dataset/val.json"))
    cubi = Path(CUBI)
    ids = []
    for i in val["images"]:
        fn = i["file_name"]
        if "high_quality_architectural/" in fn:
            sid = fn.split("high_quality_architectural/")[1].split("/")[0]
            if (cubi / sid / "model.svg").exists() and (cubi / sid / "F1_scaled.png").exists():
                ids.append(sid)
    ids = ids[:n]

    # load graphs for level4
    graphs_path = root / "benchmarks/three_way/graphs.json"
    graphs = json.load(open(graphs_path)) if graphs_path.exists() else {}

    # load existing results — rerun level4 on those that have level1-3 already
    dst = root / "benchmarks/three_way/semantic_preds.json"
    out = json.load(open(dst)) if dst.exists() else {}
    # plans that need full run (not in out at all)
    todo_full = [s for s in ids if s not in out]
    # plans that exist but need level4 rerun
    todo_l4 = [s for s in ids if s in out]
    print(f"{len(todo_full)} new + {len(todo_l4)} level4-only (of {len(ids)} total)")

    payload = []
    for sid in todo_full:
        p = {"id": sid, "bytes": (cubi / sid / "F1_scaled.png").read_bytes()}
        if sid in graphs:
            p["graph_context"] = graphs[sid]["text"]
        payload.append(p)
    for sid in todo_l4:
        p = {"id": sid, "bytes": (cubi / sid / "F1_scaled.png").read_bytes(), "only_level4": True}
        if sid in graphs:
            p["graph_context"] = graphs[sid]["text"]
        payload.append(p)

    count = 0
    for sid, levels in run_all.remote_gen(payload):
        parsed = {lvl: _extract_json(txt) for lvl, txt in levels.items()}
        if sid in out:
            out[sid]["level4_hybrid"] = parsed.get("level4_hybrid")
        else:
            out[sid] = parsed
        count += 1
        if count % 10 == 0 or count == len(payload):
            json.dump(out, open(dst, "w"), indent=2, ensure_ascii=False)
            print(f"  saved {count}/{len(payload)}")
    print(f"DONE {len(out)}/{len(ids)} plans -> {dst}")
