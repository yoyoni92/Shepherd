import torch
from model import build_model


def test_output_shape():
    model = build_model()
    model.eval()
    batch = torch.randn(4, 3, 224, 224)
    with torch.no_grad():
        out = model(batch)
    assert out.shape == (4, 5)


def test_backbone_frozen():
    model = build_model()
    frozen = [p for p in model.parameters() if not p.requires_grad]
    assert len(frozen) > 0, "backbone should have frozen params"


def test_head_trainable():
    model = build_model()
    trainable = [p for p in model.parameters() if p.requires_grad]
    assert len(trainable) > 0, "head should have trainable params"
    # head should be small relative to backbone
    n_trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    n_total = sum(p.numel() for p in model.parameters())
    assert n_trainable < n_total * 0.01, "only head should be trainable"
