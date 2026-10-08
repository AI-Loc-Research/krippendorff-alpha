"""Figures for Krippendorff's alpha results (shared by the library and custom scripts).

save_visualizations(table, data, comparisons, csv_path) writes PNGs next to the CSV:
    <prefix>_chart_<names>_<time>.png        lollipop chart of 3-flag alpha per component
    <prefix>_labels_<comparison>_<time>.png  one per comparison: each coder's raw labels
                                             (C / A / N) side by side, 25 scenarios x 7
                                             components, green = coders agree, red = differ

Design notes:
- Red vs green is indistinguishable for many colour-blind readers, so colour never carries
  the meaning alone: the chart also shows the verdict by position against labelled
  threshold lines, and the label grid marks disagreements in bold with an outline.
- Raw % agreement and alpha are different measures, so they are never drawn on one axis.
"""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files only; no window needed

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

from data_preprocessing import COMPONENTS, constant_flag  # noqa: E402

TENTATIVE, RELIABLE = 0.667, 0.800

# Status colours (fixed meaning) and neutral chart chrome
GOOD, WARNING, CRITICAL = "#0ca30c", "#fab219", "#d03b3b"
STATUS = {
    "reliable": (GOOD, "alpha >= 0.800  reliable"),
    "tentative": (WARNING, "0.667 <= alpha < 0.800  tentative conclusions only"),
    "below": (CRITICAL, "alpha < 0.667  do not rely on the data"),
    "n/a": ("#898781", "n/a: every coder gave the same flag (100% agreement, nothing to measure)"),
}
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#e1e0d9", "#c3c2b7", "#ffffff"
MATCH_FILL, DIFF_FILL, MISSING_FILL = "#cfeccf", "#f6cfcf", "#ecebe6"

SHORT = {
    "threat_source": "TS",
    "objective_or_harmful_outcome": "Obj",
    "capability": "Cap",
    "knowledge": "Know",
    "access": "Acc",
    "constraints_or_enabling_conditions": "Cond",
    "target_or_asset_at_risk": "Tgt",
}
LETTER = {"Clear": "C", "Ambiguous": "A", "Not specified": "N"}

_INSTALLED = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Segoe UI", "Helvetica Neue", "Arial") if f in _INSTALLED), "DejaVu Sans")

