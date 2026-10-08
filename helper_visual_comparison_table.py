"""Comparison tables: each coder's raw flags (C / A / N) for every scenario x component,
coders side by side, one PNG per comparison.

save_comparison_tables(data, comparisons, csv_path) writes, next to the CSV:
    <prefix>_labels_<comparison>_<time>.png

A cell is green when every coder gave the same flag and red when they differ. Red cells
also get a bold letter and an outline, so the difference is visible without colour.
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
from matplotlib.patches import FancyBboxPatch, Patch  # noqa: E402

from data_preprocessing import COMPONENTS  # noqa: E402

INK, INK_2 = "#0b0b0b", "#52514e"
CRITICAL = "#d03b3b"
PAGE, CARD, CARD_EDGE = "#ebeeec", "#ffffff", "#d6dcd8"  # light bluish-beige page, white card
MATCH_FILL, DIFF_FILL, MISSING_FILL = "#cfeccf", "#f6cfcf", "#dddbd4"
SWATCH_EDGE = "#a9aaa5"  # keeps legend swatches visible on the page colour

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

# Layout: grid units are square cells of CELL inches, so rounded corners stay round
CELL = 0.34
LABEL_W, GRID_GAP = 7.0, 1.2          # scenario-label column and gap between grids (cell units)
HEAD, FOOT, PAD = 2.4, 1.3, 0.6       # header rows, match-count row, card padding (cell units)
SIDE, TOP, BOTTOM = 0.6, 1.05, 1.45   # page margins in inches (title above, legend + key below)

_INSTALLED = {f.name for f in font_manager.fontManager.ttflist}
FONT = next((f for f in ("Segoe UI", "Helvetica Neue", "Arial") if f in _INSTALLED), "DejaVu Sans")
plt.rcParams.update({"font.family": FONT, "font.size": 10})


def pretty(component: str) -> str:
    return component.replace("_", " ").capitalize()


def file_safe(name: str) -> str:
    """'Combined (llm+human)' -> 'combined_llm_human' (safe in file names)."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def table_path(csv_path: Path, comparison_name: str) -> Path:
    """results/lib_ka_result_llm_<time>.csv + 'humans' -> results/lib_ka_labels_humans_<time>.png"""
    csv_path = Path(csv_path)
    m = re.match(r"^(.*)_result_(.*)_(\d{8}_\d{4})$", csv_path.stem)
    if m:
        prefix, _, stamp = m.groups()
        return csv_path.parent / f"{prefix}_labels_{file_safe(comparison_name)}_{stamp}.png"
    return csv_path.parent / f"{csv_path.stem}_labels_{file_safe(comparison_name)}.png"


def _key_lines(max_chars: int = 95) -> list[str]:
    """The key under the legend; lines break only between items, never inside one."""
    lines = ["C = Clear,  A = Ambiguous,  N = Not specified"]
    current = ""
    for item in (f"{SHORT[c]} = {pretty(c).lower()}" for c in COMPONENTS):
        candidate = f"{current},  {item}" if current else item
        if current and len(candidate) > max_chars:
            lines.append(current)
            candidate = item
        current = candidate
    return lines + [current]


def _agreement(data, coders: list[str]) -> np.ndarray:
    """Per cell: True (same flag from every coder), False (differ), None (a coder left it empty)."""
    n_rows, n_cols = len(data.units), len(COMPONENTS)
    agree = np.empty((n_rows, n_cols), dtype=object)
    for j, comp in enumerate(COMPONENTS):
        values = [list(data.flags[c][comp]) for c in coders]
        for i in range(n_rows):
            cell = [v[i] for v in values]
            agree[i, j] = None if any(pd.isna(x) for x in cell) else len(set(cell)) == 1
    return agree


