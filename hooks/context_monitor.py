#!/usr/bin/env python3
"""PostToolUse hook (Bash|Task|Agent): coarse context-usage nudges, de-duplicated per session.

At 40, 55 and 65 percent it suggests saving decisions to disk (/ploma:checkpoint (planned, milestone 2)); at 80 an info note; at 90 a caution.
Below 80 percent checks are throttled to one per 60 s. The percentage is a coarse proxy: the
transcript size (4 bytes per token) against PLOMA_CONTEXT_WINDOW_TOKENS (default 1,000,000),
else a tool-call counter against PLOMA_CONTEXT_MAX_TOOL_CALLS (default 400).
State: .ploma/context-monitor-cache.json, reset when stdin carries a new session_id.
Exit code: always 0.
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

import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import TextIO  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hookutil as hu  # noqa: E402

CHECKPOINT_THRESHOLDS = (40, 55, 65)
THRESHOLD_WARN = 80
THRESHOLD_CRITICAL = 90
THROTTLE_INTERVAL = 60
DEFAULT_CONTEXT_WINDOW_TOKENS = 1_000_000
DEFAULT_MAX_TOOL_CALLS = 400
APPROX_BYTES_PER_TOKEN = 4.0
CACHE_FILE = "context-monitor-cache.json"


def _env_int(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, "") or default)
    except ValueError:
        return default
    return value if value > 0 else default


def estimate(data: dict, cache: dict) -> float:
    """Percentage 0-100. Mutates cache (tool-call counter) in the fallback path."""
    transcript = data.get("transcript_path")
    if isinstance(transcript, str) and transcript:
        try:
            tokens = os.path.getsize(transcript) / APPROX_BYTES_PER_TOKEN
            return min(tokens / _env_int("PLOMA_CONTEXT_WINDOW_TOKENS", DEFAULT_CONTEXT_WINDOW_TOKENS) * 100, 100.0)
        except OSError:
            pass
    calls = int(cache.get("tool_calls", 0) or 0) + 1
    cache["tool_calls"] = calls
    return min(calls / _env_int("PLOMA_CONTEXT_MAX_TOOL_CALLS", DEFAULT_MAX_TOOL_CALLS) * 100, 100.0)


def _message(pct: float, cache: dict) -> tuple[str, str] | None:
    shown = cache.setdefault("shown_checkpoint", [])
    for threshold in CHECKPOINT_THRESHOLDS:
        if pct >= threshold and threshold not in shown:
            shown.append(threshold)
            return (f"Context about {pct:.0f}% (approximate). Save decisions and the active plan to disk before "
                    "auto-compaction (/ploma:checkpoint (planned, milestone 2) will automate this).",
                    f"Context usage is about {pct:.0f}% (coarse proxy). If decisions or a reusable finding "
                    "emerged this session, write them to the active plan or session log now so they reach disk "
                    "before auto-compaction; /ploma:checkpoint (planned, milestone 2) is not installed yet.")
    if pct >= THRESHOLD_CRITICAL and not cache.get("shown_warn_90"):
        cache["shown_warn_90"] = True
        return (f"Context about {pct:.0f}% (approximate). Auto-compaction is near; finish the current task at full quality.",
                f"Context about {pct:.0f}% (coarse proxy); auto-compaction is near. Complete the current task without "
                "skipping verification, make sure the session log and active plan are on disk, and summarise key "
                "decisions now. /ploma:status shows where the project stands.")
    if pct >= THRESHOLD_WARN and not cache.get("shown_warn_80"):
        cache["shown_warn_80"] = True
        return (f"Context about {pct:.0f}% (approximate). Auto-compaction will trigger soon; no rush.",
                f"Context about {pct:.0f}% (coarse proxy); auto-compaction will trigger soon. Keep the session log "
                "and active plan current on disk.")
    return None


@hu.fail_open
def main(stdin: TextIO | str | None = None, root: Path | None = None) -> int:
    data = hu.read_input(stdin)
    root = Path(root) if root else hu.project_dir(data)
    if not hu.has_config(root):
        return 0
    path = hu.state_dir(root) / CACHE_FILE
    cache = hu.session_scoped(hu.load_json(path), data)
    pct = estimate(data, cache)
    now = time.time()
    last = cache.get("last_check_time", 0)
    if pct < THRESHOLD_WARN and isinstance(last, (int, float)) and now - last < THROTTLE_INTERVAL:
        hu.save_json(path, cache)
        return 0
    cache["last_check_time"] = now
    msg = _message(pct, cache)
    hu.save_json(path, cache)
    if msg:
        hu.emit({"systemMessage": msg[0],
                 "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg[1]}})
    return 0


if __name__ == "__main__":
    sys.exit(main(_RAW, Path(_ROOT)))
