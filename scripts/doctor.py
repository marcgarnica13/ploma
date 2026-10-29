#!/usr/bin/env python3
"""Readiness audit: grouped PASS/WARN/FAIL/INFO/SKIP checks and one verdict (spec section 9).

Usage: doctor.py [path] [--json]

Read-only: doctor never writes a file, never runs the build and makes no network calls.
Verdict: NOT_READY if any FAIL, READY_WITH_WARNINGS if any WARN, else READY. INFO and SKIP never count.

Exit codes: 0 READY or READY_WITH_WARNINGS, 1 NOT_READY, 2 usage error or path is not a directory.
"""
from __future__ import annotations

import argparse
import difflib
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
import project_files  # noqa: E402
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
                    first, *rest = f.observed.splitlines()
                    lines.append(f"  Observed: {first}")
                    lines.extend(f"    {line}" for line in rest)
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
    elif not base.is_dir():
        out.append(_f(g, "pdf_fresh", SKIP, "document.root missing",
                      observed=f"document.root: {_get(cfg, 'document.root')}"))
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


def _drift_excerpt(diff: str, limit: int = 6) -> str:
    body = [ln for ln in diff.splitlines() if ln[:1] in "+-" and not ln.startswith(("+++", "---"))]
    more = len(body) - limit
    return "; ".join(body[:limit]) + (f" (and {more} more changed lines)" if more > 0 else "")


def _gitignore_finding(g: str, missing: list[str]) -> Finding:
    if missing:
        return _f(g, "gitignore", WARN, ".gitignore does not cover ploma's local state",
                  observed="not ignored: " + ", ".join(missing),
                  remediation="Add these lines to .gitignore (or re-run /ploma:onboard): " + ", ".join(missing))
    return _f(g, "gitignore", PASS, ".gitignore covers .ploma/, session logs and caches")


