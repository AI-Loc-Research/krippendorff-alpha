"""Tests for the from-scratch implementation (ka_script_custom.py).

1. Each computational step reproduces the intermediate numbers printed in
   Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability".
2. Final alphas reproduce the published values for all four levels of measurement.
3. On hundreds of random reliability matrices, the custom alpha equals the
   `krippendorff` library to within floating-point rounding.
"""

import krippendorff
import numpy as np
import pytest

from ka_script_custom import (
    alpha_details,
    alpha_nominal,
    coincidence_matrix,
)

nan = np.nan

EXAMPLE_A = [[0, 1, 0, 0, 0, 0, 0, 0, 1, 0],          # Meg   (p.2)
             [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]]          # Owen
EXAMPLE_B = [[1, 1, 2, 2, 4, 3, 3, 3, 5, 4, 4, 1],    # Ben   (p.3; a=1 ... e=5)
             [2, 1, 2, 2, 2, 3, 3, 3, 5, 4, 4, 4]]    # Gerry
EXAMPLE_C = [[1, 2, 3, 3, 2, 1, 4, 1, 2, nan, nan, nan],   # (p.4) 4 observers, missing data
             [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, nan, 3],
             [nan, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, nan],
             [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, nan]]


# --- Step 2: coincidence matrices printed in the paper ----------------------------------

def test_step2_example_a():
    _, o = coincidence_matrix(EXAMPLE_A)
    np.testing.assert_allclose(o, [[10, 4], [4, 2]])            # n0 = 14, n1 = 6, n = 20


def test_step2_example_b():
    _, o = coincidence_matrix(EXAMPLE_B)
    np.testing.assert_allclose(o, [[2, 1, 0, 1, 0],
                                   [1, 4, 0, 1, 0],
                                   [0, 0, 6, 0, 0],
                                   [1, 1, 0, 4, 0],
                                   [0, 0, 0, 0, 2]])
    np.testing.assert_allclose(o.sum(axis=1), [4, 6, 6, 6, 2])  # n = 24


def test_step2_example_c_with_missing_data():
    _, o = coincidence_matrix(EXAMPLE_C)
    t = 1 / 3
    np.testing.assert_allclose(o, [[7, 4 * t, t, t, 0],
                                   [4 * t, 10, 4 * t, t, 0],
                                   [t, 4 * t, 8, t, 0],
                                   [t, t, t, 4, 0],
                                   [0, 0, 0, 0, 3]])
    np.testing.assert_allclose(o.sum(axis=1), [9, 13, 10, 5, 3])  # n = 40 (unit 12 unpairable)


# --- Step 4: published alphas ------------------------------------------------------------

@pytest.mark.parametrize("data, level, expected", [
    (EXAMPLE_A, "nominal", 0.095),
    (EXAMPLE_B, "nominal", 0.692),
    (EXAMPLE_C, "nominal", 0.743),
    (EXAMPLE_C, "ordinal", 0.815),
    (EXAMPLE_C, "interval", 0.849),
    (EXAMPLE_C, "ratio", 0.797),
])
def test_published_alphas(data, level, expected):
    assert alpha_details(data, level)["alpha"] == pytest.approx(expected, abs=5e-4)


# --- Hand-computed cases (Not specified=0, Ambiguous=1, Clear=2) -------------------------

def test_candy_ingredients():
    d = alpha_details([[2, 2, 2, 0, 0, 0, 0, 2, 1, 0],
                       [2, 2, 0, 0, 0, 0, 0, 2, 0, 0]])
    assert d["D_o"] == pytest.approx(0.200)                     # 2 of 10 units differ
    assert d["D_e"] == pytest.approx(206 / 380)                 # 1 - (7*6 + 1*0 + 12*11)/(20*19)
    assert d["alpha"] == pytest.approx(0.6311, abs=1e-4)


def test_rare_category_gives_zero():
    assert alpha_nominal([[0] * 9 + [2], [0] * 10]) == pytest.approx(0.0, abs=1e-12)


def test_no_variation_is_undefined():
    d = alpha_details(np.full((2, 10), 2.0))
    assert np.isnan(d["alpha"]) and d["D_e"] == 0


def test_nothing_pairable_is_undefined():
    assert np.isnan(alpha_nominal([[1, nan, 2], [nan, 0, nan]]))  # no unit has 2 values


# --- Cross-check against the krippendorff library ----------------------------------------

def _random_matrices(seed=2026, count=100):
    rng = np.random.default_rng(seed)
    for _ in range(count):
        coders, units = rng.integers(2, 5), rng.integers(3, 30)
        m = rng.integers(1, 6, size=(coders, units)).astype(float)   # values 1..5
        m[rng.random(m.shape) < 0.2] = nan                            # 20% missing
        yield m


@pytest.mark.parametrize("level", ["nominal", "ordinal", "interval", "ratio"])
def test_matches_library_on_random_data(level):
    checked = 0
    for m in _random_matrices():
        try:
            expected = krippendorff.alpha(reliability_data=m, level_of_measurement=level)
        except ValueError:          # library refuses data with a single value
            continue
        ours = alpha_details(m, level)["alpha"]
        if np.isnan(expected):
            assert np.isnan(ours)
        else:
            assert ours == pytest.approx(float(expected), abs=1e-9)
        checked += 1
    assert checked > 90
