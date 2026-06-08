#!/bin/bash
# Batch Claude semantic eval on floor plans (fresh session per plan).
# Usage: bash run_claude_batch.sh [PARALLEL=5]

PARALLEL=${1:-5}
CUBI="$HOME/Downloads/cubicasa5k/high_quality_architectural"
OUTDIR="$(dirname "$0")/claude_preds"
mkdir -p "$OUTDIR"

PROMPT='Read the image file I am providing. This is one drawing sheet of a single-family Finnish house showing several storeys side by side. Labels are Finnish abbreviations.
Finnish glossary: MH=bedroom, OH=living room, K/KEITTIO=kitchen, RUOKAILUTILA/RUOKATILA=dining, KPH/PESUH=bathroom, WC=toilet, ET=entry hall, AULA=hall/landing, S/SAUNA=sauna, PUKUH=changing room, VH/KHH=utility room, TK=technical closet, VARASTO/VARAS=storage, AUTOTALLI=garage, PARVEKE=balcony, TERASSI=terrace, KELLARI=cellar, KATTILAHUONE=boiler room, TAKKAHUONE=fireplace room, VESIVARAAJA=water heater, ALKOVI=alcove, HALLI=hall. Floor labels: KELLARIKERROS=basement floor, (I/II) KERROS / KRS=storey, VINTTIKERROS=attic floor, POHJA=plan.

Extract a STRICT structured representation. For every storey list its rooms with a coarse relative position. Identify vertical circulation (staircases that connect storeys). For the main/ground storey give a room adjacency list (which rooms are directly connected by a door or opening). Save ONLY valid JSON (no prose, no markdown fences) to OUTPATH matching exactly:
{"building_type": "single_family_house", "floors": [{"level_index": 0, "floor_label_original": "...", "floor_role": "basement|ground|upper|attic", "rooms": [{"label": "...", "type_en": "...", "position": "top-left|top|top-right|left|center|right|bottom-left|bottom|bottom-right"}]}], "vertical_connections": [{"via": "staircase", "connects_levels": [0, 1]}], "ground_floor_adjacency": [{"from": "...", "to": "...", "via": "door|opening"}]}'

# Get plan IDs that still need processing
TODOS=()
for ID in $(python3 -c "
import json
from pathlib import Path
CUBI=Path.home()/'Downloads'/'cubicasa5k'/'high_quality_architectural'
d=json.load(open('$(dirname "$0")/../../experiments/mask2former_training/dataset/val.json'))
ids=[]
for i in d['images']:
    fn=i['file_name']
    if 'high_quality_architectural/' in fn:
        sid=fn.split('high_quality_architectural/')[1].split('/')[0]
        if (CUBI/sid/'model.svg').exists(): ids.append(sid)
ids=ids[:50]
import os
done=[f.replace('.json','') for f in os.listdir('$OUTDIR') if f.endswith('.json')]
print(' '.join(s for s in ids if s not in done))
"); do
    TODOS+=("$ID")
done

echo "Plans remaining: ${#TODOS[@]}"

run_one() {
    local ID=$1
    local IMG="$CUBI/$ID/F1_scaled.png"
    local OUT="$OUTDIR/$ID.json"
    local P="${PROMPT//OUTPATH/$OUT}"
    
    kiro-cli chat "$P Read the image at $IMG and save the JSON to $OUT" \
        --no-interactive --trust-all-tools 2>/dev/null
    
    if [ -f "$OUT" ]; then
        echo "✓ $ID"
    else
        echo "✗ $ID (no output)"
    fi
}

export -f run_one
export CUBI OUTDIR PROMPT

# Run in parallel batches
printf '%s\n' "${TODOS[@]}" | xargs -P "$PARALLEL" -I {} bash -c 'run_one "$@"' _ {}

echo "Done. Total files: $(ls "$OUTDIR"/*.json 2>/dev/null | wc -l)/50"
