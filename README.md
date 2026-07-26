# Palimpsest Veil

**Make your images toxic training data.** A Photoshop plugin backed by a local
engine that applies a near-invisible adversarial perturbation so that any AI
model which scrapes your photo to train on it comes out **degraded** — it learns
a corrupted version of your subject and produces broken, artifact-ridden output.

> Verified end-to-end: a Stable Diffusion model finetuned on 18 protected
> bald-eagle photos generates **3.6× more artifacts** — visibly glitched, broken
> eagles — than a model trained on the unprotected originals. The protected
> photos look ~identical to the originals (PSNR ~37 dB). See
> [Does it work?](#does-it-work).

## Destruction vs. redirection (why this design)

There are two ways to poison a generative model, and they trade off very
differently on visibility:

- **Redirection** (Nightshade-style: "eagle → car") *can* be done, but it
  requires shifting the whole image's latent onto the decoy, which is
  **visibly** printed onto your photo. Strong poison and visible ghosting are the
  same signal — there is no clean version. (Still available as `-m poison` in the
  CLI if you want it; it's textured.)
- **Destruction** (what ships): corrupt the training signal so the model just
  **fails** on your concept. This needs only a small, unstructured perturbation —
  so it stays **near-invisible** while still breaking the model. For "make my work
  useless to scrapers," this is the better deal, and it's the plugin's mode.

```
engine/   Python engine: perturbation, CLI, localhost bridge, tests
plugin/   Photoshop UXP panel (strength slider)
```

## Install (one double-click)

**Double-click `install.command`.** It sets up the engine, installs the plugin
(no signing / Creative Cloud), and runs the engine as a login service. The first
protect downloads open models (~1 GB, cached). Runs on the Apple-Silicon GPU.
Then **quit and reopen Photoshop** → **Plugins ▸ Palimpsest Veil**. Remove with
`uninstall.command`.

## Use

1. Open an **8- or 16-bit RGB** image.
2. Set **strength** (default 55). Higher = stronger corruption, slightly more
   visible texture on detailed areas.
3. **Protect Image** → a near-identical **`Veil — protected`** layer is added;
   your original is untouched. Flatten and export **high quality** to publish.

CLI: `python -m veil protect photo.jpg -m shade -s 0.55`

## Does it work?

The only honest test is training a model and checking it breaks. The A/B harness
(not shipped, available on request) finetunes an identical LoRA on the
unprotected vs. protected set and generates from each; artifact level is the
mean cross-channel high-frequency energy of the outputs:

| model trained on | artifact level | look |
| --- | --- | --- |
| nothing (base) | 1.32 | clean eagles |
| unprotected eagles | 1.15 | clean eagles |
| **protected eagles** | **3.64** | **glitched, broken eagles** |

The protected source images are near-invisible (PSNR ~37 dB, max change ~10/255,
smooth areas untouched by the activity mask).

## Limitations — read this

- **It's statistical.** More protected images of the same subject → stronger
  degradation. Protect a body of work.
- **Near-invisible, not zero.** Detailed areas carry faint texture, more so at
  higher strength; smooth areas (sky, water, bokeh) stay clean.
- **Not retroactive**, and low-quality re-encoding erodes it — export high quality.
- Verified against the SD-1.5 model family; a fully different architecture
  (SDXL) is untested.

Protect your own work only. This is defensive.

## Validating a specific image

`python -m veil evaluate original.png protected.png` reports visibility and
feature-space movement (`--diff` writes a difference map). The ground truth is
the train-and-check table above.

## License

MIT — see [LICENSE](LICENSE).
