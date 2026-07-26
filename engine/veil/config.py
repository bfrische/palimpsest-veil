"""Shared configuration for the palimpsest-veil engine."""
from __future__ import annotations

import os
from pathlib import Path

# --- Bridge server -----------------------------------------------------------
HOST = "127.0.0.1"
PORT = int(os.environ.get("VEIL_PORT", "8760"))

# --- Model ids (open weights, downloaded on first Deep run) -------------------
VAE_MODEL_ID = os.environ.get("VEIL_VAE", "stabilityai/sd-vae-ft-mse")
CLIP_MODEL_ID = os.environ.get("VEIL_CLIP", "openai/clip-vit-base-patch32")

# Where weights are cached. Kept out of the repo (see .gitignore).
CACHE_DIR = Path(os.environ.get("VEIL_CACHE", Path.home() / ".cache" / "palimpsest-veil"))

# --- Deep pass defaults ------------------------------------------------------
# Perceptual budget: strength 0..1 maps linearly into this L-infinity range
# (in 0..1 pixel units). Kept small so perturbation stays low-visibility.
EPS_MIN = 2.0 / 255.0
EPS_MAX = 16.0 / 255.0

# Optimisation budget: strength maps into this step-count range.
STEPS_MIN = 20
STEPS_MAX = 120

# Tiling: images larger than this (on either axis) are processed in tiles so
# VAE memory stays bounded regardless of document size.
TILE_SIZE = 512
TILE_OVERLAP = 48

VERSION = "0.2.0"

# --- Poison mode (Nightshade-style VAE-latent targeting) ----------------------
# The decoy word is turned into an "anchor" image via Stable Diffusion, encoded
# to a target latent; each protected image's latent is dragged toward it.
SD_MODEL_ID = os.environ.get("VEIL_SD", "sd-legacy/stable-diffusion-v1-5")
ANCHOR_DIR = CACHE_DIR / "anchors"
# Perceptual budget for poison (L-inf in 0..1). Verified floor for cross-VAE
# transfer is ~0.10; below that it stops poisoning. strength maps into this.
POISON_EPS_MIN = 0.06
POISON_EPS_MAX = 0.18
POISON_WORK_MAX = 1536  # cap the optimisation resolution; delta is upsampled back


def poison_strength_to_eps(strength: float) -> float:
    strength = max(0.0, min(1.0, float(strength)))
    return POISON_EPS_MIN + (POISON_EPS_MAX - POISON_EPS_MIN) * strength


def poison_strength_to_steps(strength: float) -> int:
    strength = max(0.0, min(1.0, float(strength)))
    return int(round(150 + 100 * strength))


def strength_to_eps(strength: float) -> float:
    strength = max(0.0, min(1.0, float(strength)))
    return EPS_MIN + (EPS_MAX - EPS_MIN) * strength


def strength_to_steps(strength: float) -> int:
    strength = max(0.0, min(1.0, float(strength)))
    return int(round(STEPS_MIN + (STEPS_MAX - STEPS_MIN) * strength))
