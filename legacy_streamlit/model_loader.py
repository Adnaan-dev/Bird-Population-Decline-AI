import torch
import torch.nn as nn
from torchvision import models

def load_model(model_path="bird_decline_model.pth"):
    checkpoint = torch.load(model_path, map_location="cpu")

    model = models.resnet18(weights=None)
    model.conv1 = nn.Conv2d(13, 64, kernel_size=7, stride=2, padding=3, bias=False)
    model.fc = nn.Linear(512, 1)

    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model
