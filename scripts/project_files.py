#!/usr/bin/env python3
"""Render and apply the project files /ploma:onboard writes into a paper repo (spec section 8).

The files depend on the host (spec section 11 of the multi-host design): Claude Code gets
.claude/rules/ploma-*.md and a CLAUDE.md section; Codex gets .codex/agents/ploma-*.toml, an AGENTS.md
section with the rule bodies inlined, and a .codex/config.toml block exporting CLAUDE_PLUGIN_ROOT.
The host is detected (scripts/host.py) unless --host names it.

Ownership modes:
  enforced      regenerated from ploma.yaml on every run; a hand edit shows as an overwrite diff
  created-once  written when absent, never overwritten
  merged        only ploma's part changes: the instructions-file marker section, the .gitignore
                entries, the .codex/config.toml marker block

Usage:
  python3 scripts/project_files.py [--root R] [--host H] [--json] plan
  python3 scripts/project_files.py [--root R] [--host H] [--json] apply
  python3 scripts/project_files.py [--root R] [--host H] [--json] settings
  python3 scripts/project_files.py [--root R] [--host H] [--json] record <path>
  python3 scripts/project_files.py [--root R] [--host H] [--json] switch
  python3 scripts/project_files.py [--root R] [--config C] statusline

plan shows what apply would do (--json: {"rows": [...], "withheld": [{"path", "line"}]}; withheld names a
merged file ploma will not write: the .codex/config.toml block when the user's file already defines the
shell_environment_policy table, with the line to merge by hand, and a symlinked instructions file, with
line null); apply writes create, overwrite and merge actions, deletes a
generated pipeline rule left over after pipeline.enabled turned false (action remove), records the
receipt with the host, and creates the .ploma/plugin link (and .ploma/host.json) from this script's
own plugin root (never CLAUDE_PLUGIN_ROOT); plan adds a receipt row (mode receipt, action update) when the
receipt names another host and a link row (mode link, action create) when .ploma/plugin is missing or
dangling; settings prints the proposed .claude/settings.json additions (never
written); record adds a file another skill wrote to the receipt: the host's learnings target (written
by /ploma:learn --promote) or a project skill under the host's project skills directory; switch prints
{"notice": ...}, the switch sentence when the receipt names another host, else null; statusline prints
the optional status line script rendered from the config (Claude Code only; never written; --host ignored).

With pipeline.enabled, the analysis-pipeline project skill (<project skills dir>/analysis-pipeline/SKILL.md)
is rendered created-once from the pipeline block; it stays when the pipeline is later disabled.

The learnings rule (.claude/rules/ploma-learnings.md) is never rendered, planned or written here
(Ruling R103): only /ploma:learn --promote writes it, then calls record.

Exit codes: 0 ok, 2 usage error, missing or invalid ploma.yaml, or an unreadable project file.
"""
from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import os
import posixpath
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yamlio  # noqa: E402
import host as _host  # noqa: E402
import host_adapters  # noqa: E402
import ploma_config  # noqa: E402
import receipt  # noqa: E402
import state  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent  # the running plugin, reached through any link
TEMPLATES = PLUGIN_ROOT / "templates"
MARKER_BEGIN = "<!-- ploma:begin -->"
MARKER_END = "<!-- ploma:end -->"
LEARNINGS_BEGIN = "<!-- ploma-learnings:begin -->"  # Codex promoted learnings in AGENTS.md (/ploma:learn)
LEARNINGS_END = "<!-- ploma-learnings:end -->"
TOML_BEGIN = "# ploma:begin"
TOML_END = "# ploma:end"
POLICY_TABLE = "[shell_environment_policy]"
# Any form that defines the table: [shell_environment_policy] (spaces, comments), a subtable, a dotted key.
_POLICY_RES = (re.compile(r"^\s*\[\s*shell_environment_policy\s*(\]|\.)"),
               re.compile(r"^\s*shell_environment_policy\s*\."))
SKILLS = ("compile", "validate-bib", "audit-reproducibility", "verify-claims", "proofread", "write", "format",
          "review", "devils-advocate", "brainstorm", "lit-review", "grill", "spec", "respond", "checkpoint",
          "compress-session", "learn", "deep-audit", "commit", "doctor", "status", "help", "onboard")
