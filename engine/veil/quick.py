"""Quick tier: instant, no-ML perturbation.

A deterministic, low-visibility high-frequency texture that adds friction for
naive scrapers and feature extractors. It is *not* a substitute for the Deep
pass — it is the zero-dependency fallback that also runs inside the Photoshop
plugin (mirrored in ``plugin/src/quick.js``), so the algorithm here is kept
simple enough to reimplement faithfully in plain JavaScript.

Everything works in normalised float [0, 1] so it is independent of bit depth
(the plugin feeds 8- or 16-bit documents through the same path).
"""
from __future__ import annotations

import numpy as np

# Peak amplitude, expressed in normalised [0, 1] units (≈ 1..8 of 255).
_AMP_BASE = 1.0 / 255.0
_AMP_SPAN = 7.0 / 255.0


def _hash01(idx: np.ndarray, seed: int) -> np.ndarray:
    """Counter-based integer hash -> float in [0, 1). Mirrored in JS."""
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
    h = (p[:, :-2] + 2.0 * p[:, 1:-1] + p[:, 2:]) * 0.25
    v = (h[:-2, :] + 2.0 * h[1:-1, :] + h[2:, :]) * 0.25
    return v


def quick_protect_float(rgb01: np.ndarray, strength: float = 0.5, seed: int = 1) -> np.ndarray:
    """Core: normalised float in, normalised float out.

    ``rgb01`` is (H, W) or (H, W, C) in [0, 1]. Colour channels (up to 3) are
    perturbed; any extra channel (alpha) is passed through untouched.
    """
    rgb01 = np.asarray(rgb01, dtype=np.float32)
    single = rgb01.ndim == 2
    if single:
        rgb01 = rgb01[..., None]
    h, w, c = rgb01.shape
    color_channels = min(c, 3)

    strength = float(max(0.0, min(1.0, strength)))
    amp = _AMP_BASE + _AMP_SPAN * strength

    out = rgb01.copy()
    idx_base = np.arange(h * w, dtype=np.uint64).reshape(h, w)
    for ch in range(color_channels):
        vals = _hash01((idx_base * 3 + ch).astype(np.uint32), seed).reshape(h, w)
        noise = (vals * 2.0 - 1.0).astype(np.float32)
        hp = noise - _blur3(noise)
        peak = float(np.max(np.abs(hp)))
        if peak > 1e-6:
            hp = hp / peak
        out[..., ch] += amp * hp

    np.clip(out, 0.0, 1.0, out=out)
    return out[..., 0] if single else out


def quick_protect(img: np.ndarray, strength: float = 0.5, seed: int = 1) -> np.ndarray:
    """Convenience wrapper for 8-bit ``uint8`` images (CLI / tests)."""
    img = np.asarray(img)
    out01 = quick_protect_float(img.astype(np.float32) / 255.0, strength, seed)
    return (out01 * 255.0).round().clip(0, 255).astype(np.uint8)
