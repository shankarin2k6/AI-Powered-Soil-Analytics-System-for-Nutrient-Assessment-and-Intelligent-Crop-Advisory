"""Small stand-in models with the same shapes as the real ones, so the analysis code is tested without the
real model files. The CNN is steered with the bias of its last layer, so the predicted tier is predictable."""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import LabelEncoder
from torchvision import models
from xgboost import XGBClassifier

from app.ml.loader import ModelRegistry

CLASSES = ["Alluvial", "Arid", "Black", "Laterite", "Mountain", "Red", "Yellow", "Not_Soil"]
FERTS = ["Compost", "DAP", "MOP", "NPK", "SSP", "Urea", "Zinc Sulphate"]


def make_cnn(favoured: dict[str, float] | None = None) -> nn.Module:
    """EfficientNet-B0 whose output is just the bias: class -> logit. No favoured classes = all equal (a 'retake')."""
    net = models.efficientnet_b0(weights=None)
    net.classifier[1] = nn.Linear(net.classifier[1].in_features, len(CLASSES))
    with torch.no_grad():
        net.classifier[1].weight.zero_()
        net.classifier[1].bias.zero_()
        for name, logit in (favoured or {}).items():
            net.classifier[1].bias[CLASSES.index(name)] = logit
    return net.eval()


def make_fert():
    rng = np.random.default_rng(0)
    n = 700
    X = pd.DataFrame({
        "Soil_pH": rng.uniform(4.5, 9, n), "Soil_Moisture": rng.uniform(5, 60, n),
        "Organic_Carbon": rng.uniform(0.2, 2.5, n), "Electrical_Conductivity": rng.uniform(0.1, 3, n),
        "Nitrogen_Level": rng.uniform(0, 140, n), "Phosphorus_Level": rng.uniform(0, 140, n),
        "Potassium_Level": rng.uniform(0, 200, n)})
    for prefix, vals in {"Soil_Type": ["Clay", "Loamy", "Sandy", "Silt"], "Crop_Type": ["Maize", "Wheat"],
                         "Crop_Growth_Stage": ["Sowing", "Vegetative"], "Season": ["Kharif", "Rabi"]}.items():
        pick = rng.choice(vals, n)
        for v in vals:
            X[f"{prefix}_{v}"] = pick == v
    y = np.where(X.Nitrogen_Level < 40, "Urea", np.where(X.Phosphorus_Level < 40, "DAP",
        np.where(X.Potassium_Level < 60, "MOP", np.where(X.Soil_pH < 5.5, "Compost", None))))
    rest = rng.choice(["NPK", "SSP", "Zinc Sulphate"], n)
    y = np.where(y == None, rest, y)  # noqa: E711
    le = LabelEncoder().fit(FERTS)
    model = XGBClassifier(n_estimators=25, max_depth=3, random_state=0).fit(X, le.transform(y))
    cfg = {"fert_defaults": {"Soil_Moisture": 30.0, "Organic_Carbon": 0.8, "Electrical_Conductivity": 1.0,
                             "Soil_Type": "Loamy"},
           "ranges": {"fert": {"Nitrogen_Level": [0, 140], "Soil_pH": [4.5, 9]}}}
    return {"model": model, "label_encoder": le, "columns": list(X.columns)}, cfg


def make_registry(favoured: dict[str, float] | None = None, image=True, fert=True) -> ModelRegistry:
    reg = ModelRegistry()
    if image:
        reg.cnn, reg.classes, reg.not_soil_idx = make_cnn(favoured), CLASSES, CLASSES.index("Not_Soil")
    else:
        reg.errors["image"] = "stand-in: not loaded"
    if fert:
        reg.fert, reg.cfg = make_fert()
    else:
        reg.errors["fertilizer"] = "stand-in: not loaded"
    return reg
