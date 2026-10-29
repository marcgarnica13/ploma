#!/usr/bin/env python3
"""Deterministic consistency pass: abstract numbers vs body, table cells vs results, passport claims.

Usage:
  python3 scripts/consistency.py [--root R] [main.tex] [--results D] [--metric-keys a,b]
                                 [--passport P] [--json] [--record]

With --root and no main.tex, paths come from ploma.yaml: document.main, pipeline.outputs_dir (when
pipeline.enabled), pipeline.metric_keys, pipeline.tolerances and the passport at
<outputs.dir>/passports/<document.slug>.yaml when it exists. --record writes the report
<outputs.dir>/consistency_<slug>.md and the "consistency" gate entry (a recommended check in v0.1).

Manuscript numbers are compared with each other by kind (percent, count, decimal) and display
rounding only; tolerances apply to comparisons with results files, where a percent may also match a
fraction times 100. With pipeline.metric_keys set, table cells and abstract and introduction numbers
match only results values with a metric key anywhere in their key path, or .csv columns named by
one (Ruling R159); without metric keys every numeric results value counts (Ruling R157). A count
matches only integer values and a decimal never matches an integer written as such (a count). siunitx \\num, \\qty and \\SI are read as numbers.
A "%" in a column header makes that column's bare numbers percents.

Table rows are tied to results entities by their label (Ruling R164): a label word must equal a word of
an entity key or string field above the metric key. Row labels must therefore use the results' entity
names or their words: a label "BERT-L" does not name "bert_large", so that row gets only the per-cell
check and a value copied from another entity is missed. A finding names the other entity by its
record's name-like field (name, team, model, method, label, title) or else its key, cites results files
relative to the repo root, keeps to the keys carrying the column header's word (Precision: *_precision)
when any match (Ruling R169). Each table's source is voted: every results directory (a file and its
siblings, such as cc_results.json and metrics_table.csv, count as one) scores the cells of the table
that match a value under their row's own entity there; the top-scoring directories (all of them on a
tie) are the table's source. A row whose entity the source holds is checked against the source only,
and findings cite the source, falling back to other files only when the source has no match. A comment
"%% ploma-source: <repo-relative path>" restricts the next tabular's cells to that results file; it may
sit anywhere after the previous \\end{table}, \\end{table*} or \\end{tabular} (or the start of the
file) and before the \\begin{tabular}, so above \\begin{table} or inside the float both work.

Rules (spec section 7.2):
  consistency.abstract_number_not_in_body.<raw>    FAIL  abstract number absent from the body
  consistency.abstract_number_only_in_results.<raw> WARN  absent from the body, present in results
  consistency.intro_number_not_in_body.<raw>       FAIL  introduction number (first \\section to the
                                                         next) absent from the rest of the body
  consistency.intro_number_only_in_results.<raw>   WARN  absent from the rest of the body, in results
  consistency.table_row_cell_other_entity.<label> WARN  with metric_keys set, a cell of a row whose label
                                                         names an entity in the results (a key path
                                                         component or a string field such as "model")
                                                         matches only values located under another row's
                                                         entity (Ruling R164)
  consistency.table_cell_other_column.<label>      WARN  such a cell matches the row's entity only under a
                                                         key lacking its column header's distinguishing
                                                         word (an HM cell holding the DFG value)
  consistency.table_cell_other_method.<label>      WARN  in a table section whose full-width \\multicolumn row
                                                         names a method ("(Heuristic Miner)", "(HM)"), or in
                                                         a row labelled "Heuristic Miner (HM)", a cell
                                                         matches the row's entity only under another
                                                         method's key prefix (dfg_precision, not
                                                         hm_precision); a method maps to the key prefix
                                                         equal to its acronym or its initials
  consistency.table_method_ambiguous.<file:line>   INFO  metric keys carry two or more method prefixes and
                                                         some rows of the table have no method context
  consistency.table_cell_not_in_results.<raw>      WARN  a table cell matches no results value
  consistency.table_source_missing.<file:line>     WARN  a "%% ploma-source" pin names no file (the table is
                                                         checked as if unpinned)
  consistency.table_source_unused.<file:line>      WARN  a "%% ploma-source" pin that applies to no tabular
  consistency.table_check_uninformative            INFO  the pool covers over half of the values such a cell
                                                         can display (2-decimal cells in [0, 1]: distinct
                                                         rounded values / 101), so its match says little
  consistency.placed_by_unkeyed_value.<raw>        INFO  with metric_keys set, a cell or abstract or
                                                         introduction number that only a value under
                                                         another key matches (audit-reproducibility
                                                         Phase 2 checks these)
  consistency.metric_key_missing.<key>             WARN  a metric key appears in no results file
  consistency.results_unreadable.<file>            WARN  a results file could not be parsed
  consistency.passport.<id>                        FAIL  passport claim with status FAIL or STALE
  consistency.passport_stale.<id>                  WARN  a FAIL claim whose number no longer appears at
                                                         its cited file (anywhere in it)
                                                   INFO  passport claim with status UNVERIFIED
  consistency.passport_invalid                     FAIL  passport missing, unparsable or off schema

Exit codes: 0 verdict PASS or WARN, 1 verdict FAIL, 2 usage error or unreadable input.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import functools
import json
import math
import re
import sys
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _texmask  # noqa: E402
import _yamlio  # noqa: E402
import bib_check  # noqa: E402
import ploma_config  # noqa: E402
from _findings import FAIL, INFO, PASS, WARN, Finding, render  # noqa: E402

PASSPORT_SCHEMA = Path(__file__).resolve().parent.parent / "schemas" / "passport.schema.json"
DEFAULT_TOLERANCES = {"counts": "exact", "metrics": 0.01, "percentages_pp": 0.1}
_EPS = 1e-9

# Commands whose arguments never hold manuscript numbers: None blanks every following group, n
# blanks up to the n-th brace group. Every command whose name contains "cite" is blanked too.
MASKED_COMMANDS: dict[str, int | None] = {
    **{name: None for name in (
        "label", "ref", "eqref", "autoref", "cref", "Cref", "pageref", "nameref", "vref", "url",
        "includegraphics", "input", "include", "bibliography", "bibliographystyle", "addbibresource",
        "usepackage", "documentclass", "vspace", "hspace", "setlength", "addtolength", "setcounter",
        "addtocounter", "begin", "end", "rule", "cmidrule", "cline", "fontsize",
        "linespread", "renewcommand", "newcommand", "providecommand", "definecolor", "rowcolor", "cellcolor",
        "hypersetup", "geometry", "graphicspath", "newcolumntype", "captionsetup", "setcitestyle",
        "addlinespace")},
    "href": 1, "textcolor": 1, "color": 1, "multicolumn": 2, "multirow": 2,
    # Boxes: blank the size and option groups, keep the content group.
    "resizebox": 2, "scalebox": 1, "raisebox": 1, "makebox": 0, "framebox": 0, "parbox": 1,
}
SECTION_COMMANDS = ("part", "chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph")
TABULAR_ENVS = ("tabular", "tabular*", "tabularx", "tabulary", "longtable", "longtable*")

_SECTION_RE = re.compile(r"\\(?:" + "|".join(SECTION_COMMANDS) + r")\*?\s*(?:\[[^\]]*\])?\s*\{")
_ROW_SPACING_RE = re.compile(r"\\\\\*?\s*(\[[^\]]*\])")
_DIM_RE = re.compile(r"(?<![\w.])-?\d*\.?\d+\s*\\(?:linewidth|textwidth|columnwidth|textheight|hsize|vsize|"
                     r"baselineskip|paperwidth|paperheight)\b")
_INDEX_RE = re.compile(r"(?<!\\)[_^]\s*(?:\{[^{}]*\}|\d+)")
_NUM = r"(?:\d{1,3}(?:(?:,|\\,)\d{3})+(?:\.\d+)?(?!\d)|\d+(?:\.\d+)?|\.\d+)"
NUM_RE = re.compile(r"(?<![\w.\\])(?<![A-Za-z]-)(?P<sign>(?<![-\d])-)?(?P<num>" + _NUM + r")(?P<pct>\s*\\?%)?(?!\w)")
CELL_RE = re.compile(r"(?P<sign>-)?(?P<num>" + _NUM + r")(?P<pct>\\?%)?")
# siunitx: \num[opts]{x}, \qty[opts]{x}{unit}, \SI[opts]{x}{unit}
SIUNITX_RE = re.compile(r"\\(?P<cmd>num|qty|SI)\s*(?:\[[^\]]*\])?\s*\{(?P<x>[^{}]*)\}"
                        r"(?:\s*\{(?P<unit>(?:[^{}]|\{[^{}]*\})*)\})?")
_SI_NUM_RE = re.compile(r"\s*(?P<sign>[-+])?\s*(?P<num>\d+(?:\.\d+)?|\.\d+)\s*(?:[eE](?P<exp>[-+]?\d+))?\s*")
_PM_RE = re.compile(r"\$?\s*(?:\\pm|\u00b1).*$", re.S)
_CELL_NOISE_RE = re.compile(
    r"\\(?:toprule|midrule|bottomrule|hline|cmidrule|cline|addlinespace|textbf|textit|textrm|textsf|texttt|"
    r"emph|underline|mathbf|mathrm|boldmath|bfseries|itshape|bf|it|centering|raggedleft|raggedright|"
    r"multicolumn|multirow|rowcolor|cellcolor|textcolor|color|phantom|hphantom|vphantom|noalign|bm)\b\*?")


# ---------------------------------------------------------------- number extraction

def mask_numbers(text: str) -> str:
    """Blank everything in text whose digits are not manuscript numbers (same length as text)."""
    out = _texmask.mask_definitions(text)
    out = _texmask.mask_command_args(out, MASKED_COMMANDS)
    for m in _SECTION_RE.finditer(text):
        end = _texmask.group_end(text, m.end() - 1)
        if end < 0:
            continue
        lead = re.match(r"\s*\d+(?:\.\d+)*\.?", text[m.end():end - 1])
        if lead:
            out = _texmask.blank_span(out, m.end(), m.end() + lead.end())
    for regex in (_ROW_SPACING_RE, _DIM_RE, _INDEX_RE):
        for m in regex.finditer(out):
            span = m.span(1) if regex is _ROW_SPACING_RE else m.span()
            out = _texmask.blank_span(out, *span)
    return out


def _number(m: re.Match) -> dict | None:
    num, pct, sign = m.group("num"), m.group("pct"), m.group("sign") or ""
    plain = num.replace("\\,", "").replace(",", "")
    value = float(sign + plain)
    if pct:
        kind = "percent"
    elif "." in num:
        kind = "decimal"
    else:
        kind = "count"
        if not sign and "," not in num and 1900 <= value <= 2099:
            return None  # a year
    raw = sign + num.replace("\\,", ",") + ("%" if pct else "")
    return {"value": value, "raw": raw, "kind": kind}


def _siunitx(m: re.Match) -> dict | None:
    """The number of a \\num, \\qty or \\SI match: percent when the unit is \\percent, decimal when written
    with a decimal point or an exponent, else count."""
    x = _SI_NUM_RE.fullmatch(m.group("x"))
    if not x:
        return None
    sign = "-" if x.group("sign") == "-" else ""
    value = float(sign + x.group("num") + (f"e{x.group('exp')}" if x.group("exp") else ""))
    unit = m.group("unit") or ""
    if "\\percent" in unit or unit.strip() == "\\%":
        kind = "percent"
    elif "." in x.group("num") or x.group("exp"):
        kind = "decimal"
    else:
        kind = "count"
        if not sign and 1900 <= value <= 2099:
            return None
    raw = sign + x.group("num") + (f"e{x.group('exp')}" if x.group("exp") else "") + ("%" if kind == "percent" else "")
    return {"value": value, "raw": raw, "kind": kind}


def _numbers(masked: str, lines: _texmask.LineIndex, file: str | None) -> list[dict]:
    out = []
    for m in SIUNITX_RE.finditer(masked):
        n = _siunitx(m)
        if n is not None:
            n.update(line=lines.line(m.start()), file=file, pos=m.start())
            out.append(n)
    masked = SIUNITX_RE.sub(lambda m: _texmask.blank(m.group()), masked)
    for m in NUM_RE.finditer(masked):
        n = _number(m)
        if n is not None:
            n.update(line=lines.line(m.start()), file=file, pos=m.start())
            out.append(n)
    out.sort(key=lambda n: n["pos"])
    return out


def extract_numbers(text: str, file: str | None = None) -> list[dict]:
    """Numbers in LaTeX text: dicts with value, raw, line, file and kind (count, percent or decimal).

    Ignores years 1900-2099, numbers inside citation, reference, label, URL, graphics and include
    arguments, leading section numbers, dimensions and pure math indices (x_1, ^2). Comments are not
    stripped here; run() strips them before calling.
    """
    nums = _numbers(mask_numbers(text), _texmask.LineIndex(text), file)
    for n in nums:
        del n["pos"]
    return nums


# ---------------------------------------------------------------- matching

def _dec(raw: str) -> Decimal:
    """Exact decimal value of a displayed number (raw as extracted: separators and % removed)."""
    return Decimal(raw.rstrip("%").replace(",", ""))


def _decimals(raw: str) -> int:
    """Decimal places the manuscript shows (0 for integers and for exponent forms without them)."""
    return max(0, -_dec(raw).as_tuple().exponent)


def _half_up(value: Decimal, places: int) -> Decimal:
    """Round as a reader rounds a display: half away from zero, on the exact decimal digits."""
    return value.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)


def _tol(tolerances: dict, key: str) -> float:
    value = (tolerances or {}).get(key, DEFAULT_TOLERANCES.get(key))
    if value in (None, "exact"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(DEFAULT_TOLERANCES[key]) if key != "counts" else 0.0


def same_number(a: dict, b: dict) -> bool:
    """Manuscript against manuscript: same kind, and equal once the more precise value is rounded to the
    decimals the other one shows (display rounding only; no tolerance, so 0.85 and 0.84 differ)."""
    if a["kind"] != b["kind"]:
        return False
    places = min(_decimals(a["raw"]), _decimals(b["raw"]))
    return _half_up(_dec(a["raw"]), places) == _half_up(_dec(b["raw"]), places)


def matches(num: dict, value: float, tolerances: dict) -> bool:
    """Whether a manuscript number agrees with value: counts exactly (or within tolerances.counts),
    decimals within tolerances.metrics, percentages within tolerances.percentages_pp (value as is or
    times 100). value is first rounded half up to the decimals the manuscript shows. A count only
    matches an integer value, and a decimal never matches an int (a count in the results file)."""
    kind = num["kind"]
    if kind == "count":
        # a count only matches an integer value (10 or 10.0, never 10.4)
        return float(value).is_integer() and abs(num["value"] - value) <= _tol(tolerances, "counts") + _EPS
    if kind == "decimal" and isinstance(value, int):
        return False  # a decimal cell never matches an integer-typed count (9.99 is not 10 runs)
    exact = Decimal(repr(float(value)))  # the shortest decimal that round-trips, as the results file shows it
    if kind == "percent":
        candidates, tol = (exact, exact * 100), _tol(tolerances, "percentages_pp")
    else:
        candidates, tol = (exact,), _tol(tolerances, "metrics")
    shown = _dec(num["raw"])
    places = _decimals(num["raw"])
    for v in candidates:
        if _half_up(v, places) == shown or abs(shown - v) <= Decimal(repr(tol)) + Decimal("1e-9"):
            return True
    return False


# ---------------------------------------------------------------- results

def _walk_json(data: Any, keys: set[str], res: "Results", keyed: bool = False) -> None:
    """Collect every finite number; a number with any component of its key path in keys is also keyed
    (Ruling R159: {"avg_fitness": {"mean": x}} and teams.<id>.avg_fitness both count)."""
    if isinstance(data, dict):
        for k, v in data.items():
            if k in keys and (_is_number(v) or isinstance(v, (list, dict))):
                res.keys_found.add(k)
            _walk_json(v, keys, res, keyed or k in keys)
    elif isinstance(data, list):
        for v in data:
            _walk_json(v, keys, res, keyed)
    elif _is_number(data):
        res.values.append(data)
        if keyed:
            res.keyed_values.append(data)


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _norm(text: Any) -> str:
    """Lowercase alphanumerics only: "Model A" and "model_a" both give "modela"."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def _tokens(text: Any) -> tuple[str, ...]:
    """Lowercase alphanumeric words: "hm_precision" gives ("hm", "precision")."""
    return tuple(re.findall(r"[a-z0-9]+", str(text).lower()))


