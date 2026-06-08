# Prompt pentru Claude — comparație 3-way

Atașează pe rând fiecare imagine din `~/Desktop/floorplan_comparison/`:
`plan_a.png`, `plan_b.png`, `plan_c.png`.

Pentru fiecare imagine, dă-i exact promptul de mai jos. Cere-i să producă **JSON** și,
separat, un **SVG** rendat din acel JSON (ca să avem poză + json, la fel ca celelalte
două abordări).

Imaginile au nume anonimizate intenționat (plan_a/b/c) ca modelul să nu poată
identifica sample-ul în vreun dataset public și să "tríșeze" cu ground-truth-ul.

---

## PROMPT (copiază de aici)

You are given a single architectural floor plan image (a residential building;
room labels may be Finnish abbreviations such as MH=bedroom, OH=living room,
K/KT=kitchen, KPH/PH=bathroom, WC=toilet, ET=entry hall, S=sauna, VH/KHH=utility,
VAR/VARASTO=storage, AULA=hall, PARVEKE=balcony).

Analyze ONLY what is visible in the image. Then produce TWO things:

### 1. STRICT JSON (no prose), exactly this schema:
```json
{
  "building_type": "...",
  "image_size": {"width": <int px>, "height": <int px>},
  "rooms": [{"name": "<label as written or best guess>", "type_en": "...",
             "approx_area_m2": <number or null>, "polygon": [[x,y], ...]}],
  "walls": [{"type": "external|internal", "polygon": [[x,y], ...]}],
  "doors": [{"position": [x,y]}],
  "windows": [{"position": [x,y]}],
  "adjacency": [{"from": "<room>", "to": "<room>"}]
}
```
Coordinates are pixel coordinates in the image (origin top-left).

### 2. An SVG that renders this floor plan
- Use the same pixel coordinate system as the JSON.
- Rooms filled light, walls darker, doors/windows marked, room names as text labels.
- Return the SVG as a separate ```svg code block.

---

## Unde salvezi răspunsul lui Claude
- JSON  -> `~/Desktop/floorplan_comparison/plan_a_claude.json` (etc.)
- SVG   -> `~/Desktop/floorplan_comparison/plan_a_claude.svg` (etc.)
