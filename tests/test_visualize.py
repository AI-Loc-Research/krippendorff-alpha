"""Tests for the two figure modules and constant_flag (the "n/a" label in the chart)."""

import pandas as pd

from data_preprocessing import COMPONENTS, CodingData, Comparison, constant_flag
from helper_visual_comparison_table import save_comparison_tables, table_path
from helper_visual_lp_chart import chart_path, save_lp_chart, status_of

PNG = b"\x89PNG\r\n\x1a\n"


def _data():
    """3 scenarios, 2 coders: everything Clear except two disagreements."""
    units = ["p1/S1", "p2/S1", "p3/S2"]
    a = pd.DataFrame({c: ["Clear"] * 3 for c in COMPONENTS}, index=units)
    b = a.copy()
    b.loc["p2/S1", "knowledge"] = "Not specified"   # differs in both views
    b.loc["p3/S2", "access"] = "Ambiguous"          # differs in 3 flags, same in binary
    return CodingData("a", units, {"a": a, "b": b}, {"a": [], "b": []}, {"a": 0, "b": 0})


def _table(name="humans"):
    rows = [{"comparison": name, "component": comp, "n_units": 3,
             "pct_agree_3flag": 1.0, "alpha_3flag": float("nan"),
             "pct_agree_binary": 1.0, "alpha_binary": float("nan"),
             "flags_a": "C=3 A=0 N=0", "flags_b": "C=3 A=0 N=0"}
            for comp in COMPONENTS]
    table = pd.DataFrame(rows)
    table.loc[table.component == "knowledge", "alpha_3flag"] = -0.2
    table.loc[table.component == "access", "alpha_3flag"] = 0.9
    return table


def test_status_bands():
    assert status_of(float("nan")) == "n/a"
    assert status_of(0.800) == "reliable"
    assert status_of(0.667) == "tentative"
    assert status_of(0.6669) == "below"
    assert status_of(-0.2) == "below"


def test_constant_flag():
    data = _data()
    assert constant_flag(data.matrix("threat_source", ["a", "b"], "3flag"), "3flag") == "Clear"
    assert constant_flag(data.matrix("knowledge", ["a", "b"], "3flag"), "3flag") is None
    # access: Clear vs Ambiguous varies in 3 flags, but both are "specified" in binary
    assert constant_flag(data.matrix("access", ["a", "b"], "3flag"), "3flag") is None
    assert constant_flag(data.matrix("access", ["a", "b"], "binary"), "binary") == "specified"


def test_file_names():
    csv = "results/lib_KA_chart_llm_20261008_1500.csv"
    assert chart_path(csv).name == "lib_KA_chart_llm_20261008_1500.png"
    assert table_path(csv, "humans").name == "lib_KA_labels_humans_20261008_1500.png"
    assert (table_path(csv, "Combined (llm+human)").name
            == "lib_KA_labels_combined_llm_human_20261008_1500.png")
    assert chart_path("my_run.csv").name == "my_run_chart.png"


def test_one_chart_with_a_card_per_comparison(tmp_path):
    names = ["humans", "a_vs_llm", "b_vs_llm", "Combined (llm+human)"]   # --llm: 2 x 2 grid
    table = pd.concat([_table(n) for n in names], ignore_index=True)
    comparisons = [Comparison(n, ["a", "b"]) for n in names]
    path = save_lp_chart(table, _data(), comparisons, tmp_path / "lib_ka_result_llm_20261008_1500.csv")
    assert path.read_bytes()[:8] == PNG


def test_one_comparison_table_per_comparison(tmp_path):
    comparisons = [Comparison("humans", ["a", "b"]), Comparison("Combined (llm+human)", ["a", "b"])]
    paths = save_comparison_tables(_data(), comparisons,
                                   tmp_path / "custom_ka_result_llm_20261008_1500.csv")
    assert [p.name for p in paths] == ["custom_ka_labels_humans_20261008_1500.png",
                                       "custom_ka_labels_combined_llm_human_20261008_1500.png"]
    assert all(p.read_bytes()[:8] == PNG for p in paths)