GITIGNORE_HEADER = "# ploma"
SYMLINK_NOTICE = ("`{path}` is a symlink; ploma does not write through links: replace it with a regular file "
                  "or merge the section by hand")
WRITE_ACTIONS = ("create", "overwrite", "merge")
PIPELINE_RULE = ".claude/rules/ploma-pipeline.md"
PIPELINE_SKILL = ".claude/skills/analysis-pipeline/SKILL.md"  # created-once, pipeline.enabled only
LEARNINGS_RULE = ".claude/rules/ploma-learnings.md"  # Claude: written only by /ploma:learn --promote (R103)
GENERATED_LINE = "<!-- generated by ploma from ploma.yaml; edit ploma.yaml, not this file -->"
LINTER_TOOLS = ("pdfinfo", "pdftotext", "chktex", "lacheck", "texcount")


@dataclass
class FileSpec:
    path: str  # repo-relative posix
    mode: str  # one of receipt.MODES
    content: str


# ---------------------------------------------------------------- template rendering

_VAR_RE = re.compile(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}")


def _fmt(value: Any) -> str:
    if value is None:
        return "not set"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return ", ".join(_fmt(v) for v in value) if value else "none"
    if isinstance(value, dict):
        return ", ".join(f"{k} {_fmt(v)}" for k, v in value.items()) if value else "none"
    return str(value)


def render_template(text: str, ctx: dict) -> str:
    """Replace each {{ dotted.key }} with its value in ctx; an unknown key raises KeyError naming it."""
    def value(m: re.Match) -> str:
        cur: Any = ctx
        for part in m.group(1).split("."):
            if not isinstance(cur, dict) or part not in cur:
                raise KeyError(f"template key {m.group(1)!r} is not in the config")
            cur = cur[part]
        return _fmt(cur)
    return _VAR_RE.sub(value, text)


def _fill(schema: dict, value: Any) -> Any:
    """value with every schema property it lacks set to None (objects recursively)."""
    props = schema.get("properties")
    if not props or not isinstance(value, dict):
        return value
    out = dict(value)
    for key, sub in props.items():
        if key in out:
            out[key] = _fill(sub, out[key])
        else:
            out[key] = _fill(sub, {}) if sub.get("properties") else None
    return out


def _get(cfg: dict, dotted: str) -> Any:
    cur: Any = cfg
    for part in dotted.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _rel(p: Any) -> str:
    """Normalized repo-relative posix form; '' for the repo root or a missing value."""
    if not isinstance(p, str) or not p:
        return ""
    n = posixpath.normpath(p.replace("\\", "/")).strip("/")
    return "" if n == "." else n


def _under(base: str, rest: str) -> str:
    return f"{base}/{rest}" if base else rest


def _bullets(items: Any, empty: str) -> str:
    vals = [str(v) for v in items] if isinstance(items, list) else []
    return "\n".join(f"- {v}" for v in vals) if vals else f"- {empty}"


def _quoted_list(globs: list[str]) -> str:
    return "\n".join(f"  - {json.dumps(g)}" for g in globs)


def _stage_chain(stages: Any) -> str:
    names = [str(s) for s in stages if str(s).strip()] if isinstance(stages, list) else []
    return " -> ".join(names) if names else "not declared"


_LANGUAGE_RUNNERS = {"python": "python3", "python3": "python3", "py": "python3", "r": "Rscript",
                     "julia": "julia"}


def _pipeline_bash(language: Any) -> str:
    """Bash patterns the analysis-pipeline skill pre-approves: the language's interpreter (when known)
    and make. Only fixed strings reach the frontmatter, never the config value itself."""
    runner = _LANGUAGE_RUNNERS.get(str(language or "").strip().lower())
    return ", ".join(([f"Bash({runner} *)"] if runner else []) + ["Bash(make *)"])


