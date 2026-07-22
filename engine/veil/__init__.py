"""palimpsest-veil — adversarial image protection against AI training.

Two modes, mirroring the Glaze / Nightshade paradigm, built from open parts:

* **Cloak** — Glaze-style style protection: shifts the image in a latent
  diffusion encoder's feature space so style-mimicry finetuning learns the
  wrong style.
* **Shade** — Nightshade-style concept poisoning: steers the image's features
  toward a chosen decoy concept so training pairs become inconsistent.

Two tiers:

* **Quick** — instant, no-ML high-frequency perturbation (:mod:`veil.quick`).
* **Deep** — real adversarial optimisation against an open SD VAE (+ CLIP for
  Shade), under a perceptual-visibility budget (:mod:`veil.perturb`).
"""
from .config import VERSION

__all__ = ["VERSION"]
__version__ = VERSION
