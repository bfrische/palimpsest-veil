"""Measure protection quality: visibility, feature-space disruption, how much
survives common "cleaning" transforms, and (optionally) transfer to a held-out
encoder.

These are *surrogate* metrics — they measure how far the protection moves your
image in the feature spaces AI trainers rely on (an SD VAE + CLIP). They
correlate with, but do not guarantee, real-world protection. The ground truth
is training a mimicry model on protected images; see README.
"""
from __future__ import annotations

import io
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter

from . import config, imageio as vio, models, modes

_CLIP_MEAN = (0.48145466, 0.4578275, 0.40821073)
_CLIP_STD = (0.26862954, 0.26130258, 0.27577711)


# --- small image helpers (operate on float [0,1] RGB) ------------------------
def _pil(rgb01):
    return Image.fromarray((rgb01 * 255.0).round().clip(0, 255).astype(np.uint8))


def _np(im):
    return np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0


def _resize01(rgb01, maxside):
    h, w = rgb01.shape[:2]
    if max(h, w) <= maxside:
        return rgb01
    s = maxside / max(h, w)
    return _np(_pil(rgb01).resize((max(1, int(w * s)), max(1, int(h * s))), Image.BILINEAR))


def _jpeg(rgb01, quality=75):
    buf = io.BytesIO()
    _pil(rgb01).save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return _np(Image.open(buf))


