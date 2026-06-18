import torch.nn as nn
from torchvision.models import resnet50, ResNet50_Weights


def build_model() -> nn.Module:
    model = resnet50(weights=ResNet50_Weights.DEFAULT)
    for p in model.parameters():
        p.requires_grad = False
    model.fc = nn.Linear(model.fc.in_features, 5)
    return model
