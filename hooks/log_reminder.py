#!/usr/bin/env python3
"""Stop hook: advisory session-log reminders as {"systemMessage": ...} JSON on stdout (exit 0). Never blocks.

Two reminders, each at most once until the newest log changes: when no log exists under
<outputs.dir>/session_logs/, and after 50 responses without the newest log changing.
Respects stop_hook_active. State: .ploma/log-reminder-state.json, reset when stdin carries a
new session_id. Exit code: always 0.
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
from pathlib import Path  # noqa: E402
from typing import TextIO  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hookutil as hu  # noqa: E402

THRESHOLD = 50
STATE_FILE = "log-reminder-state.json"
DEFAULT_STATE = {"counter": 0, "last_mtime": 0.0, "reminded": False, "no_log_reminded": False}


@hu.fail_open
def main(stdin: TextIO | str | None = None, root: Path | None = None, cfg: dict | None = None) -> int:
    data = hu.read_input(stdin)
    if data.get("stop_hook_active"):
        return 0
    root = Path(root) if root else hu.project_dir(data)
    if not hu.has_config(root):
        return 0
    if cfg is None:
        cfg = hu.load_config(root)
    out = hu.outputs_dir(root, cfg)
    logs_dir = out / "session_logs"
    path = hu.state_dir(root) / STATE_FILE
    state = dict(DEFAULT_STATE)
    state.update(hu.load_json(path))
    state = hu.session_scoped(state, data, DEFAULT_STATE)
    logs = hu.newest(list(logs_dir.glob("*.md"))) if logs_dir.is_dir() else []
    if not logs:
        if not state.get("no_log_reminded"):
            state["no_log_reminded"] = True
            hu.save_json(path, state)
            today = datetime.date.today().isoformat()
            rel = os.path.relpath(logs_dir, root).replace(os.sep, "/")
            hu.emit({"systemMessage": f"[session-log] No session log yet. Consider creating "
                                      f"{rel}/{today}_description.md to capture the goal and key context."})
        return 0
    latest = logs[0]
    mtime = latest.stat().st_mtime
    if mtime != state.get("last_mtime"):
        fresh = dict(DEFAULT_STATE, last_mtime=mtime)
        if state.get("session_id"):
            fresh["session_id"] = state["session_id"]
        hu.save_json(path, fresh)
        return 0
    state["counter"] = int(state.get("counter") or 0) + 1
    if state["counter"] >= THRESHOLD and not state.get("reminded"):
        state["reminded"] = True
        hu.emit({"systemMessage": f"[session-log] {state['counter']} responses without updating "
                                  f"{latest.name}. Consider appending recent progress."})
    hu.save_json(path, state)
    return 0


if __name__ == "__main__":
    sys.exit(main(_RAW, Path(_ROOT)))
