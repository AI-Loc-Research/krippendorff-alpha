"""Figures for Krippendorff's alpha results (shared by the library and custom scripts).

save_visualizations(table, comparisons, csv_path) writes two PNGs next to the CSV:
    <stem with _result_ -> _chart_>.png   lollipop chart of alpha per component
    <stem with _result_ -> _table_>.png   summary table: n, % agreement, alpha, flag counts

Design notes:
- Status colours (green / amber / red) reinforce the verdict but never carry it alone:
  red vs green is indistinguishable for deuteranopes, so every verdict is also shown
  by position against labelled threshold lines (chart) or by a text word (table).
- Raw % agreement and alpha are different measures, so they are never drawn on one
  axis: the chart lists % agreement as text beside each row instead.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files only; no window needed

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

TENTATIVE, RELIABLE = 0.667, 0.800

# Status colours (fixed meaning) and neutral chart chrome
STATUS = {
    "reliable": ("#0ca30c", "reliable", "alpha >= 0.800  reliable"),
    "tentative": ("#fab219", "tentative", "0.667 <= alpha < 0.800  tentative conclusions only"),
    "below": ("#d03b3b", "below", "alpha < 0.667  do not rely on the data"),
    "undefined": ("#898781", "undefined", "undefined: every coder gave the same flag"),
}
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE, SURFACE = "#e1e0d9", "#c3c2b7", "#ffffff"
VIEW_TITLES = {
    "3flag": "3 flags  (Clear / Ambiguous / Not specified)",
    "binary": "Binary  (specified vs not specified)",
}
VIEW_SHORT = {"3flag": "3 flags", "binary": "binary"}

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
        return "undefined"
    if alpha >= RELIABLE:
        return "reliable"
    return "tentative" if alpha >= TENTATIVE else "below"


def pretty(component: str) -> str:
    return component.replace("_", " ").capitalize()


def _views(table: pd.DataFrame) -> list[str]:
    return [v for v in ("3flag", "binary") if f"alpha_{v}" in table.columns]


# ---------------------------------------------------------------- chart

def _lollipop_panel(ax, block: pd.DataFrame, view: str, x_min: float) -> None:
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
    ax.set_xlabel("Krippendorff's alpha (nominal)", color=INK_2)
    ax.set_title(VIEW_TITLES[view], loc="left", color=INK, fontsize=10.5, pad=22)

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
        alpha = r[f"alpha_{view}"]
        status = status_of(alpha)
        color = STATUS[status][0]
        ax.text(1.03, yi, f"{r[f'pct_agree_{view}']:.0%}", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=9, color=INK_2)
        if status == "undefined":
            ax.scatter(0, yi, s=70, facecolor=SURFACE, edgecolor=color, linewidth=1.5, zorder=3)
            ax.text(0.03 * span, yi, "undefined", va="center", ha="left", fontsize=8.5, color=MUTED)
            continue
        ax.hlines(yi, 0, alpha, color=color, linewidth=2, zorder=2)
        ax.scatter(alpha, yi, s=80, color=color, edgecolor=SURFACE, linewidth=2, zorder=3)
        right = alpha >= 0
        ax.text(alpha + (0.025 if right else -0.025) * span, yi, f"{alpha:.2f}",
                va="center", ha="left" if right else "right", fontsize=9, color=INK,
                zorder=4, bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5))


def save_chart(table: pd.DataFrame, comparisons, path: Path) -> Path:
    views = _views(table)
    alphas = table[[f"alpha_{v}" for v in views]].to_numpy(dtype=float)
    lowest = np.nanmin(alphas) if np.isfinite(alphas).any() else 0.0
    x_min = min(-0.25, np.floor((lowest - 0.15) / 0.25) * 0.25)

    names = list(dict.fromkeys(table["comparison"]))
    coders_of = {c.name: c.coders for c in comparisons}
    n_rows = len(table[table["comparison"] == names[0]])
    fig = plt.figure(figsize=(13, (0.42 * n_rows + 1.9) * len(names) + 0.9),
                     layout="constrained")
    subfigs = np.atleast_1d(fig.subfigures(len(names), 1))
    for subfig, name in zip(subfigs, names):
        block = table[table["comparison"] == name]
        subfig.suptitle(f"{name}:  {'  vs  '.join(coders_of.get(name, []))}",
                        x=0.01, ha="left", fontsize=12, fontweight="semibold", color=INK)
        axes = np.atleast_1d(subfig.subplots(1, len(views), sharey=True))
        for ax, view in zip(axes, views):
            _lollipop_panel(ax, block, view, x_min)

    handles = [Line2D([], [], marker="o", linestyle="", markersize=8,
                      markerfacecolor=SURFACE if key == "undefined" else color,
                      markeredgecolor=color, label=label)
               for key, (color, _, label) in STATUS.items()]
    fig.legend(handles=handles, loc="outside lower center", ncol=4, frameon=False,
               fontsize=9, labelcolor=INK_2)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- table

def _table_columns(block: pd.DataFrame, views: list[str]) -> list[tuple[str, str, float, str]]:
    """(key, header, relative width, alignment) for each column."""
    cols = [("component", "Component", 3.1, "left"), ("n_units", "n", 0.5, "center")]
    for v in views:
        cols += [(f"pct_agree_{v}", "% agree", 0.9, "center"), (f"alpha_{v}", "alpha", 1.45, "center")]
    cols += [(c, c.removeprefix("flags_"), 1.9, "center")
             for c in block.columns if c.startswith("flags_") and block[c].notna().all()]
    return cols


def _draw_table(ax, block: pd.DataFrame, title: str, views: list[str]) -> None:
    cols = _table_columns(block, views)
    widths = np.array([c[2] for c in cols])
    edges = np.concatenate([[0], np.cumsum(widths) / widths.sum()])
    n_body = len(block)
    row_h = 1 / (n_body + 3)  # title row, group row, header row, body rows
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    def cell_x(i, align):
        if align == "left":
            return edges[i] + 0.006
        return (edges[i] + edges[i + 1]) / 2

    ax.text(0.0, 1 - 0.5 * row_h, title, ha="left", va="center", fontsize=11.5,
            fontweight="semibold", color=INK)

    # group headers ("3 flags", "binary", "flag counts") spanning their columns
    y_group = 1 - 1.5 * row_h
    for v in views:
        idx = [i for i, c in enumerate(cols) if c[0].endswith(f"_{v}")]
        ax.text((edges[idx[0]] + edges[idx[-1] + 1]) / 2, y_group, VIEW_SHORT[v],
                ha="center", va="center", fontsize=9, color=INK_2, fontweight="semibold")
        ax.plot([edges[idx[0]] + 0.004, edges[idx[-1] + 1] - 0.004], [y_group - 0.35 * row_h] * 2,
                color=BASELINE, linewidth=1)
    flag_idx = [i for i, c in enumerate(cols) if c[0].startswith("flags_")]
    if flag_idx:
        ax.text((edges[flag_idx[0]] + edges[flag_idx[-1] + 1]) / 2, y_group,
                "flag counts (C / A / N)", ha="center", va="center", fontsize=9,
                color=INK_2, fontweight="semibold")
        ax.plot([edges[flag_idx[0]] + 0.004, edges[flag_idx[-1] + 1] - 0.004],
                [y_group - 0.35 * row_h] * 2, color=BASELINE, linewidth=1)

    y_head = 1 - 2.5 * row_h
    for i, (_, header, _, align) in enumerate(cols):
        ax.text(cell_x(i, align), y_head, header, ha=align, va="center", fontsize=9, color=INK_2)
    ax.plot([0, 1], [y_head - 0.5 * row_h] * 2, color=INK_2, linewidth=1)

    for r_i, (_, r) in enumerate(block.iterrows()):
        y = 1 - (3.5 + r_i) * row_h
        if r_i % 2 == 1:
            ax.add_patch(Rectangle((0, y - 0.5 * row_h), 1, row_h, color="#f6f6f3", zorder=0))
        for i, (key, _, _, align) in enumerate(cols):
            value = r[key]
            if key == "component":
                text = pretty(value)
            elif key == "n_units":
                text = f"{int(value)}"
            elif key.startswith("pct_agree_"):
                text = f"{value:.0%}"
            elif key.startswith("alpha_"):
                status = status_of(value)
                color, word, _ = STATUS[status]
                ax.add_patch(Rectangle((edges[i] + 0.003, y - 0.42 * row_h),
                                       edges[i + 1] - edges[i] - 0.006, 0.84 * row_h,
                                       facecolor=color, alpha=0.18, edgecolor="none", zorder=1))
                text = word if status == "undefined" else f"{value:.3f}  {word}"
            elif key.startswith("flags_"):
                text = str(value).replace("C=", "").replace(" A=", " / ").replace(" N=", " / ")
            else:
                text = str(value)
            ax.text(cell_x(i, align), y, text, ha=align, va="center", fontsize=9.5,
                    color=INK, zorder=2)
    ax.plot([0, 1], [1 - (n_body + 3) * row_h] * 2, color=BASELINE, linewidth=1)  # bottom rule


def save_table(table: pd.DataFrame, comparisons, path: Path) -> Path:
    views = _views(table)
    names = list(dict.fromkeys(table["comparison"]))
    coders_of = {c.name: c.coders for c in comparisons}
    n_rows = len(table[table["comparison"] == names[0]])
    fig = plt.figure(figsize=(13, (0.34 * (n_rows + 3) + 0.25) * len(names) + 0.8))
    gs = fig.add_gridspec(len(names), 1, left=0.02, right=0.98, top=0.98, bottom=0.1, hspace=0.25)
    for i, name in enumerate(names):
        ax = fig.add_subplot(gs[i])
        title = f"{name}:  {'  vs  '.join(coders_of.get(name, []))}"
        _draw_table(ax, table[table["comparison"] == name], title, views)
    fig.text(0.02, 0.035,
             "alpha = Krippendorff's alpha (nominal), chance-corrected.  % agree = raw agreement, "
             "not chance-corrected.  n = scenarios coded by both.  Thresholds: >= 0.800 reliable, "
             ">= 0.667 tentative only (Krippendorff 2004).", fontsize=8.5, color=INK_2)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- entry point

def save_visualizations(table: pd.DataFrame, comparisons, csv_path: Path) -> list[Path]:
    """Save the chart and the table PNG next to `csv_path`, named after it."""
    csv_path = Path(csv_path)
    stem = csv_path.stem
    if "_result_" in stem:
        chart_stem, table_stem = stem.replace("_result_", "_chart_"), stem.replace("_result_", "_table_")
    else:
        chart_stem, table_stem = f"{stem}_chart", f"{stem}_table"
    folder = csv_path.parent
    folder.mkdir(parents=True, exist_ok=True)
    return [
        save_chart(table, comparisons, folder / f"{chart_stem}.png"),
        save_table(table, comparisons, folder / f"{table_stem}.png"),
    ]