def _context(cfg: dict) -> dict:
    ctx = _fill(json.loads(ploma_config.SCHEMA_PATH.read_text(encoding="utf-8")), cfg)
    manuscript = [_under(_rel(_get(cfg, "document.root")), "**/*.tex")]
    bibs = _get(cfg, "build.bib_files")
    manuscript += [_rel(b) for b in bibs if _rel(b)] if isinstance(bibs, list) else []
    budget = _get(cfg, "venue.page_budget")
    command = _get(cfg, "build.command")
    rerun = _get(cfg, "pipeline.rerun")
    ctx["_derived"] = {
        "manuscript_paths": _quoted_list(manuscript),
        "pipeline_paths": _quoted_list([_under(_rel(_get(cfg, "pipeline.run_from")), "**")]),
        "build_command": f"`{command}`" if command else "latexmk (no build.command set)",
        "page_budget": "not set" if budget is None else
        f"{budget} pages ({'including' if _get(cfg, 'venue.page_budget_includes_refs') else 'excluding'} references)",
        "anonymity": ("yes. Keep author names, affiliations, acknowledgements, funding notes and "
                      "self-identifying citations out of the manuscript.")
        if _get(cfg, "document.anonymized") else "no.",
        "document_root": _rel(_get(cfg, "document.root")) or "the repo root",
        "build_cwd": _rel(_get(cfg, "build.cwd")) or "the repo root",
        "run_from": _rel(_get(cfg, "pipeline.run_from")) or "the repo root",
        "rerun": f"`{rerun}`" if rerun else "not set",
        "env_contract": _bullets(_get(cfg, "pipeline.env_contract"), "none recorded"),
        "gotchas": _bullets(_get(cfg, "pipeline.gotchas"), "none recorded"),
        "stage_chain": _stage_chain(_get(cfg, "pipeline.stages")),
        "pipeline_bash": _pipeline_bash(_get(cfg, "pipeline.language")),
    }
    return ctx


def _template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- merged files

def _read(root: Path, rel: str) -> str | None:
    p = Path(root) / rel
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"{rel}: cannot read ({exc})") from None


def _outside_fences(lines: list[str]) -> list[bool]:
    """Per stripped line: True when it is not inside (or delimiting) a ``` or ~~~ fenced code block."""
    flags, fence = [], ""
    for ln in lines:
        m = re.match(r"(`{3,}|~{3,})", ln)
        if fence:
            flags.append(False)
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not ln[len(m.group(1)):].strip():
                fence = ""
        elif m:
            fence = m.group(1)
            flags.append(False)
        else:
            flags.append(True)
    return flags


def marker_span(text: str, begin: str = MARKER_BEGIN, end: str = MARKER_END) -> tuple[int, int] | None:
    """(begin, end) line indexes of the marked span, or None when absent. Unbalanced raises ValueError.

    Marker lines inside fenced code blocks are examples, not markers, and are ignored."""
    lines = [ln.strip() for ln in text.splitlines()]
    live = _outside_fences(lines)
    begins = [i for i, ln in enumerate(lines) if live[i] and ln == begin]
    ends = [i for i, ln in enumerate(lines) if live[i] and ln == end]
    if not begins and not ends:
        return None
    if len(begins) != 1 or len(ends) != 1 or ends[0] < begins[0]:
        raise ValueError(f"the {begin} and {end} markers are unbalanced; "
                         "fix them by hand so exactly one section remains")
    return begins[0], ends[0]


def merge_marked(existing: str | None, block: str, begin: str, end: str) -> str:
    """existing with the begin/end span replaced in place by block, or block appended after one blank
    line. Text outside the span (a learnings block after it, say) is kept as is."""
    block = block if block.endswith("\n") else block + "\n"
    if not existing:
        return block
    span = marker_span(existing, begin, end)
    if span is None:
        sep = "" if existing.endswith("\n\n") else "\n" if existing.endswith("\n") else "\n\n"
        return existing + sep + block
    lines = existing.splitlines(keepends=True)
    b, e = span
    return "".join(lines[:b]) + block + "".join(lines[e + 1:])


def merge_claude_md(existing: str | None, section: str) -> str:
    return merge_marked(existing, section, MARKER_BEGIN, MARKER_END)


def _merge_file(root: Path, rel: str, block: str, begin: str, end: str) -> str:
    """merge_marked against the file on disk; an unbalanced span names the file."""
    existing = _read(root, rel)
    try:
        return merge_marked(existing, block, begin, end)
    except ValueError as exc:
        raise ValueError(f"{rel}: {exc}") from None


