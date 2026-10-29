"""Lifecycle state for ploma: <outputs.dir>/ploma-state.yaml (spec section 6.2).

Usage:
  python3 scripts/state.py [--root R] record <skill> <status> [--artifact P] [--extra k=v ...]
  python3 scripts/state.py [--root R] next [--json]
  python3 scripts/state.py [--root R] render [--json]

Exit codes: 0 ok, 2 usage error or unreadable input (bad config, unknown skill or status).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import _yamlio
import ploma_config

STATE_VERSION = "0.1"
FILE_NAME = "ploma-state.yaml"
STAGES = ["onboard", "brainstorm", "lit-review", "grill", "spec", "write", "compile", "format",
          "validate", "review", "respond", "commit"]
SKILL_TO_STAGE: dict[str, str | None] = {
    "onboard": "onboard",
    "brainstorm": "brainstorm",
    "lit-review": "lit-review",
    "grill": "grill",
    "spec": "spec",
    "write": "write",
    "compile": "compile",
    "format": "format",
    "validate-bib": "validate",
    "verify-claims": "validate",
    "audit-reproducibility": "validate",
    "proofread": "validate",
    "review": "review",
    "devils-advocate": "review",
    "respond": "respond",
    "commit": "commit",
    # session skills: recorded, never move the stage
    "doctor": None,
    "status": None,
    "checkpoint": None,
    "compress-session": None,
    "learn": None,
    "deep-audit": None,
    "help": None,
}
STATUSES = ("PASS", "WARN", "FAIL", "INFO", "SKIP")
ROUND_SKILLS = ("review", "respond")
RENDER_LIMIT = 600


def _empty() -> dict:
    return {"ploma_state": STATE_VERSION, "stage": None, "rounds": {}, "events": []}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def path(root: Path, cfg: dict) -> Path:
    return Path(ploma_config.resolve(cfg, Path(root))["_paths"]["outputs_dir"]) / FILE_NAME


def load(root: Path, cfg: dict) -> dict:
    """Read the state file; an absent file is the empty state. Raises ValueError when unreadable."""
    p = path(root, cfg)
    if not p.is_file():
        return _empty()
    try:
        data = _yamlio.load_yaml(p)
    except (_yamlio.YamlError, OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{p} could not be read: {exc}") from exc
    if data is None:
        return _empty()
    if not isinstance(data, dict):
        raise ValueError(f"{p} must contain a mapping at the top level")
    st = _empty()
    st.update(data)
    if st["rounds"] is None:
        st["rounds"] = {}
    if st["events"] is None:
        st["events"] = []
    if not isinstance(st["rounds"], dict):
        raise ValueError(f"{p}: 'rounds' must be a mapping, got {type(st['rounds']).__name__}")
    for skill, count in st["rounds"].items():
        if not isinstance(count, int) or isinstance(count, bool):
            raise ValueError(f"{p}: 'rounds.{skill}' must be an integer, got {count!r}")
    if not isinstance(st["events"], list):
        raise ValueError(f"{p}: 'events' must be a list, got {type(st['events']).__name__}")
    for i, event in enumerate(st["events"]):
        if not isinstance(event, dict):
            raise ValueError(f"{p}: 'events.{i}' must be a mapping, got {event!r}")
    if st["stage"] is not None and st["stage"] not in STAGES:
        raise ValueError(f"{p}: 'stage' must be a lifecycle stage or null, got {st['stage']!r}")
    return st


def record(root: Path, cfg: dict, skill: str, status: str, artifact: str | None = None, **extra: Any) -> dict:
    """Append an event, update the stage and review/respond rounds, write atomically, return the state.

    A review or respond event with an integer ``round`` extra sets that skill's round to max(current, round);
    without one, the round increments, except for a ``mode=audit`` event, which leaves it.
    """
    if skill not in SKILL_TO_STAGE:
        raise ValueError(f"unknown skill {skill!r}; known: {', '.join(SKILL_TO_STAGE)}")
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}; use one of {', '.join(STATUSES)}")
    st = load(root, cfg)
    event: dict[str, Any] = {"at": _now(), "skill": skill, "status": status}
    if artifact:
        event["artifact"] = artifact
    for key, value in extra.items():
        if key not in event:
            event[key] = value
    st["events"].append(event)
    stage = SKILL_TO_STAGE[skill]
    if stage is not None:
        st["stage"] = stage
    if skill in ROUND_SKILLS:
        current = int(st["rounds"].get(skill, 0))
        explicit = extra.get("round")
        if isinstance(explicit, int) and not isinstance(explicit, bool):
            # R142: an explicit round sets the round (never lowers it); re-recording a round does not bump it.
            st["rounds"][skill] = max(current, explicit)
        elif extra.get("mode") != "audit":
            st["rounds"][skill] = current + 1
    _atomic_write(path(root, cfg), _yamlio.dump_yaml(st))
    return st


def _events(st: dict) -> list[dict]:
    events = st.get("events")
    return [e for e in events if isinstance(e, dict)] if isinstance(events, list) else []


def latest(st: dict, skill: str) -> dict | None:
    for event in reversed(_events(st)):
        if event.get("skill") == skill:
            return event
    return None


def _latest_for_stage(st: dict, stage: str) -> dict | None:
    for event in reversed(_events(st)):
        if SKILL_TO_STAGE.get(event.get("skill")) == stage:
            return event
    return None


def next_stage(st: dict, cfg: dict | None) -> dict:
    """Recommend the next stage: repeat the current one unless its latest event passed, else advance."""
    current = st.get("stage")
    if current not in STAGES:
        if cfg is None:
            return {"stage": "onboard", "reason": "no ploma.yaml yet"}
        return {"stage": "compile", "reason": "no lifecycle stage recorded yet; start by compiling"}
    last = _latest_for_stage(st, current)
    if last is not None and last.get("status") != "PASS":
        return {"stage": current, "reason": f"last {last.get('skill')} was {last.get('status')}"}
    idx = STAGES.index(current)
    if idx == len(STAGES) - 1:
        return {"stage": "commit", "reason": "cycle complete"}
    return {"stage": STAGES[idx + 1], "reason": f"{current} passed"}


def render(st: dict, cfg: dict | None) -> str:
    """Short human summary (under 600 characters) for the SessionStart hook and /ploma:status."""
    lines = [f"ploma stage: {st.get('stage') or 'none'}"]
    events = _events(st)[-5:]
    if events:
        lines.append("recent:")
        for ev in events:
            lines.append(f"- {ev.get('skill')} {ev.get('status')} {str(ev.get('at', ''))[:10]}")
    rec = next_stage(st, cfg)
    lines.append(f"next: {rec['stage']} ({rec['reason']})")
    text = "\n".join(lines)
    return text if len(text) < RENDER_LIMIT else text[:RENDER_LIMIT - 4] + "..."


def _parse_extra(items: list[str]) -> dict:
    out: dict[str, Any] = {}
    for item in items:
        key, sep, value = item.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"--extra expects k=v, got {item!r}")
        value = value.strip()
        out[key.strip()] = int(value) if re.fullmatch(r"-?\d+", value) else value
    return out


def _error(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"state: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read and write the ploma lifecycle state.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="action")
    rec = sub.add_parser("record", help="append an event")
    rec.add_argument("skill")
    rec.add_argument("status")
    rec.add_argument("--artifact", default=None)
    rec.add_argument("--extra", action="append", default=[], help="extra event field k=v (repeatable)")
    rec.add_argument("--json", action="store_true", dest="json_sub")
    for name in ("next", "render"):
        sp = sub.add_parser(name)
        sp.add_argument("--json", action="store_true", dest="json_sub")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if args.action is None:
        parser.print_usage(sys.stderr)
        return 2
    as_json = args.json or getattr(args, "json_sub", False)
    root = Path(args.root)
    try:
        cfg: dict | None = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        if args.action == "record":
            return _error(exc.message, as_json)
        cfg = None
    try:
        if args.action == "record":
            st = record(root, cfg, args.skill, args.status, artifact=args.artifact, **_parse_extra(args.extra))
            print(json.dumps(st["events"][-1]) if as_json else f"recorded {args.skill} {args.status}")
            return 0
        st = load(root, cfg) if cfg is not None else _empty()
    except ValueError as exc:
        return _error(str(exc), as_json)
    if args.action == "next":
        rec_ = next_stage(st, cfg)
        print(json.dumps(rec_) if as_json else f"{rec_['stage']}: {rec_['reason']}")
        return 0
    text = render(st, cfg)
    print(json.dumps({"render": text, "state": st}, indent=2) if as_json else text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
