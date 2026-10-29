#!/usr/bin/env python3
"""Placeholder scan: leftover TODO markers, unresolved references, dummy URLs and filler text.

Usage:
  python3 scripts/placeholders.py [file ...] [--root R] [--json]

With --root and no files, scans document.main, every file it reaches through \\input or \\include,
and the bib files from ploma.yaml. LaTeX comments, macro definitions (\\newcommand and
friends) and the preamble are skipped in .tex files (they never reach the PDF as text), except that
\\today is also found in the preamble; ``??`` counts only outside math.

Rules (id placeholder.<kind>.<file>:<line>):
  todo, xxx, fixme      FAIL  the marker words TODO, XXX, FIXME
  todo_macro            FAIL  \\todo{...}, \\todo[...]{...} or \\TODO
  unresolved_ref        FAIL  ?? (an undefined reference or citation, or a placeholder)
  example_com           FAIL  example.com
  lorem_ipsum           FAIL  lorem ipsum filler
  today                 WARN  \\today (the date changes on every build)

Exit codes: 0 no FAIL, 1 at least one FAIL, 2 usage error or unreadable input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _texmask  # noqa: E402
import bib_check  # noqa: E402
from _findings import FAIL, WARN, Finding, render, worst  # noqa: E402

# (kind, status, pattern, scanned with math blanked)
PATTERNS: list[tuple[str, str, re.Pattern, bool]] = [
    ("todo", FAIL, re.compile(r"(?<![\\\w])TODO(?!\w)"), False),
    ("xxx", FAIL, re.compile(r"(?<!\w)XXX(?!\w)"), False),
    ("fixme", FAIL, re.compile(r"(?<![\\\w])FIXME(?!\w)"), False),
    ("todo_macro", FAIL, re.compile(r"\\todo(?![A-Za-z])\s*(?:\[[^\]]*\])?\s*\{|\\TODO(?![A-Za-z])"), False),
    ("unresolved_ref", FAIL, re.compile(r"\?\?"), True),
    ("example_com", FAIL, re.compile(r"(?<![\w-])example\.com(?![\w-])", re.I), False),
    ("today", WARN, re.compile(r"\\today(?![A-Za-z])"), False),
    ("lorem_ipsum", FAIL, re.compile(r"(?<!\w)lorem\s+ipsum(?!\w)", re.I), False),
]
REMEDIATION = {
    "todo": "Finish or remove the TODO.", "xxx": "Replace the XXX marker.", "fixme": "Fix or remove the FIXME.",
    "todo_macro": "Resolve the note and delete the macro.",
    "unresolved_ref": "Fix the undefined \\ref or \\cite, or replace the placeholder; check the LaTeX log.",
    "example_com": "Replace the dummy URL with the real one.", "lorem_ipsum": "Replace the filler text.",
    "today": "Use a fixed date (\\date{} or the venue's own date field).",
}


def scan(text: str, label: str, *, is_tex: bool = True) -> list[Finding]:
    full = _texmask.strip_comments(text) if is_tex else text
    # Macro definitions (\\newcommand{\\TODO}...) and the preamble are not manuscript text. \\today is the
    # exception: \\date{\\today} in the preamble reaches the PDF through \\maketitle.
    plain = _texmask.mask_definitions(_texmask.mask_before_document(full)) if is_tex else full
    no_math = _texmask.mask_math(plain)
    lines = _texmask.LineIndex(text)
    src_lines = text.split("\n")
    hits: list[tuple[int, Finding]] = []
    for kind, status, regex, outside_math in PATTERNS:
        target = no_math if outside_math else (_texmask.mask_definitions(full) if kind == "today" and is_tex
                                               else plain)
        for m in regex.finditer(target):
            line = lines.line(m.start())
            hits.append((m.start(), Finding(f"placeholder.{kind}.{label}:{line}", status,
                                            f"placeholder {m.group().strip()!r} at {label}:{line}",
                                            observed=src_lines[line - 1].strip()[:120],
                                            remediation=REMEDIATION[kind], group="placeholder")))
    hits.sort(key=lambda h: h[0])
    return [f for _, f in hits]


def run(files: list[Path], *, root: Path | None = None) -> list[Finding]:
    """Findings for every file; labels are paths relative to root when given, else as passed."""
    findings: list[Finding] = []
    for path in files:
        path = Path(path)
        label = path.as_posix()
        if root is not None:
            try:
                label = path.resolve().relative_to(Path(root).resolve()).as_posix()
            except ValueError:
                pass
        text = path.read_text(encoding="utf-8", errors="replace")
        findings += scan(text, label, is_tex=path.suffix.lower() != ".bib")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan manuscript files for leftover placeholders.")
    parser.add_argument("files", nargs="*", help="files to scan (default: the manuscript from ploma.yaml)")
    parser.add_argument("--root", help="repo root holding ploma.yaml (default: .)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    def fail(msg: str) -> int:
        print(json.dumps({"error": msg}) if args.json else f"placeholders: {msg}",
              file=sys.stdout if args.json else sys.stderr)
        return 2

    root = Path(args.root).resolve() if args.root else None
    files = [Path(f) for f in args.files]
    if not files:
        import ploma_config
        root = root or Path(".").resolve()
        try:
            cfg = ploma_config.load(root)
        except ploma_config.ConfigError as exc:
            return fail(exc.message)
        paths = ploma_config.resolve(cfg, root)["_paths"]
        if not paths["main"] or not Path(paths["main"]).is_file():
            return fail(f"cannot read main file {paths['main'] or '(document.main not set)'}")
        files = bib_check.tex_sources(Path(paths["main"]))
        files += [Path(b) for b in paths["bib_files"] if Path(b).is_file()]
    for f in files:
        if not f.is_file():
            return fail(f"cannot read {f}")
    try:
        findings = run(files, root=root)
    except OSError as exc:
        return fail(str(exc))
    verdict = worst(findings)
    if args.json:
        print(json.dumps({"verdict": verdict, "findings": [f.to_dict() for f in findings]}, indent=2))
    else:
        print(f"placeholders: {verdict} ({len(findings)} finding(s))")
        if findings:
            print(render(findings))
    return 1 if any(f.status == FAIL for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
