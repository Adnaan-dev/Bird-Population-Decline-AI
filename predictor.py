import torch
import numpy as np
import rasterio

def compute_indices(img):
    RED  = img[3]
    GREEN = img[2]
    NIR  = img[7]
    SWIR = img[11]
    eps = 1e-6

    ndvi = (NIR - RED) / (NIR + RED + eps)
    ndwi = (GREEN - NIR) / (GREEN + NIR + eps)
    ndbi = (SWIR - NIR) / (SWIR + NIR + eps)
    return ndvi, ndwi, ndbi

def predict_image(model, image_path):
    with rasterio.open(image_path) as src:
        img = src.read().astype(np.float32)

    img = img / (img.max() + 1e-6)
    ndvi, ndwi, ndbi = compute_indices(img)

    tensor = torch.tensor(img).unsqueeze(0)
    with torch.no_grad():
        score = float(model(tensor).cpu().numpy()[0])

    risk = 100 - score

    return {
        "habitat_score": score,
        "bird_decline_risk": risk,
        "mean_ndvi": float(np.nanmean(ndvi)),
        "mean_ndwi": float(np.nanmean(ndwi)),
        "mean_ndbi": float(np.nanmean(ndbi))
    }
