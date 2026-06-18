"""Inference with confidence threshold for doc-type classification."""

import torch
import torch.nn as nn
import PIL.Image

from data.dataset import CLASSES
from data.augment import augment


def infer(image: PIL.Image.Image, model: nn.Module, threshold: float = 0.6) -> dict:
    """Classify a single image with confidence threshold.

    Args:
        image: PIL RGB image
        model: PyTorch model in eval mode
        threshold: confidence threshold (default 0.6)

    Returns:
        {"doc_type": str, "confidence": float}
    """
    return infer_batch([image], model, threshold)[0]


def infer_batch(images: list, model: nn.Module, threshold: float = 0.6) -> list:
    """Classify a batch of images with confidence threshold.

    Args:
        images: list of PIL RGB images
        model: PyTorch model in eval mode
        threshold: confidence threshold (default 0.6)

    Returns:
        list of {"doc_type": str, "confidence": float} dicts
    """
    # Augment each image with a unique seed for deterministic per-image inference
    batch_tensor = torch.stack([augment(img, seed=i) for i, img in enumerate(images)])

    # Forward pass
    with torch.no_grad():
        logits = model(batch_tensor)

    # Apply softmax
    probs = torch.softmax(logits, dim=-1)

    # Get max confidence and argmax
    max_confs, argmaxes = torch.max(probs, dim=-1)

    # Build results
    results = []
    for conf, argmax in zip(max_confs, argmaxes):
        conf_val = conf.item()
        if conf_val < threshold:
            doc_type = "uncertain"
        else:
            doc_type = CLASSES[argmax.item()]
        results.append({"doc_type": doc_type, "confidence": conf_val})

    return results
