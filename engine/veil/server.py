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
        channels: int = Query(4),
        mode: str = Query(modes.CLOAK),
        strength: float = Query(0.5),
        tier: str = Query("deep"),
        decoy: str = Query(None),
    ):
        raw = await request.body()
        expected = width * height * channels
        if len(raw) != expected:
            return Response(
                content=f"payload length {len(raw)} != expected {expected}".encode(),
                status_code=400,
            )
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, channels).copy()

        if tier == "quick":
            result = quick.quick_protect(arr, strength=strength)
        else:
            from .perturb import deep_protect

            result = deep_protect(arr, mode=mode, strength=strength, decoy=decoy)

        # Return exactly the channel count the client sent.
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