def outputs_dir(cfg: dict) -> str:
    """outputs.dir as a normalized repo-relative path; absolute or '..' values raise ValueError."""
    raw = _get(cfg, "outputs.dir") or "quality_reports"
    if not isinstance(raw, str):
        raise ValueError(f"outputs.dir must be a string path, got {raw!r}")
    unix = raw.replace("\\", "/")
    if PurePosixPath(unix).is_absolute() or PureWindowsPath(raw).drive or ".." in PurePosixPath(unix).parts:
        raise ValueError(f"outputs.dir {raw!r} must be a path inside the repo, relative to its root "
                         "and without '..'")
    return _rel(raw)


def gitignore_entries(cfg: dict) -> list[str]:
    out = outputs_dir(cfg)
    return [".ploma/", _under(out, "session_logs/"), _under(out, ".cache/")]


def gitignore_covers(lines: list[str], entry: str) -> bool:
    """True when a line ignores entry: the entry itself or any ancestor directory, written as
    d, d/, d/*, d/** (each optionally with a leading slash). Comments and negations never cover."""
    parts = entry.strip("/").split("/")
    accept = set()
    for i in range(1, len(parts) + 1):
        d = "/".join(parts[:i])
        for form in (d, d + "/", d + "/*", d + "/**"):
            accept |= {form, "/" + form}
    return any(line.strip() in accept for line in lines if not line.strip().startswith(("#", "!")))


def gitignore_missing(lines: list[str], cfg: dict) -> list[str]:
    return [e for e in gitignore_entries(cfg) if not gitignore_covers(lines, e)]


def merge_gitignore(existing: str | None, cfg: dict) -> str:
    text = existing or ""
    missing = gitignore_missing(text.splitlines(), cfg)
    if not missing:
        return text
    if text and not text.endswith("\n"):
        text += "\n"
    return text + "\n".join([GITIGNORE_HEADER] + missing) + "\n"


# ---------------------------------------------------------------- public API

def render_enforced(cfg: dict, ctx: dict | None = None) -> list[FileSpec]:
    """The enforced rules alone (render_all's first entries); reads nothing from the repo."""
    ctx = _context(cfg) if ctx is None else ctx
    specs = [FileSpec(".claude/rules/ploma-manuscript.md", "enforced",
                      render_template(_template("rules/ploma-manuscript.md"), ctx))]
    if _get(cfg, "pipeline.enabled") is True:
        specs.append(FileSpec(PIPELINE_RULE, "enforced",
                              render_template(_template("rules/ploma-pipeline.md"), ctx)))
    return specs


def _resolve(host: _host.Host | None, root: Path | None) -> _host.Host:
    return host if host is not None else _host.detect(root=None if root is None else Path(root))


def _receipt_host(h: _host.Host) -> str:
    """The host whose files h writes: an unknown host writes Claude Code's files."""
    return "claude" if h.name == "unknown" else h.name


def _rules_sentence(h: _host.Host) -> str:
    if h.rules_dir:
        return f"The rules under `{h.rules_dir}/ploma-*.md` are generated from it."
    return "The facts below are generated from it."


