import numpy as np

from veil.perturb import _feather, _starts, _tile_grid


def test_starts_cover_endpoints():
    s = _starts(1000, 512, 48)
    assert s[0] == 0
    assert s[-1] == 1000 - 512


def test_small_image_single_tile():
    assert _starts(300, 512, 48) == [0]


def test_tile_grid_covers_everything():
    h, w = 700, 900
    covered = np.zeros((h, w), bool)
    for y0, y1, x0, x1 in _tile_grid(h, w, 512, 48):
        covered[y0:y1, x0:x1] = True
    assert covered.all()


def test_feather_interior_positive():
    f = _feather(128, 128, 48)
    assert f.min() > 0.0
    assert f.max() <= 1.0