@dataclass
class Located:
    """A keyed results value and where it sits (Ruling R164): the key path (file stem first, list indices
    left out), every word of the path and of the string fields of its object and every enclosing object
    (for the column check), and its entity slots: (level, name) pairs a row label can name. A level is a
    path depth, ("depth", d), for the path components above the first metric key, or a string field,
    ("field", name), of its object or an enclosing one (a CSV row's string cells, by column; innermost
    last). where and file give the results file relative to the repo root (Ruling R169)."""
    value: float
    where: str
    path: tuple[str, ...]
    words: frozenset[str]
    slots: tuple[tuple[tuple, str], ...]
    file: str = ""


@dataclass
class Results:
    files: list[Path] = field(default_factory=list)
    values: list[float] = field(default_factory=list)  # int when the file writes an integer (a count)
    keyed_values: list[float] = field(default_factory=list)  # values with a metric key in their key path
    keys_found: set[str] = field(default_factory=set)
    unreadable: list[tuple[Path, str]] = field(default_factory=list)
    located: list[Located] = field(default_factory=list)  # keyed values with their location
    file_values: dict[str, list] = field(default_factory=dict)  # repo-relative file: its numeric values
    file_keyed: dict[str, list] = field(default_factory=dict)  # repo-relative file: its keyed values