def save_comparison_table(data, comparison, path: Path) -> Path:
    coders = comparison.coders
    n_rows, n_cols = len(data.units), len(COMPONENTS)
    agree = _agreement(data, coders)

    grid_w = len(coders) * n_cols + (len(coders) - 1) * GRID_GAP   # cell units
    content_w, content_h = LABEL_W + grid_w, HEAD + n_rows + FOOT
    card_w, card_h = (content_w + 2 * PAD) * CELL, (content_h + 2 * PAD) * CELL
    fig_w, fig_h = 2 * SIDE + card_w, TOP + card_h + BOTTOM
    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=PAGE)

    fig.add_artist(FancyBboxPatch((SIDE, BOTTOM), card_w, card_h,
                                  boxstyle="round,pad=0,rounding_size=0.2",
                                  transform=fig.dpi_scale_trans, facecolor=CARD,
                                  edgecolor=CARD_EDGE, linewidth=0.8, zorder=-1))
    ax = fig.add_axes([(SIDE + PAD * CELL) / fig_w, (BOTTOM + PAD * CELL) / fig_h,
                       content_w * CELL / fig_w, content_h * CELL / fig_h])
    ax.set_xlim(-LABEL_W, grid_w)
    ax.set_ylim(n_rows + FOOT, -HEAD)  # row 0 at the top
    ax.set_axis_off()

    for i, unit in enumerate(data.units):
        paper, scenario = unit.split("/")
        ax.text(-0.35, i + 0.5, f"{paper}  {scenario}", ha="right", va="center",
                fontsize=8.5, color=INK)

    for g, coder in enumerate(coders):
        x0 = g * (n_cols + GRID_GAP)
        ax.text(x0 + n_cols / 2, -1.6, coder, ha="center", va="center", fontsize=11,
                fontweight="semibold", color=INK)
        for j, comp in enumerate(COMPONENTS):
            ax.text(x0 + j + 0.5, -0.55, SHORT[comp], ha="center", va="center",
                    fontsize=8.5, color=INK_2)
            flags = list(data.flags[coder][comp])
            for i in range(n_rows):
                state = agree[i, j]
                fill = MISSING_FILL if state is None else (MATCH_FILL if state else DIFF_FILL)
                ax.add_patch(FancyBboxPatch((x0 + j + 0.07, i + 0.07), 0.86, 0.86,
                                            boxstyle="round,pad=0,rounding_size=0.16",
                                            facecolor=fill, linewidth=1.1,
                                            edgecolor=CRITICAL if state is False else "none"))
                letter = "–" if pd.isna(flags[i]) else LETTER[flags[i]]
                ax.text(x0 + j + 0.5, i + 0.52, letter, ha="center", va="center", fontsize=9,
                        color=INK, fontweight="bold" if state is False else "normal")
            matches = sum(1 for i in range(n_rows) if agree[i, j] is True)
            ax.text(x0 + j + 0.5, n_rows + 0.7, f"{matches}/{n_rows}", ha="center",
                    va="center", fontsize=7.5, color=INK_2)
    ax.text(-0.35, n_rows + 0.7, "same flag", ha="right", va="center", fontsize=8.5, color=INK_2)

    total = sum(1 for state in agree.flat if state is True)
    cells = n_rows * n_cols
    fig.text(0.5, 1 - 0.4 / fig_h, comparison.name, ha="center", va="center",
             fontsize=15, fontweight="semibold", color=INK)
    fig.text(0.5, 1 - 0.72 / fig_h, f"{'  vs  '.join(coders)}   ·   same flag in {total} of "
             f"{cells} cells ({total / cells:.0%})", ha="center", va="center",
             fontsize=10.5, color=INK_2)

    fig.legend(handles=[Patch(facecolor=MATCH_FILL, edgecolor=SWATCH_EDGE,
                              label="same flag from every coder"),
                        Patch(facecolor=DIFF_FILL, edgecolor=CRITICAL,
                              label="flags differ (bold letter, outlined)"),
                        Patch(facecolor=MISSING_FILL, edgecolor=SWATCH_EDGE, label="missing (–)")],
               loc="center", bbox_to_anchor=(0.5, (BOTTOM - 0.35) / fig_h), ncol=3,
               frameon=False, fontsize=9, labelcolor=INK_2, columnspacing=2.0)
    for k, line in enumerate(_key_lines()):
        fig.text(0.5, (BOTTOM - 0.78 - 0.22 * k) / fig_h, line, ha="center", va="center",
                 fontsize=8, color=INK_2)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, facecolor=PAGE)
    plt.close(fig)
    return path


def save_comparison_tables(data, comparisons, csv_path: Path) -> list[Path]:
    """One comparison table per comparison, named after the CSV."""
    return [save_comparison_table(data, c, table_path(csv_path, c.name)) for c in comparisons]
