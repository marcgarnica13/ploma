"""Onboard apply receipt for ploma: <outputs.dir>/ploma-receipt.json.

Records every project file onboard wrote (repo-relative posix path, apply mode, sha256) so a
later onboard run can tell files it may refresh from files the author has edited by hand.

Usage:
  python3 scripts/receipt.py [--root R] [--json] show
  python3 scripts/receipt.py [--root R] [--json] compare

Exit codes: 0 ok (compare: every file unchanged), 1 no receipt (show) or a file hand_edited or
missing (compare), 2 usage error, missing or invalid ploma.yaml, or a malformed receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ploma_config  # noqa: E402
from state import _atomic_write, _now  # noqa: E402

MODES = ("enforced", "created-once", "merged")
STATES = ("unchanged", "hand_edited", "missing")
FILE_NAME = "ploma-receipt.json"
DEFAULT_VERSION = "0.1.0"


def path(root: Path, cfg: dict) -> Path:
    return Path(ploma_config.resolve(cfg, Path(root))["_paths"]["outputs_dir"]) / FILE_NAME


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def plugin_version() -> str:
    """Version from .claude-plugin/plugin.json beside the scripts dir, else DEFAULT_VERSION."""
    manifest = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(manifest.read_text(encoding="utf-8")).get("version")
    except (OSError, ValueError, AttributeError):
        return DEFAULT_VERSION
    return version if isinstance(version, str) and version else DEFAULT_VERSION


def _norm_path(p: str, where: str) -> str:
    """Repo-relative posix form of p; absolute paths and any '..' part raise ValueError."""
    raw = p.replace("\\", "/")
    pure = PurePosixPath(raw)
    if pure.is_absolute() or PureWindowsPath(p).drive or PureWindowsPath(p).root:
        raise ValueError(f"{where}: receipt path {p!r} must be relative to the repo root")
    if ".." in pure.parts:
        raise ValueError(f"{where}: receipt path {p!r} must not contain '..'")
    rel = pure.as_posix()
    if rel in ("", "."):
        raise ValueError(f"{where}: receipt path {p!r} does not name a file")
    return rel


def _check_entry(entry: Any, where: str) -> None:
    if not isinstance(entry, dict):
        raise ValueError(f"{where}: file entry is not an object")
    for key in ("path", "mode", "sha256"):
        if not isinstance(entry.get(key), str) or not entry[key]:
            raise ValueError(f"{where}: file entry lacks a string {key!r}")
    if entry["mode"] not in MODES:
        raise ValueError(f"{where}: unknown mode {entry['mode']!r}; expected one of {MODES}")


def write(root: Path, cfg: dict, files: list[dict]) -> Path:
    """Write the receipt atomically, replacing any previous one; returns its path."""
    entries = []
    for f in files:
        _check_entry(f, "receipt.write")
        entries.append({"path": _norm_path(f["path"], "receipt.write"), "mode": f["mode"], "sha256": f["sha256"]})
    data = {"ploma_version": plugin_version(), "at": _now(), "files": entries}
    out = path(root, cfg)
    _atomic_write(out, json.dumps(data, indent=2) + "\n")
    return out


def load(root: Path, cfg: dict) -> dict | None:
    """The receipt, or None when none exists. A malformed receipt raises ValueError naming the file."""
    p = path(root, cfg)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"{p}: unreadable receipt ({exc})") from None
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise ValueError(f"{p}: receipt must be an object with a files list")
    for key in ("ploma_version", "at"):
        if not isinstance(data.get(key), str):
            raise ValueError(f"{p}: receipt lacks a string {key!r}")
    for entry in data["files"]:
        _check_entry(entry, str(p))
        _norm_path(entry["path"], str(p))
    return data


def compare(root: Path, cfg: dict) -> list[dict]:
    """[{path, mode, state}] per receipt file; state is unchanged, hand_edited or missing."""
    data = load(root, cfg)
    if data is None:
        return []
    base = Path(root)
    out = []
    for entry in data["files"]:
        target = base / _norm_path(entry["path"], str(path(root, cfg)))
        if not target.is_file():
            state = "missing"
        else:
            state = "unchanged" if sha256_file(target) == entry["sha256"] else "hand_edited"
        out.append({"path": entry["path"], "mode": entry["mode"], "state": state})
    return out


def _error(message: str, as_json: bool, code: int = 2) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"receipt: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Show or compare the ploma onboard apply receipt.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("action", choices=("show", "compare"))
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root)
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        return _error(exc.message, args.json)
    try:
        if args.action == "show":
            data = load(root, cfg)
            if data is None:
                return _error("no receipt yet (onboard has not applied files)", args.json, code=1)
            print(json.dumps(data, indent=2) if args.json else
                  "\n".join([f"ploma {data['ploma_version']} applied at {data['at']}"]
                            + [f"- {f['mode']} {f['path']}" for f in data["files"]]))
            return 0
        rows = compare(root, cfg)
    except ValueError as exc:
        return _error(str(exc), args.json)
    except OSError as exc:
        return _error(f"cannot hash {exc.filename or 'a receipt file'}: {exc.strerror or exc}", args.json)
    if args.json:
        print(json.dumps(rows, indent=2))
    else:
        print("\n".join(f"- {r['state']} {r['path']} ({r['mode']})" for r in rows) or "no receipt files")
    return 0 if all(r["state"] == "unchanged" for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
