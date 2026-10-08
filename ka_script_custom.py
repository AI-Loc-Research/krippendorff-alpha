"""Krippendorff's alpha implemented from scratch, following Krippendorff (2011),
"Computing Krippendorff's Alpha-Reliability", steps 1-4:

    1. reliability data matrix   coders x units, NaN = missing   (built in data_preprocessing)
    2. coincidence matrix        o[c, k] = sum over units of (c-k pairs in unit) / (m_u - 1)
    3. difference function       delta^2(c, k): nominal, ordinal, interval or ratio
    4. alpha                     1 - D_o / D_e

Run from the project root (one flag is required):
    uv run python ka_script_custom.py --human    # human coders (mentees) with each other
    uv run python ka_script_custom.py --llm      # the same, plus each human vs each LLM,
                                                 # plus all coders combined (last rows)

Every run also checks each alpha against the `krippendorff` library (one line: MATCH).
"""

from __future__ import annotations

import time
from pathlib import Path

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
from helper_visual_lp_chart import save_lp_chart

PROJECT = Path(__file__).resolve().parent
CONFIG = PROJECT / "config.toml"
RESULTS = PROJECT / "results"
THRESHOLD = 0.667  # lower bound for tentative conclusions
TIMESTAMP = time.strftime("%Y%m%d_%H%M")
LEVELS = ("nominal", "ordinal", "interval", "ratio")


# ---------------------------------------------------------------- step 2

