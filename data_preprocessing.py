"""Shared data pipeline: coding sheets (Excel) -> clean, aligned reliability matrices.

Both alpha implementations (library and custom) read their input from here, so they
always compare exactly the same data.

Pipeline: load config -> load sheets -> find flag columns -> select scenario rows
-> match units -> normalize flags -> encode -> reliability matrices.
"""

from __future__ import annotations

import argparse
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

# Numeric codes. The order (0 < 1 < 2) only matters for ordinal alpha.
# But here we use nominal alpha, so the order will not matter.
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

SCENARIO_ID = re.compile(r"^S\d+$")

# config
KINDS = ("human", "llm")


@dataclass
class CoderSource:
    name: str
    file: Path
    sheet: str | int = 0
    kind: str = "human"  # "human" (a mentee) or "llm"

@dataclass
class Comparison:
    name: str
    coders: list[str]


def load_config(path: str | Path) -> tuple[list[CoderSource], str]:
    """Read config.toml. Relative file paths are resolved against the config's folder.
    Returns (coders, units_from). `units_from` names the human coder whose scenarios
    define the units; every other coder must contain those scenarios.
    """
    path = Path(path)
    with open(path, "rb") as f:
        cfg = tomllib.load(f)

    coders = []
    for c in cfg["coders"]:
        kind = c.get("kind")
        if kind not in KINDS:
            raise ValueError(f'{path}: coder {c.get("name")!r} needs  kind = "human"  or  kind = "llm"')
        coders.append(CoderSource(c["name"], (path.parent / c["file"]).resolve(),
                                  c.get("sheet", 0), kind))
    names = [c.name for c in coders]
    if len(set(names)) != len(names):
        raise ValueError(f"Duplicate coder names in {path}: {names}")

    units_from = cfg.get("units_from")
    if units_from is None:
        raise ValueError(
            f'{path}: add  units_from = "<coder name>"  at the top of the file ' "(before any [[coders]] block)")
    if units_from not in names:
        raise ValueError(f"units_from = {units_from!r} is not one of the coders {names}")
    if next(c.kind for c in coders if c.name == units_from) != "human":
        raise ValueError(f"units_from = {units_from!r} must be a human coder (the sampled scenarios)")
    return coders, units_from

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
    """For each component, find the ONE column whose cleaned name starts with the component name and contains 'uncert' (e.g. 'access_uncertaintyt' still matches;
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
    units_from: str | None              # coder whose scenarios define the units; None = judged by all
    units: list[str]                    # unit keys, in that coder's order
    flags: dict[str, pd.DataFrame]      # coder -> flags for exactly `units`
    skipped_rows: dict[str, list[str]]
    extra_rows_ignored: dict[str, int]  # e.g. LLM sheet has 193 rows, we use 25

    def matrix(self, component: str, coders: list[str]) -> np.ndarray:
        """Reliability data matrix: rows = coders, columns = units, NaN = missing."""
        out = np.full((len(coders), len(self.units)), np.nan)
        for r, coder in enumerate(coders):
            for c, flag in enumerate(self.flags[coder][component]):
                if pd.isna(flag):  # missing (pandas may store None as NaN)
                    continue
                out[r, c] = FLAG_CODES[flag]
        return out


def load_coding_data(coders: list[CoderSource], units_from: str | None) -> CodingData:
    """Steps 1-5 for all coders, then align everyone on the same units.

    units_from = a coder's name: that coder's scenarios are the units (e.g. the 25 sampled
                 scenarios of a mentee); every other coder must contain them.
    units_from = None: the units are the scenarios that EVERY loaded coder has judged
                 (all 7 flags filled in), in the first coder's order. Used by --llm: all
                 193 when every LLM sheet is complete, fewer when one LLM stopped early.
    """
    extracted = []
    for src in coders:
        df = pd.read_excel(src.file, sheet_name=src.sheet, dtype=object)
        extracted.append(extract_flags(df, src.name))

    by_name = {cf.name: cf for cf in extracted}
    if units_from is None:
        judged = [set(cf.flags.index[cf.flags.notna().all(axis=1)]) for cf in extracted]
        common = set.intersection(*judged)
        units = [u for u in extracted[0].flags.index if u in common]
        if not units:
            raise ValueError(f"No scenario is judged (all 7 flags) by every coder: {list(by_name)}")
    else:
        units = list(by_name[units_from].flags.index)
    flags, extra = {}, {}
    for cf in extracted:
        missing = [u for u in units if u not in cf.flags.index]
        if missing:
            raise ValueError(
                f"{cf.name} is missing {len(missing)} of the {len(units)} scenarios defined by "
                f"units_from = '{units_from}'. First few: {missing[:5]}"
            )
        flags[cf.name] = cf.flags.loc[units]
        extra[cf.name] = len(cf.flags.index) - len(units)
    return CodingData(
        units_from, units, flags, {cf.name: cf.skipped_rows for cf in extracted}, extra
    )

# descriptive numbers (metrics)
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


# why alpha can be "n/a" (not an error)

def constant_flag(matrix: np.ndarray) -> str | None:
    """The one flag every coder gave in every comparable scenario, or None if flags vary."""
    pairable = (~np.isnan(matrix)).sum(axis=0) >= 2
    values = np.unique(matrix[:, pairable][~np.isnan(matrix[:, pairable])])
    if len(values) != 1:
        return None
    return {code: flag for flag, code in FLAG_CODES.items()}[int(values[0])]


def flag_counts(data: CodingData, coder: str, component: str) -> str:
    """e.g. 'C=15 A=4 N=6' (and 'missing=1' if any)."""
    col = data.flags[coder][component]
    c = col.value_counts()
    text = f"C={c.get('Clear', 0)} A={c.get('Ambiguous', 0)} N={c.get('Not specified', 0)}"
    missing = int(col.isna().sum())
    return text + (f" missing={missing}" if missing else "")


def data_check_report(data: CodingData) -> str:
    """Step 8: what was loaded, before any alpha is computed."""
    source = ("judged by every coder" if data.units_from is None
              else f"the scenarios of {data.units_from}")
    lines = [f"\n• Units (Scenarios): {len(data.units)}  ({source})"]

    for coder in data.flags:
        lines.append(f"\n[{coder}]")
        if data.extra_rows_ignored[coder]:
            lines.append(f"  rows not in the unit set (ignored): {data.extra_rows_ignored[coder]}")
        for s in data.skipped_rows[coder]:
            lines.append(f"  skipped non-scenario row -> {s}")
        for comp in COMPONENTS:
            lines.append(f"  {comp:36} {flag_counts(data, coder, comp)}")
    return "\n".join(lines)


# choose what to run: --human, --llm, or no flag (all coders combined)

def parse_mode(prog: str, engine: str) -> str:
    """Read the flag: --human -> "human", --llm -> "llm", no flag -> "all".
    argparse itself rejects both flags together or unknown flags (and -h shows the help)."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=f"Krippendorff's alpha for the threat-model coding, computed with {engine}.",
        epilog=f"examples:\n  uv run python {prog} --human\n  uv run python {prog} --llm\n"
               f"  uv run python {prog}            (no flag: all coders combined)\n\n"
               "Coders and their kind (human / llm) are listed in config.toml.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    flags = parser.add_mutually_exclusive_group()
    flags.add_argument("--human", action="store_true",
                       help="only the human coders (mentees), with each other")
    flags.add_argument("--llm", action="store_true",
                       help="only the LLM coders: all LLMs together plus every LLM pair, on the "
                            "scenarios that every LLM has judged")
    args = parser.parse_args()
    return "llm" if args.llm else "human" if args.human else "all"


