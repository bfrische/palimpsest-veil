"""FastAPI localhost bridge the Photoshop plugin talks to for the Deep tier.

Contract (keeps payloads binary — no base64 bloat):

    GET  /health                      -> JSON status
    POST /protect?width=&height=&...  -> body: raw RGBA/RGB bytes
                                         returns: raw bytes, same shape

Bind is 127.0.0.1 only. Run with ``python -m veil serve`` (or ``python server.py``).

Note: this module intentionally does NOT use ``from __future__ import annotations``.
FastAPI resolves endpoint parameter types from real annotation objects; stringised
annotations would make it mistake the ``Request`` parameter for a query field.
"""
import numpy as np

from . import config, modes, quick


def create_app():
    from fastapi import FastAPI, Query, Request, Response
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="palimpsest-veil bridge", version=config.VERSION)
    # The plugin's fetch origin is a UXP scheme, not a normal web origin; a
    # wildcard is safe here because the server only ever binds to localhost.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        from .models import status

        return {"status": "ok", "version": config.VERSION, "engine": status()}

    @app.post("/protect")
    async def protect(
        request: Request,
        width: int = Query(...),
        height: int = Query(...),
        channels: int = Query(3),
        mode: str = Query(modes.CLOAK),
        strength: float = Query(0.5),
        tier: str = Query("deep"),
        decoy: str = Query(None),
        dtype: str = Query("uint8"),
    ):
        raw = await request.body()
        bytes_per = 4 if dtype == "float32" else 1
        expected = width * height * channels * bytes_per
        if len(raw) != expected:
            return Response(
                content=f"payload length {len(raw)} != expected {expected}".encode(),
                status_code=400,
            )

        # Normalised-float path — bit-depth agnostic (the Photoshop plugin uses
        # this for both 8- and 16-bit documents).
        if dtype == "float32":
            arr = np.frombuffer(raw, dtype=np.float32).reshape(height, width, channels).copy()
            if tier == "quick":
                result = quick.quick_protect_float(arr, strength=strength)
            else:
                from .perturb import deep_protect_float

                result = deep_protect_float(arr, mode=mode, strength=strength, decoy=decoy)
            return Response(
                content=np.ascontiguousarray(result, dtype=np.float32).tobytes(),
                media_type="application/octet-stream",
            )

        # Legacy uint8 path (used by curl tests / the CLI-style contract).
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, channels).copy()
        if tier == "quick":
            result = quick.quick_protect(arr, strength=strength)
        else:
            from .perturb import deep_protect

            result = deep_protect(arr, mode=mode, strength=strength, decoy=decoy)
        if result.shape[2] != channels:
            if channels == 4 and result.shape[2] == 3:
                result = np.concatenate([result, arr[..., 3:4]], axis=2)
            else:
                result = result[..., :channels]
        return Response(
            content=np.ascontiguousarray(result, dtype=np.uint8).tobytes(),
            media_type="application/octet-stream",
        )

    return app


def run(host: str = config.HOST, port: int = config.PORT) -> None:
    import uvicorn

    print(f"[veil] bridge listening on http://{host}:{port}")
    uvicorn.run(create_app(), host=host, port=port, log_level="info")


if __name__ == "__main__":
    run()
