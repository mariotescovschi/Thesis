"""Mask2Former inference + visualization on test floor plan images."""
import os, sys, torch, json, cv2, numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # project root (this file lives in pipeline/)

# --- Config ---
MODEL_DIR = ROOT / "model/extracted"
IMAGES_ROOT = Path(os.environ.get("CUBICASA_ROOT", os.path.expanduser("~/Downloads/cubicasa5k")))
TEST_JSON = ROOT / "experiments/mask2former_training/dataset/test.json"
OUTPUT_DIR = ROOT / "benchmarks/before_after/trained_examples"
NUM_IMAGES = 2
SCORE_THRESH = 0.5

CLASSES = ["room", "wall", "door", "window", "railing"]
# Distinct colors per class (BGR)
COLORS = [
    (80, 180, 80),    # room - green
    (50, 50, 200),    # wall - red
    (200, 150, 50),   # door - blue
    (0, 200, 255),    # window - yellow
    (200, 100, 200),  # railing - purple
]


def setup_detectron2(weights=None):
    """Setup detectron2 + Mask2Former imports and build config."""
    from detectron2.config import get_cfg
    from detectron2.engine import DefaultPredictor

    # Try to import mask2former - check common locations
    m2f_paths = [
        ROOT / "vendor/Mask2Former",
        Path("/opt/ml/code/Mask2Former"),
        Path.home() / "Mask2Former",
    ]
    for p in m2f_paths:
        if (p / "mask2former").exists():
            sys.path.insert(0, str(p))
            break
    else:
        print("ERROR: Mask2Former repo not found. Clone it:")
        print("  git clone https://github.com/facebookresearch/Mask2Former.git")
        sys.exit(1)

    from mask2former import add_maskformer2_config

    cfg = get_cfg()
    add_maskformer2_config(cfg)

    # Swin-B backbone (same as training)
    cfg.MODEL.BACKBONE.NAME = "D2SwinTransformer"
    cfg.MODEL.BACKBONE.FREEZE_AT = 0
    cfg.MODEL.SWIN.EMBED_DIM = 128
    cfg.MODEL.SWIN.DEPTHS = [2, 2, 18, 2]
    cfg.MODEL.SWIN.NUM_HEADS = [4, 8, 16, 32]
    cfg.MODEL.SWIN.WINDOW_SIZE = 12
    cfg.MODEL.SWIN.APE = False
    cfg.MODEL.SWIN.DROP_PATH_RATE = 0.3
    cfg.MODEL.SWIN.PATCH_NORM = True
    cfg.MODEL.SWIN.PRETRAIN_IMG_SIZE = 384

    cfg.MODEL.META_ARCHITECTURE = "MaskFormer"
    cfg.MODEL.PIXEL_MEAN = [123.675, 116.280, 103.530]
    cfg.MODEL.PIXEL_STD = [58.395, 57.120, 57.375]

    cfg.MODEL.SEM_SEG_HEAD.NAME = "MaskFormerHead"
    cfg.MODEL.SEM_SEG_HEAD.IN_FEATURES = ["res2", "res3", "res4", "res5"]
    cfg.MODEL.SEM_SEG_HEAD.NUM_CLASSES = len(CLASSES)
    cfg.MODEL.SEM_SEG_HEAD.IGNORE_VALUE = 255
    cfg.MODEL.SEM_SEG_HEAD.LOSS_WEIGHT = 1.0
    cfg.MODEL.SEM_SEG_HEAD.CONVS_DIM = 256
    cfg.MODEL.SEM_SEG_HEAD.MASK_DIM = 256
    cfg.MODEL.SEM_SEG_HEAD.NORM = "GN"
    cfg.MODEL.SEM_SEG_HEAD.PIXEL_DECODER_NAME = "MSDeformAttnPixelDecoder"
    cfg.MODEL.SEM_SEG_HEAD.DEFORMABLE_TRANSFORMER_ENCODER_IN_FEATURES = ["res3", "res4", "res5"]
    cfg.MODEL.SEM_SEG_HEAD.COMMON_STRIDE = 4
    cfg.MODEL.SEM_SEG_HEAD.TRANSFORMER_ENC_LAYERS = 6

    cfg.MODEL.MASK_FORMER.TRANSFORMER_DECODER_NAME = "MultiScaleMaskedTransformerDecoder"
    cfg.MODEL.MASK_FORMER.TRANSFORMER_IN_FEATURE = "multi_scale_pixel_decoder"
    cfg.MODEL.MASK_FORMER.DEEP_SUPERVISION = True
    cfg.MODEL.MASK_FORMER.NO_OBJECT_WEIGHT = 0.1
    cfg.MODEL.MASK_FORMER.CLASS_WEIGHT = 2.0
    cfg.MODEL.MASK_FORMER.MASK_WEIGHT = 5.0
    cfg.MODEL.MASK_FORMER.DICE_WEIGHT = 5.0
    cfg.MODEL.MASK_FORMER.HIDDEN_DIM = 256
    cfg.MODEL.MASK_FORMER.NUM_OBJECT_QUERIES = 100
    cfg.MODEL.MASK_FORMER.NHEADS = 8
    cfg.MODEL.MASK_FORMER.DROPOUT = 0.0
    cfg.MODEL.MASK_FORMER.DIM_FEEDFORWARD = 2048
    cfg.MODEL.MASK_FORMER.ENC_LAYERS = 0
    cfg.MODEL.MASK_FORMER.PRE_NORM = False
    cfg.MODEL.MASK_FORMER.ENFORCE_INPUT_PROJ = False
    cfg.MODEL.MASK_FORMER.SIZE_DIVISIBILITY = 32
    cfg.MODEL.MASK_FORMER.DEC_LAYERS = 10
    cfg.MODEL.MASK_FORMER.TRAIN_NUM_POINTS = 12544
    cfg.MODEL.MASK_FORMER.OVERSAMPLE_RATIO = 3.0
    cfg.MODEL.MASK_FORMER.IMPORTANCE_SAMPLE_RATIO = 0.75
    cfg.MODEL.MASK_FORMER.TEST.SEMANTIC_ON = False
    cfg.MODEL.MASK_FORMER.TEST.INSTANCE_ON = True
    cfg.MODEL.MASK_FORMER.TEST.PANOPTIC_ON = False
    cfg.MODEL.MASK_FORMER.TEST.OVERLAP_THRESHOLD = 0.8
    cfg.MODEL.MASK_FORMER.TEST.OBJECT_MASK_THRESHOLD = 0.5

    cfg.MODEL.WEIGHTS = weights or str(MODEL_DIR / "model_final.pth")
    cfg.INPUT.FORMAT = "RGB"
    cfg.INPUT.MIN_SIZE_TEST = 800
    cfg.INPUT.MAX_SIZE_TEST = 1280

    # CPU inference (no GPU on Mac)
    cfg.MODEL.DEVICE = "cpu"

    # Register dummy dataset so MaskFormer can get metadata
    from detectron2.data import DatasetCatalog, MetadataCatalog
    if "floorplan_test" not in DatasetCatalog:
        DatasetCatalog.register("floorplan_test", lambda: [])
        MetadataCatalog.get("floorplan_test").set(thing_classes=list(CLASSES))
    cfg.DATASETS.TRAIN = ("floorplan_test",)
    cfg.DATASETS.TEST = ("floorplan_test",)

    cfg.freeze()
    return cfg, DefaultPredictor(cfg)