def _downup(rgb01, factor=2):
    h, w = rgb01.shape[:2]
    small = _pil(rgb01).resize((max(1, w // factor), max(1, h // factor)), Image.BILINEAR)
    return _np(small.resize((w, h), Image.BILINEAR))


def _blur(rgb01, radius=1.0):
    return _np(_pil(rgb01).filter(ImageFilter.GaussianBlur(radius)))


# --- feature extractors ------------------------------------------------------
def _vae_latent(rgb01):
    import torch

    vae, device = models.load_vae()
    x = torch.from_numpy(np.ascontiguousarray(rgb01)).permute(2, 0, 1).unsqueeze(0).float().to(device)
    with torch.no_grad():
        return vae.encode(x * 2 - 1).latent_dist.mean


def _clip_embed(rgb01, model, device):
    import torch
    import torch.nn.functional as F

    x = torch.from_numpy(np.ascontiguousarray(rgb01)).permute(2, 0, 1).unsqueeze(0).float().to(device)
    x = F.interpolate(x, size=(224, 224), mode="bilinear", align_corners=False)
    mean = torch.tensor(_CLIP_MEAN, device=device).view(1, 3, 1, 1)
    std = torch.tensor(_CLIP_STD, device=device).view(1, 3, 1, 1)
    with torch.no_grad():
        e = model.get_image_features(pixel_values=(x - mean) / std)
    return F.normalize(e, dim=-1)


def _cos_dist(a, b):
    return float((1 - (a * b).sum(-1)).mean().item())


def _rel_shift(z0, z1):
    return float((z1 - z0).norm().item() / (z0.norm().item() + 1e-8))


def _lpips_dist(a01, b01):
    try:
        import torch

        from .perturb import _maybe_lpips

        net = _maybe_lpips()
        if net is None:
            return None
        device = models.get_device()
        ta = torch.from_numpy(np.ascontiguousarray(a01)).permute(2, 0, 1).unsqueeze(0).float().to(device) * 2 - 1
        tb = torch.from_numpy(np.ascontiguousarray(b01)).permute(2, 0, 1).unsqueeze(0).float().to(device) * 2 - 1
        with torch.no_grad():
            return float(net(ta, tb).item())
    except Exception:
        return None


def evaluate(
    orig_path: str,
    prot_path: str,
    mode: str = "cloak",
    decoy: Optional[str] = None,
    transfer: bool = False,
    diff_path: Optional[str] = None,
    eval_size: int = 512,
) -> dict:
    o_arr, _ = vio.load_rgba(orig_path)
    p_arr, _ = vio.load_rgba(prot_path)
    o, p = o_arr[..., :3], p_arr[..., :3]
    if o.shape != p.shape:
        raise SystemExit(f"original {o.shape} and protected {p.shape} must be the same size")
    o01, p01 = o.astype(np.float32) / 255.0, p.astype(np.float32) / 255.0

    # --- visibility (full resolution) ---
    d = np.abs(o.astype(int) - p.astype(int))
    vis = {
        "psnr": vio.psnr(o, p),
        "ssim": vio.ssim(o, p),
        "maxd": int(d.max()),
        "meand": float(d.mean()),
    }

    # --- feature disruption (downscaled for speed / memory) ---
    oe, pe = _resize01(o01, eval_size), _resize01(p01, eval_size)
    vis["lpips"] = _lpips_dist(oe, pe)

    clip_model, _, device = models.load_clip()
    e0, e1 = _clip_embed(oe, clip_model, device), _clip_embed(pe, clip_model, device)
    z0 = _vae_latent(oe)
    vae_shift = _rel_shift(z0, _vae_latent(pe))   # what Cloak targets
    clip_cd = _cos_dist(e0, e1)                    # what Shade targets

    # Score in the space each mode actually optimizes.
    space = "VAE latent" if mode == modes.CLOAK else "CLIP embedding"

    def disruption(img01):
        if mode == modes.CLOAK:
            return _rel_shift(z0, _vae_latent(img01))
        return _cos_dist(e0, _clip_embed(img01, clip_model, device))

    d_protected = vae_shift if mode == modes.CLOAK else clip_cd

    # benign baseline: Gaussian noise matched to the protection's MSE (equal PSNR)
    sigma = float(np.mean((pe - oe) ** 2)) ** 0.5
    noise = np.clip(oe + np.random.RandomState(0).normal(0, sigma, oe.shape).astype(np.float32), 0, 1)
    d_noise = disruption(noise)
    efficiency = d_protected / (d_noise + 1e-8)

    # --- robustness: fraction of the disruption that survives each transform ---
    robust = {}
    for name, fn in (
        ("JPEG q75", lambda x: _jpeg(x, 75)),
        ("downscale 2x", lambda x: _downup(x, 2)),
        ("Gaussian blur", lambda x: _blur(x, 1.0)),
    ):
        pt = _resize01(fn(p01), eval_size)
        robust[name] = max(0.0, min(1.0, disruption(pt) / (d_protected + 1e-8)))

    # --- Shade target: did we move toward the decoy concept? ---
    shade = None
    if mode == modes.SHADE and decoy:
        demb = models.clip_text_embedding(decoy)
        shade = {
            "decoy": decoy,
            "before": float((e0 * demb).sum(-1).mean().item()),
            "after": float((e1 * demb).sum(-1).mean().item()),
        }

    # --- transfer to a held-out encoder (CLIP ViT-L/14, not optimized against) ---
    trans = None
    if transfer:
        from transformers import CLIPModel

        big = CLIPModel.from_pretrained(
            "openai/clip-vit-large-patch14", cache_dir=str(config.CACHE_DIR)
        ).to(device).eval()
        trans = _cos_dist(_clip_embed(oe, big, device), _clip_embed(pe, big, device))

    if diff_path:
        vio.save(diff_path, (np.clip(np.abs(p01 - o01) * 10.0, 0, 1) * 255).round().astype(np.uint8))

    result = {
        "visibility": vis,
        "mode": mode,
        "space": space,
        "vae_shift": vae_shift,
        "clip_cd": clip_cd,
        "d_protected": d_protected,
        "d_noise": d_noise,
        "efficiency": efficiency,
        "robust": robust,
        "shade": shade,
        "transfer": trans,
    }
    _print_report(orig_path, prot_path, o.shape, result, diff_path)
    return result


def _bar(frac, width=14):
    n = int(round(max(0.0, min(1.0, frac)) * width))
    return "█" * n + "·" * (width - n)


def _print_report(orig_path, prot_path, shape, r, diff_path):
    v = r["visibility"]
    print(f"\nPalimpsest Veil — protection report")
    print(f"  original : {orig_path} ({shape[1]}x{shape[0]})")
    print(f"  protected: {prot_path}")

    print(f"\nVisibility  (how hidden the protection is — higher PSNR/SSIM = less visible)")
    lp = "" if v["lpips"] is None else f"   LPIPS {v['lpips']:.3f}"
    print(f"  PSNR {v['psnr']:.1f} dB   SSIM {v['ssim']:.3f}{lp}   maxΔ {v['maxd']}/255   meanΔ {v['meand']:.1f}")

    print(f"\nFeature disruption  (surrogate: SD1.5 VAE + CLIP ViT-B/32)")
    print(f"  VAE latent shift      {r['vae_shift']:.3f}   (relative L2)")
    print(f"  CLIP cosine distance  {r['clip_cd']:.3f}")
    print(f"  primary for {r['mode']}: {r['space']} disruption {r['d_protected']:.3f}  vs "
          f"same-visibility noise {r['d_noise']:.3f}")
    print(f"    ->  {r['efficiency']:.1f}x stronger than plain noise per unit visibility "
          f"{'OK' if r['efficiency'] >= 2 else 'weak'}")

    if r["transfer"] is not None:
        print(f"\nTransfer to held-out encoder  (CLIP ViT-L/14, not optimized against)")
        print(f"  CLIP-L cosine distance {r['transfer']:.3f}  "
              f"{'(transfers OK)' if r['transfer'] >= 0.05 else '(little transfer)'}")

    print(f"\nRobustness  (fraction of the protection that survives cleaning)")
    for name, frac in r["robust"].items():
        print(f"  {name:<14} {_bar(frac)} {frac*100:4.0f}%")

    if r["shade"]:
        s = r["shade"]
        arrow = "moved toward decoy OK" if s["after"] > s["before"] else "did NOT move toward decoy"
        print(f"\nShade target  (decoy: \"{s['decoy']}\")")
        print(f"  CLIP similarity to decoy: {s['before']:.3f} -> {s['after']:.3f} "
              f"({s['after']-s['before']:+.3f}, {arrow})")

    if diff_path:
        print(f"\nWrote 10x-amplified difference map: {diff_path}")

    print("\nRule of thumb: efficiency >= 2x and robustness that stays well above")
    print("zero after JPEG/downscale indicate meaningful protection. The real test")
    print("is training a mimicry model on protected images (see README).\n")
