"""Lazy loading of the open models used by the Deep pass.

Nothing here is imported unless a Deep run actually happens, so the Quick tier,
the CLI's Quick path, and ``--help`` stay free of the heavy torch import and the
model download.
"""
from __future__ import annotations

import functools
from typing import Tuple

from .config import CACHE_DIR, CLIP_MODEL_ID, VAE_MODEL_ID


def get_device():
    import torch

    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


@functools.lru_cache(maxsize=1)
def load_vae():
    """Return ``(vae, device)`` — an SD VAE with parameters frozen."""
    import torch
    from diffusers import AutoencoderKL

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    device = get_device()
    vae = AutoencoderKL.from_pretrained(VAE_MODEL_ID, cache_dir=str(CACHE_DIR))
    vae = vae.to(device).eval()
    for p in vae.parameters():
        p.requires_grad_(False)
    return vae, device


@functools.lru_cache(maxsize=1)
def load_clip():
    """Return ``(model, tokenizer, device)`` — CLIP with parameters frozen."""
    import torch
    from transformers import CLIPModel, CLIPTokenizer

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    device = get_device()
    model = CLIPModel.from_pretrained(CLIP_MODEL_ID, cache_dir=str(CACHE_DIR)).to(device).eval()
    tok = CLIPTokenizer.from_pretrained(CLIP_MODEL_ID, cache_dir=str(CACHE_DIR))
    for p in model.parameters():
        p.requires_grad_(False)
    return model, tok, device


@functools.lru_cache(maxsize=16)
def clip_text_embedding(text: str):
    """L2-normalised CLIP text embedding for a decoy concept (cached)."""
    import torch
    import torch.nn.functional as F

    model, tok, device = load_clip()
    inputs = tok([text], padding=True, return_tensors="pt").to(device)
    with torch.no_grad():
        emb = model.get_text_features(**inputs)
    return F.normalize(emb, dim=-1)


def status() -> dict:
    """Cheap report for the /health endpoint — never triggers a load."""
    try:
        device = str(get_device())
    except Exception:  # torch not installed
        return {"torch": False, "device": None, "vae_loaded": False, "clip_loaded": False}
    return {
        "torch": True,
        "device": device,
        "vae_loaded": load_vae.cache_info().currsize > 0,
        "clip_loaded": load_clip.cache_info().currsize > 0,
    }
