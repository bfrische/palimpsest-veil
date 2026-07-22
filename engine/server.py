"""Convenience launcher so ``python server.py`` starts the bridge.

The implementation lives in :mod:`veil.server` so ``python -m veil serve`` works
identically from any directory.
"""
from veil.server import run

if __name__ == "__main__":
    run()
