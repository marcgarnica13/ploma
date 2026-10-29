#!/usr/bin/env python3
"""Bibliography audit: structural checks, and with --semantic existence checks against citation APIs.

Usage: python3 scripts/validate_bib.py [--root R] [--semantic] [--skip-doi] [--mailto X]
       [--openalex-key K] [--s2-key K] [--json]

Structural: cite keys against entries in every resolved bib file, near misses, duplicates, unused
entries, natbib/biblatex mixing (scripts/bib_check.py). Semantic adds a lookup of every cited entry
(scripts/cite_lookup.py, at most limits.doi_lookups_per_run network lookups, and none after a time
budget of 480 s so the run ends inside a 10-minute Bash timeout); --skip-doi leaves the lookups out.
Each lookup gives bib.lookup.<status>.<key>; an entry found by title whose DOI Crossref and DataCite
both answer 404 for also gets bib.doi_unresolved.<key> WARN (the printed DOI will be dead).
Writes <outputs.dir>/bib_audit_<structural|semantic>.md, records the "bib" gate entry (with mode and bib_sha,
the hash of the resolved .bib files) and a state event. Only --semantic without --skip-doi uses the network. Lookup cache: the plugin
data dir when CLAUDE_PLUGIN_DATA is set, else <root>/.ploma/cite_lookup.json.

Exit codes: 0 verdict PASS, 1 verdict FAIL, 2 usage error, unreadable ploma.yaml or main file.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bib_check  # noqa: E402
import cite_lookup  # noqa: E402
import gate  # noqa: E402
import ploma_config  # noqa: E402
import state  # noqa: E402
from _findings import FAIL, INFO, WARN, Finding  # noqa: E402

SEVERITY = {FAIL: "Critical", WARN: "Medium", INFO: "Low"}
# Summary rows: (label, finding id prefixes).
ROWS = [
    ("Structural (missing / typos)", ("bib.missing.", "bib.file_missing.", "bib.near_miss.")),
    ("Citation drift (duplicates)", ("bib.duplicate_",)),
    ("DOI verification", ("bib.lookup.", "bib.no_doi.", "bib.doi_unresolved.")),
    ("Style consistency", ("bib.cite_style_mix",)),
    ("Unused entries", ("bib.unused.",)),
]
LOOKUP_STATUS = {"missing": FAIL, "mismatch": FAIL, "partial": WARN, "not_indexed": WARN, "unreachable": WARN,
                 "skipped": INFO}
LOOKUP_FIX = {
    "missing": "no source knows this work: check the title and DOI against the publisher page, then fix or remove the entry",
    "mismatch": "the DOI resolves to a different work: correct the DOI, or the title, authors and year",
    "not_indexed": "not found in Crossref or OpenAlex; confirm it exists",  # R168
    "partial": "the work exists but a field disagrees: compare title, first author, year and DOI with the record",
    "unreachable": "no source answered; nothing was concluded: run /ploma:validate-bib --semantic again later",
    "skipped": "not looked up in this run; it is checked on the next run (cached results are free)",
}


class UsageError(Exception):
    """Bad input the user must fix (CLI exit 2)."""


class MainFileError(UsageError):
    pass


def lookup_cap(cfg: dict) -> int:
    """limits.doi_lookups_per_run: absent or null means 50; 0 means no lookups; anything else must be an int >= 0."""
    value = (cfg.get("limits") or {}).get("doi_lookups_per_run")
    if value is None:
        return 50
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise UsageError(f"limits.doi_lookups_per_run must be a whole number >= 0, got {value!r}")
    return value


def default_cache(root: Path) -> Path:
    """The plugin data cache when CLAUDE_PLUGIN_DATA is set, else <root>/.ploma/cite_lookup.json (R86)."""
    if os.environ.get("CLAUDE_PLUGIN_DATA"):
        return cite_lookup.default_cache_path()
    return Path(root) / ".ploma" / "cite_lookup.json"


@dataclass
class BibReport:
    mode: str
    findings: list[Finding]
    lookups: list[cite_lookup.LookupResult]
    verdict: str
    report_path: Path
    bib_files: list[str] = field(default_factory=list)
    entries: int = 0
    cited: int = 0
    skip_doi: bool = False

    def to_dict(self) -> dict:
        return {"mode": self.mode, "verdict": self.verdict, "report_path": str(self.report_path),
                "bib_files": self.bib_files, "entries": self.entries, "cited": self.cited,
                "skip_doi": self.skip_doi, "findings": [f.to_dict() for f in self.findings],
                "lookups": [r.to_dict() for r in self.lookups]}


# ---------------------------------------------------------------- semantic part

def _cited_entries(entries: list[bib_check.Entry], cited: dict[str, list]) -> list[bib_check.Entry]:
    """First entry per key, cited ones only (every entry under \\nocite{*}), in citation order."""
    first: dict[str, bib_check.Entry] = {}
    for e in entries:
        first.setdefault(e.key, e)
    if "*" in cited:
        return list(first.values())
    return [first[k] for k in cited if k in first]


def _lookup_findings(results: list[cite_lookup.LookupResult], cited: dict[str, list], root: Path,
                     dois: dict[str, str] | None = None) -> list[Finding]:
    """One bib.lookup.<status>.<key> finding per result, plus bib.doi_unresolved.<key> WARN (D14) when the
    entry's DOI is unknown to Crossref and DataCite although the work was found by title."""
    out = []
    for r in results:
        status = LOOKUP_STATUS.get(r.status)
        if status is None:
            continue
        where = cited.get(r.key) or []
        observed = r.evidence or r.status
        if where:
            observed += f"; cited at {_rel(where[0][0], root)}:{where[0][1]}"
        summary = f"{r.key}: lookup {r.status}"
        if r.status == "not_indexed":
            summary = f"{r.key}: " + r.evidence.split(";", 1)[0]
        out.append(Finding(f"bib.lookup.{r.status}.{r.key}", status, summary,
                           observed=observed, remediation=LOOKUP_FIX[r.status], group="bib"))
        if getattr(r, "doi_unresolved", False):
            out.append(Finding(f"bib.doi_unresolved.{r.key}", WARN,
                               f"{r.key}: DOI {(dois or {}).get(r.key) or r.doi} does not resolve on Crossref or "
                               f"DataCite; the printed DOI will be dead",
                               observed=observed + (f"; the record found by title has DOI {r.doi}"
                                                    if r.doi and r.doi != (dois or {}).get(r.key) else ""),
                               remediation="Copy the DOI from the publisher page (the work itself was found by "
                                           "title), or remove the doi field.", group="bib"))
    return out


