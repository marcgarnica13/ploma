"""Shared helpers for ploma hooks. Imported only after a hook has seen ploma.yaml.

Never import ploma_config here at module level: hook modules import this file, and a
hook must stay cheap and silent in repos without ploma.yaml.
"""
from __future__ import annotations

import functools
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, TextIO

CONFIG_NAME = "ploma.yaml"
STATE_DIR = ".ploma"


def read_input(stdin: TextIO | str | None = None) -> dict:
    """Parse the hook JSON from stdin (a stream or raw text). Garbage or non-objects give {}."""
    try:
        if stdin is None:
            stdin = sys.stdin
        raw = stdin if isinstance(stdin, str) else stdin.read()
        data = json.loads(raw) if raw and raw.strip() else {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def project_dir(data: dict) -> Path:
    """Project dir: stdin `cwd`, else CLAUDE_PROJECT_DIR, else the process cwd."""
    cwd = data.get("cwd")
    if isinstance(cwd, str) and cwd:
        return Path(cwd)
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path(os.getcwd())


def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    return Path(env) if env else Path(__file__).resolve().parent.parent


def add_scripts_path(root: Path | None = None) -> None:
    scripts = str((root or plugin_root()) / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


def has_config(root: Path) -> bool:
    return (Path(root) / CONFIG_NAME).is_file()


def load_config(root: Path) -> dict:
    """ploma_config.load(root); raises ploma_config.ConfigError."""
    add_scripts_path()
    import ploma_config
    return ploma_config.load(Path(root))


def outputs_dir(root: Path, cfg: dict) -> Path:
    out = (cfg.get("outputs") or {}).get("dir") if isinstance(cfg.get("outputs"), dict) else None
    return Path(root) / (out if isinstance(out, str) and out else "quality_reports")


def state_dir(root: Path) -> Path:
    d = Path(root) / STATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_json(path: Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_json(path: Path, data: dict) -> None:
    """Atomic write; errors are swallowed (hook state is best effort)."""
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def newest(paths: list[Path]) -> list[Path]:
    """Sort by mtime, newest first, skipping files that vanish mid-sort."""
    stamped = []
    for p in paths:
        try:
            stamped.append((p.stat().st_mtime, p))
        except OSError:
            continue
    return [p for _, p in sorted(stamped, key=lambda t: t[0], reverse=True)]


def emit(obj: dict, out: TextIO | None = None) -> None:
    out = out or sys.stdout
    out.write(json.dumps(obj) + "\n")
    out.flush()


def fail_open(fn: Callable[..., int]) -> Callable[..., int]:
    """Any exception gives exit code 0. Output buffered until success, so a crash prints nothing."""
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> int:
        real = sys.stdout
        buf = io.StringIO()
        sys.stdout = buf
        try:
            fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - hooks must never fail the session
            if isinstance(exc, KeyboardInterrupt):
                raise
            return 0
        finally:
            sys.stdout = real
        real.write(buf.getvalue())
        real.flush()
        return 0
    return wrapper
