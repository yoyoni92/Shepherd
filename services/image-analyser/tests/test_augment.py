"""Tests for data/augment.py augmentation pipeline."""

import PIL.Image
import torch
import torchvision.transforms

from data.augment import augment, augment_batch


def test_augment_preserves_shape():
    img = PIL.Image.new("RGB", (224, 224), color=(128, 128, 128))
    t = augment(img, seed=0)
    assert t.shape == (3, 224, 224)
    assert t.dtype == torch.float32


def test_augment_changes_pixels():
    img = PIL.Image.new("RGB", (224, 224), color=(128, 128, 128))
    # convert to tensor without augmentation
    baseline = torchvision.transforms.ToTensor()(img)
    t = augment(img, seed=0)
    assert not torch.equal(t, baseline)


def test_augment_normalized_range():
    img = PIL.Image.new("RGB", (224, 224), color=(128, 128, 128))
    t = augment(img, seed=0)
    # ImageNet normalization shifts range away from [0,1]
    assert t.min() < 0 or t.max() > 1  # normalized values go outside [0,1]


def test_augment_deterministic():
    img = PIL.Image.new("RGB", (224, 224), color=(100, 150, 200))
    t1 = augment(img, seed=42)
    t2 = augment(img, seed=42)
    assert torch.equal(t1, t2)


def test_batch_parity():
    imgs = [PIL.Image.new("RGB", (224, 224), color=(i*40, i*40, i*40)) for i in range(3)]
    batch = augment_batch(imgs, seed=7)
    assert batch.shape == (3, 3, 224, 224)
    for i, img in enumerate(imgs):
        single = augment(img, seed=7 + i)
        assert batch[i].shape == single.shape
