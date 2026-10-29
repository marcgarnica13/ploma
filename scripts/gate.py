"""Commit gate verdict for ploma: <outputs.dir>/verdicts/commit-gate.json (spec section 6.3).

Usage:
  python3 scripts/gate.py [--root R] record <check> <status> --artifact P [--extra k=v ...]
  python3 scripts/gate.py [--root R] check [--json]
  python3 scripts/gate.py [--root R] override --reason R --checks a,b

Exit codes: 0 ok (check: verdict PASS), 1 check verdict FAIL or INCOMPLETE, or override refused
after MAX_CONSECUTIVE_OVERRIDES, 2 usage error or unreadable input.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import ploma_config
from state import _atomic_write, _now, _parse_extra

SCHEMA_VERSION = 1
REQUIRED = ("compile", "bib")
RECOMMENDED = ("consistency", "claims", "proofread")
MAX_CONSECUTIVE_OVERRIDES = 3
STATUSES = ("PASS", "WARN", "FAIL")
SOURCE_SUFFIXES = (".tex", ".bib")
SUGGESTION_SUFFIX = "_suggestion.tex"
GIT_TIMEOUT = 5  # seconds per git call; gate.check runs inside the 10 s SessionStart hook
PRUNED_DIRS = frozenset({"node_modules", ".venv", "venv", "__pycache__", "build", "dist"})


def path(root: Path, cfg: dict) -> Path:
    return Path(ploma_config.resolve(cfg, Path(root))["_paths"]["outputs_dir"]) / "verdicts" / "commit-gate.json"


def _empty() -> dict:
    return {"schema": SCHEMA_VERSION, "manuscript_sha": None, "checks": {}, "overrides": [], "override_streak": 0}


def _git_ignored(base: Path, rels: list[str]) -> set[str]:
    """Paths among rels that git ignores, or an empty set when base is not in a git work tree."""
    if not rels:
        return set()
    try:
        probe = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], cwd=str(base),
                               capture_output=True, text=True, timeout=GIT_TIMEOUT)
        if probe.returncode != 0 or probe.stdout.strip() != "true":
            return set()
        payload = b"".join(os.fsencode(r) + b"\0" for r in rels)
        res = subprocess.run(["git", "check-ignore", "-z", "--stdin"], cwd=str(base), input=payload,
                             capture_output=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return set()
    if res.returncode not in (0, 1):
        return set()
    return {os.fsdecode(item) for item in res.stdout.split(b"\0") if item}


def manuscript_sha(root: Path, cfg: dict) -> str:
    """sha256 over sorted relative paths and contents of .tex/.bib under document.root,
    excluding *_suggestion.tex and gitignored files. Hidden directories (.git, .venv, ...) and
    node_modules, venv, __pycache__, build, dist are not walked."""
    base_s = ploma_config.resolve(cfg, Path(root))["_paths"]["root"]
    digest = hashlib.sha256()
    if not base_s or not Path(base_s).is_dir():
        return digest.hexdigest()
    base = Path(base_s)
    rels: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in PRUNED_DIRS]
        for name in filenames:
            if name.endswith(SOURCE_SUFFIXES) and not name.endswith(SUGGESTION_SUFFIX):
                rels.append((Path(dirpath) / name).relative_to(base).as_posix())
    ignored = _git_ignored(base, rels)
    for rel in sorted(r for r in rels if r not in ignored):
        digest.update(rel.encode("utf-8") + b"\0")
        digest.update((base / rel).read_bytes() + b"\0")
    return digest.hexdigest()


def load(root: Path, cfg: dict) -> dict:
    p = path(root, cfg)
    if not p.is_file():
        return _empty()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{p} could not be read: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{p} must contain a JSON object")
    out = _empty()
    out.update(data)
    if not isinstance(out["checks"], dict):
        raise ValueError(f"{p}: 'checks' must be an object, got {type(out['checks']).__name__}")
    for name, entry in out["checks"].items():
        if not isinstance(entry, dict):
            raise ValueError(f"{p}: 'checks.{name}' must be an object, got {type(entry).__name__}")
    if not isinstance(out["overrides"], list):
        raise ValueError(f"{p}: 'overrides' must be a list, got {type(out['overrides']).__name__}")
    streak = out["override_streak"]
    if not isinstance(streak, int) or isinstance(streak, bool) or streak < 0:
        raise ValueError(f"{p}: 'override_streak' must be a non-negative integer, got {streak!r}")
    return out


def _write(root: Path, cfg: dict, data: dict) -> None:
    _atomic_write(path(root, cfg), json.dumps(data, indent=2) + "\n")


def record(root: Path, cfg: dict, check: str, status: str, artifact: str, **extra: Any) -> dict:
    """Write one check entry stamped with time and the current manuscript sha; return the verdict data."""
    if check not in REQUIRED + RECOMMENDED:
        raise ValueError(f"unknown check {check!r}; known: {', '.join(REQUIRED + RECOMMENDED)}")
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}; use one of {', '.join(STATUSES)}")
    data = load(root, cfg)
    sha = manuscript_sha(root, cfg)
    entry: dict[str, Any] = {"status": status, "at": _now(), "artifact": artifact, "manuscript_sha": sha}
    for key, value in extra.items():
        if key not in entry:
            entry[key] = value
    data["checks"][check] = entry
    data["manuscript_sha"] = sha
    if check in REQUIRED and status == "PASS":
        data["override_streak"] = 0
    _write(root, cfg, data)
    return data


def reset_streak(root: Path, cfg: dict) -> dict:
    data = load(root, cfg)
    data["override_streak"] = 0
    _write(root, cfg, data)
    return data


class OverrideRefused(ValueError):
    """An override the gate refuses (consecutive-override cap reached); CLI exit 1, not a usage error."""


def override(root: Path, cfg: dict, reason: str, checks: list[str]) -> dict:
    """Record a `commit anyway: <reason>` override; refused once the streak reaches the cap."""
    if not reason or not reason.strip():
        raise ValueError("an override needs a reason")
    data = load(root, cfg)
    streak = int(data.get("override_streak") or 0)
    if streak >= MAX_CONSECUTIVE_OVERRIDES:
        raise OverrideRefused(f"{streak} consecutive overrides; a required check must pass before the next commit")
    data["overrides"].append({"at": _now(), "reason": reason.strip(), "checks": list(checks)})
    data["override_streak"] = streak + 1
    _write(root, cfg, data)
    return data


@dataclasses.dataclass
class GateReport:
    checks: dict[str, dict]
    verdict: str
    warnings: list[str]
    reasons: list[str]
    override_streak: int
    can_override: bool
    manuscript_sha: str

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


def check(root: Path, cfg: dict) -> GateReport:
    data = load(root, cfg)
    sha = manuscript_sha(root, cfg)
    checks: dict[str, dict] = {}
    for name in REQUIRED + RECOMMENDED:
        entry = data["checks"].get(name)
        present = isinstance(entry, dict)
        checks[name] = {"status": entry.get("status") if present else None,
                        "fresh": present and entry.get("manuscript_sha") == sha,
                        "required": name in REQUIRED, "present": present}
    failed: list[str] = []
    incomplete: list[str] = []
    for name in REQUIRED:
        c = checks[name]
        if not c["present"]:
            incomplete.append(f"{name}: missing (required)")
        elif not c["fresh"]:
            incomplete.append(f"{name}: stale, manuscript changed since it ran (required)")
        elif c["status"] == "FAIL":
            failed.append(f"{name}: FAIL (required)")
        elif c["status"] not in ("PASS", "WARN"):
            incomplete.append(f"{name}: invalid status {c['status']!r} (required; re-run it)")
    verdict = "FAIL" if failed else "INCOMPLETE" if incomplete else "PASS"
    warnings: list[str] = []
    for name in RECOMMENDED:
        c = checks[name]
        if not c["present"]:
            warnings.append(f"{name}: missing (recommended)")
        elif not c["fresh"]:
            warnings.append(f"{name}: stale, manuscript changed since it ran (recommended)")
        elif c["status"] in ("WARN", "FAIL"):
            warnings.append(f"{name}: {c['status']} (recommended)")
        elif c["status"] != "PASS":
            warnings.append(f"{name}: invalid status {c['status']!r} (recommended)")
    streak = int(data.get("override_streak") or 0)
    return GateReport(checks, verdict, warnings, failed + incomplete, streak, streak < MAX_CONSECUTIVE_OVERRIDES, sha)


def render(report: GateReport) -> str:
    lines = [f"commit gate: {report.verdict}"]
    for name, c in report.checks.items():
        kind = "required" if c["required"] else "recommended"
        state = "missing" if not c["present"] else f"{c['status']} {'FRESH' if c['fresh'] else 'STALE'}"
        lines.append(f"- {name} ({kind}): {state}")
    for r in report.reasons:
        lines.append(f"blocking: {r}")
    for w in report.warnings:
        lines.append(f"warning: {w}")
    lines.append(f"override streak: {report.override_streak}/{MAX_CONSECUTIVE_OVERRIDES}"
                 + ("" if report.can_override else " (overrides refused until a required check passes)"))
    return "\n".join(lines)


def _error(message: str, as_json: bool, code: int = 2) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"gate: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record, check and override the ploma commit gate.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="action")
    rec = sub.add_parser("record", help="write one check entry")
    rec.add_argument("check")
    rec.add_argument("status")
    rec.add_argument("--artifact", required=True)
    rec.add_argument("--extra", action="append", default=[], help="extra entry field k=v (repeatable)")
    rec.add_argument("--json", action="store_true", dest="json_sub")
    chk = sub.add_parser("check", help="report freshness and the verdict")
    chk.add_argument("--json", action="store_true", dest="json_sub")
    ovr = sub.add_parser("override", help="record a commit anyway override")
    ovr.add_argument("--reason", required=True)
    ovr.add_argument("--checks", required=True, help="comma-separated overridden checks")
    ovr.add_argument("--json", action="store_true", dest="json_sub")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if args.action is None:
        parser.print_usage(sys.stderr)
        return 2
    as_json = args.json or args.json_sub
    root = Path(args.root)
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        return _error(exc.message, as_json)
    try:
        if args.action == "record":
            data = record(root, cfg, args.check, args.status, args.artifact, **_parse_extra(args.extra))
            print(json.dumps(data["checks"][args.check]) if as_json else f"recorded {args.check} {args.status}")
            return 0
        if args.action == "override":
            checks = [c.strip() for c in args.checks.split(",") if c.strip()]
            try:
                data = override(root, cfg, args.reason, checks)
            except ValueError as exc:
                return _error(str(exc), as_json, code=1 if isinstance(exc, OverrideRefused) else 2)
            if as_json:
                print(json.dumps({"override": data["overrides"][-1], "override_streak": data["override_streak"]}))
            else:
                print(f"override recorded (streak {data['override_streak']}/{MAX_CONSECUTIVE_OVERRIDES})")
            return 0
        report = check(root, cfg)
    except ValueError as exc:
        return _error(str(exc), as_json)
    print(json.dumps(report.to_dict(), indent=2) if as_json else render(report))
    return 0 if report.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