def _uniq(values: list) -> list:
    """Distinct values, sorted; an int and the equal float are kept apart (10 is a count, 10.0 is not)."""
    return sorted({(isinstance(v, int), v): v for v in values}.values())


def _locate(path: tuple[str, ...], strings: tuple[tuple[str, str], ...], value: float, where: str,
            keys: set[str]) -> Located:
    words = {w for p in path for w in _tokens(p)} | {w for _, s in strings for w in _tokens(s)}
    slots: list[tuple[tuple, str]] = []
    for d, comp in enumerate(path):
        if comp in keys:
            break  # a metric key and what lies under it (mean, std) name no entity
        slots.append((("depth", d), comp))
    slots += [(("field", name), s) for name, s in strings if _norm(s)]
    return Located(value, where, path, frozenset(words), tuple(slots))


def _json_located(data: Any, keys: set[str], path: tuple[str, ...], where: str, strings: tuple[str, ...],
                  keyed: bool, out: list[Located]) -> None:
    """Every keyed number of a JSON document with its location (see Located)."""
    if isinstance(data, dict):
        strings = strings + tuple((str(k), v) for k, v in data.items() if isinstance(v, str))
        for k, v in data.items():
            _json_located(v, keys, path + (str(k),), f"{where}.{k}" if where else str(k), strings,
                          keyed or k in keys, out)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            _json_located(v, keys, path, f"{where}[{i}]", strings, keyed, out)
    elif _is_number(data) and keyed:
        out.append(_locate(path, strings, data, where, keys))


def _csv_text(cell: str) -> bool:
    try:
        _csv_number(cell)
    except ValueError:
        return True
    return False


def _csv_number(cell: str):
    text = cell.strip()
    if re.fullmatch(r"[-+]?\d+", text):
        return int(text)
    number = float(text)
    return number if math.isfinite(number) else None


def load_results(results_dir: Path, metric_keys: list[str], root: Path | None = None) -> Results:
    """Every numeric value at any depth of every .json, and every numeric .csv cell, under results_dir;
    keyed_values holds those with any component of their key path in metric_keys, or whose .csv
    column header is one. Located values name their file relative to root (default: the parent of
    results_dir; a file outside root is named relative to that parent too)."""
    res = Results()
    if results_dir is None or not Path(results_dir).is_dir():
        return res
    keys = set(metric_keys)
    fallback = Path(results_dir).resolve().parent
    base = Path(root).resolve() if root else fallback
    for path in sorted(Path(results_dir).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in (".json", ".csv"):
            continue
        try:
            rel = path.resolve().relative_to(base).as_posix()
        except ValueError:
            rel = _rel(path, fallback)
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                data = json.loads(text)
                one = Results()
                _walk_json(data, keys, one)
                res.values += one.values
                res.keyed_values += one.keyed_values
                res.keys_found |= one.keys_found
                res.file_values[rel], res.file_keyed[rel] = one.values, one.keyed_values
                found: list[Located] = []
                _json_located(data, keys, (path.stem,), "", (), False, found)
                for loc in found:
                    loc.where, loc.file = f"{rel}:{loc.where or '(top level)'}", rel
                res.located += found
            else:
                rows = list(csv.reader(text.splitlines()))
                header = rows[0] if rows else []
                for r, row in enumerate(rows):
                    strings = tuple((header[j].strip() if j < len(header) else str(j), c)
                                    for j, c in enumerate(row) if c.strip() and _csv_text(c))
                    for i, cell in enumerate(row):
                        try:
                            number = _csv_number(cell)
                        except ValueError:
                            continue
                        if number is None:
                            continue
                        res.values.append(number)
                        res.file_values.setdefault(rel, []).append(number)
                        if i < len(header) and header[i].strip() in keys:
                            res.keys_found.add(header[i].strip())
                            if row is not header:
                                res.keyed_values.append(number)
                                res.file_keyed.setdefault(rel, []).append(number)
                                loc = _locate((path.stem, header[i].strip()), strings, number,
                                              f"{rel} row {r + 1} {header[i].strip()}", keys)
                                loc.file = rel
                                res.located.append(loc)
        except (OSError, UnicodeDecodeError, ValueError, csv.Error) as exc:
            res.unreadable.append((path, str(exc).splitlines()[0] if str(exc) else type(exc).__name__))
            continue
        res.files.append(path)
    res.values = _uniq(res.values)
    res.keyed_values = _uniq(res.keyed_values)
    return res


def _pool(results: Results, metric_keys: list[str]) -> list[float]:
    """The values manuscript numbers are matched against: keyed values only when metric keys are set."""
    return results.keyed_values if metric_keys else results.values


def _unkeyed(num: dict, results: Results, metric_keys: list[str], tolerances: dict) -> bool:
    """With metric keys set: no keyed value matches num, but some other results value does."""
    return bool(metric_keys) and not any(matches(num, v, tolerances) for v in results.keyed_values) \
        and any(matches(num, v, tolerances) for v in results.values)


def _unkeyed_finding(num: dict, where: str) -> Finding:
    return Finding(f"consistency.placed_by_unkeyed_value.{num['raw']}", INFO,
                   f"{num['raw']} matches a results value outside pipeline.metric_keys only",
                   observed=f"{where}; matched a value under another key (for example a per-seed history)",
                   remediation="Check where the number comes from (/ploma:audit-reproducibility Phase 2); add its "
                               "key to pipeline.metric_keys if it is a reported metric.", group="tables")


# ---------------------------------------------------------------- manuscript

def _abstract_spans(text: str) -> list[tuple[int, int]]:
    spans = [(c, e) for _, c, e in _texmask.env_spans(text, ("abstract",))]
    for m in re.finditer(r"\\abstract\s*\{", text):
        end = _texmask.group_end(text, m.end() - 1)
        if end > 0:
            spans.append((m.end(), end - 1))
    return spans


def _cell_number(cell: str) -> dict | None:
    """The number a table cell holds: a plain number, a siunitx \\num/\\qty/\\SI, or the first number of
    ``x $\\pm$ y``; None for anything else."""
    cell = _PM_RE.sub("", cell)
    cell = _CELL_NOISE_RE.sub("", cell)
    si = SIUNITX_RE.search(cell)
    if si and not re.sub(r"[\s${}~]", "", cell[:si.start()] + cell[si.end():]):
        return _siunitx(si)
    m = CELL_RE.fullmatch(re.sub(r"[\s${}~]", "", cell))
    return _number(m) if m else None


def _row_label(cell: str) -> str:
    """An id-safe label from a row's first cell: its words joined by _ (empty when it has none)."""
    text = _CELL_NOISE_RE.sub("", cell)
    text = re.sub(r"\\[A-Za-z]+\*?|[{}$~]", " ", text)
    return re.sub(r"[^\w.+-]+", "_", text).strip("_.")


_PIN_RE = re.compile(r"^[ \t]*%+[ \t]*ploma-source:[ \t]*(\S+)", re.M)
_MULTICOLUMN_RE = re.compile(r"\\multicolumn\s*\{\s*(\d+)\s*\}")
_TABLE_END_RE = re.compile(r"\\end\s*\{(?:table\*?|" + "|".join(re.escape(e) for e in TABULAR_ENVS) + r")\}")


def _source_pins(raw: str, stripped: str) -> tuple[dict[int, str], list[tuple[int, str, bool]]]:
    """The "%% ploma-source: <path>" pins of one file: ({tabular begin offset: path}, [(offset, path, used)]).
    A pin applies to the next tabular whose \\begin follows it with no \\end{table}, \\end{table*} or
    \\end{tabular} in between (so above \\begin{table} or inside the float both work); each pin applies to
    one tabular at most, and the last pin before a tabular wins. raw and stripped share offsets."""
    pins = [(m.start(1), m.group(1).removeprefix("./")) for m in _PIN_RE.finditer(raw)]
    ends = [m.end() for m in _TABLE_END_RE.finditer(stripped)]
    used: set[int] = set()
    applied: dict[int, str] = {}
    for begin in sorted(b for b, _, _ in _texmask.env_spans(stripped, TABULAR_ENVS)):
        start = max((e for e in ends if e <= begin), default=0)
        cands = [k for k, (pos, _) in enumerate(pins) if start <= pos < begin and k not in used]
        if cands:
            used.add(cands[-1])
            applied[begin] = pins[cands[-1]][1]
    return applied, [(pos, path, k in used) for k, (pos, path) in enumerate(pins)]


def _table_cells(stripped: str, masked: str, lines: _texmask.LineIndex, file: str,
                 pins: dict[int, str] | None = None) -> list[dict]:
    """Numeric cells with file, line, the row they sit in ("row": file:line of the row start), the row's
    label (its first cell's words, or "line<N>"), and the column header of the latest row above with
    several cells and no number ("header"; a "%" in it makes the column's numbers percents), with its words that no other header column has ("distinct":
    "HM precision" next to "DFG precision" gives ["hm"]). Each cell also carries its table ("table":
    file:line of the \\begin), the row's first cell as written ("label_text"), the text of the latest
    full-width \\multicolumn row above in the table ("section", reset by each such row) and the table's
    "%% ploma-source:" path ("source", empty when none; see _source_pins)."""
    cells = []
    for begin, content, end in _texmask.env_spans(stripped, TABULAR_ENVS):
        body = masked[content:end]
        end_tag = body.rfind("\\end")
        body = body[:end_tag] if end_tag >= 0 else body
        text_body = stripped[content:content + len(body)]
        table = f"{file}:{lines.line(begin)}"
        source = (pins or {}).get(begin, "")
        split = re.split(r"(\\\\)", body)
        width = max((len(re.split(r"(?<!\\)&", r)) for r in split if r != "\\\\"), default=1)
        offset = content
        headers: list[str] = []
        distinct: list[list[str]] = []
        percent: list[bool] = []
        section = ""
        for row in split:
            if row != "\\\\":
                pos = offset
                column = 0
                parts = re.split(r"(?<!\\)(&)", row)
                texts = [p for p in parts if p != "&"]
                row_text = text_body[offset - content:offset - content + len(row)]
                span = _MULTICOLUMN_RE.search(row_text)
                if len(texts) == 1 and span and int(span.group(1)) >= max(width, 2):
                    section = row_text
                if len(texts) >= 2 and all(_cell_number(t) is None for t in texts):
                    headers = [_row_label(t).replace("_", " ") for t in texts]
                    percent = ["%" in t for t in texts]  # "acc (\\%)": the column's bare numbers are percents
                    words = [set(_tokens(h)) for h in headers]
                    distinct = [sorted(w - set().union(*(o for j, o in enumerate(words) if j not in (0, k))))
                                for k, w in enumerate(words)]
                row_line = lines.line(offset + len(row) - len(row.lstrip()))
                label_text = row_text.split("&", 1)[0]
                label = _row_label(parts[0]) if parts else ""
                if not label or _cell_number(parts[0]) is not None:
                    label = f"line{row_line}"
                for cell in parts:
                    if cell == "&":
                        column += 1
                    else:
                        n = _cell_number(cell)
                        if n is not None and column and column < len(percent) and percent[column]:
                            n["kind"] = "percent"
                        if n is not None and not (column == 0 and n["kind"] == "count"):
                            n.update(line=lines.line(pos + len(cell) - len(cell.lstrip())), file=file,
                                     row=f"{file}:{row_line}", label=label,
                                     header=headers[column] if column < len(headers) else "",
                                     distinct=distinct[column] if column < len(distinct) and column else [],
                                     table=table, label_text=label_text, section=section, source=source)
                            cells.append(n)
                    pos += len(cell)
            offset += len(row)
    return cells


@dataclass
class ConsistencyReport:
    main: str
    findings: list[Finding]
    verdict: str
    abstract_numbers: list[dict] = field(default_factory=list)
    body_numbers: int = 0
    intro_numbers: list[dict] = field(default_factory=list)
    table_cells: list[dict] = field(default_factory=list)
    results_dir: str | None = None
    results_files: list[str] = field(default_factory=list)
    tables_checked: bool = False
    passport: dict = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"main": self.main, "verdict": self.verdict, "findings": [f.to_dict() for f in self.findings],
                "abstract_numbers": self.abstract_numbers, "body_numbers": self.body_numbers,
                "intro_numbers": self.intro_numbers,
                "table_cells": self.table_cells, "results_dir": self.results_dir,
                "results_files": self.results_files, "tables_checked": self.tables_checked,
                "passport": self.passport, "sources": self.sources}


