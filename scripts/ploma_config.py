#!/usr/bin/env python3
"""Single loader for ploma.yaml: defaults, schema validation, resolved paths, summary.

Usage: ploma_config.py [--root R] [--json] [validate|summary]

  (no action)  print the summary, or the resolved config with --json
  validate     check ploma.yaml against schemas/ploma.schema.json and input paths
  summary      print the compact summary injected at session start

Exit codes: 0 ok, 1 validation found a FAIL, 2 usage error or ploma.yaml missing or unreadable.
"""
from __future__ import annotations

import argparse
import copy
import json
import posixpath
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yamlio  # noqa: E402
from _findings import FAIL, PASS, WARN, Finding, render, worst  # noqa: E402

CONFIG_NAME = "ploma.yaml"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "ploma.schema.json"
SUPPORTED_DOCUMENT_TYPES = ("paper",)

# Defaults for every optional key. document.root, document.slug, build.cwd, build.pdf and
# build.log are derived from document.main in load() when absent.
DEFAULTS: dict[str, Any] = {
    "document": {"type": "paper", "title": None, "anonymized": False, "discipline": None},
    "build": {"command": None, "bib_tool": "bibtex", "bib_files": [], "overfull_threshold_pt": 10},
    "venue": {"doc_class": None, "page_budget": None, "page_budget_includes_refs": False,
              "cite_style": "numeric"},
    "reviews": {"glob": None},
    "literature": {"sources": []},
    "outputs": {"dir": "quality_reports"},
    "style": {"sentences": "short-direct", "forbid_em_dash": True, "forbid_phrases": [],
              "figures": "compact-horizontal"},
    "pipeline": {"enabled": False, "language": "python", "run_from": None, "rerun": None,
                 "outputs_dir": None, "metric_keys": [], "env_contract": [], "gotchas": [],
                 "tolerances": {"counts": "exact", "metrics": 0.01, "aggregates": 0.02,
                                "percentages_pp": 0.1},
                 "figure_provenance": "optional"},
    "limits": {"review_rounds": 5, "cove_regenerations": 2, "doi_lookups_per_run": 50},
    "dependencies": {"superpowers": "soft"},
}


class ConfigError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _merge(default: Any, user: Any) -> Any:
    if isinstance(default, dict):
        if user is None:
            return copy.deepcopy(default)
        if isinstance(user, dict):
            out = copy.deepcopy(default)
            for k, v in user.items():
                out[k] = _merge(default.get(k), v) if k in default else v
            return out
    return user


def _norm(p: str) -> str:
    return posixpath.normpath(p.replace("\\", "/"))


def _derive(cfg: dict) -> None:
    doc, build = cfg.get("document"), cfg.get("build")
    if not isinstance(doc, dict) or not isinstance(build, dict) or not isinstance(doc.get("main"), str):
        return
    main = _norm(doc["main"])
    stem = posixpath.splitext(posixpath.basename(main))[0]
    doc.setdefault("root", posixpath.dirname(main) or ".")
    doc.setdefault("slug", stem)
    cwd = build.setdefault("cwd", doc["root"] if isinstance(doc["root"], str) else ".")
    if isinstance(cwd, str):
        build.setdefault("pdf", _norm(posixpath.join(cwd, stem + ".pdf")))
        build.setdefault("log", _norm(posixpath.join(cwd, stem + ".log")))


def load(root: Path) -> dict:
    """Read <root>/ploma.yaml, merge it over DEFAULTS and fill derived keys."""
    path = Path(root) / CONFIG_NAME
    if not path.is_file():
        raise ConfigError(f"{path} not found; run /ploma:onboard to create it")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path} could not be parsed ({_yamlio.LOADER}): {exc}") from exc
    return loads(text, str(path))


