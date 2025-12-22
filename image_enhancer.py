import cv2
import numpy as np
from PIL import Image


def enhance_scan_for_ocr(pil_img: Image.Image) -> Image.Image:
    img_np = np.array(pil_img)
    if img_np.ndim == 3:
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_np

    denoised = cv2.bilateralFilter(gray, d=5, sigmaColor=5, sigmaSpace=5)
    background = cv2.medianBlur(denoised, 81)
    diff = denoised.astype(np.float32) - background.astype(np.float32)
    normalized = np.clip(diff + 128, 0, 255).astype(np.uint8)
    clahe = cv2.createCLAHE(clipLimit=1.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(normalized)
    result_rgb = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)
    return Image.fromarray(result_rgb)