def _rel(path: Path, base: Path) -> str:
    try:
        return Path(path).resolve().relative_to(base).as_posix()
    except ValueError:
        return str(path)


def _where(n: dict) -> str:
    return f"{n['file']}:{n['line']}"


_SECTION_START_RE = re.compile(r"\\section\*?\s*(?:\[[^\]]*\])?\s*\{")


def _segments(main: Path, texts: dict[Path, str]) -> list[tuple[Path, int, int]]:
    """Document order: (file, start, end) runs of text, with each \\input or \\include expanded in place."""
    base = main.parent
    out: list[tuple[Path, int, int]] = []
    seen: set[Path] = set()

    def visit(path: Path) -> None:
        seen.add(path)
        text = texts[path]
        prev = 0
        for m in bib_check._INCLUDE_RE.finditer(text):
            out.append((path, prev, m.start()))
            name = m.group(1).strip()
            child = (base / (name if name.endswith(".tex") else name + ".tex")).resolve()
            if child in texts and child not in seen:
                visit(child)
            prev = m.end()
        out.append((path, prev, len(text)))

    visit(main)
    return out


def _scan(main: Path) -> tuple[list[dict], list[dict], list[dict], list[dict], list[str], list[dict]]:
    """(abstract, introduction, rest of body, table cells, source names, source pins) across main and its
    inputs; a source pin is {"file", "line", "path", "used"} (see _source_pins).

    The introduction runs from the first \\section to the next one, in document order (inputs expanded);
    a document with fewer than two \\section commands has no introduction to check.
    """
    main = Path(main).resolve()
    base = main.parent
    texts: dict[Path, str] = {}
    abstract: list[dict] = []
    body: list[dict] = []
    cells: list[dict] = []
    names: list[str] = []
    pins: list[dict] = []
    sections: list[tuple[Path, int]] = []
    for src in bib_check.tex_sources(main):
        name = _rel(src, base)
        names.append(name)
        raw = src.read_text(encoding="utf-8", errors="replace")
        stripped = _texmask.strip_comments(raw)
        if src == main:
            stripped = _texmask.mask_before_document(stripped)
        texts[src] = stripped
        masked = mask_numbers(stripped)
        lines = _texmask.LineIndex(stripped)
        spans = _abstract_spans(stripped)
        for n in _numbers(masked, lines, name):
            n["_src"] = src
            inside = any(s <= n["pos"] < e for s, e in spans)
            (abstract if inside else body).append(n)
        applied, found = _source_pins(raw, stripped)
        pins += [{"file": name, "line": lines.line(pos), "path": path, "used": used} for pos, path, used in found]
        cells.extend(_table_cells(stripped, masked, lines, name, applied))
        sections += [(src, m.start()) for m in _SECTION_START_RE.finditer(stripped)]

    segments = _segments(main, texts)

    def order(path: Path, pos: int) -> tuple[int, int]:
        for i, (p, start, end) in enumerate(segments):
            if p == path and start <= pos < end:
                return (i, pos)
        return (len(segments), pos)

    marks = sorted(order(p, pos) for p, pos in sections)
    intro: list[dict] = []
    rest: list[dict] = []
    for n in body:
        key = order(n["_src"], n["pos"])
        (intro if len(marks) >= 2 and marks[0] <= key < marks[1] else rest).append(n)
    for n in abstract + body:
        del n["_src"], n["pos"]
    return abstract, intro, rest, cells, names, pins


# ---------------------------------------------------------------- passport

def _claim_left_location(claim: dict, base: Path | None) -> bool:
    """Whether the manuscript no longer shows the claim's number where the claim says it is: the
    location's file (relative to the main file's folder or one of its parents) exists, and none of the
    numbers in the claim text appear anywhere in it. The whole file is searched even when the location
    cites lines, since lines shift when text is added above. False when this cannot be decided."""
    numbers = extract_numbers(str(claim.get("claim") or ""))
    location = str(claim.get("location") or "")
    if base is None or not numbers or not location:
        return False
    name = location.partition(":")[0]
    name = name.strip()
    target = next((d / name for d in (base, *list(base.parents)[:3]) if name and (d / name).is_file()), None)
    if target is None:
        return False
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    shown = extract_numbers(_texmask.strip_comments(text))
    return not any(same_number(n, s) for n in numbers for s in shown)


