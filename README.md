# Palimpsest Veil

**Make your photos toxic to AI image generators.** A Photoshop plugin (with a
local engine) that adds a *near‑invisible* perturbation to your images so that any
generative model which scrapes them to train on comes out **degraded** — it
learns a corrupted version of your subject and produces broken, artifact‑ridden
output. To your eye, the photo looks unchanged.

> **Verified.** A Stable Diffusion model finetuned on 18 protected bald‑eagle
> photos produced **3.6× more artifacts** — visibly glitched, broken eagles —
> than an identical model trained on the unprotected originals. The protected
> photos measured PSNR ~34–37 dB (max change ~10–18 of 255), with smooth areas
> untouched. See [Does it actually work?](#does-it-actually-work).

---

## How the protection works

AI image generators (Stable Diffusion, Midjourney‑style models, style‑mimicry
LoRAs) are trained by scraping huge numbers of images and learning to reproduce
them from their captions. Palimpsest Veil doesn't hide your image or watermark
it — it quietly **sabotages that training process**.

Here's the chain, in plain terms:

1. **A generator doesn't learn from your pixels directly.** It first compresses
   every training image into a small numeric "fingerprint" using an encoder
   (a *VAE latent* and a *CLIP embedding*). Everything the model learns about
   your photo, it learns from that fingerprint.

2. **The veil rewrites the fingerprint without rewriting the picture.** The
   engine runs an optimization: it searches for the *smallest* change to your
   pixels that pushes that fingerprint into a wrong, inconsistent place — while
   keeping the visible image essentially identical. The result is a faint,
   adversarial texture, not a filter or an overlay.

3. **It hides the texture where your eye won't look.** An *activity mask* built
   from your own image confines the perturbation to busy, detailed regions
   (feathers, foliage, fabric) and leaves smooth areas (sky, water, skin, bokeh)
   essentially untouched. That's why it stays invisible: flat areas — where the
   eye notices noise — carry almost none of it.

4. **A model that trains on it learns garbage.** When a scraper finetunes on the
   protected image under its caption, it's learning to reproduce a *corrupted*
   fingerprint. Do this across a body of your work and the model's idea of your
   subject (or your style) breaks: it generates degraded, glitched, artifacted
   results instead of clean ones.

In short: **invisible to humans, poison to the training pipeline.**

### Why "destruction," not "redirection"

There are two families of this attack. *Redirection* (Nightshade‑style: make the
model think "eagle" means "car") is possible but **inherently visible** — forcing
the fingerprint all the way onto a decoy prints that decoy faintly onto your
photo, and no amount of masking removes it (strong poison and visible ghosting
are literally the same signal). *Destruction* — just make the model **fail** on
your concept — needs only a small, unstructured nudge, so it stays near‑invisible
while still breaking the model. Palimpsest Veil ships the destruction method.
(The redirection method is available in the command line as `-m poison` for the
curious; it is textured and not recommended.)

### The technical short version

The engine perturbs the image with projected gradient descent against a
Stable‑Diffusion VAE encoder and an open CLIP encoder, under a bounded
perceptual budget (L∞ + activity mask), pushing the latent/feature
representation away from a clean, learnable target. It operates in normalized
float so 8‑ and 16‑bit images share one path, and the perturbation is optimized
to survive the downscaling a scraper applies. Cross‑model: the veil is built with
one VAE (`sd-vae-ft-mse`) yet still degrades a model trained on a *different*
Stable‑Diffusion VAE, so it doesn't need to know the scraper's exact model.

---

## Does it actually work?

The only honest test is to train a model and check that it breaks. An A/B
harness finetunes two *identical* LoRAs — one on the unprotected set, one on the
protected set — then generates from each and measures the artifact level (the
mean cross‑channel high‑frequency energy of the outputs):

| model trained on | artifact level | result |
| --- | --- | --- |
| nothing (base model) | 1.32 | clean eagles |
| your **unprotected** eagles | 1.15 | clean eagles |
| your **protected** eagles | **3.64** | **glitched, broken eagles** |

Same prompt, same seeds, same training — the only difference is the invisible
perturbation. A `check`/`evaluate` step can measure any protected file's
visibility and feature shift.

---

## Install (one double‑click, macOS + Photoshop 2024+)

1. Download and unzip the release.
2. **Double‑click `install.command`.** It sets up the local engine, installs the
   Photoshop plugin (no signing / no Creative Cloud), and runs the engine as a
   background service that starts at login. The first protect downloads open
   models (~1 GB, cached once); it runs on the Apple‑Silicon GPU.
3. **Quit and reopen Photoshop** → **Plugins ▸ Palimpsest Veil**.

To remove everything, double‑click `uninstall.command`.

## Use

1. Open an **8‑ or 16‑bit RGB** image.
2. Set **strength** (default 55; higher = stronger, slightly more texture on
   detailed areas).
3. **Protect Image** → a near‑identical **`Veil — protected`** layer is added;
   your original layer is untouched.
4. Flatten and export at **high quality** (PNG or max‑quality JPEG) before you
   publish — heavy recompression erodes the veil.

Command line: `python -m veil protect photo.jpg -m shade -s 0.55`

## Limitations — read this

- **It's a mitigation, not a guarantee.** Like all such tools (Glaze, Nightshade),
  it raises the cost of training on your work; it does not make it impossible.
- **It's statistical.** More protected images of the same subject → stronger
  degradation. Protect a body of work.
- **Near‑invisible, not zero.** Detailed areas carry faint texture (more at higher
  strength); smooth areas stay clean.
- **Not retroactive**, and low‑quality re‑encoding weakens it — export high
  quality, and protect *future* uploads.
- Verified against the Stable‑Diffusion 1.5 model family; a fully different
  architecture (e.g. SDXL) is untested.

Protect **your own** work only.

## License

Free for personal, non‑commercial use. No modifications, no redistribution.
**This is not open‑source software.** See [LICENSE](LICENSE).
