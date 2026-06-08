"""CubiCasa5k CNN baseline -> our 5 classes (room/wall/door/window/railing).

Output head (44ch) = heatmaps[0:21] + rooms[21:33] + icons[33:44].
rooms(12): 2=Wall, 8=Railing, {3..7,9,10,11}=room types.  icons(11): 1=Window, 2=Door.
"""
import os, sys, cv2, json, numpy as np, torch
import torch.nn.functional as F
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUBI = ROOT / "vendor/CubiCasa5k"
sys.path.insert(0, str(CUBI))
WEIGHTS = CUBI / "model_best_val_loss_var.pkl"

CLASSES = ["room", "wall", "door", "window", "railing"]
COLORS = [(80, 180, 80), (50, 50, 200), (200, 150, 50), (0, 200, 255), (200, 100, 200)]  # BGR, matches m2f
ROOM_IDS = [3, 4, 5, 6, 7, 9, 10, 11]
MAX_SIDE = 1024  # cap input for CPU speed; masks interpolated back to full res


def load_model():
    from floortrans.models import get_model
    cwd = os.getcwd()
    os.chdir(CUBI)  # get_model->init_weights loads backbone via relative path
    try:
        model = get_model("hg_furukawa_original", 51)
    finally:
        os.chdir(cwd)
    model.conv4_ = torch.nn.Conv2d(256, 44, bias=True, kernel_size=1)
    model.upsample = torch.nn.ConvTranspose2d(44, 44, kernel_size=4, stride=4)
    model.load_state_dict(torch.load(WEIGHTS, map_location="cpu")["model_state"])
    model.eval()
    return model


def predict(model, image_bgr):
    """Return {class: HxW bool mask} for our 5 classes."""
    h, w = image_bgr.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32)
    if scale < 1.0:
        rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)))
    x = torch.from_numpy(2 * (rgb / 255.0) - 1).permute(2, 0, 1).unsqueeze(0)
    with torch.no_grad():
        pred = model(x)
        pred = F.interpolate(pred, size=(h, w), mode="bilinear", align_corners=True)
    rooms = torch.argmax(F.softmax(pred[0, 21:33], 0), 0).numpy()
    icons = torch.argmax(F.softmax(pred[0, 33:44], 0), 0).numpy()
    return {
        "room": np.isin(rooms, ROOM_IDS),
        "wall": rooms == 2,
        "door": icons == 2,
        "window": icons == 1,
        "railing": rooms == 8,
    }


def overlay_side_by_side(image_bgr, masks):
    """original LEFT | prediction with masks RIGHT."""
    vis = image_bgr.copy()
    ov = vis.copy()
    for cls, color in zip(CLASSES, COLORS):
        ov[masks[cls]] = color
    vis = cv2.addWeighted(ov, 0.45, vis, 0.55, 0)
    for cls, color in zip(CLASSES, COLORS):
        cnts, _ = cv2.findContours(masks[cls].astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(vis, cnts, -1, color, 1)
    return np.hstack([image_bgr, vis])


def main():
    test = json.load(open(ROOT / "experiments/mask2former_training/dataset/test.json"))
    images_root = Path(os.environ.get("CUBICASA_ROOT", os.path.expanduser("~/Downloads/cubicasa5k")))
    out = ROOT / "benchmarks/before_after/cubicasa_cnn"
    out.mkdir(parents=True, exist_ok=True)
    model = load_model()
    print("CNN loaded.")
    for info in test["images"][:3]:
        p = images_root / info["file_name"]
        img = cv2.imread(str(p))
        if img is None:
            print(f"  SKIP {p}")
            continue
        masks = predict(model, img)
        counts = {c: int(masks[c].sum()) for c in CLASSES}
        print(f"{info['file_name']}  px/class: {counts}")
        cv2.imwrite(str(out / info["file_name"].replace("/", "_")), overlay_side_by_side(img, masks))
    print(f"Done -> {out}/")


if __name__ == "__main__":
    main()
