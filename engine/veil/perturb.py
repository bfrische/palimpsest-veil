"""Deep tier: adversarial optimisation under a perceptual-visibility budget.

This is the Mist / PhotoGuard-style *encoder attack*: projected gradient descent
on the image that maximises the shift in a latent-diffusion encoder's feature
space (Cloak) and, for Shade, also steers the CLIP image embedding toward a
decoy concept — all while a hard L-infinity clamp (plus optional LPIPS penalty)
keeps the change low-visibility. Large images are processed in feathered,
overlapping tiles so encoder memory is bounded by tile size, not document size.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

import numpy as np

from . import config, modes
from .models import clip_text_embedding, get_device, load_clip, load_vae

# CLIP preprocessing constants (ImageNet-style stats CLIP was trained with).
_CLIP_MEAN = (0.48145466, 0.4578275, 0.40821073)
_CLIP_STD = (0.26862954, 0.26130258, 0.27577711)


def _clip_image_embed(model, img01, device):
    import torch
    import torch.nn.functional as F

    # bilinear (no antialias) for broad MPS compatibility.
    x = F.interpolate(img01, size=(224, 224), mode="bilinear", align_corners=False)
    mean = torch.tensor(_CLIP_MEAN, device=device).view(1, 3, 1, 1)
    std = torch.tensor(_CLIP_STD, device=device).view(1, 3, 1, 1)
    x = (x - mean) / std
    return model.get_image_features(pixel_values=x)


def _maybe_lpips():
    """Construct an LPIPS net, or return None if unavailable/unsupported."""
    try:
        import lpips  # noqa: F401
        net = lpips.LPIPS(net="alex", verbose=False).to(get_device())
        for p in net.parameters():
            p.requires_grad_(False)
        return net
    except Exception:
        return None


def _protect_tile(tile01, mode, eps, steps, decoy, lpips_fn):
    import torch

    device = get_device()
    vae, _ = load_vae()

    x = torch.from_numpy(tile01).permute(2, 0, 1).unsqueeze(0).float().to(device)
    with torch.no_grad():
        clean_latent = vae.encode(x * 2 - 1).latent_dist.mean

    clip_model = decoy_emb = None
    if mode == modes.SHADE:
        clip_model, _, _ = load_clip()
        decoy_emb = clip_text_embedding(decoy or modes.DEFAULT_DECOY)

    delta = torch.zeros_like(x, requires_grad=True)
    opt = torch.optim.Adam([delta], lr=max(eps / 4.0, 1e-3))

    for _ in range(steps):
        opt.zero_grad(set_to_none=True)
        adv = torch.clamp(x + delta, 0.0, 1.0)
        adv_latent = vae.encode(adv * 2 - 1).latent_dist.mean
        loss = modes.cloak_loss(adv_latent, clean_latent)
        if mode == modes.SHADE:
            img_emb = _clip_image_embed(clip_model, adv, device)
            loss = loss + 1.5 * modes.shade_loss(img_emb, decoy_emb)
        if lpips_fn is not None:
            loss = loss + 8.0 * lpips_fn(adv * 2 - 1, x * 2 - 1).mean()
        loss.backward()
        opt.step()
        with torch.no_grad():
            delta.clamp_(-eps, eps)

    adv = torch.clamp(x + delta.detach(), 0.0, 1.0)
    out = adv.squeeze(0).permute(1, 2, 0).cpu().numpy()
    return (out * 255.0).round().clip(0, 255).astype(np.uint8)


def _starts(total: int, size: int, overlap: int) -> List[int]:
    if total <= size:
        return [0]
    step = size - overlap
    starts = list(range(0, total - size + 1, step))
    if starts[-1] != total - size:
        starts.append(total - size)
    return starts


def _tile_grid(h: int, w: int, size: int, overlap: int):
    for y0 in _starts(h, size, overlap):
        for x0 in _starts(w, size, overlap):
            yield y0, min(y0 + size, h), x0, min(x0 + size, w)


def _feather(h: int, w: int, overlap: int) -> np.ndarray:
    def ramp(n: int) -> np.ndarray:
        r = np.ones(n, dtype=np.float32)
        o = min(overlap, n // 2)
        if o > 0:
            edge = (np.arange(o, dtype=np.float32) + 1.0) / (o + 1.0)
            r[:o] = edge
            r[-o:] = edge[::-1]
        return r

    return (ramp(h)[:, None] * ramp(w)[None, :])[..., None]


def deep_protect(
    img: np.ndarray,
    mode: str = modes.CLOAK,
    strength: float = 0.5,
    decoy: Optional[str] = None,
    steps: Optional[int] = None,
    use_lpips: bool = True,
    progress: Optional[Callable[[float], None]] = None,
) -> np.ndarray:
    """Protect an ``uint8`` image (H, W, 3 or 4). Alpha is passed through."""
    mode = modes.normalize_mode(mode)
    img = np.asarray(img)
    had_alpha = img.ndim == 3 and img.shape[2] == 4
    alpha = img[..., 3:4] if had_alpha else None
    rgb = img[..., :3].astype(np.float32) / 255.0
    h, w = rgb.shape[:2]

    eps = config.strength_to_eps(strength)
    steps = int(steps) if steps else config.strength_to_steps(strength)

    lpips_fn = _maybe_lpips() if use_lpips else None
    if lpips_fn is not None:  # preflight so a mid-loop failure can't abort a run
        try:
            import torch

            probe = torch.zeros(1, 3, 16, 16, device=get_device())
            lpips_fn(probe, probe)
        except Exception:
            lpips_fn = None

    acc = np.zeros((h, w, 3), dtype=np.float32)
    wacc = np.zeros((h, w, 1), dtype=np.float32)
    tiles = list(_tile_grid(h, w, config.TILE_SIZE, config.TILE_OVERLAP))
    for k, (y0, y1, x0, x1) in enumerate(tiles):
        tile = np.ascontiguousarray(rgb[y0:y1, x0:x1])
        res = _protect_tile(tile, mode, eps, steps, decoy, lpips_fn)
        wgt = _feather(y1 - y0, x1 - x0, config.TILE_OVERLAP)
        acc[y0:y1, x0:x1] += res.astype(np.float32) * wgt
        wacc[y0:y1, x0:x1] += wgt
        if progress:
            progress((k + 1) / len(tiles))

    out = (acc / np.maximum(wacc, 1e-6)).round().clip(0, 255).astype(np.uint8)
    if had_alpha:
        out = np.concatenate([out, alpha], axis=2)
    return out
