"""Command-line interface: ``python -m veil protect ...`` and ``veil serve``."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from . import config, imageio, modes, quick


def _default_out(inp: str) -> str:
    p = Path(inp)
    return str(p.with_name(p.stem + "_veil" + (p.suffix or ".png")))


def _protect_cmd(args) -> int:
    arr, _ = imageio.load_rgba(args.input)
    t0 = time.time()
    if args.quick:
        result = quick.quick_protect(arr, strength=args.strength, seed=args.seed)
        tier, label = "quick", "quick"
    else:
        from .perturb import deep_protect

        def prog(f: float) -> None:
            print(f"\r  deep {f * 100:5.1f}%", end="", file=sys.stderr, flush=True)

        result = deep_protect(
            arr,
            mode=args.mode,
            strength=args.strength,
            decoy=args.decoy,
            use_lpips=not args.no_lpips,
            progress=prog,
        )
        print("", file=sys.stderr)
        tier, label = "deep", args.mode

    dt = time.time() - t0
    out = args.output or _default_out(args.input)
    imageio.save(out, result)

    ps = imageio.psnr(arr[..., :3], result[..., :3])
    ss = imageio.ssim(arr, result)
    print(f"[veil] {tier}/{label} strength={args.strength} -> {out}")
    print(f"[veil] {dt:.1f}s  PSNR={ps:.2f} dB  SSIM={ss:.4f}")
    return 0


def _serve_cmd(args) -> int:
    from .server import run

    run(args.host, args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="veil",
        description="Protect your own images against AI training (Cloak / Shade).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("protect", help="protect a single image")
    pp.add_argument("input", help="path to the input image")
    pp.add_argument("-o", "--output", help="output path (default: <name>_veil.<ext>)")
    pp.add_argument("-m", "--mode", choices=modes.MODES, default=modes.CLOAK,
                    help="cloak = style protection, shade = concept poisoning")
    pp.add_argument("-s", "--strength", type=float, default=0.5,
                    help="0..1; higher = stronger + more visible")
    pp.add_argument("--decoy", default=None, help="Shade decoy concept, e.g. 'stained glass'")
    pp.add_argument("--quick", action="store_true", help="use the instant no-ML tier")
    pp.add_argument("--seed", type=int, default=1, help="Quick-tier noise seed")
    pp.add_argument("--no-lpips", action="store_true", help="skip the LPIPS perceptual penalty")
    pp.set_defaults(func=_protect_cmd)

    sp = sub.add_parser("serve", help="run the localhost bridge for the Photoshop plugin")
    sp.add_argument("--host", default=config.HOST)
    sp.add_argument("--port", type=int, default=config.PORT)
    sp.set_defaults(func=_serve_cmd)

    ev = sub.add_parser("evaluate", help="measure protection quality of a protected image")
    ev.add_argument("original", help="the unprotected image")
    ev.add_argument("protected", help="the protected image (same size)")
    ev.add_argument("-m", "--mode", choices=modes.MODES, default=modes.CLOAK)
    ev.add_argument("--decoy", default=None, help="Shade decoy concept, to check it moved toward it")
    ev.add_argument("--transfer", action="store_true",
                    help="also test a held-out encoder (CLIP ViT-L/14, ~1.6 GB download)")
    ev.add_argument("--diff", dest="diff", default=None, help="write a 10x-amplified difference map here")
    ev.set_defaults(func=_evaluate_cmd)

    return p


def _evaluate_cmd(args) -> int:
    from .evaluate import evaluate

    evaluate(
        args.original,
        args.protected,
        mode=args.mode,
        decoy=args.decoy,
        transfer=args.transfer,
        diff_path=args.diff,
    )
    return 0


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
