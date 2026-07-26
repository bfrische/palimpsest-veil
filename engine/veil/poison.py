"""Poison mode — Nightshade-style concept poisoning.

Unlike Cloak/Shade (which perturb CLIP or a diffusion encoder to *disrupt*
mimicry), Poison drags each image's VAE latent toward the latent of a *decoy
concept* — the exact target a diffusion model learns from. A model trained on
poisoned images learns the wrong concept: verified end-to-end (eagles -> cars).

The decoy word is turned into an anchor image with Stable Diffusion, encoded
once to a target latent (cached under ~/.cache/palimpsest-veil/anchors), then the
optimiser matches each protected image's centre-crop latent to it. The
perturbation is concentrated in textured detail (``_detail_mask``) and bounded by
a budget; the verified floor for cross-VAE transfer is ~0.10.
"""
from __future__ import annotations

import hashlib
from typing import Callable, Optional

import numpy as np

from . import config
from .models import get_device, load_vae
from .perturb import _detail_mask

_SD = None


def _load_sd():
    global _SD
    if _SD is None:
        from diffusers import StableDiffusionPipeline

        config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _SD = StableDiffusionPipeline.from_pretrained(
            config.SD_MODEL_ID, safety_checker=None, requires_safety_checker=False,
            cache_dir=str(config.CACHE_DIR),
        ).to(get_device())
        _SD.set_progress_bar_config(disable=True)
    return _SD


def _free_sd():
    global _SD
    _SD = None
    import torch

    if get_device().type == "mps":
        torch.mps.empty_cache()


def _to_tensor(im, device, size=512):
    import torch

    im = im.convert("RGB").resize((size, size))
    a = np.asarray(im, np.float32) / 255.0
    return torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0).to(device)


def anchor_latent(decoy: str):
    """Target latent for a decoy concept (cached; generates the anchor once)."""
    import torch

    vae, device = load_vae()
    decoy = (decoy or "abstract sculpture").strip()
    config.ANCHOR_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.md5(decoy.lower().encode()).hexdigest()[:12]
    path = config.ANCHOR_DIR / f"{key}.pt"
    if path.exists():
        return torch.load(path, map_location=device)

    pipe = _load_sd()
    img = pipe(f"a photo of {decoy}", num_inference_steps=30, guidance_scale=7.5,
               generator=torch.Generator(device).manual_seed(0)).images[0]
    with torch.no_grad():
        lat = vae.encode(_to_tensor(img, device) * 2 - 1).latent_dist.mean
    torch.save(lat.cpu(), path)
    _free_sd()
    return lat.to(device)


def _center512(t):
    """Centre-crop to square and resize to 512 — matching how trainers preprocess."""
    import torch.nn.functional as F

    _, _, h, w = t.shape
    s = min(h, w)
    top, left = (h - s) // 2, (w - s) // 2
    t = t[:, :, top:top + s, left:left + s]
    return F.interpolate(t, size=(512, 512), mode="bilinear", align_corners=False)


def poison_protect_float(
    rgb01: np.ndarray,
    decoy: str,
    strength: float = 0.5,
    steps: Optional[int] = None,
    progress: Optional[Callable[[float], None]] = None,
) -> np.ndarray:
    """Poison an image (normalised float RGB, H, W, 3) toward the decoy concept."""
    import torch
    import torch.nn.functional as F

    vae, device = load_vae()
    target = anchor_latent(decoy).to(device)
    eps = config.poison_strength_to_eps(strength)
    steps = int(steps) if steps else config.poison_strength_to_steps(strength)

    rgb = np.asarray(rgb01, dtype=np.float32)[..., :3]
    h, w = rgb.shape[:2]
    x_full = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).unsqueeze(0).float().to(device)

    scale = min(1.0, config.POISON_WORK_MAX / max(h, w))
    x = (F.interpolate(x_full, scale_factor=scale, mode="bilinear", align_corners=False).clamp(0, 1)
         if scale < 1.0 else x_full)
    mask = _detail_mask(x)

    delta = torch.zeros_like(x, requires_grad=True)
    opt = torch.optim.Adam([delta], lr=max(eps / 4.0, 1e-3))
    for i in range(steps):
        opt.zero_grad(set_to_none=True)
        adv = torch.clamp(x + delta * mask, 0.0, 1.0)
        lat = vae.encode(_center512(adv) * 2 - 1).latent_dist.mean
        loss = F.mse_loss(lat, target)
        loss.backward()
        opt.step()
        with torch.no_grad():
            delta.clamp_(-eps, eps)
        if progress:
            progress((i + 1) / steps)

    with torch.no_grad():
        if scale < 1.0:
            mask_full = _detail_mask(x_full)
            dfull = F.interpolate(delta.detach(), size=(h, w), mode="bilinear", align_corners=False)
            adv_full = torch.clamp(x_full + (dfull * mask_full).clamp(-eps, eps), 0.0, 1.0)
        else:
            adv_full = torch.clamp(x_full + delta.detach() * mask, 0.0, 1.0)
    return adv_full.squeeze(0).permute(1, 2, 0).cpu().numpy().astype(np.float32)
