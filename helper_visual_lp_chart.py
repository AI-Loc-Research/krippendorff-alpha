"""Lollipop chart of Krippendorff's alpha (3 flags) per component, one panel per comparison.

save_lp_chart(table, data, comparisons, csv_path) writes one PNG next to the CSV:
    <prefix>_chart_<human|llm>_<time>.png
--human gives one panel; --llm gives a 2 x 2 grid (humans, each human vs the LLM, combined).

Colour never carries the verdict alone: each dot's position against the labelled 0.667 / 0.800
lines shows it too (red vs green is unreadable for many colour-blind readers). Raw % agreement
is a different measure, so it is listed as text beside each row, never on the alpha axis.
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # render to files only; no window needed

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from data_preprocessing import constant_flag  # noqa: E402

TENTATIVE, RELIABLE = 0.667, 0.800

# Status colours (fixed meaning)
STATUS = {
    "reliable": ("#0ca30c", "alpha >= 0.800  reliable"),
    "tentative": ("#fab219", "0.667 <= alpha < 0.800  tentative only"),
    "below": ("#d03b3b", "alpha < 0.667  do not rely on the data"),
    "n/a": ("#898781", "n/a: every coder gave the same flag"),
}
INK, INK_2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, BASELINE = "#e1e0d9", "#c3c2b7"
PAGE, CARD, CARD_EDGE = "#ebeeec", "#ffffff", "#d6dcd8"  # light bluish-beige page, white cards

# Layout in inches
PANEL = 7.5            # each card is PANEL x PANEL
GAP = 0.35             # space between cards
BAND = 1.0             # page band: title on top, legend at the bottom, equal sides
INSET_LEFT, INSET_RIGHT, INSET_TOP, INSET_BOTTOM = 1.9, 0.8, 1.25, 0.85  # axes inside a card

_INSTALLED = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Segoe UI", "Helvetica Neue", "Arial") if f in _INSTALLED), "DejaVu Sans")
plt.rcParams.update({"font.family": FONT, "font.size": 10, "axes.edgecolor": BASELINE,
                     "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": INK})


def status_of(alpha: float) -> str:
    if alpha is None or np.isnan(alpha):
        return "n/a"
    if alpha >= RELIABLE:
        return "reliable"
    return "tentative" if alpha >= TENTATIVE else "below"


def pretty(component: str) -> str:
    return component.replace("_", " ").capitalize()


def wrap_label(component: str) -> str:
    """Break long names after 'or', e.g. 'Constraints or' / 'enabling conditions'."""
    return pretty(component).replace(" or ", " or\n", 1)


def chart_path(csv_path: Path) -> Path:
    """results/lib_ka_result_llm_<time>.csv -> results/lib_ka_chart_llm_<time>.png"""
    csv_path = Path(csv_path)
    stem = csv_path.stem
    name = stem.replace("_result_", "_chart_") if "_result_" in stem else f"{stem}_chart"
    return csv_path.parent / f"{name}.png"


def _card(fig, x: float, y: float, w: float, h: float) -> None:
    """White rounded card; position and size in inches from the bottom-left corner."""
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.2",
                                  transform=fig.dpi_scale_trans, facecolor=CARD,
                                  edgecolor=CARD_EDGE, linewidth=0.8, zorder=-1))


def _panel(fig, x: float, y: float, block: pd.DataFrame, data, name: str,
           coders: list[str], x_min: float) -> None:
    fig_w, fig_h = fig.get_size_inches()
    _card(fig, x, y, PANEL, PANEL)
    cx = (x + PANEL / 2) / fig_w
    fig.text(cx, (y + PANEL - 0.38) / fig_h, name, ha="center", va="center",
             fontsize=13, fontweight="semibold", color=INK)
    fig.text(cx, (y + PANEL - 0.68) / fig_h, "  vs  ".join(coders), ha="center", va="center",
             fontsize=9.5, color=INK_2)

    ax = fig.add_axes([(x + INSET_LEFT) / fig_w, (y + INSET_BOTTOM) / fig_h,
                       (PANEL - INSET_LEFT - INSET_RIGHT) / fig_w,
                       (PANEL - INSET_TOP - INSET_BOTTOM) / fig_h])
    ax.set_facecolor("none")
    components = list(block["component"])
    ys = np.arange(len(components))[::-1]  # first component at the top

    ax.set_xlim(x_min, 1.0)
    ax.set_ylim(-0.6, len(components) - 0.4)
    # 0.75 is left out: the labelled 0.667 / 0.800 lines already mark that region
    ax.set_xticks([t for t in np.arange(-1.0, 1.01, 0.25)
                   if t >= x_min - 1e-9 and not np.isclose(t, 0.75)])
    ax.tick_params(axis="x", labelsize=9)
    ax.grid(axis="x", color=GRID, linewidth=1)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_yticks(ys, [wrap_label(c) for c in components], fontsize=9, linespacing=1.15)
    ax.set_xlabel("Krippendorff's alpha", fontsize=9.5, color=INK_2)

    ax.axvline(0, color=BASELINE, linewidth=1, zorder=1)
    for threshold, label in ((TENTATIVE, "0.667"), (RELIABLE, "0.800")):
        ax.axvline(threshold, color=INK_2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
        ax.text(threshold, 1.015, label, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=8.5, color=INK_2)

    ax.text(1.06, 1.015, "% agree", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=8.5, color=INK_2)
    span = 1.0 - x_min
    for yi, (_, r) in zip(ys, block.iterrows()):
        alpha = r["alpha_3flag"]
        status = status_of(alpha)
        color = STATUS[status][0]
        ax.text(1.06, yi, f"{r['pct_agree_3flag']:.0%}", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=9, color=INK_2)
        if status == "n/a":
            flag = constant_flag(data.matrix(r["component"], coders, "3flag"), "3flag")
            note = f"n/a: all gave '{flag}' (no variation)" if flag else "n/a: no data"
            ax.scatter(0, yi, s=60, facecolor=CARD, edgecolor=color, linewidth=1.5, zorder=3)
            ax.text(0.03 * span, yi, note, va="center", ha="left", fontsize=8.5, color=INK_2)
            continue
        ax.hlines(yi, 0, alpha, color=color, linewidth=2, zorder=2)
        ax.scatter(alpha, yi, s=70, color=color, edgecolor=CARD, linewidth=2, zorder=3)
        right = alpha >= 0
        ax.text(alpha + (0.03 if right else -0.03) * span, yi, f"{alpha:.2f}",
                va="center", ha="left" if right else "right", fontsize=9, color=INK,
                zorder=4, bbox=dict(facecolor=CARD, edgecolor="none", pad=1.5))


def save_lp_chart(table: pd.DataFrame, data, comparisons, csv_path: Path) -> Path:
    """One card per comparison: 1 card for --human, a 2 x 2 grid for --llm."""
    names = list(dict.fromkeys(table["comparison"]))
    coders_of = {c.name: c.coders for c in comparisons}
    cols = 1 if len(names) == 1 else 2
    rows = math.ceil(len(names) / cols)
    fig_w = 2 * BAND + cols * PANEL + (cols - 1) * GAP
    fig_h = 2 * BAND + rows * PANEL + (rows - 1) * GAP
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=PAGE)

    alphas = table["alpha_3flag"].to_numpy(dtype=float)
    lowest = np.nanmin(alphas) if np.isfinite(alphas).any() else 0.0
    x_min = min(-0.25, np.floor((lowest - 0.15) / 0.25) * 0.25)  # same scale on every card

    for i, name in enumerate(names):
        r, c = divmod(i, cols)
        x = BAND + c * (PANEL + GAP)
        y = fig_h - BAND - (r + 1) * PANEL - r * GAP
        _panel(fig, x, y, table[table["comparison"] == name], data, name,
               coders_of.get(name, []), x_min)

    fig.text(0.5, 1 - 0.42 / fig_h, "Krippendorff's alpha per component", ha="center",
             va="center", fontsize=17, fontweight="semibold", color=INK)
    fig.text(0.5, 1 - 0.75 / fig_h, "nominal, 3 flags (Clear / Ambiguous / Not specified)   ·   "
             "dashed lines: 0.667 tentative, 0.800 reliable", ha="center", va="center",
             fontsize=10.5, color=INK_2)
    handles = [Line2D([], [], marker="o", linestyle="", markersize=8,
                      markerfacecolor=CARD if key == "n/a" else color,
                      markeredgecolor=color, label=label)
               for key, (color, label) in STATUS.items()]
    fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, (BAND / 2) / fig_h),
               ncol=4 if cols == 2 else 2, frameon=False, fontsize=9.5, labelcolor=INK_2,
               columnspacing=2.2)

    path = chart_path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor=PAGE)
    plt.close(fig)
    return path