def loads(text: str, label: str = "ploma.yaml") -> dict:
    """Parse ploma.yaml text (a proposal not yet on disk, too), merge over DEFAULTS, derive keys."""
    try:
        data = _yamlio.loads_yaml(text)
    except _yamlio.YamlError as exc:
        raise ConfigError(f"{label} could not be parsed ({_yamlio.LOADER}): {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"{label} must contain a mapping at the top level")
    cfg = _merge(DEFAULTS, data)
    _derive(cfg)
    return cfg


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _type_ok(value: Any, types: Any) -> bool:
    checks = {"string": lambda v: isinstance(v, str), "boolean": lambda v: isinstance(v, bool),
              "null": lambda v: v is None, "object": lambda v: isinstance(v, dict),
              "array": lambda v: isinstance(v, list),
              "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
              "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool)}
    return any(checks[t](value) for t in ([types] if isinstance(types, str) else types))


def _check(value: Any, schema: dict, path: str, out: list[Finding]) -> None:
    """Minimal JSON Schema walk: type, pattern, enum, required, properties, items, additionalProperties."""
    where = path or "top level"
    if "type" in schema and not _type_ok(value, schema["type"]):
        want = schema["type"] if isinstance(schema["type"], str) else " or ".join(schema["type"])
        out.append(Finding(f"config.type.{path}", FAIL, f"{where} must be {want}",
                           observed=f"{type(value).__name__}: {value!r}",
                           remediation=f"Set {where} to a {want} in ploma.yaml.", group="config"))
        return
    if "pattern" in schema and isinstance(value, str) and not re.search(schema["pattern"], value):
        out.append(Finding(f"config.pattern.{path}", FAIL, f"{where} must match {schema['pattern']}",
                           observed=repr(value), remediation=f"Change {where} in ploma.yaml to match {schema['pattern']}.",
                           group="config"))
    if "enum" in schema and value not in schema["enum"]:
        out.append(Finding(f"config.enum.{path}", FAIL, f"{where} must be one of {', '.join(schema['enum'])}",
                           observed=repr(value), remediation=f"Pick one of {schema['enum']}.", group="config"))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                sub = f"{path}.{key}" if path else key
                out.append(Finding(f"config.required.{sub}", FAIL, f"{sub} is required",
                                   remediation=f"Add {sub} to ploma.yaml.", group="config"))
        props = schema.get("properties", {})
        for key, sub_value in value.items():
            sub = f"{path}.{key}" if path else str(key)
            if key in props:
                _check(sub_value, props[key], sub, out)
            elif schema.get("additionalProperties") is False:
                out.append(Finding(f"config.unknown.{sub}", WARN, f"{sub} is not a known ploma.yaml key",
                                   remediation="Check the spelling; unknown keys are ignored.", group="config"))
    if isinstance(value, list) and "items" in schema:
        for i, item in enumerate(value):
            _check(item, schema["items"], f"{path}.{i}", out)


def _get(cfg: dict, dotted: str) -> Any:
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _glob_prefix(pattern: str) -> str:
    parts = []
    for part in _norm(pattern).split("/")[:-1]:
        if any(c in part for c in "*?["):
            break
        parts.append(part)
    return "/".join(parts)


def _input_paths(cfg: dict) -> list[tuple[str, list[str]]]:
    """Input path keys that must exist (Ruling R2: outputs are never checked)."""
    keys = ["document.main", "document.root", "build.bib_files", "build.cwd", "literature.sources"]
    if _get(cfg, "pipeline.enabled") is True:
        keys += ["pipeline.run_from", "pipeline.outputs_dir"]
    pairs = []
    for key in keys:
        val = _get(cfg, key)
        vals = val if isinstance(val, list) else [val]
        pairs.append((key, [v for v in vals if isinstance(v, str) and v]))
    glob = _get(cfg, "reviews.glob")
    if isinstance(glob, str) and _glob_prefix(glob):
        pairs.append(("reviews.glob", [_glob_prefix(glob)]))
    return pairs


def validate(cfg: dict, root: Path) -> list[Finding]:
    """Schema shape and enums first, then document.type support, then input paths."""
    findings: list[Finding] = []
    _check(cfg, _schema(), "", findings)
    dtype = _get(cfg, "document.type")
    if isinstance(dtype, str) and dtype not in SUPPORTED_DOCUMENT_TYPES:
        findings.append(Finding("config.document_type_unsupported", FAIL,
                                f"document.type '{dtype}' is not supported in ploma v0.1",
                                observed=f"document.type: {dtype}",
                                remediation="Set document.type to paper; other types arrive in later versions.",
                                group="config"))
    root = Path(root)
    for key, rels in _input_paths(cfg):
        missing = [r for r in rels if not (root / r).exists()]
        if missing and key == "pipeline.outputs_dir":
            findings.append(Finding(f"config.path.{key}", WARN, "pipeline.outputs_dir does not exist yet",
                                    observed=", ".join(missing),
                                    remediation="Run the pipeline to generate it (results are often gitignored), "
                                                "or fix pipeline.outputs_dir in ploma.yaml.",
                                    group="config"))
        elif missing and key == "literature.sources":
            findings.append(Finding(f"config.path.{key}", WARN, "a literature.sources directory does not exist",
                                    observed=", ".join(missing),
                                    remediation="Create the directory and put the papers there, "
                                                "or fix or remove it in literature.sources in ploma.yaml.",
                                    group="config"))
        elif missing and key == "reviews.glob":
            findings.append(Finding(f"config.path.{key}", WARN, "reviews.glob points into a directory that does not exist",
                                    observed=", ".join(missing),
                                    remediation="Create the reviews directory when referee reports arrive, "
                                                "or fix or remove reviews.glob in ploma.yaml.",
                                    group="config"))
        elif missing:
            findings.append(Finding(f"config.path.{key}", FAIL, f"{key} points at a path that does not exist",
                                    observed=", ".join(missing),
                                    remediation=f"Fix {key} in ploma.yaml (paths are relative to the repo root).",
                                    group="config"))
    if not any(f.status in (FAIL, WARN) for f in findings):
        findings.append(Finding("config.valid", PASS, "ploma.yaml is valid", group="config"))
    return findings


def resolve(cfg: dict, root: Path) -> dict:
    """Copy of cfg with ``_paths``: absolute main, root, bib_files, pdf, log, outputs_dir, build_cwd."""
    root = Path(root).resolve()
    out = copy.deepcopy(cfg)

    def absolute(rel: Any) -> str | None:
        return str((root / rel).resolve()) if isinstance(rel, str) and rel else None

    bibs = _get(cfg, "build.bib_files")
    out["_paths"] = {
        "repo": str(root),
        "main": absolute(_get(cfg, "document.main")),
        "root": absolute(_get(cfg, "document.root")),
        "bib_files": [absolute(b) for b in bibs if isinstance(b, str)] if isinstance(bibs, list) else [],
        "pdf": absolute(_get(cfg, "build.pdf")),
        "log": absolute(_get(cfg, "build.log")),
        "outputs_dir": absolute(_get(cfg, "outputs.dir")),
        "build_cwd": absolute(_get(cfg, "build.cwd")),
    }
    return out


def _short(value: Any, limit: int = 100) -> str:
    s = str(value)
    return s if len(s) <= limit else s[: limit - 3] + "..."


def _list(values: Any, limit: int = 4) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    shown = ", ".join(_short(v, 60) for v in values[:limit])
    return shown + (f" (+{len(values) - limit} more)" if len(values) > limit else "")


def _present(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _clauses(*pairs: tuple[str, Any]) -> list[str]:
    """Format (template, value) pairs, dropping any whose value is None or empty."""
    return [tpl.format(_short(v)) for tpl, v in pairs if _present(v)]


def summary(cfg: dict) -> str:
    """Compact text block for the SessionStart hook; always under 1,500 characters.

    Any clause whose value is None or empty is omitted (never printed as "None")."""
    g = lambda key: _get(cfg, key)  # noqa: E731
    budget = g("venue.page_budget")
    budget_txt = "no page budget" if budget is None else \
        f"page budget {budget} ({'incl.' if g('venue.page_budget_includes_refs') else 'excl.'} references)"
    command = g("build.command")
    fmt = g("ploma")
    lines = ["ploma project config (ploma.yaml" + (f", format {fmt}" if _present(fmt) else "") + ")"]
    doc = _clauses(("{}", g("document.type")), ("main {}", g("document.main")), ("root {}", g("document.root")),
                   ("slug {}", g("document.slug")))
    doc.append(f"discipline {_short(g('document.discipline'), 40)}" if _present(g("document.discipline"))
               else "discipline generic (unset)")
    lines.append("- document: " + ", ".join(doc) + (", anonymized" if g("document.anonymized") else ", not anonymized"))
    tools = " + ".join(_clauses(("{}", g("build.engine")), ("{}", g("build.bib_tool"))))
    how = (f"command `{_short(command)}`" if _present(command) else "latexmk fallback") \
        + "".join(" " + c for c in _clauses(("from {}", g("build.cwd"))))
    build = [b for b in [tools, how] if b] + _clauses(("pdf {}", g("build.pdf")))
    lines.append("- build: " + "; ".join(build))
    lines.append(f"- bibliography: {_list(g('build.bib_files'))}")
    venue = _clauses(("{}", g("venue.profile")))
    if venue and _present(g("venue.doc_class")):
        venue[0] += f" ({g('venue.doc_class')})"
    venue += [budget_txt] + _clauses(("{} citations", g("venue.cite_style")))
    lines.append("- venue: " + ", ".join(venue))
    lines.extend(_clauses(("- reports: {}/", g("outputs.dir"))))
    if g("pipeline.enabled") is True:
        pipe = ["enabled"] + _clauses(("language {}", g("pipeline.language")),
                                      ("run from {}", g("pipeline.run_from")), ("rerun `{}`", g("pipeline.rerun")),
                                      ("outputs {}", g("pipeline.outputs_dir")),
                                      ("figure provenance {}", g("pipeline.figure_provenance")))
        lines.append("- pipeline: " + "; ".join(pipe))
        env = g("pipeline.env_contract")
        if isinstance(env, list) and env:
            lines.append("- pipeline env contract: " + _list(env, limit=12))
    else:
        lines.append("- pipeline: disabled")
    phrases = g("style.forbid_phrases")
    style = _clauses(("{} sentences", g("style.sentences")))
    style.append("em-dash " + ("forbidden" if g("style.forbid_em_dash") else "allowed"))
    style += _clauses(("figures {}", g("style.figures")))
    if isinstance(phrases, list) and phrases:
        style.append("extra forbidden phrases: " + _list(phrases, limit=6))
    lines.append("- style: " + "; ".join(style))
    limits = _clauses(("review rounds {}", g("limits.review_rounds")),
                      ("CoVe regenerations {}", g("limits.cove_regenerations")),
                      ("DOI lookups per run {}", g("limits.doi_lookups_per_run")))
    if limits:
        lines.append("- limits: " + ", ".join(limits))
    text = "\n".join(lines)
    gotchas = g("pipeline.gotchas") if g("pipeline.enabled") is True else None
    if isinstance(gotchas, list) and gotchas:
        line = _gotchas_line([str(x) for x in gotchas], SUMMARY_MAX - len(text) - 1)
        text += "\n" + line if line else ""
    return text if len(text) < SUMMARY_MAX else text[:SUMMARY_MAX - 4] + "..."


SUMMARY_MAX = 1500
_GOTCHAS_HEAD = "- pipeline gotchas: "


def _gotchas_line(gotchas: list[str], room: int) -> str:
    """Numbered gotchas, cut so the line fits in room (the summary stays under SUMMARY_MAX)."""
    full = _GOTCHAS_HEAD + " ".join(f"({i}) {x}" for i, x in enumerate(gotchas, 1))
    if len(full) < room:
        return full
    tail = f" ... (truncated; {len(gotchas)} in ploma.yaml)"
    keep = room - len(tail) - 1
    return (full[:keep] + tail) if keep > len(_GOTCHAS_HEAD) + 10 else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load, validate and summarise ploma.yaml.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("action", nargs="?", choices=["validate", "summary"])
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        cfg = load(root)
    except ConfigError as exc:
        if args.json:
            print(json.dumps({"error": exc.message}))
        else:
            print(f"ploma_config: {exc.message}", file=sys.stderr)
        return 2
    if args.action == "validate":
        findings = validate(cfg, root)
        status = worst(findings)
        if args.json:
            print(json.dumps({"status": status, "findings": [f.to_dict() for f in findings]}, indent=2))
        else:
            print(render(findings))
        return 1 if status == FAIL else 0
    if args.action == "summary" or not args.json:
        text = summary(cfg)
        print(json.dumps({"summary": text}) if args.json else text)
        return 0
    print(json.dumps(resolve(cfg, root), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
