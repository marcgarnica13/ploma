#!/usr/bin/env python3
"""arXiv source checks: the arxiv_rules entry of a venue profile's submission_checks.

Usage: python3 scripts/arxiv_rules.py [--root R] [--json]

Checks document.main, every file it reaches through \\input or \\include, and the files under
document.root:

  arxiv.pdfoutput                 WARN  pdflatex build without \\pdfoutput=1 in the first 5 lines of the main file
  arxiv.figure_format.<target>    FAIL  an \\includegraphics file that is not .pdf, .png, .jpg or .jpeg
                                        (pdflatex on arXiv reads no other format)
  arxiv.figure_missing.<target>   WARN  an \\includegraphics target with no file (\\graphicspath honoured)
  arxiv.hidden.<path>             WARN  a hidden file or directory under document.root, except .git*
                                        (.git, .gitignore, .gitattributes) and the tool directories
                                        .ploma, .claude, .vscode and .idea
  arxiv.suggestion.<path>         WARN  a *_suggestion.tex draft under document.root (it would be uploaded)
  arxiv.bbl_missing               FAIL  no <main>.bbl and the bibliography is built with biber
                                  WARN  no <main>.bbl; arXiv would have to run BibTeX on the .bib files
  arxiv.today                     WARN  \\today in the source (the date changes when arXiv rebuilds)
  arxiv.comments                  INFO  comment lines, which arXiv publishes with the source

Exit codes: 0 no FAIL, 1 at least one FAIL, 2 usage error or unreadable config or main file.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bib_check  # noqa: E402
import ploma_config  # noqa: E402
from _findings import FAIL, INFO, WARN, Finding, render, worst  # noqa: E402

FIGURE_EXTS = (".pdf", ".png", ".jpg", ".jpeg")
_TRY_EXTS = FIGURE_EXTS + (".eps", ".ps", ".svg", ".gif", ".tif", ".tiff", ".bmp")
_PDFOUTPUT_RE = re.compile(r"\\pdfoutput\s*=\s*1")
_GRAPHICS_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
_GRAPHICSPATH_RE = re.compile(r"\\graphicspath\s*\{((?:\s*\{[^}]*\})+)\s*\}")
_BIB_USED_RE = re.compile(r"\\(?:bibliography|addbibresource)\b")
_TODAY_RE = re.compile(r"\\today(?![A-Za-z])")
PDFOUTPUT_LINES = 5
TOOL_DIRS = {".ploma", ".claude", ".vscode", ".idea"}


def _ignored_hidden(name: str) -> bool:
    return name.startswith(".git") or name in TOOL_DIRS


def _rel(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _figure(base: Path, dirs: list[str], target: str) -> Path | None:
    for d in [""] + dirs:
        cand = base / d / target
        if cand.suffix and cand.is_file():
            return cand
        for ext in _TRY_EXTS:
            p = cand.with_name(cand.name + ext)
            if p.is_file():
                return p
    return None


def run(root: Path) -> list[Finding]:
    root = Path(root).resolve()
    cfg = ploma_config.load(root)
    paths = ploma_config.resolve(cfg, root)["_paths"]
    build = cfg.get("build") or {}
    main = Path(paths["main"]) if paths.get("main") else None
    if main is None or not main.is_file():
        raise ValueError(f"cannot read main file {main or '(document.main not set)'}")
    base = main.parent
    srcs = bib_check.tex_sources(main)
    code = {src: bib_check._code_lines(src) for src in srcs}
    out: list[Finding] = []

    engine = (build.get("engine") or "pdflatex").lower()
    if engine == "pdflatex":
        raw = main.read_text(encoding="utf-8", errors="replace").split("\n")
        at = next((i + 1 for i, line in enumerate(raw) if _PDFOUTPUT_RE.search(bib_check.strip_comment(line))), None)
        if at is None or at > PDFOUTPUT_LINES:
            where = f"found on line {at}" if at else "not found"
            out.append(Finding("arxiv.pdfoutput", WARN,
                               f"\\pdfoutput=1 is not within the first {PDFOUTPUT_LINES} lines of {main.name}",
                               observed=f"{_rel(main, root)}: {where}",
                               remediation=f"Add \\pdfoutput=1 as the first line of {main.name} so arXiv builds "
                                           "with pdflatex.", group="arxiv"))

    dirs: list[str] = []
    for lines in code.values():
        for line in lines:
            for m in _GRAPHICSPATH_RE.finditer(line):
                dirs += [d.strip() for d in re.findall(r"\{([^}]*)\}", m.group(1)) if d.strip()]
    seen: set[str] = set()
    for src, lines in code.items():
        for i, line in enumerate(lines, 1):
            for m in _GRAPHICS_RE.finditer(line):
                target = m.group(1).strip()
                if target in seen:
                    continue
                seen.add(target)
                where = f"{_rel(src, root)}:{i}"
                found = _figure(base, dirs, target)
                if found is None:
                    out.append(Finding(f"arxiv.figure_missing.{target}", WARN, f"figure file for {target} not found",
                                       observed=where, remediation="Add the file to the upload or fix the path.",
                                       group="arxiv"))
                elif found.suffix.lower() not in FIGURE_EXTS:
                    out.append(Finding(f"arxiv.figure_format.{target}", FAIL,
                                       f"figure {_rel(found, root)} is {found.suffix}, which pdflatex cannot include",
                                       observed=where, remediation="Convert it to PDF (vector) or PNG/JPEG (raster).",
                                       group="arxiv"))

    doc_root = Path(paths["root"]) if paths.get("root") else root
    for dirpath, dirnames, filenames in os.walk(doc_root):
        for name in sorted(dirnames + filenames):
            if name.startswith(".") and not _ignored_hidden(name):
                rel = _rel(Path(dirpath) / name, root)
                out.append(Finding(f"arxiv.hidden.{rel}", WARN, f"hidden {'directory' if name in dirnames else 'file'} "
                                   f"{rel}", observed=rel, remediation="Leave it out of the arXiv upload.",
                                   group="arxiv"))
        for name in sorted(filenames):
            if name.endswith("_suggestion.tex"):
                rel = _rel(Path(dirpath) / name, root)
                out.append(Finding(f"arxiv.suggestion.{rel}", WARN, f"draft sibling would be uploaded: {rel}",
                                   observed=rel, remediation="Merge it with /ploma:write --merge or delete it, and "
                                   "leave it out of the arXiv upload.", group="arxiv"))
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]

    bib_used = any(_BIB_USED_RE.search(line) for lines in code.values() for line in lines)
    if bib_used:
        cands = [main.with_suffix(".bbl")]
        if paths.get("build_cwd"):
            extra = Path(paths["build_cwd"]) / (main.stem + ".bbl")
            if extra.resolve() != cands[0].resolve():
                cands.append(extra)
        if not any(p.is_file() for p in cands):
            biber = (build.get("bib_tool") or "").lower() == "biber"
            out.append(Finding("arxiv.bbl_missing", FAIL if biber else WARN, f"no {main.stem}.bbl next to {main.name}",
                               observed=", ".join(_rel(p, root) for p in cands),
                               remediation=(f"Build the paper and upload {main.stem}.bbl; arXiv cannot run biber."
                                            if biber else f"Build the paper and upload {main.stem}.bbl with the "
                                            "source; arXiv's BibTeX run may differ from yours."), group="arxiv"))

    today = [f"{_rel(src, root)}:{i}" for src, lines in code.items() for i, line in enumerate(lines, 1)
             if _TODAY_RE.search(line)]
    if today:
        out.append(Finding("arxiv.today", WARN, "\\today in the source: the date changes whenever arXiv rebuilds",
                           observed=", ".join(today), remediation="Write the date out, or leave \\date{} empty.",
                           group="arxiv"))

    comments = 0
    for src in srcs:
        for line in src.read_text(encoding="utf-8", errors="replace").split("\n"):
            if bib_check.strip_comment(line) != line:
                comments += 1
    if comments:
        out.append(Finding("arxiv.comments", INFO, f"{comments} comment line(s) will be published with the source",
                           observed=f"{len(srcs)} .tex file(s)",
                           remediation="Strip comments before upload (for example with arxiv_latex_cleaner).",
                           group="arxiv"))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="arXiv source checks.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        findings = run(Path(args.root))
    except ploma_config.ConfigError as exc:
        msg = exc.message
    except (OSError, ValueError) as exc:
        msg = str(exc)
    else:
        if args.json:
            print(json.dumps({"verdict": worst(findings), "findings": [f.to_dict() for f in findings]}, indent=2))
        else:
            print(f"arxiv_rules: {worst(findings)} ({len(findings)} finding(s))")
            if findings:
                print(render(findings))
        return 1 if any(f.status == FAIL for f in findings) else 0
    print(json.dumps({"error": msg}) if args.json else f"arxiv_rules: {msg}",
          file=sys.stdout if args.json else sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