COMBINED = "Combined (llm+human)"


def build_comparisons(coders: list[CoderSource], mode: str) -> list[Comparison]:
    """--human ("human"): all human coders together.
    --llm   ("llm"):   all LLM coders together, plus every pair of LLMs.
    no flag ("all"):   every coder (humans + LLMs) together in one alpha."""
    humans = [c.name for c in coders if c.kind == "human"]
    llms = [c.name for c in coders if c.kind == "llm"]
    if mode == "human":
        if len(humans) < 2:
            raise ValueError("--human needs at least 2 coders with kind = \"human\" in config.toml")
        return [Comparison("humans", humans)]
    if mode == "llm":
        if len(llms) < 2:
            raise ValueError("--llm needs at least 2 coders with kind = \"llm\" in config.toml")
        pairs = [Comparison(f"{a}_vs_{b}", [a, b]) for i, a in enumerate(llms) for b in llms[i + 1:]]
        # with only 2 LLMs the "all LLMs" group would just repeat their pair
        return ([Comparison("llms", llms)] if len(llms) >= 3 else []) + pairs
    if not humans or len(humans) + len(llms) < 2:
        raise ValueError("No flag (all coders combined) needs at least 2 coders, including the "
                         "human coder named by units_from, in config.toml")
    return [Comparison(COMBINED, humans + llms)]


def coders_needed(
    coders: list[CoderSource], comparisons: list[Comparison], units_from: str
) -> list[CoderSource]:
    """Only the coders used by the chosen comparisons (plus `units_from`), so a
    human-only run never loads or prints the LLM's sheet."""
    needed = {units_from} | {name for c in comparisons for name in c.coders}
    return [c for c in coders if c.name in needed]
