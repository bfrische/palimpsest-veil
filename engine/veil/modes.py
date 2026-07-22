"""The two protection objectives — *what* the Deep optimiser pushes toward.

Kept separate from :mod:`veil.perturb` (which owns *how* it optimises) so the
Cloak / Shade behaviours are easy to read and tune in isolation.
"""
from __future__ import annotations

CLOAK = "cloak"
SHADE = "shade"
MODES = (CLOAK, SHADE)

# Used by Shade when the caller doesn't name a decoy concept.
DEFAULT_DECOY = "abstract textured pattern"


def normalize_mode(mode: str) -> str:
    mode = (mode or CLOAK).strip().lower()
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    return mode


def cloak_loss(adv_latent, clean_latent):
    """Glaze-style: drive the VAE latent *away* from the clean image's latent.

    Minimising the negative distance maximises the representation shift, so a
    model finetuning on the image learns a corrupted view of its style.
    """
    import torch.nn.functional as F

    return -F.mse_loss(adv_latent, clean_latent)


def shade_loss(adv_image_embed, decoy_text_embed):
    """Nightshade-style: pull the image's CLIP embedding toward a decoy concept.

    Minimising the negative cosine similarity increases alignment with the
    decoy, making the (image, true-caption) training pair internally inconsistent.
    """
    import torch.nn.functional as F

    adv = F.normalize(adv_image_embed, dim=-1)
    return -(adv * decoy_text_embed).sum(dim=-1).mean()