def _inline_rule(text: str, heading: str) -> str:
    """A rendered rule as section text: no frontmatter, no generated-by line, headings two levels down."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        lines = lines[lines.index("---", 1) + 1:]
    out = []
    for ln in lines:
        if ln.strip() == GENERATED_LINE:
            continue
        if ln.startswith("# "):
            ln = f"### {heading}"
        elif ln.startswith("## "):
            ln = "#### " + ln[3:]
        out.append(ln.replace("to regenerate this file.", "to regenerate this section."))
    return "\n".join(out).strip("\n")


def _inline_rules(cfg: dict, ctx: dict, h: _host.Host) -> str:
    """The enforced rule bodies for a host without a rules directory (Codex); '' otherwise."""
    if h.rules_dir:
        return ""
    rules = [("ploma-manuscript.md", "Manuscript facts")]
    if _get(cfg, "pipeline.enabled") is True:
        rules.append(("ploma-pipeline.md", "Pipeline facts"))
    bodies = [_inline_rule(render_template(_template(f"rules/{name}"), ctx), heading) for name, heading in rules]
    return "\n" + "\n\n".join(bodies) + "\n"


def instructions_section(cfg: dict, host: _host.Host, ctx: dict | None = None) -> str:
    """The marker-delimited ploma section of the host's instructions file (CLAUDE.md, AGENTS.md).

    An unknown host writes Claude Code's files, so it gets Claude Code's section (no churn between a
    plain shell and a Claude Code session)."""
    host = _host.HOSTS[_receipt_host(host)]
    ctx = dict(_context(cfg) if ctx is None else ctx)
    ctx["host"] = dict(dataclasses.asdict(host), rules_sentence=_rules_sentence(host))
    ctx["skills_line"] = ", ".join(_host.skill_ref(name, host) for name in SKILLS)
    ctx["inline_rules"] = _inline_rules(cfg, ctx, host)
    return _host.localize(render_template(_template("instructions-section.md"), ctx), host)


def _pipeline_skill(h: _host.Host) -> str:
    return f"{h.project_skills_dir}/analysis-pipeline/SKILL.md"


def withheld(cfg: dict, root: Path, host: _host.Host | None = None) -> list[str]:
    """Merged files ploma will not write: the instructions file when it is a symlink (ploma does not write
    through links; the user replaces it with a regular file or merges the section by hand), and the root
    export when the user's file already defines the shell_environment_policy table outside ploma's markers
    (the user merges export_line() by hand)."""
    h = _resolve(host, root)
    out = [h.instructions_file] if (Path(root) / h.instructions_file).is_symlink() else []
    return out + _export_withheld(root, h)


def _export_withheld(root: Path, h: _host.Host) -> list[str]:
    if not h.root_export:
        return []
    text = _read(Path(root), h.root_export)
    if text is None:
        return []
    try:
        span = marker_span(text, TOML_BEGIN, TOML_END)
    except ValueError as exc:
        raise ValueError(f"{h.root_export}: {exc}") from None
    ours = range(span[0], span[1] + 1) if span else range(0)
    clash = any(i not in ours and any(r.match(ln) for r in _POLICY_RES) for i, ln in enumerate(text.splitlines()))
    return [h.root_export] if clash else []


def export_line() -> str:
    """The line of the root export block a user merges by hand into their own policy table."""
    lines = _template("codex-config.toml").splitlines()
    return next(ln for ln in lines if ln.strip() and ln.strip() not in (TOML_BEGIN, TOML_END, POLICY_TABLE))


def render_all(cfg: dict, root: Path, host: _host.Host | None = None) -> list[FileSpec]:
    """Every project file onboard owns for the host, in order, with the content it should hold now.

    host None means the detected host. Merged files carry the full merged text computed from what is on
    disk under root; a withheld file (a symlinked instructions file, a clashing root export) is left
    out (see withheld)."""
    root = Path(root)
    h = _resolve(host, root)
    ctx = _context(cfg)
    out_dir = outputs_dir(cfg)
    specs = render_enforced(cfg, ctx) if h.rules_dir else []
    specs += host_adapters.render_agents(h, cfg, root)
    specs.append(FileSpec(_under(out_dir, "README.md"), "created-once",
                          render_template(_template("quality_reports/README.md"), ctx)))
    specs.append(FileSpec(_under(out_dir, "learnings.md"), "created-once",
                          render_template(_template("learnings.md"), ctx)))
    specs.append(FileSpec(_under(out_dir, state.FILE_NAME), "created-once", _yamlio.dump_yaml(state._empty())))
    if _get(cfg, "pipeline.enabled") is True:
        skill = render_template(_template("project-skills/analysis-pipeline/SKILL.md"), ctx)
        specs.append(FileSpec(_pipeline_skill(h), "created-once", _host.localize(skill, h)))
    held = withheld(cfg, root, h)
    if h.instructions_file not in held:
        section = instructions_section(cfg, h, ctx)
        specs.append(FileSpec(h.instructions_file, "merged",
                              _merge_file(root, h.instructions_file, section, MARKER_BEGIN, MARKER_END)))
    specs.append(FileSpec(".gitignore", "merged", merge_gitignore(_read(root, ".gitignore"), cfg)))
    if h.root_export and h.root_export not in held:
        specs.append(FileSpec(h.root_export, "merged",
                              _merge_file(root, h.root_export, _template("codex-config.toml"), TOML_BEGIN, TOML_END)))
    return specs


def render_statusline(cfg: dict) -> str:
    """The optional status line script onboard offers (not part of render_all)."""
    return render_template(_template("statusline.sh"), _context(cfg))


def settings_suggestion(cfg: dict) -> dict:
    """Proposed .claude/settings.json additions to show the user; plugins cannot grant these, so never written."""
    command = _get(cfg, "build.command")
    tool = "latexmk"
    if isinstance(command, str) and command.strip():
        try:
            tokens = shlex.split(command)
        except ValueError:
            tokens = command.split()
        tool = posixpath.basename(tokens[0]) if tokens else "latexmk"
    allow = [f"Bash({tool}:*)"] + [f"Bash({t}:*)" for t in LINTER_TOOLS if t != tool]
    allow.append("Bash(python3 *)")  # settings.json does not expand ${CLAUDE_PLUGIN_ROOT}
    out_dir = outputs_dir(cfg)
    return {"plansDirectory": _under(out_dir, "plans"), "permissions": {"allow": allow}}


def _diff(path: str, old: str | None, new: str) -> str:
    return "".join(difflib.unified_diff((old or "").splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile="/dev/null" if old is None else f"a/{path}",
                                        tofile=f"b/{path}"))


def has_generated_marker(text: str) -> bool:
    """True when the first body line (after any YAML frontmatter) is ploma's generated-by line."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        try:
            start = lines.index("---", 1) + 1
        except ValueError:
            return False
    return len(lines) > start and lines[start].strip() == GENERATED_LINE