def _project_files(root: Path, cfg: dict) -> list[Finding]:
    g = "project-files"
    out = []
    try:
        specs = project_files.render_enforced(cfg)  # the enforced entries of render_all; created-once never drift
    except (ValueError, KeyError, OSError) as exc:
        specs = None
        out.append(_f(g, "render", WARN, "ploma could not render the generated rules", observed=str(exc),
                      remediation="Fix ploma.yaml, then re-run /ploma:onboard."))
    if specs is not None:
        bad = 0
        for spec in (s for s in specs if s.mode == "enforced"):
            target = root / spec.path
            if not target.is_file():
                bad += 1
                out.append(_f(g, f"missing.{spec.path}", WARN, f"generated rule {spec.path} is missing",
                              observed=f"missing: {spec.path}", remediation="Re-run /ploma:onboard"))
                continue
            try:
                current = target.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                current = f"<unreadable: {exc}>"
            if current != spec.content:
                bad += 1
                diff = "".join(difflib.unified_diff(current.splitlines(keepends=True),
                                                    spec.content.splitlines(keepends=True)))
                out.append(_f(g, f"drift.{spec.path}", WARN,
                              f"{spec.path} differs from what ploma.yaml generates",
                              observed=_drift_excerpt(diff),
                              remediation="Re-run /ploma:onboard to regenerate it; change ploma.yaml, "
                                          "not the generated file."))
        stale = root / project_files.PIPELINE_RULE
        if _get(cfg, "pipeline.enabled") is not True and stale.is_file():
            try:
                generated = project_files.has_generated_marker(stale.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                generated = False
            if generated:
                bad += 1
                out.append(_f(g, f"stale.{project_files.PIPELINE_RULE}", WARN,
                              "a generated pipeline rule remains although pipeline.enabled is false",
                              observed=f"present: {project_files.PIPELINE_RULE}",
                              remediation="Re-run /ploma:onboard"))
        if not bad:
            n = len(specs)
            out.append(_f(g, "rules", PASS, f"{n} generated rules match ploma.yaml"))
    try:
        claude = (root / "CLAUDE.md").read_text(encoding="utf-8") if (root / "CLAUDE.md").is_file() else None
        span = project_files.marker_span(claude) if claude is not None else None
        problem = "" if span is not None else \
            "CLAUDE.md does not exist" if claude is None else "no ploma markers in CLAUDE.md"
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        problem = str(exc)
    out.append(_f(g, "claude_md", WARN, "the CLAUDE.md ploma section is missing or broken", observed=problem,
                  remediation="Re-run /ploma:onboard to restore the section between "
                              f"{project_files.MARKER_BEGIN} and {project_files.MARKER_END}.") if problem else
               _f(g, "claude_md", PASS, "CLAUDE.md has the ploma section"))
    gi = root / ".gitignore"
    try:
        lines = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    except (OSError, UnicodeDecodeError):
        lines = []
    try:
        missing = project_files.gitignore_missing(lines, cfg)
    except ValueError as exc:  # outputs.dir outside the repo
        out.append(_f(g, "gitignore", WARN, "cannot check .gitignore coverage", observed=str(exc),
                      remediation="Set outputs.dir to a path inside the repo in ploma.yaml."))
        missing = None
    if missing is not None:
        out.append(_gitignore_finding(g, missing))
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
    gone = [r["path"] for r in rows if r["state"] == "missing" and r["path"] != project_files.LEARNINGS_RULE]
    edited = [r["path"] for r in rows if r["state"] == "hand_edited"]
    if any(r["state"] == "missing" and r["path"] == project_files.LEARNINGS_RULE for r in rows):
        out.append(_f(g, "receipt_learnings_removed", INFO,
                      "learnings rule removed (demoted); the receipt entry drops at the next onboard",
                      observed=f"missing: {project_files.LEARNINGS_RULE}"))
    if gone:
        out.append(_f(g, "receipt_missing", WARN, f"{len(gone)} files written by onboard are gone",
                      observed=_listed(gone), remediation="Re-run /ploma:onboard to restore them."))
    if edited:
        out.append(_f(g, "receipt_edited", INFO, f"{len(edited)} files written by onboard were edited by hand",
                      observed=_listed(edited)))
    if not gone and not edited:
        same = sum(r["state"] == "unchanged" for r in rows)
        out.append(_f(g, "receipt", PASS, f"onboard receipt present; {same} files unchanged"))
    return out


def _state(root: Path, cfg: dict) -> list[Finding]:
    g = "state"
    out = []
    streak: int | None = None
    try:
        rep = gate.check(root, cfg)
    except Exception as exc:  # unreadable gate file or a manuscript_sha error: report, keep the other checks
        out.append(_f(g, "gate", WARN, "the commit gate could not be evaluated",
                      observed=f"{type(exc).__name__}: {exc}",
                      remediation="Re-run /ploma:compile and /ploma:validate-bib to rewrite it."))
        try:
            streak = int(gate.load(root, cfg).get("override_streak") or 0)
        except Exception:
            streak = None
    else:
        streak = rep.override_streak
        if rep.verdict == "PASS":
            out.append(_f(g, "gate", PASS, "commit gate verdict PASS and fresh for the current manuscript",
                          observed="; ".join(rep.warnings)))
        elif rep.verdict == "FAIL":
            failed = [r for r in rep.reasons if ": FAIL" in r]
            out.append(_f(g, "gate", WARN, "commit gate verdict FAIL: "
                          + ", ".join(r.split(":", 1)[0] for r in failed) + " failed",
                          observed="; ".join(rep.reasons),
                          remediation="fix the failing check and re-run it (e.g. /ploma:compile, /ploma:validate-bib)"))
        else:
            out.append(_f(g, "gate", INFO, f"commit gate verdict {rep.verdict}", observed="; ".join(rep.reasons),
                          remediation="Run the missing or stale checks (/ploma:compile, /ploma:validate-bib) "
                                      "before committing."))
    if streak is not None:
        if streak >= 2:
            out.append(_f(g, "override_streak", WARN, f"{streak} consecutive gate overrides",
                          observed=f"override_streak: {streak}; the gate refuses at "
                                   f"{gate.MAX_CONSECUTIVE_OVERRIDES}",
                          remediation="Fix the failing checks instead of overriding the gate again."))
        else:
            out.append(_f(g, "override_streak", PASS, f"override streak {streak}"))
    try:
        st = state.load(root, cfg)
    except ValueError as exc:
        out.append(_f(g, "next_stage", WARN, "the lifecycle state file is unreadable", observed=str(exc),
                      remediation="Fix or delete the state file; ploma starts a fresh one."))
        return out
    nxt = state.next_stage(st, cfg, root)
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


# Legacy kinds in report order: (noun for the count, what goes wrong). One WARN per kind (R127 D5).
LEGACY_KINDS = {
    "skill_name_conflict": ("skill(s) share a name with a ploma skill", "they shadow or confuse the ploma skill"),
    "hook_entry": ("hook entry file(s)", "they run alongside ploma's hooks and double-fire"),
    "statusline": ("status line(s)", "they replace the one that shows ploma's lifecycle stage"),
    "rule_restates_facts": ("rule file(s) restate build facts", "ploma.yaml now owns those facts"),
}
LEGACY_LIST_MAX = 25


def _legacy(root: Path) -> list[Finding]:
    g = "legacy-harness"
    found = inventory.detect_legacy_harness(root)
    if not found:
        return [_f(g, "none", PASS, "no legacy harness conflicts")]
    by_kind: dict[str, list[dict]] = {}
    for c in found:
        by_kind.setdefault(c["kind"], []).append(c)
    order = list(LEGACY_KINDS) + [k for k in by_kind if k not in LEGACY_KINDS]
    out = []
    for kind in order:
        items = by_kind.get(kind)
        if not items:
            continue
        noun, why = LEGACY_KINDS.get(kind, (f"{kind} item(s)", items[0]["consequence"]))
        summary = items[0]["consequence"] if len(items) == 1 else f"{len(items)} legacy {noun}: {why}"
        paths = [c["path"] for c in items]
        shown = paths[:LEGACY_LIST_MAX]
        if len(paths) > LEGACY_LIST_MAX:
            shown.append(f"and {len(paths) - LEGACY_LIST_MAX} more")
        out.append(_f(g, kind, WARN, summary, observed="\n".join(shown),
                      remediation=f"retire {'it' if len(items) == 1 else 'them'} (see the onboard retirement checklist)"))
    return out


# ---------------------------------------------------------------- entry points

# A crash in these groups could hide a FAIL, so it counts as one (Ruling R61).
FAIL_ON_ERROR = ("config", "toolchain", "manuscript")


def _guard(group: str, fn: Callable[[], list[Finding]]) -> list[Finding]:
    try:
        return fn()
    except Exception as exc:  # one broken group must not hide the others
        status = FAIL if group in FAIL_ON_ERROR else WARN
        return [_f(group, "error", status, "doctor could not complete this group",
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
