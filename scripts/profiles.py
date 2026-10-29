"""Venue profiles and discipline cards for ploma (spec section 12).

Shipped data lives in venues/<key>.yaml and disciplines/<key>.yaml beside this plugin; a project
file at <root>/ploma.d/venues/<key>.yaml (or ploma.d/disciplines/<key>.yaml) shadows the shipped
one with the same key.

Usage:
  python3 scripts/profiles.py [--root R] [--json] list
  python3 scripts/profiles.py [--root R] [--json] show <venue-key>
  python3 scripts/profiles.py [--root R] [--json] validate [<venue-key> ...]
  python3 scripts/profiles.py [--root R] [--json] for-class <doc-class>

Exit codes: 0 ok, 1 validate found a FAIL, 2 usage error, unknown key or unreadable profile.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yamlio  # noqa: E402
from _findings import FAIL, PASS, WARN, Finding, render, worst  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
VENUES_DIR = PLUGIN_ROOT / "venues"
DISCIPLINES_DIR = PLUGIN_ROOT / "disciplines"

VENUE_KEYS = ("key", "name", "kind", "doc_classes", "cite_style", "page_budget", "anonymized",
              "bib_style_hint", "focus", "bar", "referee_pool", "domain_adjustments",
              "methods_adjustments", "typical_concerns", "peeves", "format_rules", "submission_checks")
DISCIPLINE_KEYS = ("key", "name", "paper_types", "default_paper_type", "reproducibility_norms",
                   "method_conventions", "challenge_examples", "peeves")
POOL_KEYS = ("EVALUATION", "METHODOLOGY", "REPRODUCIBILITY", "NOVELTY", "SKEPTIC", "CLARITY")
KINDS = ("journal", "conference", "workshop", "preprint")
CITE_STYLES = ("numeric", "author-year")
POOL_TOLERANCE = 0.001

# venues_for_class order: specific shipped profiles, then project-only profiles (sorted), then
# the generics, arxiv last so a plain article class recommends generic-journal (Ruling R43).
SPECIFIC = ("llncs-conference", "springer-ml", "ieee-conference", "acm-sigconf", "elsevier")
FALLBACK = ("generic-journal", "generic-conference", "arxiv")

_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class ProfileError(Exception):
    """Unknown key or unreadable profile file."""


def _dirs(kind: str, root: Path | None) -> list[Path]:
    shipped = VENUES_DIR if kind == "venues" else DISCIPLINES_DIR
    dirs = [shipped]
    if root is not None:
        dirs.insert(0, Path(root) / "ploma.d" / kind)
    return dirs


def _keys(kind: str, root: Path | None) -> list[str]:
    keys = set()
    for d in _dirs(kind, root):
        if d.is_dir():
            keys.update(p.stem for p in d.glob("*.yaml") if p.is_file())
    return sorted(keys)


def _load(kind: str, key: str, root: Path | None) -> dict:
    label = "venue" if kind == "venues" else "discipline"
    available = ", ".join(_keys(kind, root)) or "none"
    if not isinstance(key, str) or not _KEY_RE.match(key):
        raise ProfileError(f"invalid {label} key {key!r}; available: {available}")
    for d in _dirs(kind, root):
        p = d / f"{key}.yaml"
        if p.is_file():
            try:
                data = _yamlio.load_yaml(p)
            except (OSError, UnicodeDecodeError, _yamlio.YamlError) as exc:
                raise ProfileError(f"{p}: unreadable {label} profile ({exc})") from None
            if not isinstance(data, dict):
                raise ProfileError(f"{p}: a {label} profile must be a mapping")
            return data
    raise ProfileError(f"unknown {label} {key!r}; available: {available}")


def load_venue(key: str, root: Path | None) -> dict:
    """Venue profile by key; <root>/ploma.d/venues/<key>.yaml shadows the shipped file."""
    return _load("venues", key, root)


def load_discipline(key: str, root: Path | None) -> dict:
    """Discipline card by key; <root>/ploma.d/disciplines/<key>.yaml shadows the shipped file."""
    return _load("disciplines", key, root)


def list_venues(root: Path | None) -> list[str]:
    return _keys("venues", root)


def list_disciplines(root: Path | None) -> list[str]:
    return _keys("disciplines", root)


def venues_for_class(doc_class: str | None, root: Path | None) -> list[str]:
    """Venue keys whose doc_classes include doc_class, most specific first. Unreadable files are skipped."""
    if not doc_class:
        return []
    matches = []
    for key in list_venues(root):
        try:
            classes = load_venue(key, root).get("doc_classes")
        except ProfileError:
            continue
        if isinstance(classes, list) and doc_class in classes:
            matches.append(key)
    rank = {k: i for i, k in enumerate(SPECIFIC)}
    rank.update({k: len(SPECIFIC) + 1 + i for i, k in enumerate(FALLBACK)})
    return sorted(matches, key=lambda k: (rank.get(k, len(SPECIFIC)), k))


# Validation ---------------------------------------------------------------------------------

def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _is_num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _is_str_list(v: Any) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


class _V:
    def __init__(self, prefix: str) -> None:
        self.prefix = prefix
        self.out: list[Finding] = []

    def fail(self, field: str, summary: str, observed: Any = "", remediation: str = "") -> None:
        self.out.append(Finding(f"{self.prefix}.{field}", FAIL, summary,
                                observed="" if observed == "" else repr(observed),
                                remediation=remediation or f"Fix {field} in the {self.prefix} profile.",
                                group="profiles"))

    def warn(self, field: str, summary: str, remediation: str) -> None:
        self.out.append(Finding(f"{self.prefix}.{field}", WARN, summary, remediation=remediation,
                                group="profiles"))

    def str_list(self, d: dict, field: str) -> None:
        if field in d and not _is_str_list(d[field]):
            self.fail(field, f"{field} must be a list of non-empty strings", d[field])

    def peeves(self, d: dict) -> None:
        p = d.get("peeves")
        if "peeves" not in d:
            return
        if not isinstance(p, dict) or set(p) != {"critical", "constructive"}:
            self.fail("peeves", "peeves must be a mapping with exactly critical and constructive", p)
            return
        for side in ("critical", "constructive"):
            if not _is_str_list(p[side]):
                self.fail(f"peeves.{side}", f"peeves.{side} must be a list of non-empty strings", p[side])

    def keys(self, d: dict, expected: tuple[str, ...]) -> None:
        for k in expected:
            if k not in d:
                self.fail(k, f"{k} is required", remediation=f"Add {k} to the {self.prefix} profile.")
        for k in d:
            if k not in expected:
                self.warn(str(k), f"{k} is not a known {self.prefix} key",
                          "Check the spelling; unknown keys are ignored.")


def _check_adjustments(v: _V, d: dict, field: str) -> None:
    if field not in d:
        return
    adj = d[field]
    if not isinstance(adj, dict):
        v.fail(field, f"{field} must map a dimension to [from, to]", adj)
        return
    for dim, pair in adj.items():
        if not (isinstance(pair, list) and len(pair) == 2 and all(_is_int(x) and 0 <= x <= 100 for x in pair)):
            v.fail(f"{field}.{dim}", f"{field}.{dim} must be a [from, to] pair of integers 0..100", pair)


def _check_pool(v: _V, d: dict) -> None:
    if "referee_pool" not in d:
        return
    pool = d["referee_pool"]
    if not isinstance(pool, dict):
        v.fail("referee_pool", "referee_pool must map each disposition to a weight", pool)
        return
    unknown = [k for k in pool if k not in POOL_KEYS]
    missing = [k for k in POOL_KEYS if k not in pool]
    if unknown:
        v.fail("referee_pool", f"referee_pool has unknown dispositions: {', '.join(map(str, unknown))}",
               remediation=f"Use exactly {', '.join(POOL_KEYS)}.")
    if missing:
        v.fail("referee_pool", f"referee_pool lacks dispositions: {', '.join(missing)}",
               remediation=f"Use exactly {', '.join(POOL_KEYS)}.")
    bad = {k: w for k, w in pool.items() if not (_is_num(w) and 0 <= w <= 1)}
    if bad:
        v.fail("referee_pool.weights", "referee_pool weights must be numbers between 0 and 1", bad)
        return
    total = sum(pool.values())
    if abs(total - 1.0) > POOL_TOLERANCE:
        v.fail("referee_pool.sum", f"referee_pool weights sum to {total:.3f}, not 1.0", total,
               "Re-weight the dispositions so they sum to 1.0.")


def validate_venue(d: Any) -> list[Finding]:
    """Shape findings for a venue profile; FAIL entries make it unusable. Empty when valid."""
    v = _V("venue")
    if not isinstance(d, dict):
        v.fail("shape", "a venue profile must be a mapping", type(d).__name__)
        return v.out
    v.keys(d, VENUE_KEYS)
    if "key" in d and not (isinstance(d["key"], str) and _KEY_RE.match(d["key"])):
        v.fail("key", "key must be lowercase letters, digits, - or _", d["key"])
    for field in ("name", "focus", "bar"):
        if field in d and not (isinstance(d[field], str) and d[field].strip()):
            v.fail(field, f"{field} must be a non-empty string", d[field])
    if "kind" in d and d["kind"] not in KINDS:
        v.fail("kind", f"kind must be one of {', '.join(KINDS)}", d["kind"])
    if "doc_classes" in d and not (_is_str_list(d["doc_classes"]) and d["doc_classes"]):
        v.fail("doc_classes", "doc_classes must be a non-empty list of class names", d["doc_classes"])
    if "cite_style" in d and d["cite_style"] not in CITE_STYLES:
        v.fail("cite_style", f"cite_style must be one of {', '.join(CITE_STYLES)}", d["cite_style"])
    if "page_budget" in d and not (d["page_budget"] is None or (_is_int(d["page_budget"]) and d["page_budget"] > 0)):
        v.fail("page_budget", "page_budget must be a positive integer or null", d["page_budget"])
    if "anonymized" in d and not isinstance(d["anonymized"], bool):
        v.fail("anonymized", "anonymized must be true or false", d["anonymized"])
    if "bib_style_hint" in d and not (d["bib_style_hint"] is None or isinstance(d["bib_style_hint"], str)):
        v.fail("bib_style_hint", "bib_style_hint must be a string or null", d["bib_style_hint"])
    _check_pool(v, d)
    _check_adjustments(v, d, "domain_adjustments")
    _check_adjustments(v, d, "methods_adjustments")
    for field in ("typical_concerns", "format_rules", "submission_checks"):
        v.str_list(d, field)
    v.peeves(d)
    return v.out


def validate_discipline(d: Any) -> list[Finding]:
    """Shape findings for a discipline card; FAIL entries make it unusable. Empty when valid."""
    v = _V("discipline")
    if not isinstance(d, dict):
        v.fail("shape", "a discipline card must be a mapping", type(d).__name__)
        return v.out
    v.keys(d, DISCIPLINE_KEYS)
    if "key" in d and not (isinstance(d["key"], str) and _KEY_RE.match(d["key"])):
        v.fail("key", "key must be lowercase letters, digits, - or _", d["key"])
    if "name" in d and not (isinstance(d["name"], str) and d["name"].strip()):
        v.fail("name", "name must be a non-empty string", d["name"])
    types = d.get("paper_types")
    type_keys: list[str] = []
    if "paper_types" in d:
        if not (isinstance(types, list) and types):
            v.fail("paper_types", "paper_types must be a non-empty list", types)
            types = []
        for i, pt in enumerate(types):
            where = f"paper_types.{i}"
            if not isinstance(pt, dict):
                v.fail(where, "each paper type must be a mapping", pt)
                continue
            for field in ("key", "name"):
                if not (isinstance(pt.get(field), str) and pt[field].strip()):
                    v.fail(f"{where}.{field}", f"{where}.{field} must be a non-empty string", pt.get(field))
            if isinstance(pt.get("key"), str):
                type_keys.append(pt["key"])
            weights = pt.get("weights")
            if not (isinstance(weights, dict) and weights and all(_is_int(w) and w >= 0 for w in weights.values())):
                v.fail(f"{where}.weights", f"{where}.weights must map dimensions to integer percentages", weights)
            elif sum(weights.values()) != 100:
                v.fail(f"{where}.weights", f"{where}.weights sum to {sum(weights.values())}, not 100",
                       sum(weights.values()))
            if not (_is_str_list(pt.get("sanity_checks")) and pt["sanity_checks"]):
                v.fail(f"{where}.sanity_checks", f"{where}.sanity_checks must be a non-empty list of strings",
                       pt.get("sanity_checks"))
            extra = set(pt) - {"key", "name", "weights", "sanity_checks"}
            if extra:
                v.warn(f"{where}.unknown", f"{where} has unknown keys: {', '.join(sorted(map(str, extra)))}",
                       "Check the spelling; unknown keys are ignored.")
    if "default_paper_type" in d and d["default_paper_type"] not in type_keys:
        v.fail("default_paper_type", "default_paper_type must name one of the paper_types keys",
               d["default_paper_type"])
    for field in ("reproducibility_norms", "method_conventions", "challenge_examples"):
        v.str_list(d, field)
    v.peeves(d)
    return v.out


# CLI ----------------------------------------------------------------------------------------

def _error(message: str, as_json: bool, code: int = 2) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"profiles: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="List, show and validate ploma venue profiles.")
    parser.add_argument("--root", default=None, help="repo root whose ploma.d/ shadows shipped profiles")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("list", help="venue keys, shipped and project")
    show = sub.add_parser("show", help="one venue profile")
    show.add_argument("key")
    val = sub.add_parser("validate", help="validate venue profiles (all when none named) and discipline cards")
    val.add_argument("keys", nargs="*")
    fc = sub.add_parser("for-class", help="venue keys for a document class")
    fc.add_argument("doc_class")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if args.action is None:
        parser.print_usage(sys.stderr)
        return 2
    root = Path(args.root) if args.root else None
    if root is not None and not root.is_dir():
        return _error(f"root {root} is not a directory", args.json)
    try:
        if args.action == "list":
            keys = list_venues(root)
            print(json.dumps(keys) if args.json else "\n".join(keys))
            return 0
        if args.action == "for-class":
            keys = venues_for_class(args.doc_class, root)
            print(json.dumps(keys) if args.json else "\n".join(keys))
            return 0
        if args.action == "show":
            data = load_venue(args.key, root)
            print(json.dumps(data, indent=2) if args.json else _yamlio.dump_yaml(data).rstrip())
            return 0
        findings: list[Finding] = []
        for key in args.keys or list_venues(root):
            findings += [_scope(f, key) for f in validate_venue(load_venue(key, root))]
        if not args.keys:
            for key in list_disciplines(root):
                findings += [_scope(f, key) for f in validate_discipline(load_discipline(key, root))]
    except ProfileError as exc:
        return _error(str(exc), args.json)
    status = worst(findings)
    if args.json:
        print(json.dumps({"status": status, "findings": [f.to_dict() for f in findings]}, indent=2))
    else:
        print(render(findings) if findings else f"{PASS}: all profiles valid")
    return 1 if status == FAIL else 0


def _scope(f: Finding, key: str) -> Finding:
    f.id = f"{f.id}[{key}]"
    return f


if __name__ == "__main__":
    sys.exit(main())