def plan(root: Path, cfg: dict, host: _host.Host | None = None) -> list[dict]:
    """[{path, mode, action, diff}] for every rendered file, plus a stale pipeline rule; reads only.

    Two rows are not files ploma renders: mode receipt (action update) when the receipt names another
    host, so a switch back is never idle; mode link (action create) when .ploma/plugin is missing or
    dangling, so a co-author's fresh clone still gets the link. apply treats both as write actions."""
    root = Path(root)
    h = _resolve(host, root)
    outputs_dir(cfg)
    receipt_state = {r["path"]: r["state"] for r in receipt.compare(root, cfg)}
    rows = []
    for spec in render_all(cfg, root, h):
        current = _read(root, spec.path)
        diff = ""
        if current is None:
            action, diff = "create", _diff(spec.path, None, spec.content)
        elif current == spec.content:
            action = "unchanged"
        elif spec.mode == "created-once":
            action = "unchanged" if receipt_state.get(spec.path) == "unchanged" else "skip_hand_edited"
        else:
            action = "overwrite" if spec.mode == "enforced" else "merge"
            diff = _diff(spec.path, current, spec.content)
        rows.append({"path": spec.path, "mode": spec.mode, "action": action, "diff": diff})
    stale = _read(root, PIPELINE_RULE) if h.rules_dir and _get(cfg, "pipeline.enabled") is not True else None
    if stale is not None:
        generated = has_generated_marker(stale)
        rows.append({"path": PIPELINE_RULE, "mode": "enforced",
                     "action": "remove" if generated else "skip_hand_edited",
                     "diff": _diff(PIPELINE_RULE, stale, "") if generated else ""})
    try:
        data = receipt.load(root, cfg)
    except ValueError:
        data = None
    if data is not None and data["host"] != _receipt_host(h):
        rows.append({"path": receipt_rel(cfg), "mode": "receipt", "action": "update", "diff": ""})
    if link_missing(root):
        rows.append({"path": _host.LINK, "mode": "link", "action": "create", "diff": ""})
    return rows


def receipt_rel(cfg: dict) -> str:
    """The receipt's repo-relative posix path."""
    return _under(outputs_dir(cfg), receipt.FILE_NAME)