def _schema_problem(f: Finding, data: dict) -> str:
    """ploma_config's schema message with the field path as claims[i].field (claim <id>) and the value
    found: "claims[1].status (claim C2) must be one of PASS, FAIL, STALE, UNVERIFIED; got 'OK'"."""
    path = f.id.split(".", 2)[2] if f.id.count(".") >= 2 else ""
    pretty = re.sub(r"\.(\d+)(?=\.|$)", r"[\1]", path)
    m = re.match(r"claims\[(\d+)\]", pretty)
    claims = data.get("claims")
    if m and isinstance(claims, list) and int(m.group(1)) < len(claims) and isinstance(claims[int(m.group(1))], dict) \
            and claims[int(m.group(1))].get("id"):
        pretty += f" (claim {claims[int(m.group(1))]['id']})"
    text = f.summary.replace(path, pretty, 1) if path else f.summary
    return text + (f"; got {f.observed}" if f.observed else "")


def _passport_findings(path: Path, base: Path | None = None) -> tuple[list[Finding], dict]:
    def invalid(problem: str, observed: str = "") -> tuple[list[Finding], dict]:
        return [Finding("consistency.passport_invalid", FAIL, f"passport {path.name}: {problem}",
                        observed=observed or str(path),
                        remediation="Fix the passport against schemas/passport.schema.json, or regenerate it "
                                    "with /ploma:audit-reproducibility.", group="passport")], {"path": str(path)}

    if not path.is_file():
        return invalid("file not found")
    try:
        data = _yamlio.load_yaml(path)
    except (_yamlio.YamlError, OSError, UnicodeDecodeError) as exc:
        return invalid("could not parse the YAML", str(exc).splitlines()[0] if str(exc) else "")
    if not isinstance(data, dict):
        return invalid("top level must be a mapping with paper and claims")
    problems: list[Finding] = []
    schema = json.loads(PASSPORT_SCHEMA.read_text(encoding="utf-8"))
    ploma_config._check(data, schema, "", problems)
    errors = [_schema_problem(f, data) for f in problems if f.status == FAIL]
    if errors:
        return invalid(errors[0] + (f" (and {len(errors) - 1} more)" if len(errors) > 1 else ""), "; ".join(errors))
    claims = data.get("claims") or []
    counts = {s: sum(1 for c in claims if c.get("status") == s) for s in ("PASS", "FAIL", "STALE", "UNVERIFIED")}
    out: list[Finding] = []
    for c in claims:
        status = c.get("status")
        where = f"{c.get('location') or 'no location'}; claim: {c.get('claim')}"
        if c.get("notes"):
            where += f"; notes: {str(c['notes']).strip()}"
        if status == "FAIL" and _claim_left_location(c, base):
            out.append(Finding(f"consistency.passport_stale.{c.get('id')}", WARN,
                               f"passport claim {c.get('id')}: claim location changed; re-run "
                               f"/ploma:audit-reproducibility",
                               observed=f"{where}; the claim's number no longer appears at that location",
                               remediation="The manuscript was corrected after the audit; re-run "
                                           "/ploma:audit-reproducibility to update the passport.", group="passport"))
        elif status in ("FAIL", "STALE"):
            fix = ("re-run the pipeline and /ploma:audit-reproducibility, or correct the manuscript number"
                   if status == "FAIL" else
                   "the source or output changed after the last verification; re-run /ploma:audit-reproducibility")
            out.append(Finding(f"consistency.passport.{c.get('id')}", FAIL, f"passport claim {c.get('id')} is {status}",
                               observed=where, remediation=fix, group="passport"))
        elif status == "UNVERIFIED":
            out.append(Finding(f"consistency.passport.{c.get('id')}", INFO,
                               f"passport claim {c.get('id')} was never verified", observed=where,
                               remediation="Run /ploma:audit-reproducibility before submission.", group="passport"))
    return out, {"path": str(path), "claims": len(claims), **{k.lower(): v for k, v in counts.items()}}


# ---------------------------------------------------------------- run

def _verdict(findings: list[Finding]) -> str:
    if any(f.status == FAIL for f in findings):
        return FAIL
    if any(f.status == WARN for f in findings):
        return WARN
    return PASS


def _check_numbers(part: str, numbers: list[dict], against: list[dict], where_text: str, results: Results,
                   tolerances: dict, metric_keys: list[str] | None = None) -> list[Finding]:
    """FAIL for each number absent from against (same kind, display rounding); WARN instead when a
    results value matches it within tolerance (only values under metric_keys when those are set, with
    an INFO placed_by_unkeyed_value when only another key's value matches)."""
    metric_keys = list(metric_keys or [])
    pool = _pool(results, metric_keys)
    label = {"abstract": "abstract", "intro": "introduction"}[part]
    group = "abstract" if part == "abstract" else "intro"
    out: list[Finding] = []
    seen: set[str] = set()
    for a in numbers:
        if a["raw"] in seen or any(same_number(a, b) for b in against):
            continue
        seen.add(a["raw"])
        if _unkeyed(a, results, metric_keys, tolerances):
            out.append(_unkeyed_finding(a, _where(a)))
        if any(matches(a, v, tolerances) for v in pool):
            out.append(Finding(f"consistency.{part}_number_only_in_results.{a['raw']}", WARN,
                               f"{label} number {a['raw']} appears in a results file but not in {where_text}",
                               observed=f"{_where(a)}; looked in {where_text} ({len(against)} numbers) and results",
                               remediation="State the number in the body where the result is reported.",
                               group=group))
        else:
            out.append(Finding(f"consistency.{part}_number_not_in_body.{a['raw']}", FAIL,
                               f"{label} number {a['raw']} does not appear in {where_text}",
                               observed=f"{_where(a)}; looked in {where_text} ({len(against)} numbers, tables and "
                                        f"captions included)" + (" and results" if results.files else ""),
                               remediation=f"Correct the {label}, or report the number in the body.", group=group))
    return out


def _vkey(v) -> tuple:
    return (isinstance(v, int), v)


def _coverage(cell: dict, pool: list, cache: dict, tolerances: dict) -> tuple[float, str] | None:
    """Share of the displayed values at the cell's precision, in the unit interval holding it, that some
    pool value would match: equal once rounded, or within the matching tolerance (for a 2-decimal cell in
    [0, 1], covered values / 101), with a short description of that space; None for counts and
    integer-shown cells."""
    kind, places = cell["kind"], _decimals(cell["raw"])
    if kind == "count" or places == 0:
        return None
    lo = math.floor(abs(cell["value"]))
    key = (kind, places, lo)
    if key not in cache:
        tol = _tol(tolerances, "percentages_pp" if kind == "percent" else "metrics")
        step = 10.0 ** -places
        reach = max(tol, step / 2) + 1e-9
        cands: list[float] = []
        for v in pool:
            if kind == "decimal" and isinstance(v, int):
                continue
            cands += [abs(float(v)), abs(float(v)) * 100] if kind == "percent" else [abs(float(v))]
        cands.sort()
        size = 10 ** places + 1
        covered = 0
        for k in range(size):
            d = lo + k * step
            j = bisect.bisect_left(cands, d - reach)
            if j < len(cands) and cands[j] <= d + reach:
                covered += 1
        cache[key] = (covered / size, f"{size} {places}-decimal {'percent ' if kind == 'percent' else ''}"
                                      f"values in [{lo}, {lo + 1}]")
    return cache[key]


@functools.lru_cache(maxsize=262144)
def _covers(name: str, label: str) -> frozenset[str]:
    """Words of a row label that an entity slot name covers: all of them when both normalise alike
    ("Model A", "model_a"), else the words they share ("Alpha HM" and "alpha" share alpha)."""
    words = frozenset(_tokens(label))
    if _norm(name) and _norm(name) == _norm(label):
        return words
    return words & frozenset(_tokens(name))


def _entity(label: str, located: list[Located]) -> tuple[list[bool], dict[tuple, set[str]]] | None:
    """The values a row label names (Ruling R164, fix round 2): those whose entity slots cover the most
    label words (so "Alpha HM" picks hm.alpha, not hm.beta or dfg.alpha), and, per slot level they
    were named at, the names that cover the label. None when no slot covers a label word."""
    covered = [frozenset().union(*(_covers(n, label) for _, n in loc.slots)) for loc in located]
    best = max((len(c) for c in covered), default=0)
    if not best:
        return None
    own = [len(c) == best for c in covered]
    levels: dict[tuple, set[str]] = {}
    for loc, mine in zip(located, own):
        if mine:
            for level, name in loc.slots:
                if _covers(name, label):
                    levels.setdefault(level, set()).add(_norm(name))
    return own, levels