# ---------------------------------------------------------------- report

def _rel(path: Any, root: Path) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(root).as_posix()
    except ValueError:
        return str(p)


def _cell(text: str) -> str:
    return cite_lookup.plain_spaces(text).replace("|", "\\|").replace("\n", " ")


def _end(text: str) -> str:
    text = text.rstrip()
    return text if text.endswith((".", "?", "!")) else text + "."


def _in(f: Finding, prefixes: tuple[str, ...]) -> bool:
    return f.id.startswith(prefixes)


def _summary_table(findings: list[Finding], rep: BibReport) -> list[str]:
    lines = ["| Check | Critical | Medium | Low |", "|---|---|---|---|"]
    for label, prefixes in ROWS:
        group = [f for f in findings if _in(f, prefixes)]
        counts = {sev: sum(1 for f in group if SEVERITY.get(f.status) == sev) for sev in SEVERITY.values()}
        if label == "DOI verification" and rep.mode == "structural":
            lines.append(f"| {label} | - | - | - (not run; use --semantic) |")
        elif label == "DOI verification" and rep.skip_doi:
            lines.append(f"| {label} | - | - | - (skipped with --skip-doi) |")
        elif label == "Unused entries":
            lines.append(f"| {label} | - | - | {counts['Low']} (informational) |")
        else:
            lines.append(f"| {label} | {counts['Critical']} | {counts['Medium']} | {counts['Low']} |")
    return lines


def _bullets(findings: list[Finding], empty: str) -> list[str]:
    if not findings:
        return [f"- {empty}"]
    out = []
    for f in findings:
        line = f"- **{f.status}** `{f.id}`: {_end(cite_lookup.plain_spaces(f.summary))}"
        if f.observed:
            line += f" Observed: {_end(cite_lookup.plain_spaces(f.observed))}"
        if f.remediation and f.status != INFO:
            line += f" Fix: {_end(f.remediation)}"
        out.append(line)
    return out


