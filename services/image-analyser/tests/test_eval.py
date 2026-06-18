import pytest
import os, numpy as np, torch
from data.generate import generate
from data.dataset import split_dataset
from train import train, load_model
from eval import evaluate


@pytest.mark.slow
def test_accuracy_gate():
    """Full train+eval cycle must reach >75% on held-out test set."""
    imgs, labels = generate(seed=42, n_per_class=80)  # 400 images
    train_ds, val_ds, test_ds = split_dataset(imgs, labels, seed=42)
    save_path = "/tmp/gate_model.pth"
    train(train_ds, val_ds, epochs=20, lr=1e-3, patience=5, save_path=save_path)
    model = load_model(save_path)
    result = evaluate(model, test_ds)
    assert result["accuracy"] > 0.75, f"accuracy {result['accuracy']:.2%} < 75%"
    assert result["confusion_matrix"].shape == (5, 5)