def _other_entity(loc: Located, levels: dict[tuple, set[str]]) -> tuple[tuple, str] | None:
    """The other entity a value belongs to: its name at a level where the row's own entity was named,
    when that name is not one of the row's best-cover names (model_b is another entity for a row
    "Model A" although it shares "model"). None for a value above the per-entity level or beside it (a
    shared count)."""
    for level, name in loc.slots:
        if level in levels and _norm(name) not in levels[level]:
            return level, name
    return None


def _method_prefixes(metric_keys: list[str]) -> set[str]:
    """Method prefixes of the metric keys: first words of keys whose remaining words another key has
    under another first word (hm_precision and dfg_precision give hm and dfg)."""
    split = [(t[0], t[1:]) for t in map(_tokens, metric_keys) if len(t) >= 2]
    return {p for p, rest in split if any(q != p and r == rest for q, r in split)}


def _method_name(text: str, prefixes: set[str]) -> str | None:
    """The prefix a method name maps to: the name itself lowercased ("HM"), or its initials ("Heuristic
    Miner", "Directly-follows graph")."""
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not words:
        return None
    if len(words) == 1 and words[0].lower() in prefixes:
        return words[0].lower()
    initials = "".join(w[0] for w in words).lower()
    return initials if initials in prefixes else None


def _method_of(text: str, prefixes: set[str], parens_only: bool = False) -> str | None:
    """The method a table text names in parentheses ("(Heuristic Miner)", "(HM)") or, unless
    parens_only, as an acronym ("HM"); None when it names none of the prefixes."""
    if not prefixes or not text:
        return None
    text = re.sub(r"\\[A-Za-z]+\*?", " ", text)
    candidates = re.findall(r"\(([^()]*)\)", text)
    if not parens_only:
        candidates += re.findall(r"\b[A-Z][A-Z0-9]+\b", text)
    for cand in candidates:
        method = _method_name(cand, prefixes)
        if method:
            return method
    return None


def _metric_key(loc: Located, keys: set[str]) -> str:
    """The metric key in the value's key path (the column name for a CSV value)."""
    return next((part for part in loc.path if part in keys), "")


NAME_FIELD_WORDS = frozenset({"name", "team", "model", "method", "label", "title"})


def _display_entity(loc: Located, level: tuple, name: str) -> str:
    """How a finding names the entity a value belongs to (Ruling R169): the name given at a string-field
    level as is; else the record's innermost name-like field (name, team, model, method, label, title,
    or a field such as team_name); else its key, with the parent key in front when the key is a number
    ("teams.93"). The file stem is printed only when the value has no deeper key."""
    if level[0] == "field":
        return name
    for lvl, value in reversed(loc.slots):
        if lvl[0] == "field" and NAME_FIELD_WORDS & set(_tokens(lvl[1])):
            return value
    depths = [(lvl[1], value) for lvl, value in loc.slots if lvl[0] == "depth"]
    if level[1] == 0 and len(depths) > 1:
        level, name = ("depth", depths[-1][0]), depths[-1][1]
    if name.isdigit():
        above = [value for d, value in depths if 0 < d < level[1]]
        if above:
            return f"{above[-1]}.{name}"
    return name


def _cell_list(items: list[tuple[dict, str]]) -> str:
    """One entry per distinct cell; the column header is added when two cells share value and line."""
    seen: dict[tuple, int] = {}
    for c, _ in items:
        seen[(c["raw"], _where(c))] = seen.get((c["raw"], _where(c)), 0) + 1
    out: list[str] = []
    for c, note in items:
        col = f", column {c.get('header')}" if seen[(c["raw"], _where(c))] > 1 and c.get("header") else ""
        entry = f"{c['raw']} ({_where(c)}{col}) {note}"
        if entry not in out:
            out.append(entry)
    return "; ".join(out)


def _dir(file: str) -> str:
    """The directory of a repo-relative results file: the unit the table-wide source vote counts."""
    return file.rsplit("/", 1)[0] if "/" in file else ""


