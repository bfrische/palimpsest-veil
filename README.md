# Palimpsest Veil

**Poison AI models that train on your images.** A Photoshop plugin backed by a
local engine that applies Nightshade-style *concept poisoning*: it perturbs your
photo — invisibly in smooth areas, as fine texture in detail — so that any model
which scrapes it to train learns your subject as something else entirely.

> Verified end-to-end: a Stable Diffusion model finetuned on 18 poisoned
> bald‑eagle photos (decoy "a vintage car") generates **vintage cars** when asked
> for "a photo of a bald eagle." A control model trained on the unprotected
> originals generates clean eagles. See [Does it actually work?](#does-it-actually-work).

## How it works

You give it a **decoy concept** (e.g. "a vintage car"). The engine turns that
word into an anchor image with Stable Diffusion, encodes it to a target **VAE
latent**, then nudges your image's latent toward it — the VAE latent is the exact
target a diffusion model learns from, which is why this poisons *training* (and
the earlier CLIP-based approaches did not). The perturbation is concentrated in
textured detail (feathers, foliage) by an activity mask and bounded by a budget.

```
engine/   Python engine: poison + anchor generation, CLI, localhost bridge, tests
plugin/   Photoshop UXP panel (decoy field + strength slider)
```

## Install (one double-click)

**Double-click `install.command`.** It sets up the Python engine, installs the
plugin (no signing / Creative Cloud), and runs the engine as a background service
that starts at login. First poison of a *new* decoy downloads / runs Stable
Diffusion (~4 GB, cached), so it can take a couple of minutes; after that each
decoy is cached. Everything runs on the Apple‑Silicon GPU.

Then **quit and reopen Photoshop** → **Plugins ▸ Palimpsest Veil**. Remove
everything with `uninstall.command`.

## Use — Photoshop plugin

1. Open an **8- or 16-bit RGB** image.
2. Type a **decoy concept** (something far from your subject — "a vintage car",
   "a pile of bricks").
3. Set **strength** (default 80). Higher = stronger poison + more visible texture.
4. **Poison Image** → the result is added as a new **`Veil — poison`** layer; your
   original is untouched. Flatten and export **high quality** (PNG or max‑quality
   JPEG) when you publish.

## Use — command line

```bash
cd engine && source .venv/bin/activate
python -m veil protect photo.jpg -m poison --decoy "a vintage car" -s 0.8
```

## Does it actually work?

The only honest test is training a model and checking it breaks. The A/B harness
that produced the result above (not shipped, available on request) finetunes an
identical LoRA on the unprotected vs. poisoned set and generates from each:

| model trained on | "bald eagle" sim | "vintage car" sim |
| --- | --- | --- |
| unprotected eagles | 0.29 | 0.15 (eagles) |
| **poisoned eagles** | **0.19** | **0.27** (cars) |

Cross-model: the poison is made with the engine's VAE (`sd-vae-ft-mse`) yet still
hijacks a model trained on SD‑1.5's **stock** VAE — so it doesn't need to know the
scraper's exact model.

## Limitations — read this

- **It's statistical.** One poisoned image mostly gets *memorised*; the concept
  shift comes from *many* poisoned images scraped under the same label. Protect a
  body of work, with a consistent decoy, for real-world effect.
- **Visible texture is the cost.** Poisoning has to move the VAE latent a real
  distance; the mask keeps smooth areas clean but detailed areas carry texture.
  The floor that still poisons is ~0.10 budget (slider ~55); the default 0.8 is
  chosen for reliable effect. Drop it if a given image can't hide the texture.
- **Transfer is verified across the SD‑1.5 family**, not (yet) a fully different
  architecture like SDXL.
- **Not retroactive**, and low‑quality re‑encoding erodes it — export high quality.

Poison your own work only. This is defensive: it exists to make your images bad
training data for anyone who takes them without consent.

## Validating a specific image

`python -m veil evaluate original.png protected.png` reports visibility (PSNR /
SSIM / LPIPS) and feature‑space movement, and writes a difference map with
`--diff`. Note the surrogate feature metrics predict CLIP disruption, not the
training‑time poison — the table above (a real finetune) is the ground truth.

## License

MIT — see [LICENSE](LICENSE). Legacy `cloak` / `shade` modes remain in the engine
and CLI but are **not** recommended: they disrupt CLIP-based systems without
poisoning a diffusion model's training.
