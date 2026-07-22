import numpy as np

from veil.quick import quick_protect


def test_deterministic_given_seed():
    img = (np.random.RandomState(0).rand(32, 32, 3) * 255).astype(np.uint8)
    a = quick_protect(img, strength=0.5, seed=7)
    b = quick_protect(img, strength=0.5, seed=7)
    assert np.array_equal(a, b)


def test_different_seed_differs():
    img = (np.random.RandomState(0).rand(32, 32, 3) * 255).astype(np.uint8)
    a = quick_protect(img, strength=0.5, seed=1)
    b = quick_protect(img, strength=0.5, seed=2)
    assert not np.array_equal(a, b)


def test_alpha_preserved():
    img = (np.random.RandomState(1).rand(16, 16, 4) * 255).astype(np.uint8)
    out = quick_protect(img, strength=0.8, seed=1)
    assert out.shape == img.shape
    assert np.array_equal(out[..., 3], img[..., 3])


def test_change_is_bounded_and_nonzero():
    img = np.full((24, 24, 3), 128, np.uint8)
    out = quick_protect(img, strength=1.0, seed=3)
    diff = np.abs(out.astype(int) - img.astype(int))
    assert diff.max() >= 1          # it actually perturbs
    assert diff.max() <= 10         # amplitude ~8 code values + rounding


def test_low_strength_is_gentle():
    img = np.full((24, 24, 3), 100, np.uint8)
    out = quick_protect(img, strength=0.0, seed=2)
    diff = np.abs(out.astype(int) - img.astype(int))
    assert diff.max() <= 3