def _render(rep: BibReport, root: Path, main_rel: str, n_sources: int) -> str:
    f_all = rep.findings
    title = "Semantic" if rep.mode == "semantic" else "Structural"
    n_fail = sum(f.status == FAIL for f in f_all)
    n_warn = sum(f.status == WARN for f in f_all)
    out = [f"# Bibliography {title} Audit", "",
           f"**Date:** {datetime.date.today().isoformat()}",
           f"**Bibliography:** {', '.join(rep.bib_files) or 'none found'} ({rep.entries} entries)",
           f"**Files scanned:** {main_rel} and {n_sources - 1} included file(s) ({rep.cited} unique cited keys)", "",
           "## Summary", ""]
    out += _summary_table(f_all, rep)
    out.append("")
    if rep.verdict == "PASS":
        tail = f" {n_warn} warning(s) to review." if n_warn else " No missing citations, no unresolved problems."
        out.append(f"**Verdict: PASS.**{tail}")
    else:
        out.append(f"**Verdict: FAIL.** {n_fail} blocking finding(s); the fixes are under Next steps.")

    def pick(prefixes: tuple[str, ...]) -> list[Finding]:
        return [f for f in f_all if _in(f, prefixes)]

    out += ["", "## Structural", ""]
    out += _bullets(pick(("bib.missing.", "bib.file_missing.", "bib.near_miss.")),
                    "Missing entries (cited, absent from the bib files): none; every cited key resolves.")
    unused = pick(("bib.unused.",))
    if unused:
        keys = ", ".join(f"`{f.id[len('bib.unused.'):]}`" for f in unused)
        out.append(f"- Unused entries: {len(unused)} (informational; never cited): {keys}.")
    out += ["", "## Citation drift", ""]
    out += _bullets(pick(("bib.duplicate_",)), "Duplicate keys, DOIs and titles: none.")
    out += ["", "## DOI verification", ""]
    if rep.mode == "structural":
        out.append("- Not run in structural mode. Run /ploma:validate-bib --semantic to check that each cited entry exists.")
    elif rep.skip_doi:
        out.append("- Skipped (--skip-doi): no lookups were made.")
    else:
        verified = sum(r.status == "verified" for r in rep.lookups)
        out.append(f"- {verified} of {len(rep.lookups)} cited entries verified.")
        timed_out = sum(r.status == "skipped" and r.evidence == "time budget reached" for r in rep.lookups)
        if timed_out:
            out.append(f"- {timed_out} cited entries skipped (time budget reached); run /ploma:validate-bib --semantic "
                       f"again to check them (results already found are cached).")
        capped = sum(r.status == "skipped" and r.evidence.startswith("over the lookup cap") for r in rep.lookups)
        if capped:
            out.append(f"- {capped} cited entries skipped (over the lookup cap); they are checked on the next run.")
        no_doi = pick(("bib.no_doi.",))
        if no_doi:
            keys = ", ".join(f"`{f.id[len('bib.no_doi.'):]}`" for f in no_doi)
            out.append(f"- {len(no_doi)} cited entries carry no DOI (Low; a DOI is optional): {keys}.")
        out += _bullets(pick(("bib.lookup.", "bib.doi_unresolved.")), "No lookup problems.")
        out += ["", "| Key | Status | Source | Evidence |", "|---|---|---|---|"]
        for r in rep.lookups:
            out.append(f"| {_cell(r.key)} | {r.status} | {r.source or '-'} | {_cell(r.evidence) or '-'} |")
    out += ["", "## Style consistency", ""]
    out += _bullets(pick(("bib.cite_style_mix",)), "Citation commands come from one package; no natbib and biblatex mix.")
    out += ["", "## Next steps", ""]
    steps = [f for f in f_all if f.status == FAIL] + [f for f in f_all if f.status == WARN]
    n = 0
    for f in steps:
        n += 1
        out.append(f"{n}. {'(Required)' if f.status == FAIL else '(Review)'} `{f.id}`: {_end(f.remediation)}")
    if rep.mode == "structural" and rep.verdict == "PASS":
        n += 1
        out.append(f"{n}. (Optional) Run /ploma:validate-bib --semantic to check that every cited entry exists.")
    if unused:
        n += 1
        out.append(f"{n}. (Optional) Prune the {len(unused)} unused entries for a tidier bib file.")
    if not n:
        out.append("1. No required fixes.")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- run

