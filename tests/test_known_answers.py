"""Known-answer tests. The alpha code must reproduce published or hand-computed values
before we trust it on our own data.

Published values: Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability",
examples A (p.3), B (p.4), C (p.5, p.8).
"""

import numpy as np
import pandas as pd
import pytest

from kalpha_data import extract_flags, normalize_flag, percent_agreement
from krippendorff_python_lib.alpha_lib import alpha_nominal

nan = np.nan

# --- Krippendorff (2011) worked examples --------------------------------------------

EXAMPLE_A = [[0, 1, 0, 0, 0, 0, 0, 0, 1, 0],          # Meg
             [1, 1, 1, 0, 0, 1, 0, 0, 0, 0]]          # Owen
EXAMPLE_B = [[1, 1, 2, 2, 4, 3, 3, 3, 5, 4, 4, 1],    # Ben   (a=1 ... e=5)
             [2, 1, 2, 2, 2, 3, 3, 3, 5, 4, 4, 4]]    # Gerry
EXAMPLE_C = [[1, 2, 3, 3, 2, 1, 4, 1, 2, nan, nan, nan],
             [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, nan, 3],
             [nan, 3, 3, 3, 2, 3, 4, 2, 2, 5, 1, nan],
             [1, 2, 3, 3, 2, 4, 4, 1, 2, 5, 1, nan]]


@pytest.mark.parametrize("data, expected", [
    (EXAMPLE_A, 0.095),   # binary, 2 observers
    (EXAMPLE_B, 0.692),   # nominal, 2 observers
    (EXAMPLE_C, 0.743),   # nominal, 4 observers, missing data
])
def test_krippendorff_2011_examples(data, expected):
    assert alpha_nominal(np.array(data, dtype=float)) == pytest.approx(expected, abs=5e-4)


# --- Our own hand-computed cases (Not specified=0, Ambiguous=1, Clear=2) ----------

def test_candy_three_flags():
    m = np.array([[2, 2, 2, 0, 0, 0, 0, 2, 1, 0],
                  [2, 2, 0, 0, 0, 0, 0, 2, 0, 0]], dtype=float)
    assert alpha_nominal(m) == pytest.approx(0.6311, abs=1e-4)   # D_o=0.200, D_e=0.542
    assert percent_agreement(m) == pytest.approx(0.8)


def test_rare_category_gives_zero():
    m = np.array([[0] * 9 + [2], [0] * 10], dtype=float)
    assert percent_agreement(m) == pytest.approx(0.9)
    assert alpha_nominal(m) == pytest.approx(0.0, abs=1e-9)       # 90% agreement, alpha 0


def test_no_variation_is_undefined():
    m = np.full((2, 10), 2.0)
    assert np.isnan(alpha_nominal(m))                             # library alone would raise


# --- Cleaning -------------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Clear", "Clear"), ("Clear ", "Clear"), ("clear", "Clear"),
    ("\nAmbiguous", "Ambiguous"), ("Ambiguous \n", "Ambiguous"),
    ("Not Specified", "Not specified"), ("Not specified", "Not specified"),
    (None, None), ("", None), (nan, None),
])
def test_normalize_flag(raw, expected):
    assert normalize_flag(raw) == expected


def test_unknown_flag_is_an_error():
    with pytest.raises(ValueError):
        normalize_flag("Maybe")


def test_messy_headers_and_notes_rows():
    components = ["threat_source", "objective_or_harmful_outcome", "capability", "knowledge",
                  "access", "constraints_or_enabling_conditions", "target_or_asset_at_risk"]
    headers = {c: f"{c}_uncertainty" for c in components}
    headers["objective_or_harmful_outcome"] += "\n"            # trailing newline
    headers["access"] = "access_uncertaintyt"                   # typo
    df = pd.DataFrame([
        {"paper_id": "p1", "scenario_id": "S1", **{h: "Clear" for h in headers.values()},
         "access_verdict_evidence\n\n": "ignored"},
        {"paper_id": "total_clear:", "scenario_id": 130},       # notes row
    ])
    cf = extract_flags(df, "test")
    assert list(cf.flags.index) == ["p1/S1"]
    assert cf.flags.loc["p1/S1", "access"] == "Clear"
    assert len(cf.skipped_rows) == 1
