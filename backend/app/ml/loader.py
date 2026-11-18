"""Loads the trained models once and hands them to the endpoints.

Each model is loaded on its own. A missing file does not stop the server: the analysis simply skips that
part and says so in its result (message key `analysis.models_unavailable`), so the lab-only analysis keeps
working while you are still developing.

    models/soil_cnn.onnx + soil_cnn_head.npz   the image model for servers (no PyTorch needed; see scripts/export_onnx.py)
    models/<cnn_file>           or the 8-class EfficientNet-B0 checkpoint {"classes", "state_dict"} (needs PyTorch)
    models/fert_model.joblib    {"model", "label_encoder", "columns"}
    models/inference_config.json  fertilizer defaults + training ranges
"""
import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import settings

log = logging.getLogger("soil.ml")
NOT_SOIL_LABEL = "Not_Soil"
MODEL_VERSION = "m2-effnetb0-xgb-1"


def canon_class(raw: str) -> str:
    """'Arid_Soil' -> 'Arid', 'Black_Soil' -> 'Black'. The tables and the frontend use the short names."""
    return raw.replace("_Soil", "").replace("_", " ").strip().title()


@dataclass
class ModelRegistry:
    cnn: Any = None
    classes: list[str] = field(default_factory=list)
    not_soil_idx: Optional[int] = None
    fert: Optional[dict] = None
    cfg: dict = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)   # part name -> why it is missing

    @property
    def image_ready(self) -> bool:
        return self.cnn is not None

    @property
    def fert_ready(self) -> bool:
        return self.fert is not None and bool(self.cfg)


def load_registry(model_dir: Path, cnn_file: str) -> ModelRegistry:
    reg = ModelRegistry()
    model_dir = Path(model_dir)

    cnn_path = model_dir / cnn_file
    onnx_path, head_path = model_dir / "soil_cnn.onnx", model_dir / "soil_cnn_head.npz"
    if onnx_path.exists() and head_path.exists():
        try:
            from app.ml.onnx_cnn import OnnxCnn

            reg.cnn = OnnxCnn(onnx_path, head_path)
            reg.classes = list(reg.cnn.classes)
            reg.not_soil_idx = reg.classes.index(NOT_SOIL_LABEL) if NOT_SOIL_LABEL in reg.classes else None
        except Exception as exc:
            log.exception("could not load the ONNX CNN")
            reg.errors["image"] = f"{type(exc).__name__}: {exc}"
    elif cnn_path.exists():
        try:
            import torch
            import torch.nn as nn
            from torchvision import models

            torch.set_num_threads(max(1, (__import__("os").cpu_count() or 2) // 2))
            ckpt = torch.load(cnn_path, map_location="cpu", weights_only=True)
            classes = list(ckpt["classes"])
            net = models.efficientnet_b0(weights=None)
            net.classifier[1] = nn.Linear(net.classifier[1].in_features, len(classes))
            net.load_state_dict(ckpt["state_dict"])
            net.eval()
            reg.cnn, reg.classes = net, classes
            reg.not_soil_idx = classes.index(NOT_SOIL_LABEL) if NOT_SOIL_LABEL in classes else None
        except Exception as exc:  # a broken checkpoint must not take the whole API down
            log.exception("could not load the CNN")
            reg.errors["image"] = f"{type(exc).__name__}: {exc}"
    else:
        reg.errors["image"] = f"missing file {cnn_path}"

    fert_path, cfg_path = model_dir / "fert_model.joblib", model_dir / "inference_config.json"
    if fert_path.exists() and cfg_path.exists():
        try:
            import joblib

            reg.fert = joblib.load(fert_path)
            reg.cfg = json.loads(cfg_path.read_text())
        except Exception as exc:
            log.exception("could not load the fertilizer model")
            reg.errors["fertilizer"] = f"{type(exc).__name__}: {exc}"
    else:
        reg.errors["fertilizer"] = f"missing file {fert_path if not fert_path.exists() else cfg_path}"
    return reg


_registry: Optional[ModelRegistry] = None
_lock = threading.Lock()


def get_registry() -> ModelRegistry:
    """FastAPI dependency. Loaded on first use; tests override it with stand-in models."""
    global _registry
    if _registry is None:
        with _lock:
            if _registry is None:
                _registry = load_registry(settings.model_dir, settings.cnn_file)
    return _registry