def _bib_sha(bib_files: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for b in bib_files:
        digest.update(_rel(b, root).encode("utf-8") + b"\0")
        try:
            digest.update(b.read_bytes() + b"\0")
        except OSError:
            digest.update(b"<missing>\0")
    return digest.hexdigest()


def bib_sha(root: Path, cfg: dict) -> str:
    """sha256 over the resolved .bib files' paths and bytes (missing files hash as missing); the
    commit gate compares it with the one a semantic run recorded (Ruling R156)."""
    root = Path(root).resolve()
    paths = ploma_config.resolve(cfg, root)["_paths"]
    main = Path(paths["main"]) if paths["main"] else None
    if main is None or not main.is_file():
        raise MainFileError(f"cannot read main file {paths['main'] or '(document.main not set)'}")
    return _bib_sha(bib_check.resolve_bib_files(main, [Path(b) for b in paths["bib_files"]]), root)


def run(root: Path, cfg: dict, *, semantic: bool, skip_doi: bool = False, mailto: str = "",
        keys: dict | None = None, fetch: cite_lookup.Fetch | None = None, cache_path: Path | None = None,
        delay_s: float = 0.5, time_budget_s: float = cite_lookup.TIME_BUDGET_S,
        clock: Any = None) -> BibReport:
    root = Path(root).resolve()
    cap = lookup_cap(cfg)
    paths = ploma_config.resolve(cfg, root)["_paths"]
    main = Path(paths["main"]) if paths["main"] else None
    if main is None or not main.is_file():
        raise MainFileError(f"cannot read main file {paths['main'] or '(document.main not set)'}")
    declared = [Path(b) for b in paths["bib_files"]]
    findings = bib_check.check(main, declared)

    bib_files = bib_check.resolve_bib_files(main, declared)
    entries: list[bib_check.Entry] = []
    for b in bib_files:
        if b.is_file():
            try:
                entries.extend(bib_check.parse_bib(b.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                pass
    sources = bib_check.tex_sources(main)
    cited = bib_check.cite_keys(sources)

    mode = "semantic" if semantic else "structural"
    lookups: list[cite_lookup.LookupResult] = []
    if semantic:
        targets = _cited_entries(entries, cited)
        for e in targets:
            if not bib_check._norm_doi(e.fields.get("doi", "")):
                findings.append(Finding(f"bib.no_doi.{e.key}", INFO, f"{e.key} has no DOI",
                                        remediation="add the DOI when the work has one", group="bib"))
        if not skip_doi:
            lookups = cite_lookup.run(targets, max_lookups=cap, delay_s=delay_s,
                                      cache_path=cache_path or default_cache(root),
                                      mailto=mailto, keys=keys or {}, fetch=fetch,
                                      time_budget_s=time_budget_s,
                                      **({"clock": clock} if clock is not None else {}))
            dois = {e.key: bib_check._norm_doi(e.fields.get("doi", "")) for e in targets}
            findings.extend(_lookup_findings(lookups, cited, root, dois))

    verdict = "FAIL" if any(f.status == FAIL for f in findings) else "PASS"
    out_dir = Path(paths["outputs_dir"])
    report_path = out_dir / f"bib_audit_{mode}.md"
    rep = BibReport(mode=mode, findings=findings, lookups=lookups, verdict=verdict, report_path=report_path,
                    bib_files=[_rel(b, root) for b in bib_files], entries=len(entries),
                    cited=len([k for k in cited if k != "*"]), skip_doi=bool(semantic and skip_doi))
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render(rep, root, _rel(main, root), len(sources)), encoding="utf-8")

    artifact = _rel(report_path, root)
    extras = {"mode": mode, "fail": sum(f.status == FAIL for f in findings),
              "warn": sum(f.status == WARN for f in findings)}
    gate.record(root, cfg, "bib", verdict, artifact, bib_sha=_bib_sha(bib_files, root), **extras)
    state.record(root, cfg, "validate-bib", verdict, artifact, **extras)
    return rep


def _option(value: str, *env_names: str) -> str:
    """A CLI value, or the first set environment variable; an unsubstituted ${...} placeholder counts as unset."""
    for v in (value, *(os.environ.get(n, "") for n in env_names)):
        v = (v or "").strip()
        if v and not v.startswith("${"):
            return v
    return ""


def _text(rep: BibReport) -> str:
    text = rep.report_path.read_text(encoding="utf-8")
    table = text.split("## Summary", 1)[1].split("\n## ", 1)[0].strip()
    lines = [table, "", f"report: {rep.report_path}"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Structural and semantic bibliography audit.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: .)")
    parser.add_argument("--semantic", action="store_true", help="also check that cited entries exist (network)")
    parser.add_argument("--skip-doi", action="store_true", help="with --semantic, make no lookups")
    parser.add_argument("--mailto", default="", help="contact address for the Crossref and OpenAlex polite pools")
    parser.add_argument("--openalex-key", default="", help="OpenAlex API key (default: $OPENALEX_API_KEY)")
    parser.add_argument("--s2-key", default="", help="Semantic Scholar API key (default: $SEMANTIC_SCHOLAR_API_KEY)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    def fail(msg: str) -> int:
        print(json.dumps({"error": msg}) if args.json else f"validate_bib: {msg}",
              file=sys.stdout if args.json else sys.stderr)
        return 2

    root = Path(args.root)
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        return fail(exc.message)
    keys = {k: v for k, v in (
        ("openalex", _option(args.openalex_key, "CLAUDE_PLUGIN_OPTION_OPENALEX_API_KEY", "OPENALEX_API_KEY")),
        ("semantic_scholar", _option(args.s2_key, "CLAUDE_PLUGIN_OPTION_SEMANTIC_SCHOLAR_API_KEY",
                                     "SEMANTIC_SCHOLAR_API_KEY"))) if v}
    mailto = _option(args.mailto, "CLAUDE_PLUGIN_OPTION_CROSSREF_MAILTO")
    try:
        rep = run(root, cfg, semantic=args.semantic, skip_doi=args.skip_doi, mailto=mailto, keys=keys)
    except UsageError as exc:
        return fail(str(exc))
    except (OSError, ValueError) as exc:
        return fail(f"cannot record the bib result: {exc}")
    print(json.dumps(rep.to_dict(), indent=2) if args.json else _text(rep))
    return 0 if rep.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
