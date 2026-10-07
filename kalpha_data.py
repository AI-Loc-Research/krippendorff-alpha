"""Shared data pipeline: coding sheets (Excel) -> clean, aligned reliability matrices.

Both alpha implementations (library and custom) read their input from here, so they
always compare exactly the same data.

Pipeline: load config -> load sheets -> find flag columns -> select scenario rows
-> match units -> normalize flags -> encode -> reliability matrices.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

COMPONENTS = [
    "threat_source",
    "objective_or_harmful_outcome",
    "capability",
    "knowledge",
    "access",
    "constraints_or_enabling_conditions",
    "target_or_asset_at_risk",
]

# Numeric codes. The order (0 < 1 < 2) only matters for ordinal alpha; nominal ignores it.
FLAG_CODES = {"Not specified": 0, "Ambiguous": 1, "Clear": 2}

# Accepted spellings after lowercasing and collapsing whitespace. Anything else is an error.
FLAG_ALIASES = {
    "clear": "Clear",
    "ambiguous": "Ambiguous",
    "ambigous": "Ambiguous",
    "not specified": "Not specified",
    "not-specified": "Not specified",
    "not_specified": "Not specified",
}

# "3flag" keeps Clear / Ambiguous / Not specified.
# "binary" = the paper's definition: specified (Clear or Ambiguous) vs Not specified.
VIEWS = ("3flag", "binary")

SCENARIO_ID = re.compile(r"^S\d+$")


# config

@dataclass
class CoderSource:
    name: str
    file: Path
    sheet: str | int = 0

@dataclass
class Comparison:
    name: str
    coders: list[str]


def load_config(path: str | Path) -> tuple[list[CoderSource], list[Comparison]]:
    """Read config.toml. Relative file paths are resolved against the config's folder."""
    path = Path(path)
    with open(path, "rb") as f:
        cfg = tomllib.load(f)

    coders = [
        CoderSource(c["name"], (path.parent / c["file"]).resolve(), c.get("sheet", 0))
        for c in cfg["coders"]
    ]
    names = [c.name for c in coders]
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate coder names in {path}: {names}")

    comparisons = [Comparison(c["name"], list(c["coders"])) for c in cfg["comparisons"]]
    for comp in comparisons:
        unknown = [n for n in comp.coders if n not in names]
        if unknown:
            raise ValueError(f"Comparison '{comp.name}' uses unknown coder(s): {unknown}")
        if len(comp.coders) < 2:
            raise ValueError(f"Comparison '{comp.name}' needs at least 2 coders")
    return coders, comparisons


# Cleaning helpers

