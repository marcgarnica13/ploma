#!/usr/bin/env python3
"""Commit gate preparation for /ploma:commit (spec section 6.3).

Usage:
  python3 scripts/commit_gate.py [--root R] prepare [--json]
  python3 scripts/commit_gate.py [--root R] override (--reason R | --reason-file F) [--json]
  python3 scripts/commit_gate.py check-override [--json] < message.txt

prepare runs the gate check; every deterministic entry (compile, bib, consistency) that is missing or
stale is produced again (scripts/compile.py, the structural part of scripts/validate_bib.py,
scripts/consistency.py with its gate entry) and the gate is checked again. The verdict is FAIL when
a required check (compile, bib) FAILs or could not run, INCOMPLETE when a required check is still
missing or stale, otherwise PASS. Consistency FAIL is a warning in v0.1. Recommended checks that are
missing or stale (claims, proofread) are named with the skill that refreshes them.

override records a `commit anyway: <reason>` override for the failing required checks through
scripts/gate.py; it is refused when the gate passes and after three consecutive overrides.
--reason-file - reads the reason from stdin (safe for quotes, $ and backticks).

check-override reads a user message on stdin and prints the override reason when a line of the
message starts with `commit anyway: <reason>` (parse_override is the reference matcher).

Exit codes: 0 prepare PASS, override recorded, or check-override found a reason; 1 prepare FAIL or
INCOMPLETE, override refused, or no override phrase; 2 usage error or unreadable input.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import compile as compile_mod  # noqa: E402
import consistency  # noqa: E402
import gate  # noqa: E402
import ploma_config  # noqa: E402
import validate_bib  # noqa: E402

REFRESHED_HERE = ("compile", "bib", "consistency")
NEXT_COMMAND = {"claims": "/ploma:verify-claims", "proofread": "/ploma:proofread"}
_OVERRIDE_RE = re.compile(r"^[ \t]*commit[ \t]+anyway[ \t]*:[ \t]*(\S.*)$", re.I | re.M)  # one line only


@dataclasses.dataclass
class GatePrep:
    verdict: str
    refreshed: list[str]
    stale: list[str]
    missing: list[str]
    failing: list[str]
    warnings: list[str]
    can_override: bool
    override_streak: int
    next_commands: list[str]
    checks: dict[str, dict] = dataclasses.field(default_factory=dict)
    errors: list[str] = dataclasses.field(default_factory=list)
    notes: list[str] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class OverrideRefused(gate.OverrideRefused):
    """The gate passes, so there is nothing to override (CLI exit 1)."""


def parse_override(message: str) -> str | None:
    """The reference matcher: the reason of the first line that starts with `commit anyway: <reason>`
    (case-insensitive, leading whitespace allowed), or None. Mid-line mentions never count."""
    m = _OVERRIDE_RE.search(message or "")
    if not m:
        return None
    reason = m.group(1).strip()
    return reason or None


def _refresh(name: str, root: Path, cfg: dict, runner: Callable[..., Any] | None, fetch: Any) -> str | None:
    """Produce one deterministic gate entry again; return an error message when it could not run."""
    try:
        if name == "compile":
            rep = compile_mod.run(root, cfg, runner=runner)
            return f"the build could not run: {rep.build_error}" if rep.build_error else None
        if name == "bib":
            validate_bib.run(root, cfg, semantic=False, fetch=fetch)
            return None
        consistency.run_recorded(root, cfg)
        return None
    except (validate_bib.UsageError, OSError, ValueError) as exc:
        return f"could not run: {exc}"


SEMANTIC_STANDS = "semantic bibliography FAIL still stands: run /ploma:validate-bib --semantic"
SEMANTIC_SUPERSEDED = ("the .bib changed, so the semantic bibliography result is superseded by a structural "
                       "re-run: run /ploma:validate-bib --semantic again")


def _semantic_bib(root: Path, cfg: dict) -> str | None:
    """'stands' when the bib entry is a semantic FAIL over the current .bib bytes, 'superseded' when
    it is a semantic result over a .bib that changed since, else None (Ruling R156)."""
    entry = gate.load(root, cfg)["checks"].get("bib") or {}
    if entry.get("mode") != "semantic":
        return None
    try:
        current = validate_bib.bib_sha(root, cfg)
    except (validate_bib.UsageError, OSError, ValueError):
        return None
    if entry.get("bib_sha") == current:
        return "stands" if entry.get("status") == "FAIL" else None
    return "superseded"


def prepare(root: Path, cfg: dict, *, runner: Callable[..., Any] | None = None, fetch: Any = None) -> GatePrep:
    root = Path(root).resolve()
    first = gate.check(root, cfg)
    refreshed: list[str] = []
    errors: dict[str, str] = {}
    notes: list[str] = []
    for name in REFRESHED_HERE:
        c = first.checks[name]
        if c["present"] and c["fresh"]:
            continue
        if name == "bib" and c["present"]:
            semantic = _semantic_bib(root, cfg)
            if semantic == "stands":
                gate.refresh_sha(root, cfg, "bib")
                notes.append(SEMANTIC_STANDS)
                continue
            if semantic == "superseded":
                notes.append(SEMANTIC_SUPERSEDED)
        err = _refresh(name, root, cfg, runner, fetch)
        refreshed.append(name)
        if err:
            errors[name] = err
    rep = gate.check(root, cfg) if refreshed or notes else first

    failing = [n for n in gate.REQUIRED
               if n in errors or (rep.checks[n]["present"] and rep.checks[n]["fresh"]
                                  and rep.checks[n]["status"] == "FAIL")]
    missing = [n for n, c in rep.checks.items() if not c["present"]]
    stale = [n for n, c in rep.checks.items() if c["present"] and not c["fresh"]]
    if failing:
        verdict = "FAIL"
    elif any(n in missing or n in stale for n in gate.REQUIRED) or rep.verdict != "PASS":
        verdict = "INCOMPLETE"
    else:
        verdict = "PASS"
    warnings = list(rep.warnings)
    warnings += [f"{n}: {e} (recommended)" for n, e in errors.items() if n not in gate.REQUIRED]
    next_commands = [cmd for n, cmd in NEXT_COMMAND.items() if n in missing or n in stale]
    return GatePrep(verdict=verdict, refreshed=refreshed, stale=stale, missing=missing, failing=failing,
                    warnings=warnings, can_override=rep.can_override, override_streak=rep.override_streak,
                    next_commands=next_commands,
                    checks={n: {"status": c["status"], "fresh": c["fresh"], "required": c["required"]}
                            for n, c in rep.checks.items()},
                    errors=[f"{n}: {e}" for n, e in errors.items()], notes=notes)


def render(prep: GatePrep) -> str:
    lines = [f"commit gate: {prep.verdict}"]
    if prep.refreshed:
        lines.append(f"refreshed: {', '.join(prep.refreshed)}")
    for name, c in prep.checks.items():
        kind = "required" if c["required"] else "recommended"
        st = "missing" if c["status"] is None else f"{c['status']} {'FRESH' if c['fresh'] else 'STALE'}"
        lines.append(f"- {name} ({kind}): {st}")
    for e in prep.errors:
        lines.append(f"error: {e}")
    for n in prep.failing:
        lines.append(f"failing: {n} (required)")
    for n in prep.notes:
        lines.append(f"note: {n}")
    for w in prep.warnings:
        lines.append(f"warning: {w}")
    for cmd in prep.next_commands:
        lines.append(f"next: {cmd}")
    lines.append(f"override streak: {prep.override_streak}/{gate.MAX_CONSECUTIVE_OVERRIDES}"
                 + ("" if prep.can_override else " (overrides refused until a required check passes)"))
    return "\n".join(lines)


def override(root: Path, cfg: dict, reason: str) -> dict:
    """Record an override of the required checks that do not pass; ValueError when refused."""
    rep = gate.check(root, cfg)
    if rep.verdict == "PASS":
        raise OverrideRefused("the gate passes; nothing to override")
    checks = [n for n in gate.REQUIRED
              if not (rep.checks[n]["present"] and rep.checks[n]["fresh"]
                      and rep.checks[n]["status"] in ("PASS", "WARN"))]
    return gate.override(root, cfg, reason, checks)


def _error(message: str, as_json: bool, code: int = 2) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"commit_gate: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the deterministic gate checks and give the commit verdict.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="action")
    prep_p = sub.add_parser("prepare", help="refresh missing or stale compile, bib, consistency; give the verdict")
    prep_p.add_argument("--json", action="store_true", dest="json_sub")
    ovr = sub.add_parser("override", help="record a commit anyway override")
    src = ovr.add_mutually_exclusive_group(required=True)
    src.add_argument("--reason", help="the override reason (manual use)")
    src.add_argument("--reason-file", help="read the reason from this file; - for stdin")
    ovr.add_argument("--json", action="store_true", dest="json_sub")
    chk = sub.add_parser("check-override", help="read a user message on stdin; print the override reason")
    chk.add_argument("--json", action="store_true", dest="json_sub")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if args.action is None:
        parser.print_usage(sys.stderr)
        return 2
    as_json = args.json or args.json_sub
    if args.action == "check-override":
        reason = parse_override(sys.stdin.read())
        if as_json:
            print(json.dumps({"override": reason is not None, "reason": reason}))
        else:
            print(f"override reason: {reason}" if reason else "no override phrase")
        return 0 if reason else 1
    root = Path(args.root)
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        return _error(exc.message, as_json)
    if args.action == "override":
        try:
            if args.reason_file is not None:
                reason = sys.stdin.read() if args.reason_file == "-" else \
                    Path(args.reason_file).read_text(encoding="utf-8")
            else:
                reason = args.reason
            data = override(root, cfg, reason)
        except gate.OverrideRefused as exc:
            return _error(str(exc), as_json, code=1)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return _error(str(exc), as_json, code=2)
        last = data["overrides"][-1]
        if as_json:
            print(json.dumps({"override": last, "override_streak": data["override_streak"]}))
        else:
            print(f"override recorded for {', '.join(last['checks']) or 'no check'} "
                  f"(streak {data['override_streak']}/{gate.MAX_CONSECUTIVE_OVERRIDES})")
        return 0
    try:
        prep = prepare(root, cfg)
    except ValueError as exc:
        return _error(str(exc), as_json)
    print(json.dumps(prep.to_dict(), indent=2) if as_json else render(prep))
    return 0 if prep.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
