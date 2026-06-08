"""Mask2Former Swin-B training on CubiCasa5k (5 classes) for SageMaker."""
import os, sys, copy, torch
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
import numpy as np
from pathlib import Path

from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer
from detectron2.data import DatasetCatalog, MetadataCatalog, build_detection_train_loader
from detectron2.data.datasets import load_coco_json
from detectron2.data import detection_utils as utils, transforms as T, DatasetMapper
from detectron2.evaluation import COCOEvaluator
from detectron2.solver import get_default_optimizer_params
from detectron2.checkpoint import DetectionCheckpointer

# Build MSDeformAttn CUDA ops at runtime (CodeBuild has no GPU)
import subprocess
ops_dir = "/opt/ml/code/Mask2Former/mask2former/modeling/pixel_decoder/ops"
subprocess.run(["python3", "setup.py", "build", "install"], cwd=ops_dir, check=True)

sys.path.insert(0, "/opt/ml/code/Mask2Former")
from mask2former import add_maskformer2_config

SM_CHANNEL_TRAIN = os.environ.get("SM_CHANNEL_TRAINING", "/opt/ml/input/data/training")
SM_MODEL_DIR = os.environ.get("SM_MODEL_DIR", "/opt/ml/model")
SM_OUTPUT_DIR = os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output/data")

CLASSES = ["room", "wall", "door", "window", "railing"]
WEIGHTS = "https://dl.fbaipublicfiles.com/maskformer/mask2former/coco/instance/maskformer2_swin_base_IN21k_384_bs16_50ep/model_final_83d103.pkl"


def register_datasets():
    data_dir = Path(SM_CHANNEL_TRAIN)
    img_dir = str(data_dir / "images")
    id_map = {i+1: i for i in range(len(CLASSES))}  # {1:0, 2:1, 3:2, 4:3, 5:4}
    for split in ["train", "val"]:
        name = f"floorplan_{split}"
        if name not in DatasetCatalog.list():
            json_path = str(data_dir / f"{split}.json")
            DatasetCatalog.register(name, lambda j=json_path, i=img_dir: load_coco_json(j, i, name))
            MetadataCatalog.get(name).set(
                thing_classes=CLASSES,
                thing_dataset_id_to_contiguous_id=id_map,
            )


class MaskMapper(DatasetMapper):
    def __call__(self, dataset_dict):
        dataset_dict = copy.deepcopy(dataset_dict)
        image = utils.read_image(dataset_dict["file_name"], format="RGB")
        aug_input = T.AugInput(image)
        transforms = self.augmentations(aug_input)
        image = aug_input.image
        image_shape = image.shape[:2]
        dataset_dict["image"] = torch.as_tensor(np.ascontiguousarray(image.transpose(2, 0, 1)))

        if "annotations" in dataset_dict:
            annos = [
                utils.transform_instance_annotations(obj, transforms, image_shape)
                for obj in dataset_dict.pop("annotations")
                if obj.get("iscrowd", 0) == 0
            ]
            instances = utils.annotations_to_instances(annos, image_shape, mask_format="bitmask")
            dataset_dict["instances"] = utils.filter_empty_instances(instances)
            if hasattr(dataset_dict["instances"], "gt_masks"):
                dataset_dict["instances"].gt_masks = dataset_dict["instances"].gt_masks.tensor
        return dataset_dict


class Trainer(DefaultTrainer):
    @classmethod
    def build_optimizer(cls, cfg, model):
        params = get_default_optimizer_params(
            model, base_lr=cfg.SOLVER.BASE_LR, weight_decay=cfg.SOLVER.WEIGHT_DECAY
        )
        return torch.optim.AdamW(params, lr=cfg.SOLVER.BASE_LR, weight_decay=cfg.SOLVER.WEIGHT_DECAY)

    @classmethod
    def build_train_loader(cls, cfg):
        mapper = MaskMapper(cfg, is_train=True, augmentations=[
            T.ResizeShortestEdge(cfg.INPUT.MIN_SIZE_TRAIN, cfg.INPUT.MAX_SIZE_TRAIN, "choice"),
            T.RandomFlip(),
        ])
        return build_detection_train_loader(cfg, mapper=mapper)

    @classmethod
    def build_evaluator(cls, cfg, dataset_name):
        return COCOEvaluator(dataset_name, output_dir=SM_OUTPUT_DIR)


def setup_cfg():
    cfg = get_cfg()
    add_maskformer2_config(cfg)

    # Swin-B backbone
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

    # Mask2Former head
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

    # Transformer decoder
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
    cfg.MODEL.MASK_FORMER.TEST.OBJECT_MASK_THRESHOLD = 0.8

    cfg.MODEL.WEIGHTS = WEIGHTS

    # Datasets
    cfg.DATASETS.TRAIN = ("floorplan_train",)
    cfg.DATASETS.TEST = ("floorplan_val",)

    # Solver — L40S 44GB: batch 2, max 1280px
    cfg.SOLVER.IMS_PER_BATCH = 2
    cfg.SOLVER.BASE_LR = 1e-4
    cfg.SOLVER.MAX_ITER = 20000
    cfg.SOLVER.WARMUP_FACTOR = 1.0
    cfg.SOLVER.WARMUP_ITERS = 500
    cfg.SOLVER.LR_SCHEDULER_NAME = "WarmupCosineLR"
    cfg.SOLVER.WEIGHT_DECAY = 0.05
    cfg.SOLVER.AMP.ENABLED = True
    cfg.SOLVER.CHECKPOINT_PERIOD = 2000
    cfg.SOLVER.CLIP_GRADIENTS.ENABLED = True
    cfg.SOLVER.CLIP_GRADIENTS.CLIP_TYPE = "value"
    cfg.SOLVER.CLIP_GRADIENTS.CLIP_VALUE = 0.01
    cfg.SOLVER.CLIP_GRADIENTS.NORM_TYPE = 2.0

    # Input
    cfg.INPUT.FORMAT = "RGB"
    cfg.INPUT.MIN_SIZE_TRAIN = (640, 800, 1024)
    cfg.INPUT.MAX_SIZE_TRAIN = 1280
    cfg.INPUT.MIN_SIZE_TEST = 800
    cfg.INPUT.MAX_SIZE_TEST = 1280

    # Eval & output
    cfg.TEST.EVAL_PERIOD = 2000
    cfg.OUTPUT_DIR = SM_MODEL_DIR
    cfg.DATALOADER.NUM_WORKERS = 4
    cfg.DATALOADER.FILTER_EMPTY_ANNOTATIONS = True

    return cfg


def main():
    register_datasets()
    cfg = setup_cfg()
    os.makedirs(cfg.OUTPUT_DIR, exist_ok=True)

    trainer = Trainer(cfg)
    trainer.resume_or_load(resume=False)
    trainer.train()

    # Save final model
    checkpointer = DetectionCheckpointer(trainer.model, save_dir=SM_MODEL_DIR)
    checkpointer.save("model_final")


if __name__ == "__main__":
    main()