def clean_text(value) -> str:
    """Collapse all whitespace (spaces, tabs, newlines) to single spaces and strip."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return " ".join(str(value).split())

def clean_header(value) -> str:
    """Header key: lowercase with all whitespace removed (fixes 'name\\n' and 'na me')."""
    return "".join(str(value).split()).lower()

def normalize_flag(value) -> str | None:
    """Map a raw cell to 'Clear' / 'Ambiguous' / 'Not specified', or None if empty."""
    text = clean_text(value).lower()
    if text == "":
        return None
    if text in FLAG_ALIASES:
        return FLAG_ALIASES[text]
    raise ValueError(f"unknown flag {value!r}")


def find_flag_columns(df: pd.DataFrame) -> dict[str, str]:
    """For each component, find the ONE column whose cleaned name starts with the
    component name and contains 'uncert' (e.g. 'access_uncertaintyt' still matches;
    '..._evidence' columns never do)."""
    found, problems = {}, []
    for comp in COMPONENTS:
        matches = [
            col for col in df.columns
            if clean_header(col).startswith(comp) and "uncert" in clean_header(col)
        ]
        if len(matches) == 1:
            found[comp] = matches[0]
        else:
            problems.append(f"{comp}: {len(matches)} matching columns {matches}")
    if problems:
        raise ValueError("Could not locate flag columns:\n  " + "\n  ".join(problems))
    return found


def find_column(df: pd.DataFrame, wanted: str) -> str:
    matches = [col for col in df.columns if clean_header(col) == wanted]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one '{wanted}' column, found {matches}")
    return matches[0]


# one coder's sheet

@dataclass
class CoderFlags:
    name: str
    flags: pd.DataFrame        # index = unit key "paper_id/scenario_id", columns = COMPONENTS
    skipped_rows: list[str]    # non-empty rows that are not scenarios (e.g. notes)


def extract_flags(df: pd.DataFrame, coder: str) -> CoderFlags:
    """Steps 2-5 for one sheet: find columns, keep scenario rows, normalize flags."""
    paper_col = find_column(df, "paper_id")
    scen_col = find_column(df, "scenario_id")
    flag_cols = find_flag_columns(df)

    keys, rows, skipped, errors = [], [], [], []
    for i, row in df.iterrows():
        excel_row = i + 2  # header is Excel row 1
        paper, scen = clean_text(row[paper_col]), clean_text(row[scen_col])
        if not paper and not scen and row.isna().all():
            continue  # fully blank row
        if not paper or not SCENARIO_ID.match(scen):
            skipped.append(f"Excel row {excel_row}: {paper!r} {scen!r}")
            continue
        flags = {}
        for comp, col in flag_cols.items():
            try:
                flags[comp] = normalize_flag(row[col])
            except ValueError as e:
                errors.append(f"{coder} Excel row {excel_row} ({paper}/{scen}) {comp}: {e}")
        keys.append(f"{paper}/{scen}")
        rows.append(flags)

    if errors:
        raise ValueError("Unrecognized flag values:\n  " + "\n  ".join(errors))
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    if dupes:
        raise ValueError(f"{coder}: duplicate scenarios {dupes}")

    flags_df = pd.DataFrame(rows, index=keys, columns=COMPONENTS)
    return CoderFlags(coder, flags_df, skipped)


# all coders, aligned

@dataclass
class CodingData:
    units: list[str]                    # unit keys, in the first coder's order
    flags: dict[str, pd.DataFrame]      # coder -> flags for exactly `units`
    skipped_rows: dict[str, list[str]]
    extra_rows_ignored: dict[str, int]  # e.g. LLM sheet has 193 rows, we use 25

    def matrix(self, component: str, coders: list[str], view: str = "3flag") -> np.ndarray:
        """Reliability data matrix: rows = coders, columns = units, NaN = missing."""
        if view not in VIEWS:
            raise ValueError(f"view must be one of {VIEWS}")
        out = np.full((len(coders), len(self.units)), np.nan)
        for r, coder in enumerate(coders):
            for c, flag in enumerate(self.flags[coder][component]):
                if pd.isna(flag):  # missing (pandas may store None as NaN)
                    continue
                code = FLAG_CODES[flag]
                out[r, c] = code if view == "3flag" else float(code > 0)
        return out


def load_coding_data(coders: list[CoderSource]) -> CodingData:
    """Steps 1-5 for all coders, then align everyone on the first coder's units."""
    extracted = []
    for src in coders:
        df = pd.read_excel(src.file, sheet_name=src.sheet, dtype=object)
        extracted.append(extract_flags(df, src.name))

    units = list(extracted[0].flags.index)
    flags, extra = {}, {}
    for cf in extracted:
        missing = [u for u in units if u not in cf.flags.index]
        if missing:
            raise ValueError(f"{cf.name} is missing {len(missing)} scenario(s): {missing}")
        flags[cf.name] = cf.flags.loc[units]
        extra[cf.name] = len(cf.flags.index) - len(units)
    return CodingData(units, flags, {cf.name: cf.skipped_rows for cf in extracted}, extra)


# descriptive numbers

def percent_agreement(matrix: np.ndarray) -> float:
    """Share of agreeing coder pairs, averaged over units with >= 2 values."""
    scores = []
    for unit in matrix.T:
        vals = unit[~np.isnan(unit)]
        m = len(vals)
        if m < 2:
            continue
        pairs = m * (m - 1) / 2
        agree = sum((vals == v).sum() - 1 for v in vals) / 2
        scores.append(agree / pairs)
    return float(np.mean(scores)) if scores else float("nan")


def pairable_units(matrix: np.ndarray) -> int:
    return int(((~np.isnan(matrix)).sum(axis=0) >= 2).sum())


def flag_counts(data: CodingData, coder: str, component: str) -> str:
    """e.g. 'C=15 A=4 N=6' (and 'missing=1' if any)."""
    col = data.flags[coder][component]
    c = col.value_counts()
    text = f"C={c.get('Clear', 0)} A={c.get('Ambiguous', 0)} N={c.get('Not specified', 0)}"
    missing = int(col.isna().sum())
    return text + (f" missing={missing}" if missing else "")


def data_check_report(data: CodingData) -> str:
    """Step 8: what was loaded, before any alpha is computed."""
    lines = [f"Units (scenarios): {len(data.units)}"]
    for coder in data.flags:
        lines.append(f"\n[{coder}]")
        if data.extra_rows_ignored[coder]:
            lines.append(f"  rows not in the unit set (ignored): {data.extra_rows_ignored[coder]}")
        for s in data.skipped_rows[coder]:
            lines.append(f"  skipped non-scenario row -> {s}")
        for comp in COMPONENTS:
            lines.append(f"  {comp:36} {flag_counts(data, coder, comp)}")
    return "\n".join(lines)
