"""Lollipop chart of Krippendorff's alpha (3 flags) per component, one panel per comparison.

save_lp_chart(table, data, comparisons, csv_path) writes one PNG next to the CSV:
    <prefix>_chart_<human|llm>_<time>.png
--human gives one panel; --llm gives a 2 x 2 grid (humans, each human vs the LLM, combined).

Colour never carries the verdict alone: each dot's position against the labelled 0.667 / 0.800
lines shows it too (red vs green is unreadable for many colour-blind readers). Raw % agreement
is a different measure, so it is listed as text beside each row, never as an alpha value.

When every coder gave the same flag everywhere (e.g. threat source: all Clear), agreement is
100% but alpha is 0/0, not 1.0. That row is drawn as a green dotted line running to the
"% agree" column, labelled "alpha not defined", so it never reads as a measured alpha of 1.
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
GOOD, WARNING, CRITICAL = "#0ca30c", "#fab219", "#d03b3b"
STATUS = {
    "reliable": (GOOD, "alpha >= 0.800  reliable"),
    "tentative": (WARNING, "0.667 <= alpha < 0.800  tentative only"),
    "below": (CRITICAL, "alpha < 0.667  do not rely on the data"),
}
DOTTED = (0, (1, 2))
INK, INK_2, MUTED = "#0b0b0b", "#4a4641", "#898781"
BASELINE = "#c3c2b7"
PAGE, CARD, CARD_EDGE = "#ebeeec", "#ffffff", "#d6dcd8"  # light bluish-beige page, white cards

# Layout in inches
PANEL = 8                       # each card is PANEL x PANEL
GAP = 0.2                            # space between cards
TOP, BOTTOM = 0.85, 0.43            # page bands: title above, legend below
SIDE = (TOP + BOTTOM) / 2.2            # equal side margins keep the image square
INSET_LEFT, INSET_RIGHT, INSET_TOP, INSET_BOTTOM = 1.9, 0.9, 1.2, 0.85  # axes inside a card

_INSTALLED = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Segoe UI", "Helvetica Neue", "Arial") if f in _INSTALLED), "DejaVu Sans")
plt.rcParams.update({"font.family": FONT, "font.size": 13, "axes.edgecolor": BASELINE,
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
    fig.text(
        cx,
        (y + PANEL - 0.36) / fig_h,
        f"{name} judgements: {'  vs  '.join(coders)}",
        ha="center",
        va="center",
        fontsize=15,
        fontweight="semibold",
        color=INK,
    )

    ax = fig.add_axes([(x + INSET_LEFT) / fig_w, (y + INSET_BOTTOM) / fig_h,
                       (PANEL - INSET_LEFT - INSET_RIGHT) / fig_w,
                       (PANEL - INSET_TOP - INSET_BOTTOM) / fig_h])
    ax.set_facecolor("none")
    components = list(block["component"])
    ys = np.arange(len(components))[::-1]  # first component at the top

    ax.set_xlim(x_min, 1.0)
    ax.set_ylim(-0.6, len(components) - 0.4)
    ax.set_xticks([t for t in np.arange(-1.0, 1.01, 0.25) if t >= x_min - 1e-9])
    ax.tick_params(axis="x", labelsize=11)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_yticks(ys, [wrap_label(c) for c in components], fontsize=13, linespacing=1.15)
    ax.set_xlabel("Krippendorff's alpha", fontsize=11.5, color=INK_2)

    ax.axvline(0, color=BASELINE, linewidth=1, zorder=1)
    for threshold, label in ((TENTATIVE, "0.667"), (RELIABLE, "0.800")):
        ax.axvline(threshold, color=INK_2, linewidth=1, linestyle=(0, (4, 3)), zorder=1)
        ax.text(threshold, 1.015, label, transform=ax.get_xaxis_transform(),
                ha="center", va="bottom", fontsize=11.5, color=INK_2)

    ax.text(1.06, 1.015, "% agree", transform=ax.transAxes, ha="left", va="bottom",
            fontsize=10.5, color=INK_2)
    span = 1.0 - x_min
    for yi, (_, r) in zip(ys, block.iterrows()):
        alpha = r["alpha_3flag"]
        status = status_of(alpha)
        ax.text(1.06, yi, f"{r['pct_agree_3flag']:.0%}", transform=ax.get_yaxis_transform(),
                ha="left", va="center", fontsize=11, color=INK_2,
                fontweight="semibold" if status == "n/a" else "normal")
        if status == "n/a":
            flag = constant_flag(data.matrix(r["component"], coders, "3flag"), "3flag")
            if flag is None:  # no scenario coded by two coders
                ax.text(0.03 * span, yi, "no data", va="center", ha="left", fontsize=10.5,
                        color=MUTED)
                continue
            # 100% agreement, alpha = 0/0: line from 0 to the "% agree" column
            ax.plot([-x_min / span, 1.045], [yi, yi], transform=ax.get_yaxis_transform(),
                    color=GOOD, linewidth=2.6, clip_on=False, zorder=2)
            ax.text(0.01, yi + 0.18, f"100% agreement", transform=ax.get_yaxis_transform(), va="bottom",
                    ha="left", fontsize=10, color=INK_2, zorder=4,
                    bbox=dict(facecolor=CARD, edgecolor="none", pad=1.5))
            continue
        color = STATUS[status][0]
        ax.hlines(yi, 0, alpha, color=color, linewidth=2.4, zorder=2)
        ax.scatter(alpha, yi, s=85, color=color, edgecolor=CARD, linewidth=2, zorder=3)
        right = alpha >= 0
        ax.text(alpha + (0.03 if right else -0.03) * span, yi, f"{alpha:.2f}",
                va="center", ha="left" if right else "right", fontsize=12, color=INK,
                zorder=4, bbox=dict(facecolor=CARD, edgecolor="none", pad=1.5))


def save_lp_chart(table: pd.DataFrame, data, comparisons, csv_path: Path) -> Path:
    """One card per comparison: 1 card for --human, a 2 x 2 grid for --llm."""
    names = list(dict.fromkeys(table["comparison"]))
    coders_of = {c.name: c.coders for c in comparisons}
    cols = 1 if len(names) == 1 else 2
    rows = math.ceil(len(names) / cols)
    fig_w = 2 * SIDE + cols * PANEL + (cols - 1) * GAP
    fig_h = TOP + BOTTOM + rows * PANEL + (rows - 1) * GAP
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=PAGE)

    alphas = table["alpha_3flag"].to_numpy(dtype=float)
    lowest = np.nanmin(alphas) if np.isfinite(alphas).any() else 0.0
    x_min = min(-0.25, np.floor((lowest - 0.15) / 0.25) * 0.25)  # same scale on every card

    for i, name in enumerate(names):
        r, c = divmod(i, cols)
        x = SIDE + c * (PANEL + GAP)
        y = fig_h - TOP - (r + 1) * PANEL - r * GAP
        _panel(fig, x, y, table[table["comparison"] == name], data, name,
               coders_of.get(name, []), x_min)

    fig.text(0.5, 1 - 0.36 / fig_h, "Krippendorff's alpha (nominal) per component", ha="center",
             va="center", fontsize=19, fontweight="semibold", color=INK)
    fig.text(0.5, 1 - 0.7 / fig_h, "3 Flags [Clear / Ambiguous / Not specified]", ha="center", va="center",
             fontsize=12.5, color=INK_2)
    handles = [Line2D([], [], marker="o", linestyle="", markersize=9, markerfacecolor=color,
                      markeredgecolor=color, label=label) for color, label in STATUS.values()]
    fig.legend(handles=handles, loc="center", bbox_to_anchor=(0.5, (BOTTOM / 2) / fig_h),
               ncol=4 if cols == 2 else 2, frameon=False, fontsize=11.5, labelcolor=INK_2,
               columnspacing=2.0, handlelength=2.2)

    path = chart_path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor=PAGE)
    plt.close(fig)
    return path
