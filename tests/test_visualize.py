"""Tests for helper_visualize: status bands and the two saved PNG files."""

import pandas as pd

from data_preprocessing import Comparison
from helper_visualize import save_visualizations, status_of


def _table():
    rows = []
    for comp, a3, ab in [("threat_source", float("nan"), float("nan")),
                         ("capability", 0.87, 0.87),
                         ("knowledge", -0.16, 0.755)]:
        rows.append({"comparison": "humans", "component": comp, "n_units": 25,
                     "pct_agree_3flag": 0.90, "alpha_3flag": a3,
                     "pct_agree_binary": 0.92, "alpha_binary": ab,
                     "flags_a": "C=20 A=1 N=4", "flags_b": "C=19 A=0 N=6"})
    return pd.DataFrame(rows)


def test_status_bands():
    assert status_of(float("nan")) == "undefined"
    assert status_of(0.800) == "reliable"
    assert status_of(0.667) == "tentative"
    assert status_of(0.6669) == "below"
    assert status_of(-0.2) == "below"


def test_saves_two_pngs_named_after_csv(tmp_path):
    csv = tmp_path / "results" / "lib_ka_result_humans_20261008_1500.csv"
    paths = save_visualizations(_table(), [Comparison("humans", ["a", "b"])], csv)
    assert [p.name for p in paths] == ["lib_ka_chart_humans_20261008_1500.png",
                                       "lib_ka_table_humans_20261008_1500.png"]
    for p in paths:
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"   # a real PNG file
