"""The model loader reads the same file formats the training notebooks write."""
import json

import pytest

torch = pytest.importorskip("torch")
joblib = pytest.importorskip("joblib")

from PIL import Image  # noqa: E402

from app.ml.image import classify_soil  # noqa: E402
from app.ml.loader import load_registry  # noqa: E402
from tests.standins import CLASSES, make_cnn, make_fert  # noqa: E402


def test_loads_checkpoint_and_joblib_from_disk(tmp_path):
    cnn = make_cnn({"Red": 5.0})
    torch.save({"classes": CLASSES, "state_dict": cnn.state_dict()}, tmp_path / "cnn.pt")
    fert, cfg = make_fert()
    joblib.dump(fert, tmp_path / "fert_model.joblib")
    (tmp_path / "inference_config.json").write_text(json.dumps(cfg))
    reg = load_registry(tmp_path, "cnn.pt")
    assert reg.image_ready and reg.fert_ready and not reg.errors
    assert reg.classes == CLASSES and reg.not_soil_idx == CLASSES.index("Not_Soil")
    res, png = classify_soil(Image.new("RGB", (300, 200), (150, 60, 40)), reg)
    assert res["tier"] == "confident" and res["soil_class"] == "Red" and png[:4] == b"\x89PNG"


def test_missing_files_are_reported_not_raised(tmp_path):
    reg = load_registry(tmp_path, "nothing.pt")
    assert not reg.image_ready and not reg.fert_ready
    assert set(reg.errors) == {"image", "fertilizer"}


def test_broken_checkpoint_does_not_crash(tmp_path):
    (tmp_path / "bad.pt").write_bytes(b"not a checkpoint")
    reg = load_registry(tmp_path, "bad.pt")
    assert not reg.image_ready and "image" in reg.errors


def test_gradcam_responds_to_the_image():
    """With real (non-zero) weights the heat-map must vary across the picture and stay in 0..1."""
    import numpy as np
    from app.ml.image import _forward_with_cam
    torch.manual_seed(0)
    net = make_cnn()
    torch.nn.init.normal_(net.classifier[1].weight, std=0.05)
    rng = np.random.default_rng(1)
    img = Image.fromarray(rng.integers(0, 255, (240, 320, 3), dtype=np.uint8))
    probs, cam = _forward_with_cam(net, img)
    assert cam.shape == (224, 224) and 0 <= cam.min() and cam.max() <= 1 and cam.std() > 0.01
    assert abs(probs.sum() - 1) < 1e-4


def test_onnx_model_matches_pytorch(tmp_path):
    """The server-side ONNX model (no PyTorch) must give the same probabilities and Grad-CAM as the checkpoint."""
    pytest.importorskip("onnxruntime")
    import numpy as np
    import subprocess
    import sys
    from pathlib import Path

    from app.ml import image as im

    cnn = make_cnn({"Red": 2.0})
    with torch.no_grad():   # a non-trivial last layer, so the heat-map is not flat
        torch.manual_seed(1)
        torch.nn.init.normal_(cnn.classifier[1].weight, std=0.05)
    torch.save({"classes": CLASSES, "state_dict": cnn.state_dict()}, tmp_path / "cnn.pt")
    script = Path(__file__).resolve().parents[1] / "scripts" / "export_onnx.py"
    subprocess.run([sys.executable, str(script), str(tmp_path / "cnn.pt"), str(tmp_path)], check=True, capture_output=True)
    reg = load_registry(tmp_path, "cnn.pt")
    assert type(reg.cnn).__name__ == "OnnxCnn" and reg.classes == CLASSES
    img = Image.fromarray(np.random.default_rng(3).integers(0, 255, (180, 260, 3), dtype="uint8"))
    p_onnx, cam_onnx = reg.cnn.forward(img)
    p_torch, cam_torch = im._torch_forward_with_cam(cnn, img)
    assert abs(p_onnx - p_torch).max() < 1e-3 and abs(cam_onnx - cam_torch).max() < 1e-2
    res, png = classify_soil(img, reg)
    assert res["available"] and (png is None or png[:4] == b"\x89PNG")
