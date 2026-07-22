"""Quick tier: instant, no-ML perturbation.

A deterministic, low-visibility high-frequency texture that adds friction for
naive scrapers and feature extractors. It is *not* a substitute for the Deep
pass — it is the zero-dependency fallback that also runs inside the Photoshop
plugin (mirrored in ``plugin/src/quick.js``), so the algorithm here is kept
simple enough to reimplement faithfully in plain JavaScript.

The perturbation is placed in the highest spatial frequencies (a random field
minus its own blur), which the human eye tolerates far better than low-frequency
changes while still disturbing the statistics a model learns from.
"""
from __future__ import annotations

import numpy as np


def _hash01(idx: np.ndarray, seed: int) -> np.ndarray:
    """Counter-based integer hash -> float in [0, 1).

    Deterministic and dependency-free so the exact same construction can be
    mirrored in JavaScript (Math.imul + >>> 0). Uses the Murmur3-style finaliser.
    """
    x = (idx.astype(np.uint32) + np.uint32((seed * 0x9E3779B1) & 0xFFFFFFFF)).astype(np.uint32)
    x ^= x >> np.uint32(16)
    x = (x * np.uint32(0x7FEB352D)).astype(np.uint32)
    x ^= x >> np.uint32(15)
    x = (x * np.uint32(0x846CA68B)).astype(np.uint32)
    x ^= x >> np.uint32(16)
    return x.astype(np.float64) / 4294967296.0


def _blur3(a: np.ndarray) -> np.ndarray:
    """Separable 1-2-1 blur with edge replication (a mild low-pass)."""
    p = np.pad(a, 1, mode="edge")
    h = (p[:, :-2] + 2.0 * p[:, 1:-1] + p[:, 2:]) * 0.25          # -> (H+2, W)
    v = (h[:-2, :] + 2.0 * h[1:-1, :] + h[2:, :]) * 0.25          # -> (H,   W)
    return v


def quick_protect(img: np.ndarray, strength: float = 0.5, seed: int = 1) -> np.ndarray:
    """Apply the Quick perturbation to an ``uint8`` image array.

    Parameters
    ----------
    img : ndarray, shape (H, W) or (H, W, C)
        Input image, ``uint8``. An alpha channel (index 3) is passed through
        untouched; only the colour channels are perturbed.
    strength : float in [0, 1]
        Maps to a peak amplitude of roughly 1..8 code values (< ~3%).
    seed : int
        Fixes the noise field, making the transform reproducible.
    """
    img = np.asarray(img)
    single = img.ndim == 2
    if single:
        img = img[..., None]
    h, w, c = img.shape
    color_channels = min(c, 3)

    strength = float(max(0.0, min(1.0, strength)))
    amp = 1.0 + 7.0 * strength  # peak amplitude in 0..255 code values

    out = img.astype(np.float32).copy()
    idx_base = np.arange(h * w, dtype=np.uint64).reshape(h, w)
    for ch in range(color_channels):
        vals = _hash01((idx_base * 3 + ch).astype(np.uint32), seed).reshape(h, w)
        noise = (vals * 2.0 - 1.0).astype(np.float32)
        hp = noise - _blur3(noise)
        peak = float(np.max(np.abs(hp)))
        if peak > 1e-6:
            hp = hp / peak
        out[..., ch] += amp * hp

    np.clip(out, 0, 255, out=out)
    out = out.astype(np.uint8)
    return out[..., 0] if single else out