plt.rcParams.update({
    "font.family": FONT,
    "font.size": 10,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_2,
    "xtick.color": MUTED,
    "ytick.color": INK,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def status_of(alpha: float) -> str:
    if alpha is None or np.isnan(alpha):
        return "n/a"
    if alpha >= RELIABLE:
        return "reliable"
    return "tentative" if alpha >= TENTATIVE else "below"


def pretty(component: str) -> str:
    return component.replace("_", " ").capitalize()


# ---------------------------------------------------------------- chart (3 flags only)

def _lollipop_panel(ax, block: pd.DataFrame, data, coders: list[str], x_min: float) -> None:
    components = list(block["component"])
    y = np.arange(len(components))[::-1]  # first component at the top

    ax.set_xlim(x_min, 1.0)
    ax.set_ylim(-0.7, len(components) - 0.3)
    # 0.75 is left out: the labelled 0.667 / 0.800 threshold lines already mark that region
    ax.set_xticks([t for t in np.arange(-1.0, 1.01, 0.25)
                   if t >= x_min - 1e-9 and not np.isclose(t, 0.75)])
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_yticks(y, [pretty(c) for c in components])
    ax.set_xlabel("Krippendorff's alpha (nominal, 3 flags: Clear / Ambiguous / Not specified)",
                  color=INK_2)

    ax.axvline(0, color=BASELINE, linewidth=1, zorder=1)
    for threshold, label in ((TENTATIVE, "0.667"), (RELIABLE, "0.800")):
        ax.axvline(threshold, color=INK_2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
        ax.text(threshold, 1.01, label, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8.5, color=INK_2)

    # raw % agreement as a text column on the right (different measure, so no shared axis)
    ax.text(1.03, 1.01, "% agree", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, color=INK_2)
    span = 1.0 - x_min
    for yi, (_, r) in zip(y, block.iterrows()):
        alpha = r["alpha_3flag"]
        status = status_of(alpha)
        color = STATUS[status][0]
        ax.text(1.03, yi, f"{r['pct_agree_3flag']:.0%}", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=9, color=INK_2)
        if status == "n/a":
            flag = constant_flag(data.matrix(r["component"], coders, "3flag"), "3flag")
            reason = f"n/a: all coders gave '{flag}' to every scenario" if flag else "n/a: no data"
            ax.scatter(0, yi, s=70, facecolor=SURFACE, edgecolor=color, linewidth=1.5, zorder=3)
            ax.text(0.03 * span, yi, reason, va="center", ha="left", fontsize=8.5, color=INK_2)
            continue
        ax.hlines(yi, 0, alpha, color=color, linewidth=2, zorder=2)
        ax.scatter(alpha, yi, s=80, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
        right = alpha >= 0
        ax.text(alpha + (0.025 if right else -0.025) * span, yi, f"{alpha:.2f}",
                va="center", ha="left" if right else "right", fontsize=9, color=INK,
                zorder=4, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5))


def save_chart(table: pd.DataFrame, data, comparisons, path: Path) -> Path:
    alphas = table["alpha_3flag"].to_numpy(dtype=float)
    lowest = np.nanmin(alphas) if np.isfinite(alphas).any() else 0.0
    x_min = min(-0.25, np.floor((lowest - 0.15) / 0.25) * 0.25)

    names = list(dict.fromkeys(table["comparison"]))
    coders_of = {c.name: c.coders for c in comparisons}
    n_rows = len(table[table["comparison"] == names[0]])
    fig, axes = plt.subplots(len(names), 1, figsize=(10, (0.42 * n_rows + 1.5) * len(names) + 0.8),
                             layout="constrained", squeeze=False)
    for ax, name in zip(axes[:, 0], names):
        coders = coders_of.get(name, [])
        ax.set_title(f"{name}:  {'  vs  '.join(coders)}", loc="left", fontsize=12,
                     fontweight="semibold", color=INK, pad=22)
        _lollipop_panel(ax, table[table["comparison"] == name], data, coders, x_min)

    handles = [Line2D([], [], marker="o", linestyle="", markersize=8,
                      markerfacecolor=SURFACE if key == "n/a" else color,
                      markeredgecolor=color, label=label)
               for key, (color, label) in STATUS.items()]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False,
               fontsize=9, labelcolor=INK_2)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- label grid

def save_label_grid(data, comparison, path: Path) -> Path:
    """Each coder's raw flags as a scenarios x components grid, grids side by side.
    A cell is green when every coder gave the same flag, red (bold, outlined) when not."""
    coders = comparison.coders
    units = data.units
    n_rows, n_cols = len(units), len(COMPONENTS)
    gap, label_w = 1.2, 6.2  # gap between grids, width of the scenario-label column (cell units)

    # agreement per cell: True / False, or None when a coder left it empty
    agree = np.empty((n_rows, n_cols), dtype=object)
    for j, comp in enumerate(COMPONENTS):
        values = [list(data.flags[c][comp]) for c in coders]
        for i in range(n_rows):
            cell = [v[i] for v in values]
            agree[i, j] = None if any(pd.isna(x) for x in cell) else len(set(cell)) == 1

    width = label_w + len(coders) * n_cols + (len(coders) - 1) * gap
    fig_h = 0.3 * (n_rows + 3.8) + 1.25         # grid rows + headers/counts, plus title & footer
    fig = plt.figure(figsize=(0.42 * width + 0.6, fig_h))
    ax = fig.add_axes([0.01, 1.0 / fig_h, 0.98, 1 - 1.55 / fig_h])
    ax.set_xlim(-label_w, width - label_w)
    ax.set_ylim(n_rows + 1.6, -2.2)  # top: grid titles and headers; bottom: match counts
    ax.set_axis_off()

    for i, unit in enumerate(units):
        paper, scenario = unit.split("/")
        ax.text(-0.3, i + 0.5, f"{paper}  {scenario}", ha="right", va="center",
                fontsize=8.5, color=INK)

    for g, coder in enumerate(coders):
        x0 = g * (n_cols + gap)
        ax.text(x0 + n_cols / 2, -1.55, coder, ha="center", va="center", fontsize=11,
                fontweight="semibold", color=INK)
        for j, comp in enumerate(COMPONENTS):
            ax.text(x0 + j + 0.5, -0.5, SHORT[comp], ha="center", va="center",
                    fontsize=8.5, color=INK_2)
            flags = list(data.flags[coder][comp])
            for i in range(n_rows):
                state = agree[i, j]
                fill = MISSING_FILL if state is None else (MATCH_FILL if state else DIFF_FILL)
                ax.add_patch(Rectangle((x0 + j + 0.05, i + 0.05), 0.9, 0.9, facecolor=fill,
                                       edgecolor=CRITICAL if state is False else "none",
                                       linewidth=1.1))
                letter = "–" if pd.isna(flags[i]) else LETTER[flags[i]]
                ax.text(x0 + j + 0.5, i + 0.5, letter, ha="center", va="center", fontsize=9,
                        color=INK, fontweight="bold" if state is False else "normal")
            matches = sum(1 for i in range(n_rows) if agree[i, j] is True)
            ax.text(x0 + j + 0.5, n_rows + 0.75, f"{matches}/{n_rows}", ha="center",
                    va="center", fontsize=7.5, color=INK_2)
    ax.text(-0.3, n_rows + 0.75, "same flag", ha="right", va="center", fontsize=8.5, color=INK_2)

    total = sum(1 for state in agree.flat if state is True)
    fig.suptitle(f"{comparison.name}:  {'  vs  '.join(coders)}   ·   same flag in {total} of "
                 f"{n_rows * n_cols} cells ({total / (n_rows * n_cols):.0%})",
                 x=0.01, y=1 - 0.12 / fig_h, ha="left", va="top", fontsize=12,
                 fontweight="semibold", color=INK)
    fig.legend(handles=[Patch(facecolor=MATCH_FILL, label="same flag from every coder"),
                        Patch(facecolor=DIFF_FILL, edgecolor=CRITICAL,
                              label="flags differ (bold letter, outlined)"),
                        Patch(facecolor=MISSING_FILL, label="missing (–)")],
               loc="lower left", bbox_to_anchor=(0.01, 0.62 / fig_h), ncol=3, frameon=False,
               fontsize=8.5, labelcolor=INK_2)
    fig.text(0.01, 0.36 / fig_h, "C = Clear,  A = Ambiguous,  N = Not specified",
             fontsize=8, color=INK_2)
    fig.text(0.01, 0.14 / fig_h, ",  ".join(f"{SHORT[c]} = {pretty(c).lower()}"
                                             for c in COMPONENTS), fontsize=8, color=INK_2)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- entry point

def save_visualizations(table: pd.DataFrame, data, comparisons, csv_path: Path) -> list[Path]:
    """Save the chart and one label grid per comparison next to `csv_path`, named after it."""
    csv_path = Path(csv_path)
    folder = csv_path.parent
    folder.mkdir(parents=True, exist_ok=True)
    stem = csv_path.stem
    m = re.match(r"^(.*)_result_(.*)_(\d{8}_\d{4})$", stem)  # e.g. lib_ka_result_humans_20261008_1530

    if m:
        prefix, names, stamp = m.groups()
        chart = folder / f"{prefix}_chart_{names}_{stamp}.png"
        grid = lambda c: folder / f"{prefix}_labels_{c.name}_{stamp}.png"  # noqa: E731
    else:  # custom --out name
        chart = folder / f"{stem}_chart.png"
        grid = lambda c: folder / f"{stem}_labels_{c.name}.png"  # noqa: E731

    paths = [save_chart(table, data, comparisons, chart)]
    paths += [save_label_grid(data, c, grid(c)) for c in comparisons]
    return paths