def apply(root: Path, cfg: dict, plan: list[dict], host: _host.Host | None = None) -> list[dict]:
    """Write files whose planned action is create, overwrite or merge, then record the receipt.

    Content is re-rendered at apply time; returns the plan rows each with a ``written`` flag. The receipt
    is always rewritten (a receipt row only marks a host switch), and the .ploma/plugin link and
    .ploma/host.json are created from this script's plugin root (best effort)."""
    root = Path(root)
    h = _resolve(host, root)
    outputs_dir(cfg)  # validate before anything is written
    actions = {row["path"]: row["action"] for row in plan}
    specs = render_all(cfg, root, h)
    written: set[str] = set()
    for spec in specs:
        target = root / spec.path
        if actions.get(spec.path) not in WRITE_ACTIONS:
            continue
        if spec.mode == "created-once" and target.exists():
            continue  # appeared after the plan: never overwrite a created-once file
        state._atomic_write(target, spec.content)
        written.add(spec.path)
    if h.rules_dir and actions.get(PIPELINE_RULE) == "remove" and PIPELINE_RULE not in {s.path for s in specs}:
        target = root / PIPELINE_RULE
        current = _read(root, PIPELINE_RULE)
        if current is not None and has_generated_marker(current):
            target.unlink()
            written.add(PIPELINE_RULE)
    files = [{"path": s.path, "mode": s.mode, "sha256": receipt.sha256_file(root / s.path)}
             for s in specs if (root / s.path).is_file()]
    files += _recorded_elsewhere(root, cfg, {s.path for s in specs}, h)
    receipt.write(root, cfg, files, _receipt_host(h))
    if actions.get(receipt_rel(cfg)) == "update":
        written.add(receipt_rel(cfg))
    if _link_plugin(root, h) and actions.get(_host.LINK) == "create":
        written.add(_host.LINK)
    return [dict(row, written=row["path"] in written) for row in plan]


def _link_plugin(root: Path, h: _host.Host) -> bool:
    """Create .ploma/plugin, and .ploma/host.json when the hook has not written it; True when linked.

    The plugin root is this script's own plugin directory (Ruling R9), never CLAUDE_PLUGIN_ROOT: on Codex
    the model's shell exports CLAUDE_PLUGIN_ROOT=.ploma/plugin, which would link the link to itself."""
    plugin_root = PLUGIN_ROOT
    try:
        _host.ensure_plugin_link(root, plugin_root)
        if h.name != "unknown" and _host.read_host_json(root) is None:
            _host.write_host_json(root, h, plugin_root, receipt.plugin_version())
    except (OSError, ValueError):
        return False  # the session hook refreshes the link; doctor reports it when missing
    return True


def link_missing(root: Path) -> bool:
    """True when <root>/.ploma/plugin is missing or dangling."""
    link = Path(root) / _host.LINK
    return not (link.is_symlink() and link.is_dir())


def _recordable(rel: str, h: _host.Host) -> bool:
    """True for the paths record accepts on host h: its learnings target or a project skill file."""
    return rel == h.learnings_target or rel.startswith(h.project_skills_dir + "/")


def _recorded_elsewhere(root: Path, cfg: dict, rendered: set[str], h: _host.Host) -> list[dict]:
    """Receipt entries record added that onboard does not render, when the file still exists.

    Only paths record accepts on host h are carried forward (Ruling R148), so a switch drops the old
    host's entries; the recorded sha is kept, so a later hand edit still shows as hand_edited."""
    try:
        data = receipt.load(root, cfg)
    except ValueError:
        return []
    if data is None:
        return []
    return [dict(e) for e in data["files"]
            if _recordable(e["path"], h) and e["path"] not in rendered and e["mode"] == "created-once"
            and (Path(root) / e["path"]).is_file()]


def record_created_once(root: Path, cfg: dict, path: str, host: _host.Host | None = None) -> dict:
    """Add (or refresh) path in the receipt as a file another skill wrote.

    Accepted (an allowlist, Ruling R148): the host's learnings target and files under its project skills
    directory; the file must exist. The learnings target is the instructions file on Codex, recorded as
    merged (its sha refreshed); anything else is created-once and must not be an onboard file. Onboard's
    entries and the receipt's host are kept; an earlier entry for path is replaced. Returns the entry."""
    root = Path(root)
    h = _resolve(host, root)
    rel = receipt._norm_path(path, "record")
    rel = posixpath.normpath(rel)
    if not _recordable(rel, h):
        raise ValueError(f"record accepts only {h.learnings_target} (written by {_host.skill_ref('learn', h)} "
                         f"--promote) or a project skill under {h.project_skills_dir}/, not {rel}")
    merged = rel == h.instructions_file
    rendered = {s.path for s in render_all(cfg, root, h)} | {PIPELINE_RULE}
    if rel in rendered and not merged:
        raise ValueError(f"{rel} is written by {_host.skill_ref('onboard', h)}; it is recorded when onboard applies")
    target = root / rel
    if not target.is_file():
        raise ValueError(f"{rel}: no such file to record")
    entry = {"path": rel, "mode": "merged" if merged else "created-once", "sha256": receipt.sha256_file(target)}
    data = receipt.load(root, cfg)
    files = [e for e in (data["files"] if data else []) if e["path"] != rel]
    receipt.write(root, cfg, files + [entry], data["host"] if data else _receipt_host(h))
    return entry