def _check_tables(cells: list[dict], results: Results, metric_keys: list[str], tolerances: dict) -> list[Finding]:
    """Table cells against the results (Ruling R164). With metric keys, a row whose label (first cell)
    names an entity in the results (see _entity) must have every numeric cell matched by a keyed
    value located under that entity; a cell matched only under another row's entity is WARN
    table_row_cell_other_entity, and a cell matched only under a key that lacks its column header's
    distinguishing word (hm vs dfg) while the entity has such a key is WARN table_cell_other_column.
    Values located under no table entity (a shared count) still match. Other rows, and every row
    without metric keys, are matched cell by cell against the whole pool, with an INFO
    table_check_uninformative when that pool covers more than half of the values a cell can display.
    A cell matching no results value is WARN table_cell_not_in_results."""
    pool = _pool(results, metric_keys)
    files = results.file_keyed if metric_keys else results.file_values

    def pool_of(c: dict) -> list:
        return _uniq(files.get(c["source"], [])) if c.get("source") else pool

    by_raw: dict[tuple[str, str, str], set] = {}
    for c in cells:
        key = (c["kind"], c["raw"], c.get("source") or "")
        if key not in by_raw:
            by_raw[key] = {_vkey(v) for v in pool_of(c) if matches(c, v, tolerances)}
    hits = [by_raw[(c["kind"], c["raw"], c.get("source") or "")] for c in cells]
    rows: dict[str, list[int]] = {}
    for i, c in enumerate(cells):
        rows.setdefault(c.get("row", f"{c['file']}:{c['line']}"), []).append(i)
    all_located = results.located if metric_keys else []
    key_set = set(metric_keys)
    key_words = {w for k in metric_keys for w in _tokens(k)}
    prefixes = _method_prefixes(metric_keys)
    entities: dict[tuple[str, str], Any] = {}

    def method_of(c: dict) -> str | None:
        """The row's own method ("Heuristic Miner (HM)"), else its section's."""
        return _method_of(c.get("label_text", ""), prefixes, parens_only=True) \
            or _method_of(c.get("section", ""), prefixes)

    def key_method(loc: Located) -> str | None:
        words = _tokens(_metric_key(loc, key_set))
        return words[0] if len(words) >= 2 and words[0] in prefixes else None

    def table_of(c: dict) -> str:
        return c.get("table") or c["file"]

    def located_of(source: str) -> list[Located]:
        return [loc for loc in all_located if loc.file == source] if source else all_located

    def named_of(c: dict):
        label, source = c.get("label") or "", c.get("source") or ""
        located = located_of(source)
        if label and not re.fullmatch(r"line\d+", label) and located and (label, source) not in entities:
            entities[(label, source)] = _entity(label, located)
        return entities.get((label, source))

    # The table-wide source vote: each unpinned table's source is the results directory (a file and its
    # siblings: cc_results.json and metrics_table.csv count as one) whose values under each row's own
    # entity match the most cells of the table; tied directories are all its source.
    votes: dict[str, dict[str, int]] = {}
    for idxs in rows.values():
        c0 = cells[idxs[0]]
        named = named_of(c0)
        if not named or c0.get("source"):
            continue
        ent = [loc for loc, m in zip(located_of(""), named[0]) if m]
        score = votes.setdefault(table_of(c0), {})
        for i in idxs:
            if hits[i]:
                for d in {_dir(loc.file) for loc in ent if _vkey(loc.value) in hits[i]}:
                    score[d] = score.get(d, 0) + 1
    table_dirs = {t: {d for d, n in score.items() if n == max(score.values())} for t, score in votes.items() if score}

    out: list[Finding] = []
    missed: dict[str, list[dict]] = {}
    unplaced: list[dict] = []
    dense: list[tuple[float, str, dict]] = []
    cache: dict = {}
    ids: set[str] = set()
    for idxs in rows.values():
        unplaced += [cells[i] for i in idxs if not hits[i]]
        label = cells[idxs[0]].get("label") or ""
        source = cells[idxs[0]].get("source") or ""
        located = located_of(source)
        named = named_of(cells[idxs[0]])
        if not named:
            for i in idxs:
                if not hits[i]:
                    missed.setdefault(cells[i]["raw"], []).append(cells[i])
                else:
                    cov = _coverage(cells[i], pool_of(cells[i]), cache if not source else {}, tolerances)
                    if cov and cov[0] > 0.5:
                        dense.append((cov[0], cov[1], cells[i]))
            continue
        own, levels = named
        ent = [loc for loc, m in zip(located, own) if m]
        dirs = table_dirs.get(table_of(cells[idxs[0]]), set())
        # When the table's source holds the row's entity, its cells must match there.
        ent = [loc for loc in ent if _dir(loc.file) in dirs] or ent
        other_entity: list[tuple[dict, str]] = []
        other_column: list[tuple[dict, str]] = []
        other_method: list[tuple[dict, str]] = []
        found_by = {i: [loc for loc in ent if _vkey(loc.value) in hits[i]] for i in idxs if hits[i]}
        for i in idxs:
            c = cells[i]
            if not hits[i]:
                missed.setdefault(c["raw"], []).append(c)
                continue
            found = found_by[i]
            col = set(_tokens(c.get("header") or "")) & key_words
            method = method_of(c) if found else None
            if method:
                in_col = [loc for loc in found if not col or col & set(_tokens(_metric_key(loc, key_set)))]
                methods = {key_method(loc) for loc in in_col}
                if in_col and all(m and m != method for m in methods):
                    expected = [loc for loc in ent if key_method(loc) == method
                                and (not col or col & set(_tokens(_metric_key(loc, key_set))))]
                    note = f"is in the {method.upper()} section but matches only " + ", ".join(
                        f"{loc.where} = {loc.value}" for loc in in_col[:3])
                    if expected:
                        note += f"; the {method.upper()} value is {expected[0].where} = {expected[0].value}"
                    other_method.append((c, note))
                    continue
            if found:
                want = set(c.get("distinct") or ())
                if want and any(want & loc.words for loc in ent) and not any(want & loc.words for loc in found):
                    other_column.append((c, f"is in column '{c.get('header')}' but matches "
                                            + ", ".join(loc.where for loc in found[:3])
                                            + f", which lacks '{'/'.join(sorted(want))}'"))
                continue
            elsewhere = [loc for loc in located if _vkey(loc.value) in hits[i]]
            # R169: the column header picks the key first (a Precision cell goes to *_precision keys).
            by_column = [loc for loc in elsewhere if col & {w for part in loc.path for w in _tokens(part)}]
            elsewhere = by_column or elsewhere
            owners = [_other_entity(loc, levels) for loc in elsewhere]
            if elsewhere and all(owners):
                pairs = list(zip(elsewhere, owners))
                pairs = [x for x in pairs if _dir(x[0].file) in dirs] or pairs  # the table's source first
                other_entity.append((c, "matches only " + ", ".join(
                    f"{loc.where} ({_display_entity(loc, *o)})" for loc, o in pairs[:3])))
        for rule, items, summary, fix in (
                ("table_row_cell_other_entity", other_entity,
                 "holds a value the results give for another row's entity",
                 "Copy the value from this row's own results record; re-run the pipeline or correct the table."),
                ("table_cell_other_column", other_column,
                 "holds a value from another column's metric of the same entity",
                 "Copy the value from the key that matches the column header; re-run the pipeline or correct "
                 "the table."),
                ("table_cell_other_method", other_method,
                 "holds the same entity's value for another method than its section's",
                 "Copy the value from the key of the section's method; re-run the pipeline or correct the "
                 "table.")):
            if not items:
                continue
            fid = f"consistency.{rule}.{label}"
            if fid in ids:
                fid = f"{fid}_line{items[0][0]['line']}"
            ids.add(fid)
            cells_txt = ", ".join(f"{c['raw']}" + (f" ({c.get('header')})" if c.get("header") else "")
                                  for c, _ in items)
            out.append(Finding(fid, WARN, f"table row {label}: {cells_txt} {summary}",
                               observed=_cell_list(items), remediation=fix, group="tables"))
    for raw, where in missed.items():
        out.append(Finding(f"consistency.table_cell_not_in_results.{raw}", WARN,
                           f"table cell {raw} matches no value in the results files",
                           observed=", ".join(_where(c) for c in where)
                           + f"; looked in {len(results.files)} results file(s)",
                           remediation="Check the cell against the pipeline outputs; re-run the pipeline "
                                       "or correct the table.", group="tables"))
    seen: set[str] = set()
    for c in unplaced:
        if c["raw"] not in seen and _unkeyed(c, results, metric_keys, tolerances):
            seen.add(c["raw"])
            out.append(_unkeyed_finding(c, ", ".join(_where(x) for x in unplaced if x["raw"] == c["raw"])))
    if len(prefixes) >= 2:
        tables: dict[str, list[dict]] = {}
        for c in cells:
            tables.setdefault(c.get("table") or c["file"], []).append(c)
        for table, tcells in tables.items():
            if all(method_of(c) or prefixes & set(_tokens(c.get("header") or ""))
                   or prefixes & set(_tokens(c.get("label") or "")) for c in tcells):
                continue
            out.append(Finding(
                f"consistency.table_method_ambiguous.{table}", INFO,
                f"the cell check cannot tell methods apart in table at {table}; add a section row naming the "
                f"method or rely on the per-claim audit",
                observed=f"metric keys carry the method prefixes {', '.join(sorted(prefixes))}; no section row, "
                         f"row label or column header names a method for some rows",
                remediation="Add a full-width \\multicolumn row naming the method, such as \"(Heuristic Miner)\", "
                            "above the rows it covers (/ploma:audit-reproducibility checks each claim).",
                group="tables"))
    if dense:
        top = max(d[0] for d in dense)
        out.append(Finding(
            "consistency.table_check_uninformative", INFO,
            f"the per-cell table check is uninformative: the results values cover up to {top * 100:.0f}% of "
            f"the values a cell can display, so almost any cell would match",
            observed="; ".join(f"{c['raw']} ({_where(c)}): {cov * 100:.0f}% of the {space}" for cov, space, c in dense),
            remediation="Narrow pipeline.metric_keys to the reported metrics, or check these cells by hand "
                        "(/ploma:audit-reproducibility Phase 2).", group="tables"))
    return out


def _pin_findings(pins: list[dict], cells: list[dict], root: Path) -> list[Finding]:
    """WARN table_source_unused for a pin no tabular takes, WARN table_source_missing for a pin naming no
    file under root; the cells of a missing pin's table are checked as if unpinned."""
    out: list[Finding] = []
    for pin in pins:
        at = f"{pin['file']}:{pin['line']}"
        if not pin["used"]:
            out.append(Finding(f"consistency.table_source_unused.{at}", WARN,
                               f"source pin {pin['path']} at {at} applies to no tabular",
                               observed="no \\begin{tabular} follows it before the next pin, a table's \\end or the "
                                        "end of the file",
                               remediation="Move the comment above the table's \\begin{table} or \\begin{tabular} "
                                           "(after the previous table's \\end), or remove it.", group="tables"))
        elif not (root / pin["path"]).is_file():
            for c in cells:
                if c["file"] == pin["file"] and c.get("source") == pin["path"]:
                    c["source"] = ""
            out.append(Finding(f"consistency.table_source_missing.{at}", WARN,
                               f"source pin {pin['path']} at {at} names no file",
                               observed=f"{root / pin['path']} does not exist; the table was checked against every "
                                        f"results file",
                               remediation="Give the results file's path relative to the repo root, or remove the "
                                           "comment.", group="tables"))
    return out


def run(main: Path, *, results_dir: Path | None = None, metric_keys: list[str] | None = None,
        tolerances: dict | None = None, passport: Path | None = None, root: Path | None = None) -> ConsistencyReport:
    """The consistency pass; findings cite results files relative to root (default: the main file's folder)."""
    main = Path(main).resolve()
    if not main.is_file():
        raise FileNotFoundError(f"cannot read main file {main}")
    tolerances = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    metric_keys = list(metric_keys or [])
    abstract, intro, rest, cells, names, pins = _scan(main)
    body = intro + rest
    results = load_results(results_dir, metric_keys, root or main.parent) if results_dir else Results()
    findings = _pin_findings(pins, cells, Path(root or main.parent))
    for part, numbers, against, where_text in (
            ("abstract", abstract, body, "the body"),
            ("intro", intro, rest, "the rest of the body")):
        findings += _check_numbers(part, numbers, against, where_text, results, tolerances, metric_keys)

    tables_checked = bool(results.files) and bool(results.values)
    if tables_checked:
        findings += _check_tables(cells, results, metric_keys, tolerances)
    if results.files:
        for key in metric_keys:
            if key not in results.keys_found:
                findings.append(Finding(f"consistency.metric_key_missing.{key}", WARN,
                                        f"metric key {key} appears in no results file",
                                        observed=f"looked in {len(results.files)} results file(s)",
                                        remediation="Re-run the pipeline, or update pipeline.metric_keys.",
                                        group="tables"))
    base = Path(results_dir).resolve() if results_dir else main.parent
    for path, err in results.unreadable:
        findings.append(Finding(f"consistency.results_unreadable.{_rel(path, base)}", WARN,
                                f"results file {path.name} could not be read", observed=err,
                                remediation="Fix or remove the file.", group="tables"))

    passport_info: dict = {}
    if passport is not None:
        pf, passport_info = _passport_findings(Path(passport), main.parent)
        findings.extend(pf)

    return ConsistencyReport(
        main=str(main), findings=findings, verdict=_verdict(findings), abstract_numbers=abstract, intro_numbers=intro,
        body_numbers=len(body), table_cells=cells, results_dir=str(results_dir) if results_dir else None,
        results_files=[_rel(p, main.parent) for p in results.files], tables_checked=tables_checked,
        passport=passport_info, sources=names)


