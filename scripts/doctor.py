#!/usr/bin/env python3
"""Readiness audit: grouped PASS/WARN/FAIL/INFO/SKIP checks and one verdict (spec section 9).

Usage: doctor.py [path] [--json]

Read-only: doctor never writes a file, never runs the build and makes no network calls.
Verdict: NOT_READY if any FAIL, READY_WITH_WARNINGS if any WARN, else READY. INFO and SKIP never count.

Exit codes: 0 READY or READY_WITH_WARNINGS, 1 NOT_READY, 2 usage error or path is not a directory.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yamlio  # noqa: E402
import bib_check  # noqa: E402
import gate  # noqa: E402
import inventory  # noqa: E402
import ploma_config  # noqa: E402
import profiles  # noqa: E402
import receipt  # noqa: E402
import state  # noqa: E402
from _findings import FAIL, INFO, PASS, SKIP, STATUSES, WARN, Finding  # noqa: E402

GROUPS = (("runtime", "Runtime"), ("config", "Config"), ("toolchain", "Toolchain"),
          ("manuscript", "Manuscript"), ("project-files", "Project files"), ("state", "State"),
          ("dependencies", "Dependencies"), ("legacy-harness", "Legacy harness"))
NEEDS_CONFIG = ("toolchain", "manuscript", "project-files", "state", "legacy-harness")
LINTERS = ("chktex", "lacheck", "texcount")
PDF_TOOLS = ("pdfinfo", "pdftotext")
SOURCE_SUFFIXES = (".tex", ".bib")
MAX_LISTED = 10
SUPERPOWERS_INSTALL = ("Install superpowers: /plugin install superpowers@claude-plugins-official "
                       "(or add the superpowers-marketplace marketplace with "
                       "/plugin marketplace add obra/superpowers-marketplace and run "
                       "/plugin install superpowers@superpowers-marketplace).")

Which = Callable[[str], "str | None"]


def verdict_for(findings: list[Finding]) -> str:
    statuses = {f.status for f in findings}
    if FAIL in statuses:
        return "NOT_READY"
    if WARN in statuses:
        return "READY_WITH_WARNINGS"
    return "READY"


@dataclass
class DoctorReport:
    groups: list[dict] = field(default_factory=list)

    def findings(self) -> list[Finding]:
        return [f for g in self.groups for f in g["findings"]]

    @property
    def verdict(self) -> str:
        return verdict_for(self.findings())

    @property
    def counts(self) -> dict:
        out = {s: 0 for s in STATUSES}
        for f in self.findings():
            out[f.status] += 1
        return out

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "counts": self.counts,
                "groups": [{"id": g["id"], "title": g["title"],
                            "findings": [f.to_dict() for f in g["findings"]]} for g in self.groups]}

    def render(self) -> str:
        c = self.counts
        lines = [f"Overall verdict: {self.verdict}",
                 "Counts: " + " ".join(f"{s} {c[s]}" for s in (PASS, WARN, FAIL, INFO, SKIP))]
        for n, g in enumerate(self.groups, 1):
            lines.append("")
            lines.append(f"{n}. {g['title']}")
            for f in g["findings"]:
                lines.append(f"- {f.status} {f.id}: {f.summary}")
                if f.observed:
                    lines.append(f"  Observed: {f.observed}")
                if f.remediation:
                    lines.append(f"  Remediation: {f.remediation}")
        return "\n".join(lines)


def _f(group: str, check: str, status: str, summary: str, observed: str = "", remediation: str = "") -> Finding:
    return Finding(f"{group}.{check}", status, summary, observed=observed, remediation=remediation, group=group)


def _get(cfg: dict, dotted: str) -> Any:
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _listed(items: list[str]) -> str:
    more = len(items) - MAX_LISTED
    return ", ".join(items[:MAX_LISTED]) + (f" and {more} more" if more > 0 else "")


# ---------------------------------------------------------------- groups

def _runtime(which: Which) -> list[Finding]:
    g = "runtime"
    ver = ".".join(str(x) for x in sys.version_info[:3])
    out = [_f(g, "python", PASS, f"python {ver}", observed=sys.executable)
           if sys.version_info >= (3, 10) else
           _f(g, "python", FAIL, f"python {ver} is older than 3.10", observed=sys.executable,
              remediation="Install python 3.10 or newer and make it the python3 on PATH.")]
    out.append(_f(g, "yaml_loader", INFO, f"YAML loader in use: {_yamlio.LOADER}"))
    git = which("git")
    out.append(_f(g, "git", PASS, "git is installed", observed=git) if git else
               _f(g, "git", WARN, "git is not installed",
                  remediation="Install git; the commit gate and gitignore checks rely on it."))
    return out


def _config(root: Path, cfg: dict) -> list[Finding]:
    out = []
    for f in ploma_config.validate(cfg, root):
        f.group = "config"
        out.append(f)
    for label, key_path, loader, validator in (
            ("venue", "venue.profile", profiles.load_venue, profiles.validate_venue),
            ("discipline", "document.discipline", profiles.load_discipline, profiles.validate_discipline)):
        key = _get(cfg, key_path)
        if key is None:
            out.append(_f("config", label, SKIP, f"no {key_path} set"))
            continue
        try:
            data = loader(key, root)
        except profiles.ProfileError as exc:
            out.append(_f("config", label, FAIL, f"{label} profile {key!r} does not resolve", observed=str(exc),
                          remediation=f"Set {key_path} to an available key, or add "
                                      f"ploma.d/{label}s/{key}.yaml."))
            continue
        shape = validator(data)
        for f in shape:
            f.id = f"config.{f.id}"
            f.group = "config"
            out.append(f)
        if not any(f.status == FAIL for f in shape):
            out.append(_f("config", label, PASS, f"{label} profile {key} resolves"))
    return out


def _uses(command: str, tool: str) -> bool:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    return any(os.path.basename(t) == tool for t in tokens)


def _toolchain(cfg: dict, which: Which) -> list[Finding]:
    g = "toolchain"
    out = []
    engine = _get(cfg, "build.engine") or "pdflatex"
    path = which(engine)
    out.append(_f(g, "engine", PASS, f"{engine} is installed", observed=path) if path else
               _f(g, "engine", FAIL, f"TeX engine {engine} is not installed", observed=f"build.engine: {engine}",
                  remediation=f"Install a TeX distribution that provides {engine}, or change build.engine."))
    bib = _get(cfg, "build.bib_tool") or "bibtex"
    path = which(bib)
    out.append(_f(g, "bib_tool", PASS, f"{bib} is installed", observed=path) if path else
               _f(g, "bib_tool", FAIL, f"bibliography tool {bib} is not installed",
                  observed=f"build.bib_tool: {bib}",
                  remediation=f"Install {bib} (it ships with TeX distributions), or change build.bib_tool."))
    command = _get(cfg, "build.command")
    for tool in ("make", "latexmk"):
        if (command is None and tool == "latexmk") or (isinstance(command, str) and _uses(command, tool)):
            path = which(tool)
            why = "build.command is null (latexmk fallback)" if command is None else f"build.command: {command}"
            out.append(_f(g, tool, PASS, f"{tool} is installed", observed=path) if path else
                       _f(g, tool, FAIL, f"{tool} is not installed but the build needs it", observed=why,
                          remediation=f"Install {tool}, or change build.command."))
    for tool in PDF_TOOLS:
        path = which(tool)
        out.append(_f(g, tool, PASS, f"{tool} is installed", observed=path) if path else
                   _f(g, tool, WARN, f"{tool} is not installed",
                      remediation="Install poppler-utils; page counts and PDF text checks need it."))
    for tool in LINTERS:
        path = which(tool)
        out.append(_f(g, tool, PASS, f"{tool} is installed", observed=path) if path else
                   _f(g, tool, SKIP, "optional linter not installed", observed=f"{tool} not found on PATH"))
    out.append(_f(g, "build_dry_run", SKIP, "not run by doctor",
                  observed="the build command is exercised by /ploma:compile"))
    return out


def _newest_source(base: Path) -> tuple[float, Path] | None:
    newest: tuple[float, Path] | None = None
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for name in filenames:
            if name.endswith(SOURCE_SUFFIXES) and not name.endswith(gate.SUGGESTION_SUFFIX):
                p = Path(dirpath) / name
                try:
                    m = p.stat().st_mtime
                except OSError:
                    continue
                if newest is None or m > newest[0]:
                    newest = (m, p)
    return newest


def _bib_findings(main: Path, bibs: list[Path]) -> list[Finding]:
    g = "manuscript"
    raw = bib_check.check(main, bibs)

    def item(f: Finding) -> str:
        parts = f.id.split(".", 2)
        name = parts[2] if len(parts) == 3 else f.id
        return f"{name} ({f.observed})" if f.observed and f.status == FAIL else name

    by = {s: [f for f in raw if f.status == s] for s in (FAIL, WARN, INFO)}
    out = []
    if by[FAIL]:
        missing = sum(f.id.startswith("bib.missing.") for f in by[FAIL])
        files = sum(f.id.startswith("bib.file_missing.") for f in by[FAIL])
        out.append(_f(g, "bib", FAIL, f"{len(by[FAIL])} bibliography errors: {missing} cite keys without an entry, "
                                      f"{files} bib files not found",
                      observed=_listed([item(f) for f in by[FAIL]]),
                      remediation="Run /ploma:validate-bib and fix the keys or bib paths."))
    else:
        out.append(_f(g, "bib", PASS, "every cite key resolves to a bibliography entry"))
    if by[WARN]:
        out.append(_f(g, "bib_warnings", WARN, f"{len(by[WARN])} bibliography warnings (near-miss keys, "
                                               "duplicates or mixed citation commands)",
                      observed=_listed([item(f) for f in by[WARN]]),
                      remediation="Run /ploma:validate-bib for details."))
    if by[INFO]:
        out.append(_f(g, "bib_unused", INFO, f"{len(by[INFO])} bibliography entries are never cited",
                      observed=_listed([item(f) for f in by[INFO]])))
    return out


def _manuscript(root: Path, cfg: dict) -> list[Finding]:
    g = "manuscript"
    paths = ploma_config.resolve(cfg, root)["_paths"]
    out = []
    pdf = Path(paths["pdf"]) if paths["pdf"] else None
    base = Path(paths["root"]) if paths["root"] else root
    newest = _newest_source(base) if base.is_dir() else None
    if pdf is None or not pdf.is_file():
        out.append(_f(g, "pdf_stale", WARN, "no compiled PDF", observed=f"missing: {_get(cfg, 'build.pdf')}",
                      remediation="Run /ploma:compile"))
    elif newest is not None and newest[0] > pdf.stat().st_mtime:
        out.append(_f(g, "pdf_stale", WARN, "the PDF is older than its sources",
                      observed=f"{newest[1].relative_to(base).as_posix()} changed after {_get(cfg, 'build.pdf')}",
                      remediation="Run /ploma:compile"))
    else:
        out.append(_f(g, "pdf_fresh", PASS, "the PDF is newer than every .tex and .bib source"))
    main = Path(paths["main"]) if paths["main"] else None
    if main is None or not main.is_file():
        out.append(_f(g, "bib", SKIP, "document.main not found", observed=str(_get(cfg, "document.main"))))
        return out
    out.extend(_bib_findings(main, [Path(b) for b in paths["bib_files"]]))
    if _get(cfg, "pipeline.enabled") is True:
        figs = inventory._figures(bib_check.tex_sources(main), root)  # shared figure scan with onboard
        bare = [f"{x['path']} ({x['source']}:{x['line']})" for x in figs if not x["has_provenance"]]
        if bare:
            required = _get(cfg, "pipeline.figure_provenance") == "required"
            out.append(_f(g, "figure_provenance", WARN if required else INFO,
                          f"{len(bare)} of {len(figs)} figures lack a '% ploma:source' provenance comment",
                          observed=_listed(bare),
                          remediation="Add '% ploma:source <script and arguments>' on the line before each "
                                      "\\includegraphics."))
        else:
            out.append(_f(g, "figure_provenance", PASS, f"all {len(figs)} figures carry a provenance comment"))
    return out


def _ignored_by(lines: list[str], target: str) -> bool:
    parts = target.strip("/").split("/")
    accept = {"/".join(parts[:i]) for i in range(1, len(parts) + 1)} | {parts[-1]}
    for line in lines:
        s = line.strip()
        if not s or s.startswith(("#", "!")):
            continue
        for suffix in ("/**", "/*"):
            if s.endswith(suffix):
                s = s[: -len(suffix)]
        if s.strip("/") in accept:
            return True
    return False


def _project_files(root: Path, cfg: dict) -> list[Finding]:
    g = "project-files"
    out = [_f(g, "renderer", SKIP, "renderer not available until onboard support lands")]
    gi = root / ".gitignore"
    try:
        lines = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    except (OSError, UnicodeDecodeError):
        lines = []
    outputs = str(_get(cfg, "outputs.dir") or "quality_reports").strip("/")
    wanted = [".ploma/", f"{outputs}/session_logs/"]
    missing = [w for w in wanted if not _ignored_by(lines, w)]
    out.append(_f(g, "gitignore", WARN, ".gitignore does not cover ploma's local state",
                  observed="not ignored: " + ", ".join(missing),
                  remediation="Add these lines to .gitignore: " + ", ".join(missing)) if missing else
               _f(g, "gitignore", PASS, ".gitignore covers .ploma/ and session logs"))
    try:
        data = receipt.load(root, cfg)
    except ValueError as exc:
        out.append(_f(g, "receipt", WARN, "the onboard receipt is unreadable", observed=str(exc),
                      remediation="Re-run /ploma:onboard to rewrite the project files and receipt."))
        return out
    if data is None:
        out.append(_f(g, "receipt", INFO, "no onboard receipt", observed=f"missing: {receipt.path(root, cfg)}",
                      remediation="Run /ploma:onboard to write the project files and receipt."))
        return out
    rows = receipt.compare(root, cfg)
    gone = [r["path"] for r in rows if r["state"] == "missing"]
    edited = [r["path"] for r in rows if r["state"] == "hand_edited"]
    if gone:
        out.append(_f(g, "receipt_missing", WARN, f"{len(gone)} files written by onboard are gone",
                      observed=_listed(gone), remediation="Re-run /ploma:onboard to restore them."))
    if edited:
        out.append(_f(g, "receipt_edited", INFO, f"{len(edited)} files written by onboard were edited by hand",
                      observed=_listed(edited)))
    if not gone and not edited:
        out.append(_f(g, "receipt", PASS, f"onboard receipt present; {len(rows)} files unchanged"))
    return out


def _state(root: Path, cfg: dict) -> list[Finding]:
    g = "state"
    out = []
    try:
        rep = gate.check(root, cfg)
    except ValueError as exc:
        out.append(_f(g, "gate", WARN, "the commit gate file is unreadable", observed=str(exc),
                      remediation="Re-run /ploma:compile and /ploma:validate-bib to rewrite it."))
        rep = None
    if rep is not None:
        if rep.verdict == "PASS":
            out.append(_f(g, "gate", PASS, "commit gate verdict PASS and fresh for the current manuscript",
                          observed="; ".join(rep.warnings)))
        else:
            out.append(_f(g, "gate", INFO, f"commit gate verdict {rep.verdict}", observed="; ".join(rep.reasons),
                          remediation="Run the missing or stale checks (/ploma:compile, /ploma:validate-bib) "
                                      "before committing."))
        if rep.override_streak >= 2:
            out.append(_f(g, "override_streak", WARN, f"{rep.override_streak} consecutive gate overrides",
                          observed=f"override_streak: {rep.override_streak}; the gate refuses at "
                                   f"{gate.MAX_CONSECUTIVE_OVERRIDES}",
                          remediation="Fix the failing checks instead of overriding the gate again."))
        else:
            out.append(_f(g, "override_streak", PASS, f"override streak {rep.override_streak}"))
    try:
        st = state.load(root, cfg)
    except ValueError as exc:
        out.append(_f(g, "next_stage", WARN, "the lifecycle state file is unreadable", observed=str(exc),
                      remediation="Fix or delete the state file; ploma starts a fresh one."))
        return out
    nxt = state.next_stage(st, cfg)
    out.append(_f(g, "next_stage", INFO, f"next stage: {nxt['stage']}", observed=nxt["reason"]))
    return out


def _dependencies(root: Path, home: Path) -> list[Finding]:
    g = "dependencies"
    sp = inventory._superpowers(root, home)  # same settings lookup onboard uses, without the full inventory walk
    out = [_f(g, "superpowers", PASS, "superpowers is enabled", observed=sp["id"]) if sp["enabled"] else
           _f(g, "superpowers", WARN, "superpowers is not enabled",
              observed="no enabled superpowers@* plugin in user or project settings",
              remediation=SUPERPOWERS_INSTALL)]
    out.append(_f(g, "citation_apis", SKIP, "doctor makes no network calls",
                  observed="citation API reachability is checked by /ploma:validate-bib"))
    return out


def _legacy(root: Path) -> list[Finding]:
    g = "legacy-harness"
    found = inventory.detect_legacy_harness(root)
    if not found:
        return [_f(g, "none", PASS, "no legacy harness conflicts")]
    return [Finding(f"{g}.{c['kind']}.{Path(c['path']).name}", WARN, c["consequence"], observed=c["path"],
                    remediation="retire it (see the onboard retirement checklist)", group=g) for c in found]


# ---------------------------------------------------------------- entry points

def _guard(group: str, fn: Callable[[], list[Finding]]) -> list[Finding]:
    try:
        return fn()
    except Exception as exc:  # one broken group must not hide the others
        return [_f(group, "error", WARN, "doctor could not complete this group",
                   observed=f"{type(exc).__name__}: {exc}",
                   remediation="Report this; the other groups are unaffected.")]


def run(root: Path, *, which: Which = shutil.which, home: Path | None = None) -> DoctorReport:
    root = Path(root)
    home = Path.home() if home is None else Path(home)
    found: dict[str, list[Finding]] = {"runtime": _guard("runtime", lambda: _runtime(which))}
    cfg: dict | None = None
    skip_reason = ""
    if not (root / ploma_config.CONFIG_NAME).is_file():
        found["config"] = [_f("config", "missing", FAIL, "no ploma.yaml in this directory",
                              observed=str(root / ploma_config.CONFIG_NAME), remediation="Run /ploma:onboard")]
        skip_reason = "no ploma.yaml"
    else:
        try:
            cfg = ploma_config.load(root)
        except ploma_config.ConfigError as exc:
            found["config"] = [_f("config", "parse", FAIL, "ploma.yaml could not be parsed", observed=exc.message,
                                  remediation="Fix the YAML syntax in ploma.yaml, or re-run /ploma:onboard.")]
            skip_reason = "ploma.yaml could not be parsed"
    if cfg is None:
        for gid in NEEDS_CONFIG:
            found[gid] = [_f(gid, "skipped", SKIP, skip_reason)]
    else:
        c = cfg
        found["config"] = _guard("config", lambda: _config(root, c))
        found["toolchain"] = _guard("toolchain", lambda: _toolchain(c, which))
        found["manuscript"] = _guard("manuscript", lambda: _manuscript(root, c))
        found["project-files"] = _guard("project-files", lambda: _project_files(root, c))
        found["state"] = _guard("state", lambda: _state(root, c))
        found["legacy-harness"] = _guard("legacy-harness", lambda: _legacy(root))
    found["dependencies"] = _guard("dependencies", lambda: _dependencies(root, home))
    return DoctorReport([{"id": gid, "title": title, "findings": found[gid]} for gid, title in GROUPS])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only readiness audit for a ploma project.")
    parser.add_argument("path", nargs="?", default=".", help="project root (default: current directory)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.path)
    if not root.is_dir():
        msg = f"{root} is not a directory"
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(f"doctor: {msg}", file=sys.stderr)
        return 2
    report = run(root)
    print(json.dumps(report.to_dict(), indent=2) if args.json else report.render())
    return 1 if report.verdict == "NOT_READY" else 0


if __name__ == "__main__":
    sys.exit(main())
