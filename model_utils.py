import torch
import torch.nn as nn
from torchvision import models
import numpy as np


# ---------------- NDVI / NDWI / NDBI ---------------- #

def compute_indices(img):
    """
    Compute NDVI, NDWI, NDBI from multi-band Sentinel image.
    img shape: [13, H, W]
    """
    RED = img[3]
    GREEN = img[2]
    NIR = img[7]
    SWIR = img[11]

    eps = 1e-6

    ndvi = (NIR - RED) / (NIR + RED + eps)
    ndwi = (GREEN - NIR) / (GREEN + NIR + eps)
    ndbi = (SWIR - NIR) / (SWIR + NIR + eps)

    return ndvi, ndwi, ndbi


# ---------------- CREATE RGB FROM BANDS ---------------- #

def make_rgb(img):
    """
    Create RGB visualization from bands:
    R = B04
    G = B03
    B = B02
    """
    r, g, b = img[3], img[2], img[1]
    rgb = np.stack([r, g, b], axis=-1)
    rgb = (rgb - rgb.min()) / (rgb.max() - rgb.min() + 1e-6)
    return rgb


# ---------------- LOAD TRAINED MODEL ---------------- #

def load_model():
    checkpoint = torch.load("bird_decline_model.pth", map_location="cpu")
    state_dict = checkpoint["model_state_dict"]

    # remove "model." prefix from keys
    new_state = {}
    for k, v in state_dict.items():
        new_state[k.replace("model.", "")] = v

    # base model
    model = models.resnet18(weights=None)

    # change 3-channel → 13-channel
    model.conv1 = nn.Conv2d(13, 64, kernel_size=7, stride=2, padding=3, bias=False)

    # final layer → 1 output (health score)
    model.fc = nn.Linear(512, 1)

    model.load_state_dict(new_state)
    model.eval()
    return model


# ---------------- RUN MODEL PREDICTION ---------------- #

def predict_image(model, img):
    """
    img shape: [13, H, W]
    Output:
    - habitat health score
    - bird decline risk
    - ndvi, ndwi, ndbi
    """
    img_norm = img / (img.max() + 1e-6)
    tensor = torch.tensor(img_norm).unsqueeze(0).float()  # shape: [1, 13, H, W]

    with torch.no_grad():
        score = float(model(tensor).cpu().numpy()[0])

    risk = 100 - score

    ndvi, ndwi, ndbi = compute_indices(img_norm)

    return score, risk, ndvi, ndwi, ndbi
