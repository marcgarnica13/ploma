#!/usr/bin/env python3
"""Build the PDF, triage the log, check pages against the budget, record the compile gate entry.

Usage: python3 scripts/compile.py [--root R] [--clean] [--json]

Runs build.command through the shell in build.cwd when set (the user's own command, e.g. make);
otherwise latexmk with the engine flag from build.engine. The log at build.log is parsed even when
the build fails. Writes <outputs.dir>/compile_<slug>.md, records the "compile" gate entry and a
state event.

Exit codes: 0 PASS, 1 FAIL (build error, log errors, undefined citations or references, over budget,
missing log or PDF), 2 usage error or unreadable ploma.yaml.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gate  # noqa: E402
import latex_log  # noqa: E402
import pdf_pages  # noqa: E402
import ploma_config  # noqa: E402
import state  # noqa: E402

TIMEOUT_S = 600
TAIL_LINES = 40
ENGINE_FLAGS = {"pdflatex": "-pdf", "xelatex": "-pdfxe", "lualatex": "-pdflua"}
MAKEFILES = ("GNUmakefile", "makefile", "Makefile")
_CLEAN_TARGET = re.compile(r"^clean\s*:", re.M)
# "make: pdflatex: No such file or directory", "sh: 1: latexmk: not found", "bash: x: command not found"
_MISSING_TOOL = re.compile(r"^(?:make(?:\[\d+\])?: |(?:/bin/)?(?:ba|da)?sh: (?:line )?\d*:? ?)([\w.+-]+): "
                           r"(?:No such file or directory|not found|command not found)\s*$", re.M)
_REFS_HEADING = re.compile(r"^\s*(?:\d+\.?\s+)?(?:references|bibliography)\s*$", re.I | re.M)

_default_runner: Callable[..., Any] = subprocess.run


@dataclass
class CompileReport:
    ok: bool
    status: str
    command: str
    cwd: str
    returncode: int | None
    log: latex_log.LogReport
    pages: int | None
    budget: dict
    report_path: Path
    duration_s: float
    output_tail: str = ""
    build_error: str = ""
    notes: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["log"] = self.log.to_dict()
        d["report_path"] = str(self.report_path)
        return d


# ---------------------------------------------------------------- commands

def build_command(cfg: dict, paths: dict) -> tuple[str | list[str], bool]:
    """(command, use_shell): build.command verbatim through the shell, else latexmk."""
    command = (cfg.get("build") or {}).get("command")
    if isinstance(command, str) and command.strip():
        return command, True
    engine = (cfg.get("build") or {}).get("engine") or "pdflatex"
    flag = ENGINE_FLAGS.get(engine, "-pdf")
    main = os.path.relpath(paths["main"], paths["build_cwd"])
    return ["latexmk", flag, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", main], False


def _uses_make(cfg: dict, cwd: Path) -> bool:
    command = (cfg.get("build") or {}).get("command")
    if not isinstance(command, str) or not command.strip():
        return False
    try:
        first = shlex.split(command)[0]
    except (ValueError, IndexError):
        return False
    if Path(first).name not in ("make", "gmake"):
        return False
    for name in MAKEFILES:
        p = cwd / name
        if p.is_file():
            try:
                return bool(_CLEAN_TARGET.search(p.read_text(encoding="utf-8", errors="replace")))
            except OSError:
                return False
    return False


def clean_command(cfg: dict, paths: dict) -> tuple[str | list[str], bool]:
    if _uses_make(cfg, Path(paths["build_cwd"])):
        return "make clean", True
    return ["latexmk", "-c", os.path.relpath(paths["main"], paths["build_cwd"])], False


def _tool_name(cmd: str | list[str]) -> str:
    if isinstance(cmd, list):
        return cmd[0]
    try:
        return shlex.split(cmd)[0]
    except (ValueError, IndexError):
        return cmd


def _show(cmd: str | list[str]) -> str:
    return cmd if isinstance(cmd, str) else " ".join(shlex.quote(c) for c in cmd)


def _tail(*texts: Any) -> str:
    lines: list[str] = []
    for t in texts:
        if isinstance(t, bytes):
            t = t.decode("utf-8", errors="replace")
        if isinstance(t, str) and t:
            lines.extend(t.splitlines())
    return "\n".join(lines[-TAIL_LINES:])


def _execute(runner: Callable[..., Any], cmd: str | list[str], shell: bool, cwd: str) -> tuple[int | None, str, str]:
    """(returncode, output tail, error message); never raises for a missing tool or a timeout."""
    try:
        res = runner(cmd, cwd=cwd, shell=shell, capture_output=True, text=True, timeout=TIMEOUT_S)
    except FileNotFoundError:
        return None, "", f"build tool not found: {_tool_name(cmd)}"
    except subprocess.TimeoutExpired as exc:
        return None, _tail(exc.stdout, exc.stderr), f"build timed out after {TIMEOUT_S} s"
    except OSError as exc:
        return None, "", f"could not run {_tool_name(cmd)}: {exc.strerror or exc}"
    tail = _tail(res.stdout, res.stderr)
    if res.returncode:
        m = _MISSING_TOOL.search(tail)
        if m:
            return res.returncode, tail, f"build tool not found: {m.group(1)}"
        if res.returncode == 127:
            return 127, tail, f"build tool not found: {_tool_name(cmd)}"
    return res.returncode, tail, ""


# ---------------------------------------------------------------- pages

def _body_pages(pdf: Path, total: int) -> tuple[int, str]:
    """Pages up to and including the page where the references heading starts; total when not found."""
    if not pdf_pages._which("pdftotext"):
        return total, "references not located (pdftotext not found); total pages compared"
    try:
        text = pdf_pages._run(["pdftotext", "-layout", str(pdf), "-"])
    except (OSError, subprocess.SubprocessError):
        return total, "references not located (pdftotext failed); total pages compared"
    found = [i for i, page in enumerate(text.split("\f"), 1) if _REFS_HEADING.search(page)]
    if not found:
        return total, "references heading not found; total pages compared"
    return found[-1], f"references start on page {found[-1]}; pages 1 to {found[-1]} compared"


def _pages(cfg: dict, pdf: Path, started: float, root: Path) -> tuple[int | None, dict, list[str]]:
    notes: list[str] = []
    venue = cfg.get("venue") or {}
    budget = venue.get("page_budget")
    pages, how = pdf_pages.page_count(pdf) if pdf.is_file() else (None, f"PDF not found at {_rel(pdf, root)}")
    if pages is None:
        return None, {"pages": None, "budget": budget, "over_by": None, "status": "SKIP", "reason": how}, notes
    try:
        if pdf.stat().st_mtime < started - 1:
            notes.append(f"the PDF at {pdf.name} is older than this build (left from a previous run)")
    except OSError:
        pass
    counted = pages
    if budget is not None and not venue.get("page_budget_includes_refs", False):
        counted, note = _body_pages(pdf, pages)
        notes.append(note)
    report = pdf_pages.budget_report(counted, budget if isinstance(budget, int) else None)
    report["total_pages"] = pages
    return pages, report, notes


# ---------------------------------------------------------------- report

def _rel(path: str | Path, root: Path) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(root).as_posix() or "."
    except ValueError:
        return str(p)


def _where(err: dict) -> str:
    f = err.get("file") or "?"
    if f.startswith("./"):
        f = f[2:]
    line = err.get("line")
    return f"{f}:{line if line is not None else '?'}"


def _render(rep: CompileReport, cfg: dict, threshold: float) -> str:
    log = rep.log
    slug = (cfg.get("document") or {}).get("slug") or "document"
    out = [f"# Compile report: {slug}", "",
           f"**Status: {rep.status}.** " + ("; ".join(rep.reasons) if rep.reasons else "build clean."), ""]
    out += ["## Build", "",
            f"- Command: `{rep.command}`",
            f"- Directory: `{rep.cwd}`",
            f"- Exit code: {rep.returncode if rep.returncode is not None else 'none'}",
            f"- Duration: {rep.duration_s:.1f} s"]
    if rep.build_error:
        out.append(f"- FAIL {rep.build_error}")
    for n in rep.notes:
        out.append(f"- Note: {n}")
    if log.rerun_needed:
        out.append("- WARN rerun needed: cross-references may have changed; build again before submitting")
    if rep.output_tail:
        out += ["", f"Last {TAIL_LINES} lines of build output:", "", "```", rep.output_tail, "```"]
    out += ["", "## Errors", ""]
    if log.errors:
        out.append(f"{len(log.errors)} error(s). Fix the first error, not the last: later errors often follow from it.")
        out.append("")
        for i, e in enumerate(log.errors, 1):
            out.append(f"{i}. `{_where(e)}`: {e['message']}")
    else:
        out.append("None.")
    out += ["", "## Undefined", ""]
    if log.undefined_citations or log.undefined_references:
        if log.undefined_citations:
            out.append("- Citations: " + ", ".join(f"`{k}`" for k in log.undefined_citations))
        if log.undefined_references:
            out.append("- References: " + ", ".join(f"`{k}`" for k in log.undefined_references))
    else:
        out.append("None.")
    out += ["", "## Overfull", "",
            f"{log.overfull_total} overfull box(es) in total, {len(log.overfull)} above {threshold:g}pt."]
    for o in log.overfull:
        out.append(f"- {o['pt']:g}pt: {o['context']}")
    out += ["", "## Pages vs budget", ""]
    b = rep.budget
    if rep.pages is None:
        out.append(f"Page count unavailable: {b.get('reason', 'no PDF')}.")
    elif b.get("budget") is None:
        out.append(f"{rep.pages} pages; no page budget set (SKIP).")
    else:
        line = f"{rep.pages} pages in total; {b['pages']} counted against a budget of {b['budget']}: {b['status']}"
        if b.get("over_by"):
            line += f", over by {b['over_by']}"
        out.append(line + ".")
    out += ["", "## Next step", ""]
    out += [f"- {s}" for s in _next_steps(rep)]
    return "\n".join(out) + "\n"


def _next_steps(rep: CompileReport) -> list[str]:
    log, steps = rep.log, []
    if rep.build_error.startswith("build tool not found"):
        steps.append("Install the build tool or fix build.command in ploma.yaml, then run /ploma:compile.")
    if log.errors:
        steps.append(f"Fix the first error at `{_where(log.errors[0])}`, then run /ploma:compile again.")
    if log.undefined_citations:
        steps.append("Undefined citations: run /ploma:validate-bib to find the missing or misspelt keys.")
    if log.undefined_references:
        steps.append("Undefined references: check the \\label and \\ref names, then rebuild.")
    if rep.budget.get("status") == "FAIL":
        steps.append(f"Over the page budget by {rep.budget['over_by']}: run /ploma:format for the page map and a cut plan.")
    if not steps and rep.status == "FAIL":
        steps.append("Fix the problem named in the Build section, then run /ploma:compile again.")
    if rep.status == "PASS":
        steps.append("Run /ploma:validate-bib next (the bib check is the other required gate entry).")
    return steps


# ---------------------------------------------------------------- run

def run(root: Path, cfg: dict, *, runner: Callable[..., Any] | None = None, clean: bool = False) -> CompileReport:
    root = Path(root).resolve()
    runner = runner or _default_runner
    resolved = ploma_config.resolve(cfg, root)
    paths = resolved["_paths"]
    build = cfg.get("build") or {}
    threshold = float(build.get("overfull_threshold_pt") or 10)
    cwd = paths["build_cwd"] or str(root)
    notes: list[str] = []

    started = time.time()
    if clean:
        ccmd, cshell = clean_command(cfg, paths)
        crc, _ctail, cerr = _execute(runner, ccmd, cshell, cwd)
        if cerr or crc:
            notes.append(f"clean step `{_show(ccmd)}` did not succeed: {cerr or f'exit {crc}'}")
    cmd, shell = build_command(cfg, paths)
    returncode, tail, build_error = _execute(runner, cmd, shell, cwd)
    duration = time.time() - started

    log_path = Path(paths["log"]) if paths["log"] else None
    log_report = latex_log.LogReport()
    log_missing = ""
    if log_path is None or not log_path.is_file():
        log_missing = f"log not found at {_rel(log_path, root)}" if log_path else "build.log is not set"
    else:
        try:
            text = log_path.read_bytes().decode("utf-8", errors="replace")
            log_report = latex_log.parse_log(text, threshold)
        except OSError as exc:
            log_missing = f"log not readable at {_rel(log_path, root)}: {exc.strerror or exc}"

    pdf_path = Path(paths["pdf"]) if paths["pdf"] else None
    if pdf_path is not None:
        pages, budget, pnotes = _pages(cfg, pdf_path, started, root)
        notes.extend(pnotes)
    else:
        pages, budget = None, {"pages": None, "budget": None, "over_by": None, "status": "SKIP",
                               "reason": "build.pdf is not set"}

    reasons: list[str] = []
    if build_error:
        reasons.append(build_error)
    elif returncode:
        reasons.append(f"build exited with code {returncode}")
    if log_missing:
        reasons.append(log_missing)
    if log_report.errors:
        reasons.append(f"{len(log_report.errors)} error(s) in the log, first at {_where(log_report.errors[0])}")
    n_undef = len(log_report.undefined_citations) + len(log_report.undefined_references)
    if n_undef:
        reasons.append(f"{n_undef} undefined citation(s) or reference(s)")
    if budget.get("status") == "FAIL":
        reasons.append(f"over the page budget by {budget['over_by']}")
    if pages is None and not build_error and not returncode:
        reasons.append(f"no PDF: {budget.get('reason')}")
    status = "FAIL" if reasons else "PASS"

    slug = (cfg.get("document") or {}).get("slug") or "document"
    out_dir = Path(paths["outputs_dir"])
    report_path = out_dir / f"compile_{slug}.md"
    rep = CompileReport(ok=status == "PASS", status=status, command=_show(cmd), cwd=_rel(cwd, root), returncode=returncode,
                        log=log_report, pages=pages, budget=budget, report_path=report_path,
                        duration_s=round(duration, 2), output_tail=tail, build_error=build_error,
                        notes=notes, reasons=reasons)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_render(rep, cfg, threshold), encoding="utf-8")

    artifact = report_path.relative_to(root).as_posix() if root in report_path.parents else str(report_path)
    extras = {"pages": pages, "overfull": len(log_report.overfull), "undefined": n_undef}
    gate.record(root, cfg, "compile", status, artifact, **extras)
    state.record(root, cfg, "compile", status, artifact, **extras)
    return rep


def _summary(rep: CompileReport) -> str:
    lines = [f"compile: {rep.status}" + (f" ({'; '.join(rep.reasons)})" if rep.reasons else "")]
    if rep.log.errors:
        e = rep.log.errors[0]
        lines.append(f"first error: {_where(e)}: {e['message']}")
    lines.append(f"report: {rep.report_path}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PDF and triage the result.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: .)")
    parser.add_argument("--clean", action="store_true", help="clean build artifacts first")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root)
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        if args.json:
            print(json.dumps({"error": exc.message}))
        else:
            print(f"compile: {exc.message}", file=sys.stderr)
        return 2
    try:
        rep = run(root, cfg, runner=_default_runner, clean=args.clean)
    except (OSError, ValueError) as exc:
        msg = f"cannot record the compile result: {exc}"
        print(json.dumps({"error": msg}) if args.json else f"compile: {msg}",
              file=sys.stdout if args.json else sys.stderr)
        return 2
    print(json.dumps(rep.to_dict(), indent=2) if args.json else _summary(rep))
    return 0 if rep.ok else 1


if __name__ == "__main__":
    sys.exit(main())
