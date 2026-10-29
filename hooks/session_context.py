#!/usr/bin/env python3
"""SessionStart and SubagentStart hook: inject eager rules, config summary, status, resume block.

Usage (hooks.json): python3 session_context.py [--subagent]   (hook JSON on stdin)

Prints one JSON object {"hookSpecificOutput": {"hookEventName", "additionalContext"}} or nothing.
Without ploma.yaml it prints the onboard line only when a .tex file sits within two directory
levels of the project dir (SessionStart only), else nothing. Exit code: always 0.
"""
from __future__ import annotations

import json
import os
import sys

ONBOARD_LINE = ("ploma is installed but this repo has no ploma.yaml. "
                "Run /ploma:onboard to set it up, or /ploma:help.")


def _has_tex(d: str, depth: int = 2) -> bool:
    """True when a .tex file exists in d or up to `depth` directory levels below it (no hidden dirs)."""
    try:
        with os.scandir(d) as it:
            subdirs = []
            for entry in it:
                if entry.name.startswith("."):
                    continue
                if entry.is_file(follow_symlinks=False) and entry.name.lower().endswith(".tex"):
                    return True
                if depth > 0 and entry.is_dir(follow_symlinks=False):
                    subdirs.append(entry.path)
    except OSError:
        return False
    return any(_has_tex(s, depth - 1) for s in subdirs)


def _early_exit_if_no_config() -> str:
    """Run as a script: read stdin; without ploma.yaml print at most the onboard line and exit 0."""
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except ValueError:
            data = {}
        if not isinstance(data, dict):
            data = {}
        cwd = data.get("cwd")
        d = cwd if isinstance(cwd, str) and cwd else os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if os.path.isfile(os.path.join(d, "ploma.yaml")):
            return raw
        if "--subagent" not in sys.argv[1:] and _has_tex(d):
            event = data.get("hook_event_name") if isinstance(data.get("hook_event_name"), str) else "SessionStart"
            sys.stdout.write(json.dumps({"hookSpecificOutput": {"hookEventName": event,
                                                               "additionalContext": ONBOARD_LINE}}) + "\n")
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    _RAW = _early_exit_if_no_config()

import re  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import TextIO  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hookutil as hu  # noqa: E402

CAP = 9500
STATUS_RE = re.compile(r"^\*\*Status:\*\*\s*(DRAFT|APPROVED|COMPLETED)\b", re.MULTILINE)


def eager_rules(plugin_root: Path) -> str:
    files = sorted((Path(plugin_root) / "rules" / "eager").glob("*.md"))
    return "\n\n".join(p.read_text(encoding="utf-8").strip() for p in files)


def _status_block(root: Path, cfg: dict) -> str:
    import gate
    import state
    lines = ["## ploma status"]
    try:
        lines.append(state.render(state.load(root, cfg), cfg))
    except Exception as exc:  # noqa: BLE001
        lines.append(f"lifecycle state unavailable: {exc}")
    try:
        report = gate.check(root, cfg)
        fresh = [n for n, c in report.checks.items() if c["present"] and c["fresh"]]
        line = f"commit gate: {report.verdict}; fresh checks: {', '.join(fresh) or 'none'}"
        if report.reasons:
            line += "; blocking: " + "; ".join(report.reasons)
        if report.warnings:
            line += f"; {len(report.warnings)} recommended check(s) missing, stale or not passing"
        lines.append(line)
    except Exception as exc:  # noqa: BLE001
        lines.append(f"commit gate unavailable: {exc}")
    return "\n".join(lines)


def _plan_info(plans_dir: Path) -> dict | None:
    plans = hu.newest(list(plans_dir.glob("*.md"))) if plans_dir.is_dir() else []
    if not plans:
        return None
    text = plans[0].read_text(encoding="utf-8", errors="replace")
    m = STATUS_RE.search(text)
    task = next((ln.split("- [ ]", 1)[1].strip() for ln in text.splitlines()
                 if ln.lstrip().startswith("- [ ]")), None)
    return {"name": plans[0].name, "status": m.group(1) if m else "unknown", "task": task}