def visualize(image, instances, output_path):
    """Draw colored masks + labels on image."""
    vis = image.copy()
    if len(instances) == 0:
        cv2.imwrite(str(output_path), vis)
        return

    masks = instances.pred_masks.numpy()
    classes = instances.pred_classes.numpy()
    scores = instances.scores.numpy()

    # Sort by area (largest first) so small objects render on top
    areas = masks.sum(axis=(1, 2))
    order = areas.argsort()[::-1]

    overlay = vis.copy()
    for idx in order:
        if scores[idx] < SCORE_THRESH:
            continue
        mask = masks[idx].astype(bool)
        cls_id = classes[idx]
        color = COLORS[cls_id]
        overlay[mask] = color

    # Blend
    vis = cv2.addWeighted(overlay, 0.45, vis, 0.55, 0)

    # Draw contours + labels
    for idx in order:
        if scores[idx] < SCORE_THRESH:
            continue
        mask = masks[idx].astype(np.uint8)
        cls_id = classes[idx]
        color = COLORS[cls_id]
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, contours, -1, color, 2)

        # Label at centroid
        M = cv2.moments(mask)
        if M["m00"] > 0:
            cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
            label = f"{CLASSES[cls_id]} {scores[idx]:.2f}"
            cv2.putText(vis, label, (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            cv2.putText(vis, label, (cx - 30, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.imwrite(str(output_path), vis)
    print(f"  Saved: {output_path}")


def main():
    # Load test images list
    with open(TEST_JSON) as f:
        test_data = json.load(f)
    test_images = test_data["images"][:NUM_IMAGES]

    print(f"Loading model from {MODEL_DIR}...")
    cfg, predictor = setup_detectron2()
    print("Model loaded.")

    OUTPUT_DIR.mkdir(exist_ok=True)

    for img_info in test_images:
        img_path = IMAGES_ROOT / img_info["file_name"]
        if not img_path.exists():
            print(f"  SKIP (not found): {img_path}")
            continue

        print(f"\nProcessing: {img_info['file_name']}")
        image = cv2.imread(str(img_path))

        with torch.no_grad():
            outputs = predictor(image)

        instances = outputs["instances"].to("cpu")
        # Filter by score
        keep = instances.scores >= SCORE_THRESH
        instances = instances[keep]

        print(f"  Detected {len(instances)} instances:")
        for cls_id in range(len(CLASSES)):
            n = (instances.pred_classes == cls_id).sum().item()
            if n > 0:
                print(f"    {CLASSES[cls_id]}: {n}")

        out_name = img_info["file_name"].replace("/", "_")
        visualize(image, instances, OUTPUT_DIR / out_name)

    # Legend
    legend = np.zeros((150, 250, 3), dtype=np.uint8)
    for i, (cls, color) in enumerate(zip(CLASSES, COLORS)):
        y = 25 + i * 25
        cv2.rectangle(legend, (10, y - 12), (30, y + 3), color, -1)
        cv2.putText(legend, cls, (40, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
    cv2.imwrite(str(OUTPUT_DIR / "legend.png"), legend)

    print(f"\nDone! Results in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
