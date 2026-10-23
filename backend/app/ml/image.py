"""Soil photo -> soil type, with a Grad-CAM heat-map showing where the CNN looked.

Moved from ml_legacy/soil_api.py. The tiers were tuned on the validation set; re-tune them if the CNN is retrained.
"""
import io
from typing import Optional

import numpy as np
import torch
import torch.nn.functional as F
from matplotlib import colormaps
from PIL import Image
from torchvision import transforms

from app.ml.loader import ModelRegistry, canon_class

SOIL_CONFIDENT = 0.60   # >= this: show the soil type as the diagnosis
SOIL_CONFIRM = 0.40     # between CONFIRM and CONFIDENT: top-2 candidates, the farmer confirms
# Optionally reject as "not soil" when P(Not_Soil) alone reaches this value (None = argmax rule only).
NOT_SOIL_REJECT: Optional[float] = None

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
EVAL_TF = transforms.Compose([
    transforms.Resize(256), transforms.CenterCrop(224),
    transforms.ToTensor(), transforms.Normalize(MEAN, STD),
])


def _forward_with_cam(cnn, img: Image.Image):
    """Forward pass + Grad-CAM for the predicted class. Returns (probabilities, heat-map 224x224 in 0..1)."""
    x = EVAL_TF(img).unsqueeze(0)
    with torch.enable_grad():
        a = cnn.features(x)                                    # last conv feature map (1, C, 7, 7)
        out = cnn.classifier(torch.flatten(cnn.avgpool(a), 1))
        probs = torch.softmax(out, 1)[0]
        idx = int(probs.argmax())
        g = torch.autograd.grad(out[0, idx], a)[0]             # d(class score) / d(feature map)
    w = g.mean(dim=(2, 3), keepdim=True)
    cam = F.relu((w * a).sum(1, keepdim=True)).detach()
    cam = F.interpolate(cam, size=(224, 224), mode="bilinear", align_corners=False)[0, 0].numpy()
    span = float(cam.max() - cam.min())
    cam = (cam - cam.min()) / span if span > 0 else np.zeros_like(cam)   # a flat map stays flat
    return probs.detach().numpy(), cam


def _overlay_png(img: Image.Image, cam: np.ndarray) -> bytes:
    base = transforms.CenterCrop(224)(transforms.Resize(256)(img))
    heat = (colormaps["jet"](cam)[..., :3] * 255).astype(np.uint8)
    mix = (0.55 * np.asarray(base) + 0.45 * heat).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(mix).save(buf, "PNG")
    return buf.getvalue()


def classify_soil(img: Image.Image, reg: ModelRegistry) -> tuple[dict, Optional[bytes]]:
    """Returns (result dict, Grad-CAM overlay PNG bytes or None when the photo is not soil)."""
    probs, cam = _forward_with_cam(reg.cnn, img.convert("RGB"))
    classes, ns = reg.classes, reg.not_soil_idx
    order = np.argsort(probs)[::-1]
    name = lambda i: classes[i] if i == ns else canon_class(classes[i])     # noqa: E731  (Not_Soil stays as it is)
    top3 = [{"soil_class": name(i), "probability": round(float(probs[i]), 3)} for i in order[:3]]
    soil_order = [int(i) for i in order if i != ns]            # soil classes only, best first
    p_not = float(probs[ns]) if ns is not None else 0.0

    rejected = ns is not None and (order[0] == ns or (NOT_SOIL_REJECT is not None and p_not >= NOT_SOIL_REJECT))
    soil, candidates = None, []
    if rejected:
        tier, key, conf = "not_soil", "soil.not_soil", p_not
    else:
        p1 = conf = float(probs[soil_order[0]])
        if p1 >= SOIL_CONFIDENT:
            tier, key, soil = "confident", "soil.confident", name(soil_order[0])
            candidates = [{"soil_class": soil, "probability": round(p1, 3)}]
        elif p1 >= SOIL_CONFIRM:
            tier, key = "confirm", "soil.confirm"
            candidates = [{"soil_class": name(i), "probability": round(float(probs[i]), 3)} for i in soil_order[:2]]
        else:
            tier, key = "retake", "soil.retake"
    result = {"available": True, "tier": tier, "soil_class": soil, "confidence": round(conf, 3),
              "candidates": candidates, "top3": top3, "message_key": key}
    return result, (None if tier == "not_soil" else _overlay_png(img, cam))