def _resume_block(root: Path, cfg: dict, source: str) -> str:
    out = hu.outputs_dir(root, cfg)
    rel = os.path.relpath(out, root)
    lines = ["## Resuming", f"Session source: {source}."]
    saved = hu.load_json(Path(root) / hu.STATE_DIR / "pre-compact-state.json")
    if saved:
        if saved.get("plan_path"):
            lines.append(f"Before compaction: plan {saved['plan_path']} ({saved.get('plan_status')})")
        if saved.get("current_task"):
            lines.append(f"Task in progress: {saved['current_task']}")
        for d in (saved.get("decisions") or [])[-3:]:
            lines.append(f"- decision: {d}")
    plan = _plan_info(out / "plans")
    if plan:
        lines.append(f"Newest plan: {rel}/plans/{plan['name']} (status {plan['status']})")
        if plan["task"]:
            lines.append(f"Next unchecked item: {plan['task']}")
    else:
        lines.append(f"No plan under {rel}/plans/.")
    logs_dir = out / "session_logs"
    logs = hu.newest(list(logs_dir.glob("*.md"))) if logs_dir.is_dir() else []
    lines.append(f"Newest session log: {rel}/session_logs/{logs[0].name}" if logs else "No session log yet.")
    lines.append("Recover: read the newest plan, check `git log --oneline -10` and `git diff`, "
                 "state the current task, then continue.")
    return "\n".join(lines)


def _fit(head: str, status: str, resume: str, cap: int = CAP) -> str:
    """Join blocks under cap: shrink status first, then resume. head (rules + project) is never cut."""
    def join(*parts: str) -> str:
        return "\n\n".join(p for p in parts if p)

    marker = "\n[truncated]"
    text = join(head, status, resume)
    if len(text) < cap:
        return text
    room = cap - len(join(head, "", resume)) - 2 - len(marker) - 1
    status = status[:room] + marker if room > 40 else ""
    text = join(head, status, resume)
    if len(text) < cap:
        return text
    room = cap - len(head) - 2 - len(marker) - 1
    resume = resume[:room] + marker if room > 40 else ""
    return join(head, resume)


def build_context(root: Path, *, subagent: bool, source: str, plugin_root: Path) -> str:
    root = Path(root)
    if not hu.has_config(root):
        return "" if subagent or not _has_tex(str(root)) else ONBOARD_LINE
    hu.add_scripts_path(Path(plugin_root))
    import ploma_config
    rules = eager_rules(plugin_root)
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        msg = exc.message.replace("\n", " ")
        notice = msg if "could not be parsed" in msg else f"ploma.yaml could not be parsed: {msg}"
        return "\n\n".join([rules, "## ploma project", notice[:1000] + " Fix it or run /ploma:doctor."])
    head = rules + "\n\n## ploma project\n" + ploma_config.summary(cfg)
    if subagent:
        return head
    status = _status_block(root, cfg)
    resume = _resume_block(root, cfg, source) if source in ("compact", "resume") else ""
    return _fit(head, status, resume)


@hu.fail_open
def main(stdin: TextIO | str | None = None, plugin_root: Path | None = None,
         argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    data = hu.read_input(stdin)
    subagent = "--subagent" in argv
    event = data.get("hook_event_name")
    if not isinstance(event, str) or not event:
        event = "SubagentStart" if subagent else "SessionStart"
    source = data.get("source") if isinstance(data.get("source"), str) else "startup"
    text = build_context(hu.project_dir(data), subagent=subagent, source=source,
                         plugin_root=Path(plugin_root) if plugin_root else hu.plugin_root())
    if text:
        hu.emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})
    return 0


if __name__ == "__main__":
    sys.exit(main(_RAW))
