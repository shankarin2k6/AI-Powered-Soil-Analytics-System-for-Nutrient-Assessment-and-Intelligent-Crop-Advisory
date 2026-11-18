"""One-time conversion of the trained PyTorch CNN to ONNX (a small file that needs no PyTorch to run).

    python scripts/export_onnx.py models/soil_cnn_D_hard_negatives.pt models

Writes models/soil_cnn.onnx (the image features) and models/soil_cnn_head.npz (the final layer + class names).
Needs torch and torchvision on the machine that runs this (not on the server).
"""
import sys, numpy as np, torch, torch.nn as nn
from torchvision import models
src, out = sys.argv[1], sys.argv[2]
ck = torch.load(src, map_location="cpu", weights_only=True)
classes = list(ck["classes"]); print(classes, ck.keys())
net = models.efficientnet_b0(weights=None)
net.classifier[1] = nn.Linear(net.classifier[1].in_features, len(classes))
net.load_state_dict(ck["state_dict"]); net.eval()
class Feat(nn.Module):
    def __init__(s, n): super().__init__(); s.f = n.features
    def forward(s, x): return s.f(x)
torch.onnx.export(Feat(net), torch.randn(1,3,224,224), f"{out}/soil_cnn.onnx", input_names=["image"], output_names=["features"],
                  dynamic_axes=None, opset_version=17, dynamo=False)
W = net.classifier[1].weight.detach().numpy(); b = net.classifier[1].bias.detach().numpy()
np.savez(f"{out}/soil_cnn_head.npz", W=W, b=b, classes=np.array(classes))
print(W.shape, b.shape)
