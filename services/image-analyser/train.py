"""Training loop with early stopping and checkpoint for doc-type classifier."""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from model import build_model


def train(
    train_ds,
    val_ds,
    epochs: int = 10,
    lr: float = 1e-3,
    patience: int = 3,
    save_path: str = "artifacts/model.pth",
) -> float:
    """Fine-tune model head; save best checkpoint. Returns final val accuracy."""
    model = build_model()
    optimizer = torch.optim.Adam(model.fc.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()

    train_loader = DataLoader(train_ds, batch_size=8, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=8, shuffle=False)

    best_val_loss = float("inf")
    no_improve = 0
    best_acc = 0.0

    for epoch in range(epochs):
        model.train()
        for x, y in train_loader:
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()

        # validation
        model.eval()
        val_loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for x, y in val_loader:
                logits = model(x)
                val_loss += criterion(logits, y).item() * len(y)
                correct += (logits.argmax(1) == y).sum().item()
                total += len(y)

        val_loss /= max(total, 1)
        val_acc = correct / max(total, 1)
        print(f"epoch {epoch + 1}/{epochs} - val_loss={val_loss:.4f} val_acc={val_acc:.4f}")

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_acc = val_acc
            no_improve = 0
            torch.save(model.state_dict(), save_path)
        else:
            no_improve += 1
            if no_improve >= patience:
                print("early stopping")
                break

    return best_acc


def load_model(path: str) -> nn.Module:
    """Load a checkpoint saved by train(); returns model in eval mode."""
    model = build_model()
    model.load_state_dict(torch.load(path, map_location="cpu", weights_only=True))
    model.eval()
    return model
