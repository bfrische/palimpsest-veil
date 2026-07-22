# Palimpsest Veil

Protect **your own** images from being used to train AI models — a Photoshop
plugin backed by a local adversarial-protection engine. It implements the two
techniques popularised by the University of Chicago's [Glaze and
Nightshade](https://glaze.cs.uchicago.edu/), rebuilt from open components so the
whole pipeline lives in this repo and runs on your machine.

> A *palimpsest* is a manuscript overwritten so the original shows only faintly
> beneath. That's the idea: to a scraper's model the image reads as something
> else, while to your eye it still looks like your art.

## Two modes

| Mode | Inspired by | What it does |
| --- | --- | --- |
| **Cloak** | Glaze | Shifts the image in a latent-diffusion encoder's feature space so **style-mimicry** finetuning learns the *wrong* style. |
| **Shade** | Nightshade | Steers the image's features toward a chosen **decoy concept**, so a model that scrapes it without consent learns a corrupted concept association. |

## Two tiers

- **Quick** — an instant, no-ML high-frequency perturbation. Runs entirely inside
  Photoshop (no backend), adds scraping friction, and is the graceful fallback.
- **Deep** — the real thing: projected-gradient adversarial optimisation against
  an open Stable Diffusion VAE (plus CLIP for Shade), constrained by a perceptual
  (LPIPS + L∞) budget so the change stays low-visibility. Needs the local engine.

## Layout

```
engine/   Python + PyTorch engine: CLI, localhost bridge server, tests
plugin/   Photoshop UXP panel (manifest v5, Spectrum UI, Imaging API)
```

## Install — engine

```bash
cd engine
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

The Quick tier and the CLI's `--quick` path need only `numpy` + `pillow`. The
Deep tier downloads ~1 GB of open model weights on first use (cached under
`~/.cache/palimpsest-veil`, never committed). On Apple Silicon it runs on the
MPS GPU automatically.

## Use — command line

```bash
# Deep style-cloak at 60% strength
python -m veil protect art.png -m cloak -s 0.6 -o art_cloaked.png

# Deep concept-poison toward a decoy
python -m veil protect art.png -m shade --decoy "stained glass" -s 0.6

# Instant Quick pass, no models required
python -m veil protect art.png --quick -s 0.5
```

Each run prints elapsed time plus **PSNR** and **SSIM** so you can see how visible
the protection is.

## Use — Photoshop plugin

1. Start the bridge the plugin talks to:
   ```bash
   cd engine && source .venv/bin/activate && python -m veil serve
   ```
2. Open **Adobe UXP Developer Tool** → **Add Plugin** → select
   `plugin/manifest.json` → **Load**. (Photoshop 2026 must be running.)
3. In Photoshop: **Plugins → Palimpsest Veil**. Pick a mode, strength, and tier,
   then **Protect Image**. The result is added as a new **`Veil — …`** layer; your
   original layer is left untouched. The green/red dot shows whether the Deep
   backend is reachable; Quick works with the backend off.

## Limitations — read this

Protection tools like these are **mitigations, not guarantees**:

- **Not retroactive.** Anything already scraped into a training set stays there.
  Protect *future* uploads.
- **It's an arms race.** Researchers publish purification/denoising countermeasures,
  and stronger ones will appear. Higher strength resists more but is more visible.
- **Re-encoding can weaken it.** Aggressive recompression or downscaling by a
  platform can erode the perturbation; export at the resolution you'll publish.
- **Quick tier is friction, not armour.** For real protection use **Deep**.

Apply protection to your own work only. This project is defensive: it exists to
keep your images from being used to train models without your consent.

## License

MIT — see [LICENSE](LICENSE).