# ---------------------------------------------------------------- report

def _end(text: str) -> str:
    text = text.rstrip()
    return text if text.endswith((".", "?", "!")) else text + "."


def _bullets(findings: list[Finding], empty: str) -> list[str]:
    if not findings:
        return [f"- {empty}"]
    return [f"- **{f.status}** `{f.id}`: {_end(f.summary)}" + (f" Observed: {_end(f.observed)}" if f.observed else "")
            for f in findings]


def render_report(rep: ConsistencyReport, main_rel: str, root: Path | None = None) -> str:
    groups = {g: [f for f in rep.findings if f.group == g] for g in ("abstract", "intro", "tables", "passport")}
    n_fail = sum(f.status == FAIL for f in rep.findings)
    n_warn = sum(f.status == WARN for f in rep.findings)
    out = [f"# Consistency report: {main_rel}", "", "## Summary", "",
           f"- Sources: {len(rep.sources)} file(s) from {main_rel}.",
           f"- Abstract numbers: {len(rep.abstract_numbers)}; introduction numbers: {len(rep.intro_numbers)}; "
           f"body numbers: {rep.body_numbers}; "
           f"table cells: {len(rep.table_cells)}.",
           f"- Results files: {len(rep.results_files)}" + (f" under {_rel(Path(rep.results_dir), root) if root else rep.results_dir}."
                                                   if rep.results_dir else "."),
           f"- Findings: {n_fail} FAIL, {n_warn} WARN.",
           f"- **Verdict: {rep.verdict}.** Consistency is a recommended gate check in v0.1; a FAIL warns and "
           f"never blocks a commit.", "", "## Abstract vs body", ""]
    out += _bullets(groups["abstract"], "Every abstract number appears in the body."
                    if rep.abstract_numbers else "No numbers in the abstract.")
    out += ["", "## Introduction vs body", ""]
    out += _bullets(groups["intro"], "Every introduction number appears in the rest of the body."
                    if rep.intro_numbers else "No introduction numbers checked (none, or fewer than two sections).")
    out += ["", "## Tables vs results", ""]
    if not rep.tables_checked:
        out.append("- Not checked: no results files (pipeline disabled, or pipeline.outputs_dir is empty).")
    else:
        out += _bullets(groups["tables"], f"All {len(rep.table_cells)} numeric table cells match a results value.")
    out += ["", "## Passport", ""]
    if not rep.passport:
        out.append("- No passport. /ploma:audit-reproducibility creates one.")
    elif "claims" not in rep.passport:
        out += _bullets(groups["passport"], "")
    else:
        p = rep.passport
        out.append(f"- {p['claims']} claim(s): PASS {p['pass']}, FAIL {p['fail']}, STALE {p['stale']}, "
                   f"UNVERIFIED {p['unverified']}.")
        out += [line for line in _bullets(groups["passport"], "") if line != "- "]
    out += ["", "## Next steps", ""]
    steps = [f for f in rep.findings if f.status == FAIL] + [f for f in rep.findings if f.status == WARN]
    for i, f in enumerate(steps, 1):
        out.append(f"{i}. {'(Fix)' if f.status == FAIL else '(Review)'} `{f.id}`: {_end(f.remediation)}")
    if not steps:
        out.append("1. No fixes needed.")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- configured run

def configured_inputs(root: Path, cfg: dict) -> dict:
    """run() inputs from ploma.yaml: main file, results dir (pipeline enabled), metric keys, tolerances,
    the passport when it exists, and the slug."""
    root = Path(root).resolve()
    paths = ploma_config.resolve(cfg, root)["_paths"]
    pipe = cfg.get("pipeline") or {}
    main_path = Path(paths["main"]) if paths.get("main") else None
    results_dir = root / pipe["outputs_dir"] if pipe.get("enabled") and pipe.get("outputs_dir") else None
    slug = (cfg.get("document") or {}).get("slug") or (main_path.stem if main_path else "document")
    default = Path(paths["outputs_dir"]) / "passports" / f"{slug}.yaml"
    return {"main": main_path, "results_dir": results_dir, "metric_keys": list(pipe.get("metric_keys") or []),
            "tolerances": pipe.get("tolerances") or {}, "passport": default if default.is_file() else None,
            "slug": slug}


def record_report(root: Path, cfg: dict, rep: ConsistencyReport, main_path: Path, slug: str) -> Path:
    """Write <outputs.dir>/consistency_<slug>.md and the consistency gate entry; return the report path."""
    import gate  # deferred: only recording touches the gate
    root = Path(root).resolve()
    out_dir = Path(ploma_config.resolve(cfg, root)["_paths"]["outputs_dir"])
    report_path = out_dir / f"consistency_{slug}.md"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rep, _rel(Path(main_path), root), root), encoding="utf-8")
    gate.record(root, cfg, "consistency", rep.verdict, _rel(report_path, root),
                fail=sum(f.status == FAIL for f in rep.findings),
                warn=sum(f.status == WARN for f in rep.findings))
    return report_path


def run_recorded(root: Path, cfg: dict) -> tuple[ConsistencyReport, Path]:
    """run() with the configured inputs, then record_report(); what `--root R --record` does."""
    inp = configured_inputs(root, cfg)
    if inp["main"] is None or not inp["main"].is_file():
        raise FileNotFoundError(f"cannot read main file {inp['main'] or '(document.main not set)'}")
    rep = run(inp["main"], results_dir=inp["results_dir"], metric_keys=inp["metric_keys"],
              tolerances=inp["tolerances"], passport=inp["passport"], root=root)
    return rep, record_report(root, cfg, rep, inp["main"], inp["slug"])


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Deterministic text, tables and results consistency pass.")
    parser.add_argument("main", nargs="?", help="main .tex file (default: document.main from ploma.yaml)")
    parser.add_argument("--root", help="repo root holding ploma.yaml")
    parser.add_argument("--results", help="results directory (default: pipeline.outputs_dir when enabled)")
    parser.add_argument("--metric-keys", help="comma-separated metric keys (default: pipeline.metric_keys)")
    parser.add_argument("--passport", help="passport YAML (default: <outputs.dir>/passports/<slug>.yaml)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--record", action="store_true", help="write the report and the consistency gate entry")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    def fail(msg: str) -> int:
        print(json.dumps({"error": msg}) if args.json else f"consistency: {msg}",
              file=sys.stdout if args.json else sys.stderr)
        return 2

    cfg = None
    root = Path(args.root).resolve() if args.root else None
    if root is not None or args.record or not args.main:
        root = root or Path(".").resolve()
        try:
            cfg = ploma_config.load(root)
        except ploma_config.ConfigError as exc:
            return fail(exc.message)
    conf = configured_inputs(root, cfg) if cfg else {}
    main_path = Path(args.main) if args.main else conf.get("main")
    if main_path is None or not main_path.is_file():
        return fail(f"cannot read main file {main_path or '(document.main not set)'}")
    results_dir = Path(args.results) if args.results else conf.get("results_dir")
    if args.metric_keys is not None:
        keys = [k.strip() for k in args.metric_keys.split(",") if k.strip()]
    else:
        keys = conf.get("metric_keys", [])
    tolerances = conf.get("tolerances", {})
    slug = ((cfg or {}).get("document") or {}).get("slug") or main_path.stem
    if args.passport:
        passport: Path | None = Path(args.passport)
    elif cfg and conf["slug"] == slug:
        passport = conf["passport"]
    elif cfg:
        default = Path(ploma_config.resolve(cfg, root)["_paths"]["outputs_dir"]) / "passports" / f"{slug}.yaml"
        passport = default if default.is_file() else None
    else:
        passport = None

    try:
        rep = run(main_path, results_dir=results_dir, metric_keys=keys, tolerances=tolerances, passport=passport,
                  root=root)
    except (OSError, ValueError) as exc:
        return fail(str(exc))

    report_path = None
    if args.record:
        try:
            report_path = record_report(root, cfg, rep, main_path, slug)
        except (OSError, ValueError) as exc:
            return fail(f"cannot record the consistency result: {exc}")

    if args.json:
        data = rep.to_dict()
        data["report"] = str(report_path) if report_path else None
        print(json.dumps(data, indent=2))
    else:
        print(f"consistency: {rep.verdict} ({len(rep.findings)} finding(s))")
        if rep.findings:
            print(render(rep.findings))
        if report_path:
            print(f"report: {report_path}")
    return 1 if rep.verdict == FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
