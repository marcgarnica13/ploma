#!/usr/bin/env python3
"""Deterministic consistency pass: abstract numbers vs body, table cells vs results, passport claims.

Usage:
  python3 scripts/consistency.py [--root R] [main.tex] [--results D] [--metric-keys a,b]
                                 [--passport P] [--json] [--record]

With --root and no main.tex, paths come from ploma.yaml: document.main, pipeline.outputs_dir (when
pipeline.enabled), pipeline.metric_keys, pipeline.tolerances and the passport at
<outputs.dir>/passports/<document.slug>.yaml when it exists. --record writes the report
<outputs.dir>/consistency_<slug>.md and the "consistency" gate entry (a recommended check in v0.1).

Rules (spec section 7.2):
  consistency.abstract_number_not_in_body.<raw>    FAIL  abstract number absent from the body
  consistency.abstract_number_only_in_results.<raw> WARN  absent from the body, present in results
  consistency.table_cell_not_in_results.<raw>      WARN  table cell matches no results value
  consistency.metric_key_missing.<key>             WARN  a metric key appears in no results file
  consistency.results_unreadable.<file>            WARN  a results file could not be parsed
  consistency.passport.<id>                        FAIL  passport claim with status FAIL or STALE
                                                   INFO  passport claim with status UNVERIFIED
  consistency.passport_invalid                     FAIL  passport missing, unparsable or off schema

Exit codes: 0 verdict PASS or WARN, 1 verdict FAIL, 2 usage error or unreadable input.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass, field
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
        "addtocounter", "begin", "end", "resizebox", "scalebox", "rule", "cmidrule", "cline", "fontsize",
        "linespread", "renewcommand", "newcommand", "providecommand", "definecolor", "rowcolor", "cellcolor",
        "hypersetup", "geometry", "graphicspath", "newcolumntype", "captionsetup", "setcitestyle",
        "addlinespace", "raisebox", "makebox", "parbox")},
    "href": 1, "textcolor": 1, "color": 1, "multicolumn": 2, "multirow": 2,
}
SECTION_COMMANDS = ("part", "chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph")
TABULAR_ENVS = ("tabular", "tabular*", "tabularx", "tabulary", "longtable", "longtable*")

_SECTION_RE = re.compile(r"\\(?:" + "|".join(SECTION_COMMANDS) + r")\*?\s*(?:\[[^\]]*\])?\s*\{")
_ROW_SPACING_RE = re.compile(r"\\\\\*?\s*(\[[^\]]*\])")
_DIM_RE = re.compile(r"(?<![\w.])-?\d*\.?\d+\s*\\(?:linewidth|textwidth|columnwidth|textheight|hsize|vsize|"
                     r"baselineskip|paperwidth|paperheight)\b")
_INDEX_RE = re.compile(r"(?<!\\)[_^]\s*(?:\{[^{}]*\}|\d+)")
_NUM = r"(?:\d{1,3}(?:(?:,|\\,)\d{3})+(?!\d)|\d+(?:\.\d+)?|\.\d+)"
NUM_RE = re.compile(r"(?<![\w.\\])(?<![A-Za-z]-)(?P<sign>-)?(?P<num>" + _NUM + r")(?P<pct>\s*\\?%)?(?!\w)")
CELL_RE = re.compile(r"(?P<sign>-)?(?P<num>" + _NUM + r")(?P<pct>\\?%)?")
_CELL_NOISE_RE = re.compile(
    r"\\(?:toprule|midrule|bottomrule|hline|cmidrule|cline|addlinespace|textbf|textit|textrm|textsf|texttt|"
    r"emph|underline|mathbf|mathrm|boldmath|bfseries|itshape|bf|it|centering|raggedleft|raggedright|"
    r"multicolumn|multirow|rowcolor|cellcolor|textcolor|color|phantom|hphantom|vphantom|noalign|bm)\b\*?")


# ---------------------------------------------------------------- number extraction

def mask_numbers(text: str) -> str:
    """Blank everything in text whose digits are not manuscript numbers (same length as text)."""
    out = _texmask.mask_command_args(text, MASKED_COMMANDS)
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


def _numbers(masked: str, lines: _texmask.LineIndex, file: str | None) -> list[dict]:
    out = []
    for m in NUM_RE.finditer(masked):
        n = _number(m)
        if n is not None:
            n.update(line=lines.line(m.start()), file=file, pos=m.start())
            out.append(n)
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

def _decimals(raw: str) -> int:
    digits = raw.rstrip("%")
    return len(digits.split(".", 1)[1]) if "." in digits else 0


def _tol(tolerances: dict, key: str) -> float:
    value = (tolerances or {}).get(key, DEFAULT_TOLERANCES.get(key))
    if value in (None, "exact"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(DEFAULT_TOLERANCES[key]) if key != "counts" else 0.0


def matches(num: dict, value: float, tolerances: dict) -> bool:
    """Whether a manuscript number agrees with value: counts exactly (or within tolerances.counts),
    decimals within tolerances.metrics, percentages within tolerances.percentages_pp (value as is or
    times 100). value is first rounded to the decimals the manuscript shows."""
    kind = num["kind"]
    if kind == "count":
        return abs(num["value"] - value) <= _tol(tolerances, "counts") + _EPS
    if kind == "percent":
        candidates, tol = (value, value * 100), _tol(tolerances, "percentages_pp")
    else:
        candidates, tol = (value,), _tol(tolerances, "metrics")
    places = _decimals(num["raw"])
    for v in candidates:
        if abs(num["value"] - round(v, places)) <= _EPS or abs(num["value"] - v) <= tol + _EPS:
            return True
    return False


# ---------------------------------------------------------------- results

def _walk_json(data: Any, keys: set[str], values: list[float], found: set[str]) -> None:
    if isinstance(data, dict):
        for k, v in data.items():
            if k in keys and (_is_number(v) or isinstance(v, (list, dict))):
                found.add(k)
            _walk_json(v, keys, values, found)
    elif isinstance(data, list):
        for v in data:
            _walk_json(v, keys, values, found)
    elif _is_number(data):
        values.append(float(data))


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


@dataclass
class Results:
    files: list[Path] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    keys_found: set[str] = field(default_factory=set)
    unreadable: list[tuple[Path, str]] = field(default_factory=list)


def load_results(results_dir: Path, metric_keys: list[str]) -> Results:
    """Every numeric value at any depth of every .json, and every numeric .csv cell, under results_dir."""
    res = Results()
    if results_dir is None or not Path(results_dir).is_dir():
        return res
    keys = set(metric_keys)
    for path in sorted(Path(results_dir).rglob("*")):
        if not path.is_file() or path.suffix.lower() not in (".json", ".csv"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            if path.suffix.lower() == ".json":
                _walk_json(json.loads(text), keys, res.values, res.keys_found)
            else:
                rows = list(csv.reader(text.splitlines()))
                header = rows[0] if rows else []
                for row in rows:
                    for i, cell in enumerate(row):
                        try:
                            res.values.append(float(cell.strip()))
                            if i < len(header) and header[i].strip() in keys:
                                res.keys_found.add(header[i].strip())
                        except ValueError:
                            pass
        except (OSError, UnicodeDecodeError, ValueError, csv.Error) as exc:
            res.unreadable.append((path, str(exc).splitlines()[0] if str(exc) else type(exc).__name__))
            continue
        res.files.append(path)
    res.values = sorted(set(res.values))
    return res


# ---------------------------------------------------------------- manuscript

def _abstract_spans(text: str) -> list[tuple[int, int]]:
    spans = [(c, e) for _, c, e in _texmask.env_spans(text, ("abstract",))]
    for m in re.finditer(r"\\abstract\s*\{", text):
        end = _texmask.group_end(text, m.end() - 1)
        if end > 0:
            spans.append((m.end(), end - 1))
    return spans


def _clean_cell(cell: str) -> str:
    cell = _CELL_NOISE_RE.sub("", cell)
    return re.sub(r"[\s${}~]", "", cell)


def _table_cells(stripped: str, masked: str, lines: _texmask.LineIndex, file: str) -> list[dict]:
    cells = []
    for _, content, end in _texmask.env_spans(stripped, TABULAR_ENVS):
        body = masked[content:end]
        end_tag = body.rfind("\\end")
        body = body[:end_tag] if end_tag >= 0 else body
        offset = content
        for row in re.split(r"(\\\\)", body):
            if row != "\\\\":
                pos = offset
                for cell in re.split(r"(?<!\\)(&)", row):
                    if cell != "&":
                        m = CELL_RE.fullmatch(_clean_cell(cell))
                        n = _number(m) if m else None
                        if n is not None:
                            n.update(line=lines.line(pos + len(cell) - len(cell.lstrip())), file=file)
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
    table_cells: list[dict] = field(default_factory=list)
    results_dir: str | None = None
    results_files: list[str] = field(default_factory=list)
    tables_checked: bool = False
    passport: dict = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"main": self.main, "verdict": self.verdict, "findings": [f.to_dict() for f in self.findings],
                "abstract_numbers": self.abstract_numbers, "body_numbers": self.body_numbers,
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


def _scan(main: Path) -> tuple[list[dict], list[dict], list[dict], list[str]]:
    """(abstract numbers, body numbers, table cells, source names) across main and its inputs."""
    main = Path(main).resolve()
    base = main.parent
    abstract: list[dict] = []
    body: list[dict] = []
    cells: list[dict] = []
    names: list[str] = []
    for src in bib_check.tex_sources(main):
        name = _rel(src, base)
        names.append(name)
        raw = src.read_text(encoding="utf-8", errors="replace")
        stripped = _texmask.strip_comments(raw)
        if src == main:
            stripped = _texmask.mask_before_document(stripped)
        masked = mask_numbers(stripped)
        lines = _texmask.LineIndex(stripped)
        spans = _abstract_spans(stripped)
        for n in _numbers(masked, lines, name):
            inside = any(s <= n["pos"] < e for s, e in spans)
            del n["pos"]
            (abstract if inside else body).append(n)
        cells.extend(_table_cells(stripped, masked, lines, name))
    return abstract, body, cells, names


# ---------------------------------------------------------------- passport

def _passport_findings(path: Path) -> tuple[list[Finding], dict]:
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
    errors = [f.summary for f in problems if f.status == FAIL]
    if errors:
        return invalid("does not match the schema", "; ".join(errors))
    claims = data.get("claims") or []
    counts = {s: sum(1 for c in claims if c.get("status") == s) for s in ("PASS", "FAIL", "STALE", "UNVERIFIED")}
    out: list[Finding] = []
    for c in claims:
        status = c.get("status")
        where = f"{c.get('location') or 'no location'}; claim: {c.get('claim')}"
        if c.get("notes"):
            where += f"; notes: {str(c['notes']).strip()}"
        if status in ("FAIL", "STALE"):
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


def run(main: Path, *, results_dir: Path | None = None, metric_keys: list[str] | None = None,
        tolerances: dict | None = None, passport: Path | None = None) -> ConsistencyReport:
    main = Path(main).resolve()
    if not main.is_file():
        raise FileNotFoundError(f"cannot read main file {main}")
    tolerances = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    metric_keys = list(metric_keys or [])
    abstract, body, cells, names = _scan(main)
    results = load_results(results_dir, metric_keys) if results_dir else Results()
    findings: list[Finding] = []

    seen: set[str] = set()
    for a in abstract:
        if a["raw"] in seen:
            continue
        if any(matches(a, b["value"], tolerances) for b in body):
            continue
        seen.add(a["raw"])
        if any(matches(a, v, tolerances) for v in results.values):
            findings.append(Finding(f"consistency.abstract_number_only_in_results.{a['raw']}", WARN,
                                    f"abstract number {a['raw']} appears in a results file but not in the body",
                                    observed=f"{_where(a)}; looked in the body ({len(body)} numbers) and results",
                                    remediation="State the number in the body where the result is reported.",
                                    group="abstract"))
        else:
            findings.append(Finding(f"consistency.abstract_number_not_in_body.{a['raw']}", FAIL,
                                    f"abstract number {a['raw']} does not appear in the body",
                                    observed=f"{_where(a)}; looked in the body ({len(body)} numbers, tables and "
                                             f"captions included)" + (" and results" if results.files else ""),
                                    remediation="Correct the abstract, or report the number in the body.",
                                    group="abstract"))

    tables_checked = bool(results.files) and bool(results.values)
    if tables_checked:
        missed: dict[str, list[dict]] = {}
        for c in cells:
            if not any(matches(c, v, tolerances) for v in results.values):
                missed.setdefault(c["raw"], []).append(c)
        for raw, where in missed.items():
            findings.append(Finding(f"consistency.table_cell_not_in_results.{raw}", WARN,
                                    f"table cell {raw} matches no value in the results files",
                                    observed=", ".join(_where(c) for c in where)
                                    + f"; looked in {len(results.files)} results file(s)",
                                    remediation="Check the cell against the pipeline outputs; re-run the pipeline "
                                                "or correct the table.", group="tables"))
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
        pf, passport_info = _passport_findings(Path(passport))
        findings.extend(pf)

    return ConsistencyReport(
        main=str(main), findings=findings, verdict=_verdict(findings), abstract_numbers=abstract,
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
    groups = {g: [f for f in rep.findings if f.group == g] for g in ("abstract", "tables", "passport")}
    n_fail = sum(f.status == FAIL for f in rep.findings)
    n_warn = sum(f.status == WARN for f in rep.findings)
    out = [f"# Consistency report: {main_rel}", "", "## Summary", "",
           f"- Sources: {len(rep.sources)} file(s) from {main_rel}.",
           f"- Abstract numbers: {len(rep.abstract_numbers)}; body numbers: {rep.body_numbers}; "
           f"table cells: {len(rep.table_cells)}.",
           f"- Results files: {len(rep.results_files)}" + (f" under {_rel(Path(rep.results_dir), root) if root else rep.results_dir}."
                                                   if rep.results_dir else "."),
           f"- Findings: {n_fail} FAIL, {n_warn} WARN.",
           f"- **Verdict: {rep.verdict}.** Consistency is a recommended gate check in v0.1; a FAIL warns and "
           f"never blocks a commit.", "", "## Abstract vs body", ""]
    out += _bullets(groups["abstract"], "Every abstract number appears in the body."
                    if rep.abstract_numbers else "No numbers in the abstract.")
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
    paths = ploma_config.resolve(cfg, root)["_paths"] if cfg else {}
    pipe = (cfg or {}).get("pipeline") or {}

    main_path = Path(args.main) if args.main else (Path(paths["main"]) if paths.get("main") else None)
    if main_path is None or not main_path.is_file():
        return fail(f"cannot read main file {main_path or '(document.main not set)'}")
    if args.results:
        results_dir: Path | None = Path(args.results)
    elif cfg and pipe.get("enabled") and pipe.get("outputs_dir"):
        results_dir = root / pipe["outputs_dir"]
    else:
        results_dir = None
    if args.metric_keys is not None:
        keys = [k.strip() for k in args.metric_keys.split(",") if k.strip()]
    else:
        keys = list(pipe.get("metric_keys") or []) if cfg else []
    tolerances = pipe.get("tolerances") or {} if cfg else {}
    slug = ((cfg or {}).get("document") or {}).get("slug") or main_path.stem
    if args.passport:
        passport: Path | None = Path(args.passport)
    elif cfg:
        default = Path(paths["outputs_dir"]) / "passports" / f"{slug}.yaml"
        passport = default if default.is_file() else None
    else:
        passport = None

    try:
        rep = run(main_path, results_dir=results_dir, metric_keys=keys, tolerances=tolerances, passport=passport)
    except (OSError, ValueError) as exc:
        return fail(str(exc))

    report_path = None
    if args.record:
        import gate  # deferred: only --record touches the gate
        out_dir = Path(paths["outputs_dir"])
        report_path = out_dir / f"consistency_{slug}.md"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_report(rep, _rel(main_path, root), root), encoding="utf-8")
            gate.record(root, cfg, "consistency", rep.verdict, _rel(report_path, root),
                        fail=sum(f.status == FAIL for f in rep.findings),
                        warn=sum(f.status == WARN for f in rep.findings))
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