def switch_notice(root: Path, cfg: dict, host: _host.Host) -> str | None:
    """The switch sentence (spec section 11) when the receipt names another host than host, else None."""
    data = receipt.load(root, cfg)
    if data is None or data["host"] == _receipt_host(host):
        return None
    old = _host.HOSTS.get(data["host"])
    old_display = old.display if old else data["host"]
    listing = ", ".join(_host.host_files(root, cfg).get(data["host"], [])) or "none found"
    return (f"This repo is onboarded for {old_display}. You are running {host.display}. Onboard will write the "
            f"{host.display} files and leave the {old_display} files in place: {listing}.")


# ---------------------------------------------------------------- CLI

def _error(message: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"error": message}))
    else:
        print(f"project_files: {message}", file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan, apply or suggest ploma project files.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--config", default=None,
                        help="proposed ploma.yaml to plan from instead of <root>/ploma.yaml "
                             "('-' reads stdin); plan, settings and statusline only")
    parser.add_argument("--host", default=None, choices=tuple(_host.HOSTS),
                        help="the host to write files for (default: detected)")
    parser.add_argument("action", choices=("plan", "apply", "settings", "record", "switch", "statusline"))
    parser.add_argument("target", nargs="?", default=None, help="record: the repo-relative file to record")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root)
    if (args.target is None) == (args.action == "record"):
        return _error("record takes exactly one path; plan, apply, settings, switch and statusline take none", args.json)
    if args.config is not None and args.action == "record":
        return _error("record reads the written ploma.yaml; --config is for plan and settings", args.json)
    if args.config is not None and args.action == "apply":
        return _error("apply reads the written ploma.yaml; --config is for plan and settings", args.json)
    try:
        if args.config is None:
            cfg = ploma_config.load(root)
        elif args.config == "-":
            cfg = ploma_config.loads(sys.stdin.read(), "stdin")
        else:
            cfg = ploma_config.loads(Path(args.config).read_text(encoding="utf-8"), args.config)
    except ploma_config.ConfigError as exc:
        return _error(exc.message, args.json)
    except (OSError, UnicodeDecodeError) as exc:
        return _error(f"--config {args.config}: {exc}", args.json)
    if args.action == "statusline":
        print(render_statusline(cfg), end="")
        return 0
    h = _host.HOSTS[args.host] if args.host else _host.detect(root=root)
    held: list[str] = []
    try:
        if args.action == "settings":
            data: Any = settings_suggestion(cfg)
            print(json.dumps(data, indent=2))
            return 0
        if args.action == "record":
            entry = record_created_once(root, cfg, args.target, h)
            out = {"path": entry["path"], "mode": entry["mode"], "recorded": True}
            print(json.dumps(out) if args.json else f"- recorded {entry['path']} [{entry['mode']}]")
            return 0
        if args.action == "switch":
            notice = switch_notice(root, cfg, h)
            idle = "no receipt: not onboarded" if receipt.load(root, cfg) is None else \
                f"no switch: onboarded for {h.display}"
            print(json.dumps({"notice": notice}) if args.json else notice or idle)
            return 0
        rows = plan(root, cfg, h)
        if args.action == "apply":
            rows = apply(root, cfg, rows, h)
        else:
            held = withheld(cfg, root, h)
    except (ValueError, KeyError, OSError) as exc:
        return _error(str(exc), args.json)
    if args.json:
        held_rows = [{"path": rel, "line": export_line() if rel == h.root_export else None} for rel in held]
        print(json.dumps({"rows": rows, "withheld": held_rows} if args.action == "plan" else rows, indent=2))
    else:
        for row in rows:
            flag = " (written)" if row.get("written") else ""
            print(f"- {row['action']} {row['path']} [{row['mode']}]{flag}")
            if row["diff"] and args.action == "plan":
                print(row["diff"].rstrip("\n"))
        for rel in held:
            if rel == h.root_export:
                print(f"- withheld {rel}: it already defines shell_environment_policy outside the ploma markers; "
                      f"merge this line into that table by hand: {export_line()}")
            else:
                print(f"- withheld {rel}: {SYMLINK_NOTICE.format(path=rel)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
