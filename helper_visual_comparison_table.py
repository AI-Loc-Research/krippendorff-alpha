"""Comparison tables: each coder's raw flags (C / A / N) for every scenario x component,
coders side by side, one PNG per comparison.

save_comparison_tables(data, comparisons, csv_path) writes, next to the CSV:
    <prefix>_labels_<comparison>_<time>.png

A cell is green when every coder gave the same flag and red when they differ.
Red cells also get a bold letter and an outline, so the difference is visible
without relying only on colour.
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import FancyBboxPatch, Patch

from data_preprocessing import COMPONENTS


# ---------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------

INK, INK_2 = "#0b0b0b", "#4a4641"
CRITICAL = "#d03b3b"

PAGE = "#ebeeec"
CARD = "#ffffff"
CARD_EDGE = "#d6dcd8"

MATCH_FILL = "#cfeccf"
DIFF_FILL = "#f6cfcf"
MISSING_FILL = "#dddbd4"

SWATCH_EDGE = "#a9aaa5"


# ---------------------------------------------------------------------
# Component abbreviations
# ---------------------------------------------------------------------

SHORT = {
    "threat_source": "TS",
    "objective_or_harmful_outcome": "Obj",
    "capability": "Cap",
    "knowledge": "Know",
    "access": "Acc",
    "constraints_or_enabling_conditions": "Cond",
    "target_or_asset_at_risk": "Tgt",
}

LETTER = {
    "Clear": "C",
    "Ambiguous": "A",
    "Not specified": "N",
}


# ---------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------
#
# CELL controls the overall size of the cells.
#
# LABEL_W controls the width available for scenario names.
#
# GRID_GAP controls the gap between coder tables.
#
# HEAD controls space above the table inside the white card.
#
# FOOT controls the space below the table for "25/25", etc.
#
# PAD controls the padding between the card edge and table.
#
# SIDE = left/right page margin
#
# TOP = space above white card
#
# BOTTOM = space below white card, including legend + abbreviation box
#
# ---------------------------------------------------------------------

CELL = 0.34

LABEL_W = 7.0
GRID_GAP = 1.2

HEAD = 2.4
FOOT = 1.3
PAD = 0.55

SIDE = 0.45
TOP = 0.55
BOTTOM = 1.55


# ---------------------------------------------------------------------
# Font
# ---------------------------------------------------------------------

_INSTALLED = {f.name for f in font_manager.fontManager.ttflist}

FONT = next(
    (
        f
        for f in ("Segoe UI", "Helvetica Neue", "Arial")
        if f in _INSTALLED
    ),
    "DejaVu Sans",
)

plt.rcParams.update(
    {
        "font.family": FONT,
        "font.size": 10,
    }
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def pretty(component: str) -> str:
    """Convert component key to readable title case."""
    return component.replace("_", " ").capitalize()


def wrap_scenario_label(
    paper: str,
    scenario: str,
    width: int = 28,
) -> str:
    """Wrap long scenario labels without breaking words."""

    text = f"{paper}  {scenario.replace('_', ' ')}"

    return "\n".join(
        textwrap.wrap(
            text,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def file_safe(name: str) -> str:
    """Make comparison name safe for filenames."""

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        name.lower(),
    ).strip("_")


def table_path(
    csv_path: Path,
    comparison_name: str,
) -> Path:
    """Create output PNG path."""

    csv_path = Path(csv_path)

    m = re.match(
        r"^(.*)_result_(.*)_(\d{8}_\d{4})$",
        csv_path.stem,
    )

    if m:
        prefix, _, stamp = m.groups()

        return csv_path.parent / (
            f"{prefix}_labels_{file_safe(comparison_name)}_{stamp}.png"
        )

    return csv_path.parent / (
        f"{csv_path.stem}_labels_{file_safe(comparison_name)}.png"
    )


def component_key_text() -> str:
    """
    Create one readable abbreviation key.

    Example:
    [TS = Threat source, Obj = Objective or harmful outcome, ...]
    """

    items = [
        f"{SHORT[c]} = {pretty(c).lower()}"
        for c in COMPONENTS
    ]

    return "[ " + ",  ".join(items) + " ]"


# ---------------------------------------------------------------------
# Agreement calculation
# ---------------------------------------------------------------------

def _agreement(
    data,
    coders: list[str],
) -> np.ndarray:
    """
    Per cell:

        True  = same flag from every coder
        False = coders differ
        None  = at least one coder left it empty
    """

    n_rows = len(data.units)
    n_cols = len(COMPONENTS)

    agree = np.empty(
        (n_rows, n_cols),
        dtype=object,
    )

    for j, comp in enumerate(COMPONENTS):

        values = [
            list(data.flags[c][comp])
            for c in coders
        ]

        for i in range(n_rows):

            cell = [
                v[i]
                for v in values
            ]

            agree[i, j] = (
                None
                if any(pd.isna(x) for x in cell)
                else len(set(cell)) == 1
            )

    return agree


# ---------------------------------------------------------------------
# Main table
# ---------------------------------------------------------------------

def save_comparison_table(
    data,
    comparison,
    path: Path,
) -> Path:

    coders = comparison.coders

    n_rows = len(data.units)
    n_cols = len(COMPONENTS)

    agree = _agreement(
        data,
        coders,
    )

    # -------------------------------------------------------------
    # Calculate dimensions
    # -------------------------------------------------------------

    grid_w = (
        len(coders) * n_cols
        + (len(coders) - 1) * GRID_GAP
    )

    content_w = LABEL_W + grid_w
    content_h = HEAD + n_rows + FOOT

    card_w = (
        content_w + 2 * PAD
    ) * CELL

    card_h = (
        content_h + 2 * PAD
    ) * CELL

    fig_w = (
        2 * SIDE
        + card_w
    )

    fig_h = (
        TOP
        + card_h
        + BOTTOM
    )

    fig = plt.figure(
        figsize=(fig_w, fig_h),
        facecolor=PAGE,
    )

    # -------------------------------------------------------------
    # White card
    # -------------------------------------------------------------

    fig.add_artist(
        FancyBboxPatch(
            (SIDE, BOTTOM),
            card_w,
            card_h,
            boxstyle="round,pad=0,rounding_size=0.20",
            transform=fig.dpi_scale_trans,
            facecolor=CARD,
            edgecolor=CARD_EDGE,
            linewidth=0.8,
            zorder=-1,
        )
    )

    # -------------------------------------------------------------
    # Table axes
    # -------------------------------------------------------------

    ax = fig.add_axes(
        [
            (SIDE + PAD * CELL) / fig_w,
            (BOTTOM + PAD * CELL) / fig_h,
            content_w * CELL / fig_w,
            content_h * CELL / fig_h,
        ]
    )

    ax.set_xlim(
        -LABEL_W,
        grid_w,
    )

    ax.set_ylim(
        n_rows + FOOT,
        -HEAD,
    )

    ax.set_axis_off()

    # -------------------------------------------------------------
    # Scenario names
    # -------------------------------------------------------------

    for i, unit in enumerate(data.units):

        paper, scenario = unit.split("/")

        label = wrap_scenario_label(
            paper,
            scenario,
            width=28,
        )

        ax.text(
            -0.35,
            i + 0.5,
            label,
            ha="right",
            va="center",

            # Increased Y-axis/scenario label size
            fontsize=10,

            color=INK,
            linespacing=1.05,
        )

    # -------------------------------------------------------------
    # Coder grids
    # -------------------------------------------------------------

    for g, coder in enumerate(coders):

        x0 = g * (
            n_cols + GRID_GAP
        )

        # Coder name
        ax.text(
            x0 + n_cols / 2,
            -1.6,
            coder,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="semibold",
            color=INK,
        )

        # Component abbreviations
        for j, comp in enumerate(COMPONENTS):

            ax.text(
                x0 + j + 0.5,
                -0.55,
                SHORT[comp],
                ha="center",
                va="center",
                fontsize=9.5,
                color=INK_2,
                fontweight="normal",
            )

            flags = list(
                data.flags[coder][comp]
            )

            # Cells
            for i in range(n_rows):

                state = agree[i, j]

                if state is None:
                    fill = MISSING_FILL
                elif state:
                    fill = MATCH_FILL
                else:
                    fill = DIFF_FILL

                ax.add_patch(
                    FancyBboxPatch(
                        (
                            x0 + j + 0.07,
                            i + 0.07,
                        ),
                        0.86,
                        0.86,
                        boxstyle=(
                            "round,pad=0,"
                            "rounding_size=0.16"
                        ),
                        facecolor=fill,
                        linewidth=1.1,
                        edgecolor=(
                            CRITICAL
                            if state is False
                            else "none"
                        ),
                    )
                )

                letter = (
                    "–"
                    if pd.isna(flags[i])
                    else LETTER[flags[i]]
                )

                ax.text(
                    x0 + j + 0.5,
                    i + 0.52,
                    letter,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=INK,
                    fontweight=(
                        "bold"
                        if state is False
                        else "normal"
                    ),
                )

            # Match count
            matches = sum(
                1
                for i in range(n_rows)
                if agree[i, j] is True
            )

            ax.text(
                x0 + j + 0.5,
                n_rows + 0.7,
                f"{matches}/{n_rows}",
                ha="center",
                va="center",
                fontsize=7.5,
                color=INK_2,
            )

    # "same flag" label
    ax.text(
        -0.35,
        n_rows + 0.7,
        "same flag",
        ha="right",
        va="center",
        fontsize=8.5,
        color=INK_2,
    )

    # -------------------------------------------------------------
    # Header
    # -------------------------------------------------------------

    total = sum(
        1
        for state in agree.flat
        if state is True
    )

    cells = n_rows * n_cols

    header = (
        f"{'  vs  '.join(coders)}"
        f"   ·   "
        f"same flag in {total} of {cells} cells "
        f"({total / cells:.0%})"
    )

    fig.text(
        0.5,
        1 - 0.28 / fig_h,
        header,
        ha="center",
        va="center",
        fontsize=15,
        fontweight="semibold",
        color=INK,
    )

    # -------------------------------------------------------------
    # Legend
    # -------------------------------------------------------------

    legend_y = (
        BOTTOM - 0.28
    ) / fig_h

    fig.legend(
        handles=[
            Patch(
                facecolor=MATCH_FILL,
                edgecolor=SWATCH_EDGE,
                label="same flag from every coder",
            ),
            Patch(
                facecolor=DIFF_FILL,
                edgecolor=CRITICAL,
                label="flags differ (bold letter, outlined)",
            ),
            Patch(
                facecolor=MISSING_FILL,
                edgecolor=SWATCH_EDGE,
                label="missing (–)",
            ),
        ],
        loc="center",
        bbox_to_anchor=(
            0.5,
            legend_y,
        ),
        ncol=3,
        frameon=False,
        fontsize=9,
        labelcolor=INK_2,
        columnspacing=2.0,
    )

    # -------------------------------------------------------------
    # Component abbreviation box
    # -------------------------------------------------------------

    key_text = component_key_text()

    # Wrap into two balanced lines if necessary.
    #
    # This is intentionally one text object rather than many
    # scattered fig.text() calls.
    key_lines = textwrap.wrap(
        key_text,
        width=105,
        break_long_words=False,
        break_on_hyphens=False,
    )

    key_text_wrapped = "\n".join(
        key_lines
    )

    # Rectangle dimensions
    key_x = SIDE + 0.15
    key_w = card_w - 0.30

    key_h = (
        0.62
        if len(key_lines) <= 1
        else 0.82
    )

    key_y = (
        0.18
    )

    # Rounded rectangle
    fig.add_artist(
        FancyBboxPatch(
            (
                key_x,
                key_y,
            ),
            key_w,
            key_h,
            boxstyle=(
                "round,pad=0.08,"
                "rounding_size=0.08"
            ),
            transform=fig.dpi_scale_trans,
            facecolor=CARD,
            edgecolor=CARD_EDGE,
            linewidth=0.8,
            zorder=0,
        )
    )

    # Text inside rectangle
    fig.text(
        0.5,
        (
            key_y
            + key_h / 2
        ) / fig_h,
        key_text_wrapped,
        ha="center",
        va="center",
        fontsize=8.5,
        color=INK_2,
        linespacing=1.5,
    )

    # -------------------------------------------------------------
    # Save
    # -------------------------------------------------------------

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fig.savefig(
        path,
        dpi=200,
        facecolor=PAGE,
        bbox_inches=None,
    )

    plt.close(fig)

    return path


# ---------------------------------------------------------------------
# Save all comparison tables
# ---------------------------------------------------------------------

def save_comparison_tables(
    data,
    comparisons,
    csv_path: Path,
) -> list[Path]:

    return [
        save_comparison_table(
            data,
            c,
            table_path(
                csv_path,
                c.name,
            ),
        )
        for c in comparisons
    ]