"""The image model without PyTorch: ONNX Runtime runs the EfficientNet-B0 feature extractor and numpy does the last layer.

Files made once by scripts/export_onnx.py:
    models/soil_cnn.onnx        image (1,3,224,224) -> last conv feature map (1,1280,7,7)
    models/soil_cnn_head.npz    W (classes x 1280), b, classes

The network ends with  average-pool -> (dropout, off at inference) -> linear,  so the class score is
    score_c = W_c . mean(feature map) + b_c
and its gradient with respect to every feature-map value is W_c / 49. That makes Grad-CAM a one-line
calculation without autograd, with the same result as the PyTorch version.
"""
from pathlib import Path

import numpy as np

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)


def preprocess_pil(img):
    """PIL image -> the 224x224 centre crop (resize shorter side to 256 first), as in the training pipeline."""
    from PIL import Image

    w, h = img.size
    short = 256
    nw, nh = (short, max(1, int(short * h / w))) if w <= h else (max(1, int(short * w / h)), short)
    img = img.resize((nw, nh), Image.BILINEAR)
    left, top = int(round((nw - 224) / 2.0)), int(round((nh - 224) / 2.0))
    return img.crop((left, top, left + 224, top + 224))


def preprocess(img):
    """PIL image -> (1,3,224,224) float32, normalised."""
    x = np.asarray(preprocess_pil(img), dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    return (x - MEAN) / STD


class OnnxCnn:
    def __init__(self, onnx_path: Path, head_path: Path):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.enable_mem_pattern = False       # smaller memory footprint on small servers
        self.session = ort.InferenceSession(str(onnx_path), opts, providers=["CPUExecutionProvider"])
        head = np.load(head_path, allow_pickle=False)
        self.W, self.b = head["W"].astype(np.float32), head["b"].astype(np.float32)
        self.classes = [str(c) for c in head["classes"]]

    def forward(self, img):
        """Returns (probabilities, Grad-CAM heat-map 224x224 in 0..1) for the predicted class."""
        import cv2

        a = self.session.run(None, {"image": preprocess(img)})[0][0]          # (1280, 7, 7)
        logits = self.W @ a.mean(axis=(1, 2)) + self.b
        e = np.exp(logits - logits.max())
        probs = e / e.sum()
        w = self.W[int(probs.argmax())] / a.shape[1] / a.shape[2]              # = gradient, averaged over the map
        cam = np.maximum((w[:, None, None] * a).sum(axis=0), 0).astype(np.float32)
        cam = cv2.resize(cam, (224, 224), interpolation=cv2.INTER_LINEAR)
        span = float(cam.max() - cam.min())
        cam = (cam - cam.min()) / span if span > 0 else np.zeros_like(cam)
        return probs, cam
