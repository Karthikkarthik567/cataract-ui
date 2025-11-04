import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def try_load_ultralytics(model_path):
    """
    Loads a YOLOv8 (Ultralytics) model.
    """
    try:
        from ultralytics import YOLO
    except Exception as e:
        raise RuntimeError(
            "Ultralytics package not available. Install it via `pip install ultralytics`."
        ) from e

    model = YOLO(model_path)
    names = {0: "cataract", 1: "normal"}
    print(f"✅ YOLO model loaded from {model_path}")
    if names:
        print(f"🧠 Classes: {names}")
    return {"framework": "yolo", "model": model, "names": names}


def try_load_torch(model_path):
    """
    Fallback loader for plain PyTorch checkpoints (not used for YOLOv8 models).
    You can adapt this if your model is custom.
    """
    import torch

    ckpt = torch.load(model_path, map_location="cpu")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"⚙️ Loaded Torch checkpoint on {device}: {list(ckpt.keys())[:5]}")
    return {"framework": "torch", "ckpt": ckpt, "device": device}


def load_model(model_path):
    """
    Main loader that first tries Ultralytics YOLO, then falls back to Torch checkpoint.
    """
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"❌ Model path not found: {model_path}")

    try:
        return try_load_ultralytics(model_path)
    except Exception as yolo_err:
        print(f"⚠️ YOLO load failed: {yolo_err}")

    try:
        return try_load_torch(model_path)
    except Exception as e:
        raise RuntimeError(
            "❌ Could not auto-load model. Provide a YOLO .pt file or adapt the Torch loader."
        ) from e


def run_inference(model_bundle, image_path, imgsz=640, conf_thresh=0.25):
    """
    Runs inference on an image using the loaded model.
    Returns:
        {
          'label': str,
          'confidence': float,
          'boxes': [ {x1,y1,x2,y2,confidence,cls} ],
          'names': {cls->name}
        }
    """
    if model_bundle["framework"] == "yolo":
        model = model_bundle["model"]
        results = model(image_path, imgsz=imgsz, conf=conf_thresh)
        r = results[0]
        boxes_out = []

        # collect all boxes
        if hasattr(r, "boxes") and len(r.boxes):
            for box in r.boxes.data.tolist():
                x1, y1, x2, y2, conf, cls = box
                boxes_out.append(
                    {
                        "x1": float(x1),
                        "y1": float(y1),
                        "x2": float(x2),
                        "y2": float(y2),
                        "confidence": float(conf),
                        "class": int(cls),
                    }
                )

        # pick best prediction
        names = model_bundle.get("names", None)
        if boxes_out:
            top = max(boxes_out, key=lambda b: b["confidence"])
            top_conf = float(top["confidence"])
            cls = top["class"]
            top_label = names[cls] if names and cls in names else str(cls)
        else:
            top_label = "no-detection"
            top_conf = 0.0

        print(
            f"🔍 Prediction done: {top_label} ({top_conf:.3f}) — {len(boxes_out)} boxes detected."
        )
        return {
            "label": top_label,
            "confidence": top_conf,
            "boxes": boxes_out,
            "names": names,
        }

    elif model_bundle["framework"] == "torch":
        raise NotImplementedError(
            "⚠️ Torch checkpoint inference not implemented. Adapt this for your model."
        )

    else:
        raise RuntimeError("❌ Unknown model framework.")


def draw_boxes_on_image(src_image_path, boxes, dst_image_path, labels=None, thickness=2):
    img = Image.open(src_image_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    try:
        font = ImageFont.truetype("arial.ttf", size=max(14, int(min(W, H) * 0.03)))
    except Exception:
        font = ImageFont.load_default()

    for b in boxes:
        x1, y1, x2, y2 = b['x1'], b['y1'], b['x2'], b['y2']
        xy = (int(x1), int(y1), int(x2), int(y2))
        draw.rectangle(xy, outline="red", width=thickness)

        label_text = f"{labels[b['class']] if labels and b['class'] in labels else b.get('class', '')}: {b.get('confidence',0):.2f}"

        # ✅ new Pillow 10+ compatible text sizing
        try:
            bbox = draw.textbbox((0, 0), label_text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            text_w, text_h = font.getsize(label_text)

        draw.rectangle([xy[0], xy[1] - text_h - 4, xy[0] + text_w + 4, xy[1]], fill="red")
        draw.text((xy[0] + 2, xy[1] - text_h - 2), label_text, fill="white", font=font)

    img.save(dst_image_path)
    print(f"🖼️ Saved annotated image: {dst_image_path}")
    return dst_image_path
