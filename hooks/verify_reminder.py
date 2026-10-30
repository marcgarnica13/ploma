#!/usr/bin/env python3
"""PostToolUse hook (edit tools on either host, see _hookutil.classify_tool): remind to verify an edited source file, once per file per 300 s.

.tex -> /ploma:compile; .bib -> /ploma:validate-bib; the pipeline language extension
(python .py, r .r, julia .jl, matlab .m; only with pipeline.enabled) -> the code reviewer.
Skips paths under <outputs.dir>/, .claude/, .ploma/ and docs/. Suffixes compare lower-cased.
Paths come from tool_input.file_path (Claude Code), else from the "*** Add File:" and "*** Update File:"
lines of tool_input.command (Codex apply_patch), relative paths resolved against the payload cwd; one
reminder per file. Silent when neither names a file.
State: .ploma/verify-reminder-cache.json. Exit code: always 0.
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

import posixpath  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import TextIO  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _hookutil as hu  # noqa: E402

DEDUPE_SECONDS = 300
CACHE_FILE = "verify-reminder-cache.json"
LANGUAGE_EXT = {"python": ".py", "r": ".r", "julia": ".jl", "matlab": ".m"}
FIXED_SKIP = (".claude", ".ploma", "docs")
PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+?)\s*$", re.MULTILINE)


def edited_paths(data: dict) -> list[str]:
    """The files an edit tool call changed: file_path, else the apply_patch file lines (against cwd)."""
    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return []
    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path:
        return [file_path]
    patch = tool_input.get("command")
    if not isinstance(patch, str):
        return []
    cwd = data.get("cwd")
    out: list[str] = []
    for m in PATCH_FILE_RE.finditer(patch):
        p = m.group(1)
        if not os.path.isabs(p) and isinstance(cwd, str) and cwd:
            p = os.path.join(cwd, p)
        if p not in out:
            out.append(p)
    return out


def action_for(rel: str, cfg: dict) -> str | None:
    suffix = posixpath.splitext(rel)[1].lower()
    if suffix == ".tex":
        return "Run /ploma:compile"
    if suffix == ".bib":
        return "Run /ploma:validate-bib"
    pipe = cfg.get("pipeline") if isinstance(cfg.get("pipeline"), dict) else {}
    lang = pipe.get("language")
    ext = LANGUAGE_EXT.get(lang.lower()) if isinstance(lang, str) else None
    if pipe.get("enabled") is True and ext and suffix == ext.lower():
        return "Run the code reviewer"
    return None


def _relative(file_path: str, root: Path) -> str | None:
    p = Path(file_path)
    if not p.is_absolute():
        p = root / p
    try:
        rel = os.path.relpath(os.path.normpath(str(p)), os.path.normpath(str(root)))
    except ValueError:
        return None
    rel = rel.replace(os.sep, "/")
    return rel


def skipped(rel: str, cfg: dict) -> bool:
    out = (cfg.get("outputs") or {}).get("dir") if isinstance(cfg.get("outputs"), dict) else None
    prefixes = list(FIXED_SKIP)
    if isinstance(out, str) and out:
        prefixes.append(posixpath.normpath(out.replace("\\", "/")).lower())
    low = rel.lower()
    return any(low == p or low.startswith(p.rstrip("/") + "/") for p in prefixes)


@hu.fail_open
def main(stdin: TextIO | str | None = None, root: Path | None = None, cfg: dict | None = None) -> int:
    data = hu.read_input(stdin)
    if hu.classify_tool(data.get("tool_name")) != "edit":
        return 0
    root = Path(root) if root else hu.project_dir(data)
    if not hu.has_config(root):
        return 0
    paths = edited_paths(data)
    if not paths:
        return 0
    if cfg is None:
        cfg = hu.load_config(root)
    due: list[tuple[str, str]] = []
    for file_path in paths:
        rel = _relative(file_path, root)
        if rel is None or rel.startswith("../") or rel == ".." or skipped(rel, cfg):
            continue
        action = action_for(rel, cfg)
        if action:
            due.append((rel, action))
    if not due:
        return 0
    path = hu.state_dir(root) / CACHE_FILE
    cache = hu.load_json(path)
    now = time.time()
    fresh = {k: v for k, v in cache.items() if isinstance(v, (int, float)) and now - v < DEDUPE_SECONDS}
    messages = []
    for rel, action in due:
        if rel in fresh:
            continue
        fresh[rel] = now
        messages.append(f"Verification reminder: {rel} changed. {action} before marking the task complete.")
    hu.save_json(path, fresh)
    if messages:
        message = "\n".join(messages)
        hu.emit({"systemMessage": message,
                 "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}})
    return 0


if __name__ == "__main__":
    sys.exit(main(_RAW, Path(_ROOT)))
