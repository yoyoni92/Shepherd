import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from data.generate import generate
from data.dataset import DocDataset, split_dataset


def test_split_ratios():
    imgs, labels = generate(seed=0, n_per_class=20)  # 100 total
    train, val, test = split_dataset(imgs, labels, seed=42)
    assert len(train) >= 60  # ~70%
    assert len(val) >= 10    # ~15%
    assert len(test) >= 10   # ~15%
    assert len(train) + len(val) + len(test) == len(imgs)


def test_split_all_classes_in_each():
    imgs, labels = generate(seed=0, n_per_class=20)
    train, val, test = split_dataset(imgs, labels, seed=42)
    for ds in (train, val, test):
        class_indices = {ds.labels[i] for i in range(len(ds))}
        assert len(class_indices) == 5


def test_split_no_leak():
    imgs, labels = generate(seed=0, n_per_class=20)
    train, val, test = split_dataset(imgs, labels, seed=42)
    train_ids = set(train.indices)
    val_ids = set(val.indices)
    test_ids = set(test.indices)
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(test_ids)
    assert val_ids.isdisjoint(test_ids)


def test_dataset_item_shape():
    imgs, labels = generate(seed=0, n_per_class=5)
    ds = DocDataset(imgs, labels)
    tensor, label_idx = ds[0]
    assert tensor.shape == (3, 224, 224)
    assert isinstance(label_idx, int)
    assert 0 <= label_idx < 5
