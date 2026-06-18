"""Dataset and stratified split for fleet document image classification."""

import numpy as np
from torch.utils.data import Dataset

from data.augment import augment

CLASSES = ["annual_license", "insurance_cert", "other", "traffic_ticket", "vehicle_photo"]

_CLASS_TO_IDX = {c: i for i, c in enumerate(CLASSES)}


class DocDataset(Dataset):
    def __init__(self, images, labels, indices=None):
        self.images = images
        self.labels = labels
        # indices tracks original positions (for leak detection)
        self.indices = list(range(len(images))) if indices is None else list(indices)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, i):
        tensor = augment(self.images[i], seed=i)
        label_idx = _CLASS_TO_IDX[self.labels[i]]
        return tensor, label_idx


def split_dataset(images, labels, seed):
    """Stratified 70/15/15 train/val/test split.

    Returns three DocDataset instances with no index overlap.
    """
    rng = np.random.RandomState(seed)
    labels_arr = np.array(labels)

    train_idx, val_idx, test_idx = [], [], []

    for cls in CLASSES:
        cls_indices = np.where(labels_arr == cls)[0]
        cls_indices = rng.permutation(cls_indices)
        n = len(cls_indices)
        n_train = max(1, round(n * 0.70))
        n_val = max(1, round(n * 0.15))
        # remainder goes to test
        train_idx.extend(cls_indices[:n_train].tolist())
        val_idx.extend(cls_indices[n_train:n_train + n_val].tolist())
        test_idx.extend(cls_indices[n_train + n_val:].tolist())

    def _make_ds(idx_list):
        imgs = [images[i] for i in idx_list]
        lbls = [labels[i] for i in idx_list]
        return DocDataset(imgs, lbls, indices=idx_list)

    return _make_ds(train_idx), _make_ds(val_idx), _make_ds(test_idx)
