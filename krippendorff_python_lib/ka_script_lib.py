"""Krippendorff's alpha computed with the `krippendorff` library (fast-krippendorff).

Run from the project root:
    uv run python -m krippendorff_python_lib.ka_script_lib                      # all comparisons
    uv run python -m krippendorff_python_lib.ka_script_lib --only humans        # just one
    uv run python -m krippendorff_python_lib.ka_script_lib --only humans adya_vs_llm
"""

from __future__ import annotations

import argparse
from pathlib import Path
import time

import krippendorff
import numpy as np
import pandas as pd

from data_preprocessing import (
    COMPONENTS,
    VIEWS,
    coders_needed,
    data_check_report,
    flag_counts,
    load_coding_data,
    load_config,
    pairable_units,
    percent_agreement,
    select_comparisons,
)
from helper_visualize import save_visualizations

THRESHOLD = 0.667  # lower bound for tentative conclusions
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


def verdict(alpha: float) -> str:
    if np.isnan(alpha):
        return "undefined"
    return "PASS" if alpha >= THRESHOLD else "below 0.667"


def print_table(df: pd.DataFrame, comparisons) -> None:
    coders_of = {c.name: c.coders for c in comparisons}
    for name, block in df.groupby("comparison", sort=False):
        print(f"\n• {name} judgement; between: {' vs '.join(coders_of[name])} (THRESHOLD: {THRESHOLD})\n")
        print(f"{'component':36} | {'%agree':>6} {'alpha':>7} {'':11} | "
              f"{'%agree':>6} {'alpha':>7} {'':11}")
        print(f"{'':36} |{'----- 3 flags -----':^26} | {'----- binary -----':^26}")
        for _, r in block.iterrows():
            print(f"{r.component:36} | "
                  f"{r.pct_agree_3flag:>6.1%} {r.alpha_3flag:>7.3f} {verdict(r.alpha_3flag):11} | "
                  f"{r.pct_agree_binary:>6.1%} {r.alpha_binary:>7.3f} {verdict(r.alpha_binary):11}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default="config.toml")
    parser.add_argument("--only", nargs="+", metavar="NAME",
                        help="run only these comparisons from config.toml (default: all)")
    parser.add_argument("--out", default=None,
                        help="CSV path (default: results/lib_ka_result_all_TIMESTAMP.csv, or "
                           "results/lib_ka_result_<names>_TIMESTAMP.csv with --only)")
    args = parser.parse_args()

    coders, comparisons, units_from = load_config(args.config)
    comparisons = select_comparisons(comparisons, args.only)
    data = load_coding_data(coders_needed(coders, comparisons, units_from), units_from)

    print(data_check_report(data))

    table = pd.concat(
        [alpha_table(data, c.name, c.coders) for c in comparisons], ignore_index=True
    )
    print_table(table, comparisons)

    if args.out:
        out = Path(args.out)
    elif args.only:
        out = Path(f"results/lib_ka_result_{'_'.join(args.only)}_{TIMESTAMP}.csv")
    else:
        out = Path(f"results/lib_ka_result_all_{TIMESTAMP}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(out, index=False)
    print(f"\nSaved: {out}")
    for path in save_visualizations(table, comparisons, out):
        print(f"Saved: {path}")


if __name__ == "__main__":
    main()
