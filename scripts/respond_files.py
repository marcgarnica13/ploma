#!/usr/bin/env python3
"""File steps of /ploma:respond that must not need a shell rm or mv (Ruling R158).

Usage:
  python3 scripts/respond_files.py [--root R] archive-round <N> [--json]
  python3 scripts/respond_files.py clean-tmp <path> [<path> ...] [--json]

archive-round renames <outputs.dir>/response_to_referees.md to response_to_referees_r<N>.md and
response_to_referees_matrix.csv to response_to_referees_matrix_r<N>.csv, so a new referee round
starts from a fresh document. It refuses when an archive of round <N> already exists or when there is
no response document.

clean-tmp deletes temporary files made with mktemp: each path must be a regular file (not a link)
directly inside the system temporary directory ($TMPDIR, else /tmp) whose name mktemp gives (tmp.*,
or ploma-respond* from mktemp -t). Any other path is refused and left alone; the rest are deleted.

Exit codes: 0 done, 1 refused (an archive exists, nothing to archive, a path that is not a temporary
file), 2 usage error or unreadable ploma.yaml.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ploma_config  # noqa: E402

RESPONSE = "response_to_referees.md"
MATRIX = "response_to_referees_matrix.csv"
TMP_PREFIXES = ("tmp.", "ploma-respond")


class Refused(Exception):
    """The step was refused; nothing was changed (CLI exit 1)."""


def archive_round(root: Path, cfg: dict, n: int) -> list[tuple[str, str]]:
    """Rename the response and its matrix to their _r<n> names; return (old, new) pairs."""
    if n < 1:
        raise ValueError("the round must be a positive integer")
    out = Path(ploma_config.resolve(cfg, Path(root))["_paths"]["outputs_dir"])
    pairs = [(out / RESPONSE, out / f"response_to_referees_r{n}.md"),
             (out / MATRIX, out / f"response_to_referees_matrix_r{n}.csv")]
    if not pairs[0][0].is_file():
        raise Refused(f"no {RESPONSE} under {out} to archive")
    for _, new in pairs:
        if new.exists():
            raise Refused(f"{new.name} already exists; round {n} is archived already")
    done = []
    for old, new in pairs:
        if old.is_file():
            old.rename(new)
            done.append((str(old), str(new)))
    return done


def _tmp_dir() -> Path:
    return Path(os.environ.get("TMPDIR") or tempfile.gettempdir() or "/tmp").resolve()


def clean_tmp(paths: list[str]) -> tuple[list[str], list[str]]:
    """Delete each path that is a mktemp file in the temporary directory; return (deleted, refused)."""
    bases = {_tmp_dir(), Path("/tmp").resolve()}
    deleted: list[str] = []
    refused: list[str] = []
    for raw in paths:
        p = Path(raw)
        ok = (p.name.startswith(TMP_PREFIXES) and not p.is_symlink() and p.is_file()
              and p.parent.resolve() in bases)
        if not ok:
            refused.append(raw)
            continue
        p.unlink()
        deleted.append(raw)
    return deleted, refused


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Archive a response round; delete respond's temporary files.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="action")
    arc = sub.add_parser("archive-round", help="rename the response files to their _r<N> names")
    arc.add_argument("round", type=int)
    arc.add_argument("--json", action="store_true", dest="json_sub")
    cln = sub.add_parser("clean-tmp", help="delete mktemp files in the temporary directory")
    cln.add_argument("paths", nargs="+")
    cln.add_argument("--json", action="store_true", dest="json_sub")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if args.action is None:
        parser.print_usage(sys.stderr)
        return 2
    as_json = args.json or args.json_sub

    def say(data: dict, text: str, code: int) -> int:
        print(json.dumps(data) if as_json else text, file=sys.stdout if as_json or code == 0 else sys.stderr)
        return code

    if args.action == "clean-tmp":
        deleted, refused = clean_tmp(args.paths)
        text = "\n".join([f"deleted {p}" for p in deleted] + [f"refused (not a temporary file) {p}" for p in refused])
        return say({"deleted": deleted, "refused": refused}, text, 1 if refused else 0)
    try:
        cfg = ploma_config.load(Path(args.root))
        done = archive_round(Path(args.root), cfg, args.round)
    except ploma_config.ConfigError as exc:
        return say({"error": exc.message}, f"respond_files: {exc.message}", 2)
    except ValueError as exc:
        return say({"error": str(exc)}, f"respond_files: {exc}", 2)
    except Refused as exc:
        return say({"error": str(exc)}, f"respond_files: {exc}", 1)
    except OSError as exc:
        return say({"error": str(exc)}, f"respond_files: {exc}", 2)
    return say({"renamed": [{"from": a, "to": b} for a, b in done]},
               "\n".join(f"renamed {a} -> {b}" for a, b in done), 0)


if __name__ == "__main__":
    sys.exit(main())
