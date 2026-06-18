"""Augmentation pipeline for fleet document images.

augment(image, seed) -> torch.Tensor [3, 224, 224] float32, ImageNet-normalized.
"""

import io

import PIL.Image
import torch
import torchvision.transforms as T

_MEAN = [0.485, 0.456, 0.406]
_STD = [0.229, 0.224, 0.225]

_GEOMETRIC = T.Compose([
    T.RandomRotation(degrees=10),
    T.RandomAffine(degrees=0, shear=8),
])

_PHOTOMETRIC = T.Compose([
    T.ColorJitter(brightness=0.4, contrast=0.4),
    T.GaussianBlur(kernel_size=3, sigma=(0.1, 1.5)),
])

_TO_TENSOR = T.ToTensor()
_NORMALIZE = T.Normalize(mean=_MEAN, std=_STD)


def _jpeg_round_trip(img: PIL.Image.Image, quality: int = 60) -> PIL.Image.Image:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return PIL.Image.open(buf).copy()


def augment(image: PIL.Image.Image, seed: int) -> torch.Tensor:
    """Apply augmentation pipeline to a single PIL image.

    Args:
        image: 224x224 RGB PIL image.
        seed: RNG seed for determinism.

    Returns:
        [3, 224, 224] float32 tensor, ImageNet-normalized.
    """
    torch.manual_seed(seed)

    img = _GEOMETRIC(image)
    img = _PHOTOMETRIC(img)
    img = _jpeg_round_trip(img)

    t = _TO_TENSOR(img)
    t = t + torch.randn_like(t) * 0.05
    t = _NORMALIZE(t)
    return t


def augment_batch(images: list, seed: int) -> torch.Tensor:
    """Augment a list of PIL images, using seed+i for the i-th image.

    Args:
        images: list of 224x224 RGB PIL images.
        seed: base RNG seed; image i uses seed+i.

    Returns:
        [N, 3, 224, 224] float32 tensor, ImageNet-normalized.
    """
    tensors = [augment(img, seed + i) for i, img in enumerate(images)]
    return torch.stack(tensors)
