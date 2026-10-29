#!/usr/bin/env python3
"""PreCompact hook: capture the active plan, current task and recent decisions in .ploma/.

session_context.py surfaces the saved state after compaction. Optional guard: with
PLOMA_PRECOMPACT_BLOCK_ON_DRAFT=1, compaction is blocked once per DRAFT plan (sentinel in
.ploma/precompact-block-sentinel.json). Never writes to project files. Exit code: always 0.
"""
from __future__ import annotations

import json
import os
import sys


def _find_project_dir(data: object) -> str:
    """CLAUDE_PROJECT_DIR, else stdin cwd, else os.getcwd(); then walk up at most 4 parent levels
    (stopping at a directory holding .git) to the first directory with ploma.yaml. os.path only."""
    cwd = data.get("cwd") if isinstance(data, dict) else None
    start = os.environ.get("CLAUDE_PROJECT_DIR") or (cwd if isinstance(cwd, str) and cwd else "") or os.getcwd()
    d = os.path.abspath(start)
    for _ in range(5):
        if os.path.isfile(os.path.join(d, "ploma.yaml")):
            return d
        if os.path.exists(os.path.join(d, ".git")):
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return start


def _early_exit_if_no_config() -> tuple[str, str]:
    """Run as a script: read stdin; exit 0 silently unless a project dir with ploma.yaml is found."""
    try:
        raw = sys.stdin.read()
        try:
            data = json.loads(raw) if raw.strip() else {}
        except ValueError:
            data = {}
        d = _find_project_dir(data)
        if os.path.isfile(os.path.join(d, "ploma.yaml")):
            return raw, d
    except Exception:
        pass
    sys.exit(0)


if __name__ == "__main__":
    _RAW, _ROOT = _early_exit_if_no_config()

import datetime  # noqa: E402
import re  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import TextIO  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hookutil as hu  # noqa: E402

DECISION_RE = re.compile(r"^(?:Decision|Decided):\s*(.+)")
STATE_FILE = "pre-compact-state.json"
SENTINEL_FILE = "precompact-block-sentinel.json"
ENV_BLOCK = "PLOMA_PRECOMPACT_BLOCK_ON_DRAFT"


def find_active_plan(plans_dir: Path) -> dict | None:
    """Among the three newest plans, the first whose **Status:** line is not COMPLETED."""
    plan = hu.active_plan(plans_dir)
    if plan is None:
        return None
    status = plan["status"] if plan["status"] in ("DRAFT", "APPROVED") else None
    return {"plan_path": str(plan["path"]), "plan_name": plan["name"],
            "status": status.lower() if status else "unknown", "current_task": plan["task"]}


def recent_decisions(logs_dir: Path, limit: int = 3) -> list[str]:
    if not logs_dir.is_dir():
        return []
    logs = hu.newest(list(logs_dir.glob("*.md")))
    if not logs:
        return []
    out: list[str] = []
    for line in logs[0].read_text(encoding="utf-8", errors="replace").splitlines()[-50:]:
        m = DECISION_RE.match(line.strip())
        if m:
            out.append(m.group(1).strip()[:200])
    return out[-limit:]


def should_block(state_dir: Path, plan: dict | None) -> tuple[bool, str]:
    if os.environ.get(ENV_BLOCK, "0") != "1" or not plan or plan.get("status") != "draft":
        return False, ""
    sentinel = state_dir / SENTINEL_FILE
    try:
        if sentinel.exists() and json.loads(sentinel.read_text(encoding="utf-8")).get("last_blocked_plan") == plan["plan_path"]:
            return False, ""
    except (OSError, ValueError, AttributeError):
        return False, ""
    try:
        sentinel.write_text(json.dumps({"last_blocked_plan": plan["plan_path"],
                                        "when": datetime.datetime.now().isoformat()}), encoding="utf-8")
    except OSError:
        return False, ""
    reason = (f"Compaction blocked once: the active plan {plan['plan_name']} is still DRAFT. "
              "Approve it (set its status line to **Status:** APPROVED) or run compaction again; "
              f"this guard blocks at most once per DRAFT plan. Unset {ENV_BLOCK} to disable it.")
    return True, reason


@hu.fail_open
def main(stdin: TextIO | str | None = None, root: Path | None = None) -> int:
    data = hu.read_input(stdin)
    root = Path(root) if root else hu.project_dir(data)
    if not hu.has_config(root):
        return 0
    cfg = hu.load_config(root)
    out = hu.outputs_dir(root, cfg)
    plan = find_active_plan(out / "plans")
    decisions = recent_decisions(out / "session_logs")
    sdir = hu.state_dir(root)
    block, reason = should_block(sdir, plan)
    if block:
        sys.stderr.write(f"ploma: {reason}\n")
        hu.emit({"decision": "block", "reason": reason})
        return 0
    hu.save_json(sdir / STATE_FILE, {
        "trigger": data.get("trigger", "auto"),
        "timestamp": datetime.datetime.now().isoformat(),
        "plan_path": plan["plan_path"] if plan else None,
        "plan_status": plan["status"] if plan else None,
        "current_task": plan["current_task"] if plan else None,
        "decisions": decisions,
    })
    lines = ["ploma: context compaction starting; state saved to .ploma/."]
    if plan:
        lines.append(f"  plan: {plan['plan_name']} ({plan['status']})")
        if plan["current_task"]:
            lines.append(f"  next task: {plan['current_task']}")
    for d in decisions:
        lines.append(f"  decision: {d[:100]}")
    sys.stderr.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(_RAW, Path(_ROOT)))
