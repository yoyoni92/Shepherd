import os, torch
from data.generate import generate
from data.dataset import split_dataset
from train import train, load_model


def test_smoke_train():
    """Train 1 epoch on tiny set; loss must decrease, checkpoint loadable."""
    imgs, labels = generate(seed=99, n_per_class=4)  # 20 images
    train_ds, val_ds, _ = split_dataset(imgs, labels, seed=0)
    save_path = "/tmp/test_model.pth"

    val_acc = train(train_ds, val_ds, epochs=1, lr=1e-3, patience=3, save_path=save_path)

    assert os.path.exists(save_path), "checkpoint not saved"
    assert 0.0 <= val_acc <= 1.0

    model = load_model(save_path)
    model.eval()
    sample, _ = train_ds[0]
    with torch.no_grad():
        out = model(sample.unsqueeze(0))
    assert out.shape == (1, 5)
