#!/usr/bin/env python3
"""
Build COCO dataset from CubiCasa5k — 5 classes: room, wall, door, window, railing.
SVG coordinates are already in pixel space of F1_scaled.png.
"""
import json, re, os
import numpy as np
import cv2
from pathlib import Path
from PIL import Image
from pycocotools import mask as maskUtils
from tqdm import tqdm

Image.MAX_IMAGE_PIXELS = None

CUBICASA_ROOT = Path(os.path.expanduser("~/Downloads/cubicasa5k"))
OUTPUT_DIR = Path(os.path.expanduser("~/Projects/Facultate/Licenta/dataset"))
MIN_AREA = 50

CATEGORIES = [
    {"id": 1, "name": "room", "supercategory": "structure"},
    {"id": 2, "name": "wall", "supercategory": "structure"},
    {"id": 3, "name": "door", "supercategory": "opening"},
    {"id": 4, "name": "window", "supercategory": "opening"},
    {"id": 5, "name": "railing", "supercategory": "structure"},
]


def parse_points(pts_str):
    coords = []
    for pt in pts_str.strip().split():
        parts = pt.split(",")
        if len(parts) == 2:
            coords.append((round(float(parts[0])), round(float(parts[1]))))
    return coords


def parse_svg(svg_path):
    text = svg_path.read_text()
    elements = {1: [], 2: [], 3: [], 4: [], 5: []}

    for m in re.finditer(r'class="Space ([^"]+)"[^>]*>.*?<polygon points="([^"]+)"', text, re.DOTALL):
        pts = parse_points(m.group(2))
        if len(pts) >= 3:
            elements[1].append(pts)

    for m in re.finditer(r'<g id="Wall"[^>]*class="(Wall[^"]*)"[^>]*><polygon points="([^"]+)"', text):
        pts = parse_points(m.group(2))
        if len(pts) >= 3:
            elements[2].append(pts)

    for m in re.finditer(r'<g id="Door"[^>]*>[^<]*<polygon points="([^"]+)"', text):
        pts = parse_points(m.group(1))
        if len(pts) >= 3:
            elements[3].append(pts)

    for m in re.finditer(r'<g id="Window"[^>]*>[^<]*<polygon points="([^"]+)"', text):
        pts = parse_points(m.group(1))
        if len(pts) >= 3:
            elements[4].append(pts)

    for m in re.finditer(r'<g id="Railing"[^>]*>[^<]*<polygon points="([^"]+)"', text):
        pts = parse_points(m.group(1))
        if len(pts) >= 3:
            elements[5].append(pts)

    return elements


def polygon_to_rle(polygon, img_w, img_h):
    pts = np.array(polygon, dtype=np.int32)
    mask = np.zeros((img_h, img_w), dtype=np.uint8)
    cv2.fillPoly(mask, [pts], 1)
    rle = maskUtils.encode(np.asfortranarray(mask))
    rle["counts"] = rle["counts"].decode("utf-8")
    area = int(maskUtils.area(rle))
    bbox = list(maskUtils.toBbox(rle).astype(float))
    return rle, area, bbox


def process_split(split):
    split_file = CUBICASA_ROOT / f"{split}.txt"
    paths = [l.strip() for l in split_file.read_text().strip().split("\n") if l.strip()]

    images, annotations = [], []
    img_id, ann_id, skipped = 0, 0, 0

    for rel_path in tqdm(paths, desc=f"{split}"):
        sample_dir = CUBICASA_ROOT / rel_path.lstrip("/")
        svg_path = sample_dir / "model.svg"
        img_path = sample_dir / "F1_scaled.png"

        if not svg_path.exists() or not img_path.exists():
            skipped += 1
            continue

        img = Image.open(img_path)
        img_w, img_h = img.size
        elements = parse_svg(svg_path)

        if not any(elements.values()):
            skipped += 1
            continue

        img_id += 1
        images.append({
            "id": img_id,
            "file_name": f"{rel_path.strip('/')}/F1_scaled.png",
            "width": img_w, "height": img_h,
        })

        for cat_id, polys in elements.items():
            for poly in polys:
                rle, area, bbox = polygon_to_rle(poly, img_w, img_h)
                if area < MIN_AREA:
                    continue
                ann_id += 1
                annotations.append({
                    "id": ann_id, "image_id": img_id, "category_id": cat_id,
                    "segmentation": rle, "bbox": bbox, "area": area, "iscrowd": 0,
                })

    print(f"  {split}: {len(images)} images, {len(annotations)} anns, {skipped} skipped")
    return images, annotations


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building CubiCasa5k dataset (5 classes)")
    print("=" * 60)

    splits = {}
    for split in ["train", "val", "test"]:
        splits[split] = process_split(split)

    for name, (imgs, anns) in splits.items():
        data = {"images": imgs, "annotations": anns, "categories": CATEGORIES}
        out_path = OUTPUT_DIR / f"{name}.json"
        with open(out_path, "w") as f:
            json.dump(data, f)

    img_link = OUTPUT_DIR / "images"
    if not img_link.exists():
        os.symlink(CUBICASA_ROOT, img_link)

    print(f"\n{'='*60}")
    print(f"Output: {OUTPUT_DIR}")
    all_anns = sum((a for _, a in splits.values()), [])
    for cat in CATEGORIES:
        n = sum(1 for a in all_anns if a["category_id"] == cat["id"])
        print(f"  {cat['name']:10s}: {n}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
