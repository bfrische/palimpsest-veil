"""Image load/save and simple visibility metrics (numpy + Pillow only)."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image


def load_rgba(path: str | Path) -> Tuple[np.ndarray, bool]:
    """Load an image as an ``uint8`` array.

    Returns ``(array, had_alpha)``. RGB images come back as (H, W, 3); images
    with transparency as (H, W, 4).
    """
    im = Image.open(path)
    had_alpha = im.mode in ("RGBA", "LA", "PA") or "transparency" in im.info
    im = im.convert("RGBA" if had_alpha else "RGB")
    return np.asarray(im, dtype=np.uint8), had_alpha


def save(path: str | Path, arr: np.ndarray) -> None:
    arr = np.asarray(arr, dtype=np.uint8)
    mode = "RGBA" if arr.ndim == 3 and arr.shape[2] == 4 else "RGB"
    Image.fromarray(arr, mode=mode).save(path)


def psnr(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64)
    b = b.astype(np.float64)
    mse = float(np.mean((a - b) ** 2))
    if mse <= 1e-12:
        return float("inf")
    return 10.0 * float(np.log10((255.0 ** 2) / mse))


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    """Global SSIM on luminance — a lightweight visibility proxy (no SciPy)."""
    def luma(x: np.ndarray) -> np.ndarray:
        x = x.astype(np.float64)
        if x.ndim == 3:
            x = x[..., :3] @ np.array([0.299, 0.587, 0.114])
        return x

    x, y = luma(a), luma(b)
    mu_x, mu_y = x.mean(), y.mean()
    var_x, var_y = x.var(), y.var()
    cov = float(((x - mu_x) * (y - mu_y)).mean())
    c1, c2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    num = (2 * mu_x * mu_y + c1) * (2 * cov + c2)
    den = (mu_x ** 2 + mu_y ** 2 + c1) * (var_x + var_y + c2)
    return float(num / den)
