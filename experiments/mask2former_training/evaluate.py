"""Evaluate Mask2Former on CubiCasa5k test set (COCO mAP)."""
import sys, os, json, time
import numpy as np
from pathlib import Path
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
from pycocotools import mask as mask_util
import cv2

ROOT = Path(__file__).resolve().parents[2]  # project root (file in experiments/mask2former_training/)
sys.path.insert(0, str(ROOT / "vendor/Mask2Former"))

NUM_IMAGES = 30
SCORE_THRESH = 0.0  # keep all for mAP computation
IMAGES_ROOT = Path(os.environ.get("CUBICASA_ROOT", os.path.expanduser("~/Downloads/cubicasa5k")))
TEST_JSON = ROOT / "experiments/mask2former_training/dataset/test.json"

def build_predictor():
    from detectron2.config import get_cfg
    from detectron2.engine import DefaultPredictor
    from detectron2.data import DatasetCatalog, MetadataCatalog
    from mask2former import add_maskformer2_config

    CLASSES = ["room", "wall", "door", "window", "railing"]
    cfg = get_cfg()
    add_maskformer2_config(cfg)
    cfg.MODEL.BACKBONE.NAME = "D2SwinTransformer"
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
    cfg.MODEL.SEM_SEG_HEAD.NUM_CLASSES = 5
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
    cfg.MODEL.MASK_FORMER.TEST.SEMANTIC_ON = False
    cfg.MODEL.MASK_FORMER.TEST.INSTANCE_ON = True
    cfg.MODEL.MASK_FORMER.TEST.PANOPTIC_ON = False
    cfg.MODEL.MASK_FORMER.TEST.OVERLAP_THRESHOLD = 0.8
    cfg.MODEL.MASK_FORMER.TEST.OBJECT_MASK_THRESHOLD = 0.5
    cfg.MODEL.WEIGHTS = str(ROOT / "model/extracted/model_final.pth")
    cfg.INPUT.FORMAT = "RGB"
    cfg.INPUT.MIN_SIZE_TEST = 800
    cfg.INPUT.MAX_SIZE_TEST = 1280
    cfg.MODEL.DEVICE = "cpu"

    if "floorplan_test" not in DatasetCatalog:
        DatasetCatalog.register("floorplan_test", lambda: [])
        MetadataCatalog.get("floorplan_test").set(thing_classes=list(CLASSES))
    cfg.DATASETS.TRAIN = ("floorplan_test",)
    cfg.DATASETS.TEST = ("floorplan_test",)
    cfg.freeze()
    return DefaultPredictor(cfg)


def main():
    print(f"Loading test annotations from {TEST_JSON}...")
    coco_gt = COCO(str(TEST_JSON))

    # Take first N images
    image_ids = sorted(coco_gt.getImgIds())[:NUM_IMAGES]
    print(f"Evaluating on {len(image_ids)} images\n")

    print("Loading model...")
    predictor = build_predictor()
    print("Model loaded.\n")

    results = []
    t0 = time.time()

    for i, img_id in enumerate(image_ids):
        img_info = coco_gt.loadImgs(img_id)[0]
        img_path = IMAGES_ROOT / img_info["file_name"]
        image = cv2.imread(str(img_path))
        if image is None:
            print(f"  SKIP (not found): {img_path}")
            continue

        outputs = predictor(image)
        instances = outputs["instances"]

        # Convert predictions to COCO format
        masks = instances.pred_masks.numpy()
        classes = instances.pred_classes.numpy()
        scores = instances.scores.numpy()

        for j in range(len(instances)):
            mask_rle = mask_util.encode(np.asfortranarray(masks[j].astype(np.uint8)))
            mask_rle["counts"] = mask_rle["counts"].decode("utf-8")
            results.append({
                "image_id": img_id,
                "category_id": int(classes[j]) + 1,  # COCO categories are 1-indexed
                "segmentation": mask_rle,
                "score": float(scores[j]),
            })

        elapsed = time.time() - t0
        avg = elapsed / (i + 1)
        print(f"  [{i+1}/{len(image_ids)}] {img_info['file_name']} - {len(instances)} detections ({avg:.1f}s/img)")

    print(f"\nTotal predictions: {len(results)}")
    print(f"Total time: {time.time()-t0:.0f}s\n")

    # Save predictions
    pred_path = str(ROOT / "experiments/mask2former_training/eval_predictions.json")
    with open(pred_path, "w") as f:
        json.dump(results, f)

    # Run COCO evaluation
    print("=" * 60)
    print("COCO Instance Segmentation Evaluation")
    print("=" * 60)
    coco_dt = coco_gt.loadRes(pred_path)
    coco_eval = COCOeval(coco_gt, coco_dt, "segm")
    coco_eval.params.imgIds = image_ids
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()

    # Per-category AP
    print("\n" + "=" * 60)
    print("Per-category AP@0.5:0.95")
    print("=" * 60)
    cats = coco_gt.loadCats(coco_gt.getCatIds())
    for cat in cats:
        coco_eval_cat = COCOeval(coco_gt, coco_dt, "segm")
        coco_eval_cat.params.imgIds = image_ids
        coco_eval_cat.params.catIds = [cat["id"]]
        coco_eval_cat.evaluate()
        coco_eval_cat.accumulate()
        ap = coco_eval_cat.stats[0]  # AP@0.5:0.95
        ap50 = coco_eval_cat.stats[1]  # AP@0.5
        print(f"  {cat['name']:10s}: AP={ap:.3f}  AP50={ap50:.3f}")


if __name__ == "__main__":
    main()
