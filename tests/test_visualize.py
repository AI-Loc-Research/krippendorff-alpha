"""Tests for the two figure modules and constant_flag (the "n/a" label in the chart)."""

import pandas as pd

import helper_visual_lp_graph
from data_preprocessing import COMPONENTS, CodingData, Comparison, constant_flag
from helper_visual_comparison_table import save_comparison_tables, table_path
from helper_visual_lp_graph import (
    ACCEPTABLE_THRESHOLD,
    RELIABLE_THRESHOLD,
    chart_path,
    save_lp_chart,
    status_of,
    value_label_position,
)

PNG = b"\x89PNG\r\n\x1a\n"


def _data():
    """3 scenarios, 2 coders: everything Clear except two disagreements."""
    units = ["p1/S1", "p2/S1", "p3/S2"]
    a = pd.DataFrame({c: ["Clear"] * 3 for c in COMPONENTS}, index=units)
    b = a.copy()
    b.loc["p2/S1", "knowledge"] = "Not specified"
    b.loc["p3/S2", "access"] = "Ambiguous"
    return CodingData("a", units, {"a": a, "b": b}, {"a": [], "b": []}, {"a": 0, "b": 0})


def _table(name="humans"):
    rows = [{"comparison": name, "component": comp, "n_units": 3,
             "pct_agree": 1.0, "alpha": float("nan"),
             "flags_a": "C=3 A=0 N=0", "flags_b": "C=3 A=0 N=0"}
            for comp in COMPONENTS]
    table = pd.DataFrame(rows)
    table.loc[table.component == "knowledge", "alpha"] = -0.2
    table.loc[table.component == "access", "alpha"] = 0.9
    return table


def test_status_bands():
    # the chart's thresholds (currently 0.750 tentative, 0.900 reliable)
    assert (ACCEPTABLE_THRESHOLD, RELIABLE_THRESHOLD) == (0.750, 0.900)
    assert status_of(float("nan")) == "n/a"
    assert status_of(RELIABLE_THRESHOLD) == "reliable"
    assert status_of(1.0) == "reliable"
    assert status_of(RELIABLE_THRESHOLD - 0.0001) == "tentative"
    assert status_of(ACCEPTABLE_THRESHOLD) == "tentative"
    assert status_of(ACCEPTABLE_THRESHOLD - 0.0001) == "below"
    assert status_of(-0.2) == "below"


def test_value_label_does_not_run_into_the_agree_column():
    span = 1.25   # axis from -0.25 to 1.0
    # near 1.0 (e.g. alpha = 1.00): above the dot, centred on it, so it stays left of "% agree"
    x, y, ha, va = value_label_position(1.0, 3, span)
    assert (x, ha, va) == (1.0, "center", "bottom") and y > 3
    # normal: right of the dot; negative: left of it
    assert value_label_position(0.5, 3, span)[1:] == (3, "left", "center")
    assert value_label_position(0.5, 3, span)[0] > 0.5
    assert value_label_position(-0.2, 3, span)[1:] == (3, "right", "center")
    assert value_label_position(-0.2, 3, span)[0] < -0.2


def test_constant_flag():
    data = _data()
    assert constant_flag(data.matrix("threat_source", ["a", "b"])) == "Clear"
    assert constant_flag(data.matrix("knowledge", ["a", "b"])) is None
    assert constant_flag(data.matrix("access", ["a", "b"])) is None


def test_matrix_preserves_three_flag_codes():
    matrix = _data().matrix("access", ["a", "b"])
    assert matrix[0, 2] == 2
    assert matrix[1, 2] == 1


def test_file_names():
    run_stem = "results/KA_result_llm_20261008_1500"
    assert chart_path(run_stem).name == "KA_chart_llm_20261008_1500.png"
    assert table_path(run_stem, "llms").name == "judgement_comparison_llms_20261008_1500.png"
    assert (table_path(run_stem, "llm_glm_5.3_vs_llm_deepseek_v4.1").name
            == "judgement_comparison_llm_glm_5_3_vs_llm_deepseek_v4_1_20261008_1500.png")
    run_stem = "results/KA_result_all_20261008_1500"
    assert chart_path(run_stem).name == "KA_chart_all_20261008_1500.png"
    assert (table_path(run_stem, "Combined (llm+human)").name
            == "judgement_comparison_combined_llm_human_20261008_1500.png")
    assert table_path("my_run", "humans").name == "judgement_comparison_humans.png"
    assert chart_path("my_run").name == "my_run_chart.png"


def test_one_chart_with_a_card_per_comparison(tmp_path):
    names = ["llms", "a_vs_b", "a_vs_c", "b_vs_c", "Combined (llm+human)"]   # 2 cards per row
    table = pd.concat([_table(n) for n in names], ignore_index=True)
    comparisons = [Comparison(n, ["a", "b"]) for n in names]
    path = save_lp_chart(table, _data(), comparisons, tmp_path / "lib_ka_result_llm_20261008_1500")
    assert path.read_bytes()[:8] == PNG


def test_perfect_agreement_uses_alpha_one_marker_and_label(tmp_path, monkeypatch):
    monkeypatch.setattr(helper_visual_lp_graph.plt, "close", lambda _fig: None)
    table = _table()
    comparisons = [Comparison("humans", ["a", "b"])]

    save_lp_chart(table, _data(), comparisons, tmp_path / "perfect_agreement")

    ax = helper_visual_lp_graph.plt.gcf().axes[0]
    assert any("1.00" in text.get_text() for text in ax.texts)
    assert not any("100% agreement" in text.get_text() for text in ax.texts)
    assert any((collection.get_offsets() == [[1.0, len(COMPONENTS) - 1]]).all()
               for collection in ax.collections if collection.get_offsets().shape == (1, 2))


def test_one_comparison_table_per_comparison(tmp_path):
    comparisons = [Comparison("humans", ["a", "b"]), Comparison("Combined (llm+human)", ["a", "b"])]
    paths = save_comparison_tables(_data(), comparisons,
                                   tmp_path / "custom_ka_result_llm_20261008_1500")
    assert [p.name for p in paths] == ["judgement_comparison_humans_20261008_1500.png",
                                       "judgement_comparison_combined_llm_human_20261008_1500.png"]
    assert all(p.read_bytes()[:8] == PNG for p in paths)
