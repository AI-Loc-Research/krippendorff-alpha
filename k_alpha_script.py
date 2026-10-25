"""Krippendorff's alpha computed with the `krippendorff` library (fast-krippendorff).

Run from the project root:
    uv run python ka_script_lib.py --human    # only the human coders (mentees), with each other
    uv run python ka_script_lib.py --llm      # only the LLM coders: all LLMs together plus every
                                              # LLM pair, on the scenarios every LLM has judged
    uv run python ka_script_lib.py            # no flag: all coders (humans + LLMs) combined,
                                              # on the scenarios of units_from (config.toml)
"""

from __future__ import annotations

import time
from pathlib import Path

import krippendorff
import numpy as np
import pandas as pd

from data_preprocessing import (
    COMPONENTS,
    VIEWS,
    build_comparisons,
    coders_needed,
    data_check_report,
    flag_counts,
    load_coding_data,
    load_config,
    pairable_units,
    parse_mode,
    percent_agreement,
)
from helper_visual_comparison_table import save_comparison_tables
from helper_visual_lp_graph import save_lp_chart

PROJECT = Path(__file__).resolve().parent
CONFIG = PROJECT / "config.toml"
RESULTS = PROJECT / "results"
THRESHOLD = 0.750
TIMESTAMP = time.strftime("%Y%m%d_%H%M")


def alpha_nominal(matrix: np.ndarray) -> float:
    """Nominal alpha for a coders x units matrix (NaN = missing).

    Returns NaN when alpha is undefined: all values identical (no variation, D_e = 0).
    The library would raise ValueError in that case.
    """
    values = matrix[~np.isnan(matrix)]
    if np.unique(values).size < 2:
        return float("nan")
    # level_of_measurement MUST be explicit: the library default is "interval".
    return float(krippendorff.alpha(reliability_data=matrix, level_of_measurement="nominal"))


def alpha_table(data, comparison_name: str, coders: list[str]) -> pd.DataFrame:
    rows = []
    for comp in COMPONENTS:
        # Missing cells are the same in both views, so one n_units covers both.
        row = {
            "comparison": comparison_name,
            "component": comp,
            "n_units": pairable_units(data.matrix(comp, coders, "3flag")),
        }
        for view in VIEWS:
            m = data.matrix(comp, coders, view)
            row[f"pct_agree_{view}"] = percent_agreement(m)
            row[f"alpha_{view}"] = alpha_nominal(m)
        for coder in coders:
            row[f"flags_{coder}"] = flag_counts(data, coder, comp)
        rows.append(row)
    return pd.DataFrame(rows)


def verdict(alpha: float, n_units: int = 1) -> str:
    if np.isnan(alpha):  # not an error: every coder gave the same flag, so alpha = 0/0
        return "no variation" if n_units > 0 else "no data"
    return "PASS" if alpha >= THRESHOLD else f"below {THRESHOLD:.3f}"


def alpha_text(alpha: float) -> str:
    return "n/a" if np.isnan(alpha) else f"{alpha:.3f}"


def print_table(df: pd.DataFrame, comparisons) -> None:
    coders_of = {c.name: c.coders for c in comparisons}
    for name, block in df.groupby("comparison", sort=False):
        print(f"\n• {name} judgement; between: {' vs '.join(coders_of[name])} (THRESHOLD: {THRESHOLD})\n")
        print(f"{'component':36} | {'%agree':>6} {'alpha':>7} {'':12} | "
              f"{'%agree':>6} {'alpha':>7} {'':12}")
        print(f"{'':36} |{'----- 3 flags -----':^27} | {'----- binary -----':^27}")
        for _, r in block.iterrows():
            print(f"{r.component:36} | "
                  f"{r.pct_agree_3flag:>6.1%} {alpha_text(r.alpha_3flag):>7} "
                  f"{verdict(r.alpha_3flag, r.n_units):12} | "
                  f"{r.pct_agree_binary:>6.1%} {alpha_text(r.alpha_binary):>7} "
                  f"{verdict(r.alpha_binary, r.n_units):12}")


def main() -> None:
    mode = parse_mode("ka_script_lib.py", "the krippendorff library")
    coders, units_from = load_config(CONFIG)
    comparisons = build_comparisons(coders, mode)
    # --llm: the units are the scenarios every LLM has judged (no human sheet is loaded);
    # --human and no flag: the scenarios of the units_from coder (the 25 sampled)
    units = None if mode == "llm" else units_from
    data = load_coding_data(coders_needed(coders, comparisons, units), units)

    print(data_check_report(data))

    table = pd.concat(
        [alpha_table(data, c.name, c.coders) for c in comparisons], ignore_index=True
    )
    print_table(table, comparisons)

    out = RESULTS / f"k_alpha_result_{mode}_{TIMESTAMP}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.round(4).to_csv(out, index=False)  # 4 decimals in the file; charts use full precision
    print(f"\nSaved: {out.relative_to(PROJECT)}")
    saved = [save_lp_chart(table, data, comparisons, out),
             *save_comparison_tables(data, comparisons, out)]
    for path in saved:
        print(f"Saved: {path.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
