#!/usr/bin/env python3
"""Triage a pdflatex log: errors, undefined citations and references, overfull boxes, rerun hints.

Usage: python3 scripts/latex_log.py <logfile> [--threshold 10] [--json]
Exit codes: 0 no errors, 1 the log holds errors, 2 usage error or unreadable log.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# pdflatex hard-wraps log output at max_print_line (79 characters by default).
WRAP_WIDTH = 79

# A line that starts one of these is a new message, never the continuation of a wrapped line.
_NEW_MESSAGE = re.compile(
    r"^(?:! |l\.\d+ |LaTeX |Package |Class |Overfull |Underfull |\([^)\s]*\) |"
    r"(?:[A-Za-z]:)?[^\s:]*[./][^\s:]*:\d+: )"
)
_FILE_LINE_ERROR = re.compile(r"^((?:[A-Za-z]:)?[^\s:]*[./][^\s:]*):(\d+): (.+)$")
_BANG_ERROR = re.compile(r"^! (.+)$")
_L_MARKER = re.compile(r"^l\.(\d+)\b")
_OVERFULL = re.compile(r"^Overfull \\[hv]box \((\d+(?:\.\d+)?)pt too (?:wide|high)\)\s*(.*)$")
_CITATION = re.compile(r"Citation [`']([^`']+)' on page \S+ undefined")
_REFERENCE = re.compile(r"Reference [`']([^`']+)' on page \S+ undefined")
_RERUN = re.compile(r"Label\(s\) may have changed|Rerun to get|Please \(?re\)?run")
_PACKAGE_WARNING = re.compile(r"^(?:Package|Class) (\S+) Warning: (.+)$")

# How far below a "! ..." error we look for its "l.<n>" marker.
_L_MARKER_WINDOW = 12


@dataclass
class LogReport:
    errors: list[dict] = field(default_factory=list)
    undefined_citations: list[str] = field(default_factory=list)
    undefined_references: list[str] = field(default_factory=list)
    overfull: list[dict] = field(default_factory=list)
    overfull_total: int = 0
    rerun_needed: bool = False
    package_warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ok"] = self.ok
        return d


def unwrap(text: str) -> list[str]:
    """Normalise line endings and rejoin lines pdflatex split at WRAP_WIDTH characters.

    A line of exactly WRAP_WIDTH characters is joined with the next one unless the next is
    empty or visibly starts a new message, so a genuinely 79-character line rarely swallows
    a following error or warning.
    """
    raw = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    while i < len(raw):
        line = raw[i]
        while (len(line) % WRAP_WIDTH == 0 and line and i + 1 < len(raw)
               and raw[i + 1] and not _NEW_MESSAGE.match(raw[i + 1])):
            i += 1
            line += raw[i]
        out.append(line)
        i += 1
    return out


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def parse_log(text: str, overfull_threshold_pt: float = 10.0) -> LogReport:
    lines = unwrap(text)
    report = LogReport()
    for idx, line in enumerate(lines):
        m = _FILE_LINE_ERROR.match(line)
        if m:
            report.errors.append({"file": m.group(1), "line": int(m.group(2)), "message": m.group(3).strip()})
            continue
        m = _BANG_ERROR.match(line)
        if m:
            lineno = None
            for follow in lines[idx + 1: idx + 1 + _L_MARKER_WINDOW]:
                if follow.startswith("! "):
                    break
                lm = _L_MARKER.match(follow)
                if lm:
                    lineno = int(lm.group(1))
                    break
            report.errors.append({"file": None, "line": lineno, "message": m.group(1).strip()})
            continue
        m = _OVERFULL.match(line)
        if m:
            report.overfull_total += 1
            pt = float(m.group(1))
            if pt > overfull_threshold_pt:
                report.overfull.append({"pt": pt, "context": m.group(2).strip()})
            continue
        m = _CITATION.search(line)
        if m:
            _add_unique(report.undefined_citations, m.group(1))
            continue
        m = _REFERENCE.search(line)
        if m:
            _add_unique(report.undefined_references, m.group(1))
            continue
        if _RERUN.search(line):
            report.rerun_needed = True
        m = _PACKAGE_WARNING.match(line)
        if m:
            _add_unique(report.package_warnings, f"{m.group(1)}: {m.group(2).strip()}")
    return report


def render_text(report: LogReport, threshold: float) -> str:
    out = [f"status: {'OK' if report.ok else 'ERRORS'}"]
    for e in report.errors:
        where = f"{e['file'] or '?'}:{e['line'] if e['line'] is not None else '?'}"
        out.append(f"- error {where}: {e['message']}")
    if report.undefined_citations:
        out.append("- undefined citations: " + ", ".join(report.undefined_citations))
    if report.undefined_references:
        out.append("- undefined references: " + ", ".join(report.undefined_references))
    out.append(f"- overfull boxes: {report.overfull_total} total, {len(report.overfull)} above {threshold:g}pt")
    for o in report.overfull:
        out.append(f"  {o['pt']:g}pt {o['context']}")
    if report.rerun_needed:
        out.append("- rerun needed: cross-references may have changed")
    for w in report.package_warnings:
        out.append(f"- package warning: {w}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Triage a pdflatex log file.")
    parser.add_argument("logfile", help="path to the .log file")
    parser.add_argument("--threshold", type=float, default=10.0,
                        help="report overfull boxes wider than this many points (default 10)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        text = Path(args.logfile).read_bytes().decode("utf-8", errors="replace")
    except OSError as exc:
        msg = f"cannot read {args.logfile}: {exc.strerror or exc}"
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(f"latex_log: {msg}", file=sys.stderr)
        return 2
    report = parse_log(text, args.threshold)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_text(report, args.threshold))
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
