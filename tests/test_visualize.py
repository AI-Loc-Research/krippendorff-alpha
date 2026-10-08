"""Tests for helper_visualize and the "n/a" explanations in data_preprocessing."""

import pandas as pd

from data_preprocessing import (
    COMPONENTS,
    CodingData,
    Comparison,
    alpha_note,
    constant_flag,
    undefined_reason,
)
from helper_visualize import save_visualizations, status_of

PNG = b"\x89PNG\r\n\x1a\n"


def _data():
    """3 scenarios, 2 coders: everything Clear except two disagreements."""
    units = ["p1/S1", "p2/S1", "p3/S2"]
    a = pd.DataFrame({c: ["Clear"] * 3 for c in COMPONENTS}, index=units)
    b = a.copy()
    b.loc["p2/S1", "knowledge"] = "Not specified"   # differs in both views
    b.loc["p3/S2", "access"] = "Ambiguous"          # differs in 3 flags, same in binary
    return CodingData("a", units, {"a": a, "b": b}, {"a": [], "b": []}, {"a": 0, "b": 0})


def _table():
    rows = [{"comparison": "humans", "component": comp, "n_units": 3,
             "pct_agree_3flag": 1.0, "alpha_3flag": float("nan"),
             "pct_agree_binary": 1.0, "alpha_binary": float("nan"),
             "flags_a": "C=3 A=0 N=0", "flags_b": "C=3 A=0 N=0", "note": ""}
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


def test_why_alpha_is_na():
    data = _data()
    same = data.matrix("threat_source", ["a", "b"], "3flag")
    assert constant_flag(same, "3flag") == "Clear"
    assert "every coder gave 'Clear'" in undefined_reason(same, "3flag")
    varies = data.matrix("knowledge", ["a", "b"], "3flag")
    assert constant_flag(varies, "3flag") is None and undefined_reason(varies, "3flag") == ""


def test_alpha_note_covers_each_view():
    data = _data()
    both = alpha_note(data, ["a", "b"], "threat_source")
    assert "3flag: alpha n/a" in both and "binary: alpha n/a" in both
    # access: Clear vs Ambiguous varies in 3 flags, but both are "specified" in binary
    only_binary = alpha_note(data, ["a", "b"], "access")
    assert only_binary.startswith("binary:") and "'specified'" in only_binary
    assert alpha_note(data, ["a", "b"], "knowledge") == ""


def test_files_named_after_csv(tmp_path):
    csv = tmp_path / "results" / "lib_ka_result_humans_20261008_1500.csv"
    paths = save_visualizations(_table(), _data(), [Comparison("humans", ["a", "b"])], csv)
    assert [p.name for p in paths] == ["lib_ka_chart_humans_20261008_1500.png",
                                       "lib_ka_labels_humans_20261008_1500.png"]
    assert all(p.read_bytes()[:8] == PNG for p in paths)


def test_one_label_grid_per_comparison(tmp_path):
    table = pd.concat([_table(), _table().assign(comparison="other")], ignore_index=True)
    comparisons = [Comparison("humans", ["a", "b"]), Comparison("other", ["b", "a"])]
    csv = tmp_path / "custom_ka_result_all_20261008_1500.csv"
    paths = save_visualizations(table, _data(), comparisons, csv)
    assert [p.name for p in paths] == ["custom_ka_chart_all_20261008_1500.png",
                                       "custom_ka_labels_humans_20261008_1500.png",
                                       "custom_ka_labels_other_20261008_1500.png"]


def test_custom_out_name(tmp_path):
    paths = save_visualizations(_table(), _data(), [Comparison("humans", ["a", "b"])],
                                tmp_path / "my_run.csv")
    assert [p.name for p in paths] == ["my_run_chart.png", "my_run_labels_humans.png"]