def coincidence_matrix(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (values, o) where values are the distinct codes (sorted) and o is the
    coincidence matrix. Units with fewer than 2 values cannot be paired and add nothing."""
    matrix = np.asarray(matrix, dtype=float)
    values = np.unique(matrix[~np.isnan(matrix)])
    index = {v: i for i, v in enumerate(values)}
    o = np.zeros((len(values), len(values)))

    for unit in matrix.T:                      # one column = one unit (scenario)
        unit_values = unit[~np.isnan(unit)]
        m_u = len(unit_values)
        if m_u < 2:
            continue
        counts = np.zeros(len(values))         # how many coders gave each value here
        for v in unit_values:
            counts[index[v]] += 1
        # ordered pairs from different coders: c != k gives n_c * n_k, c == k gives n_c(n_c - 1)
        pairs = np.outer(counts, counts) - np.diag(counts)
        o += pairs / (m_u - 1)
    return values, o


# ---------------------------------------------------------------- step 3

def difference_function(values: np.ndarray, n_c: np.ndarray, level: str) -> np.ndarray:
    """delta^2[c, k] for every pair of values."""
    if level not in LEVELS:
        raise ValueError(f"level must be one of {LEVELS}")
    size = len(values)
    d2 = np.zeros((size, size))
    for c in range(size):
        for k in range(size):
            if level == "nominal":
                d2[c, k] = 0.0 if c == k else 1.0
            elif level == "ordinal":
                lo, hi = min(c, k), max(c, k)
                d2[c, k] = (n_c[lo:hi + 1].sum() - (n_c[c] + n_c[k]) / 2) ** 2
            elif level == "interval":
                d2[c, k] = (values[c] - values[k]) ** 2
            else:  # ratio
                total = values[c] + values[k]
                d2[c, k] = 0.0 if total == 0 else ((values[c] - values[k]) / total) ** 2
    return d2


# ---------------------------------------------------------------- step 4

def alpha_details(matrix: np.ndarray, level: str = "nominal") -> dict:
    """alpha together with its ingredients. alpha is NaN (undefined) when there is
    nothing to compare: fewer than 2 pairable values, or no variation (D_e = 0)."""
    values, o = coincidence_matrix(matrix)
    n_c = o.sum(axis=1)                        # how often each value was used (pairable only)
    n = n_c.sum()                              # total pairable values
    if n < 2:
        return {"alpha": float("nan"), "D_o": float("nan"), "D_e": float("nan"), "n": n}

    d2 = difference_function(values, n_c, level)
    D_o = (o * d2).sum() / n                               # observed disagreement
    D_e = (np.outer(n_c, n_c) * d2).sum() / (n * (n - 1))  # expected (chance) disagreement
    alpha = float("nan") if D_e == 0 else 1 - D_o / D_e
    return {"alpha": float(alpha), "D_o": float(D_o), "D_e": float(D_e), "n": float(n)}


def alpha_nominal(matrix: np.ndarray) -> float:
    return alpha_details(matrix, "nominal")["alpha"]


# ---------------------------------------------------------------- report

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
            details = alpha_details(m, "nominal")
            row[f"pct_agree_{view}"] = percent_agreement(m)
            row[f"D_o_{view}"] = details["D_o"]
            row[f"D_e_{view}"] = details["D_e"]
            row[f"alpha_{view}"] = details["alpha"]
        for coder in coders:
            row[f"flags_{coder}"] = flag_counts(data, coder, comp)
        rows.append(row)
    return pd.DataFrame(rows)


def verdict(alpha: float, n_units: int = 1) -> str:
    if np.isnan(alpha):  # not an error: every coder gave the same flag, so alpha = 0/0
        return "no variation" if n_units > 0 else "no data"
    return "PASS" if alpha >= THRESHOLD else "below 0.667"


def alpha_text(alpha: float) -> str:
    return "n/a" if np.isnan(alpha) else f"{alpha:.3f}"


def print_table(df: pd.DataFrame, comparisons) -> None:
    coders_of = {c.name: c.coders for c in comparisons}
    for name, block in df.groupby("comparison", sort=False):
        print(f"\n• {name} judgement; between: {' vs '.join(coders_of[name])} "
              f"(THRESHOLD: {THRESHOLD})  [alpha = 1 - D_o / D_e]\n")
        head = f"{'%agree':>6} {'D_o':>6} {'D_e':>6} {'alpha':>7} {'':12}"
        print(f"{'component':36} | {head} | {head}")
        print(f"{'':36} |{'------------ 3 flags ------------':^41} |"
              f"{'------------ binary ------------':^41}")
        for _, r in block.iterrows():
            cells = []
            for view in VIEWS:
                cells.append(f"{r[f'pct_agree_{view}']:>6.1%} {r[f'D_o_{view}']:>6.3f} "
                             f"{r[f'D_e_{view}']:>6.3f} {alpha_text(r[f'alpha_{view}']):>7} "
                             f"{verdict(r[f'alpha_{view}'], r.n_units):12}")
            print(f"{r.component:36} | {cells[0]} | {cells[1]}")


def crosscheck(data, comparisons) -> None:
    """Compare every alpha with the `krippendorff` library (runs on every call)."""
    from ka_script_lib import alpha_nominal as library_alpha

    worst, count = 0.0, 0
    for c in comparisons:
        for comp in COMPONENTS:
            for view in VIEWS:
                m = data.matrix(comp, c.coders, view)
                ours, theirs = alpha_nominal(m), library_alpha(m)
                count += 1
                if np.isnan(ours) and np.isnan(theirs):
                    continue
                worst = max(worst, abs(ours - theirs))
    status = "MATCH" if worst < 1e-9 else "MISMATCH"
    print(f"\nCross-check vs krippendorff library: {count} alphas, "
          f"max difference {worst:.1e} -> {status}")


def main() -> None:
    mode = parse_mode("ka_script_custom.py", "our from-scratch implementation")
    coders, units_from = load_config(CONFIG)
    comparisons = build_comparisons(coders, mode)
    data = load_coding_data(coders_needed(coders, comparisons, units_from), units_from)

    print(data_check_report(data))

    table = pd.concat(
        [alpha_table(data, c.name, c.coders) for c in comparisons], ignore_index=True
    )
    print_table(table, comparisons)
    crosscheck(data, comparisons)

    out = RESULTS / f"custom_KA_result_{mode}_{TIMESTAMP}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    table.round(4).to_csv(out, index=False)  # 4 decimals in the file; charts use full precision
    print(f"\nSaved: {out.relative_to(PROJECT)}")
    saved = [save_lp_chart(table, data, comparisons, out),
             *save_comparison_tables(data, comparisons, out)]
    for path in saved:
        print(f"Saved: {path.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
