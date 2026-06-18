"""Evaluation script for doc-type classifier. Computes accuracy and confusion matrix."""

import argparse
import os
import numpy as np
import torch
from torch.utils.data import DataLoader

from data.generate import generate
from data.dataset import split_dataset
from train import load_model


def evaluate(model, test_ds) -> dict:
    """
    Runs model in eval mode on test_ds.
    Returns {"accuracy": float, "confusion_matrix": np.ndarray shape [5,5]}
    Confusion matrix: rows = true class, cols = predicted class.
    """
    loader = DataLoader(test_ds, batch_size=32, shuffle=False)

    all_preds = []
    all_labels = []

    model.eval()
    with torch.no_grad():
        for x, y in loader:
            logits = model(x)
            preds = logits.argmax(1)
            all_preds.append(preds.cpu().numpy())
            all_labels.append(y.cpu().numpy())

    all_preds = np.concatenate(all_preds)
    all_labels = np.concatenate(all_labels)

    accuracy = (all_preds == all_labels).mean()

    cm = np.zeros((5, 5), dtype=np.int64)
    for true_idx, pred_idx in zip(all_labels, all_preds):
        cm[true_idx, pred_idx] += 1

    return {
        "accuracy": float(accuracy),
        "confusion_matrix": cm
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate doc-type classifier on test set")
    parser.add_argument("--checkpoint", type=str, default="artifacts/model.pth",
                        help="Path to model checkpoint")
    parser.add_argument("--seed", type=int, default=0,
                        help="Random seed for data generation")
    parser.add_argument("--n-per-class", type=int, default=80,
                        help="Number of images per class")
    args = parser.parse_args()

    imgs, labels = generate(seed=args.seed, n_per_class=args.n_per_class)
    _, _, test_ds = split_dataset(imgs, labels, seed=args.seed)

    model = load_model(args.checkpoint)
    result = evaluate(model, test_ds)

    print(result["accuracy"])

    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/accuracy.txt", "w") as f:
        f.write(str(result["accuracy"]))
    np.save("artifacts/confusion_matrix.npy", result["confusion_matrix"])


if __name__ == "__main__":
    main()
