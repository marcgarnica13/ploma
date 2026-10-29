#!/usr/bin/env python3
"""Read-only repository inventory for /ploma:onboard: what the repo already says about the paper.

Usage: inventory.py [--root R] [--main FILE] [--json] [inventory|propose|gaps]

  inventory  (default) facts detected in the repo: main file, class, engine, bib, build, figures,
             reviews, results, code tree, git remote, superpowers, legacy harness
  propose    the ploma.yaml proposal built from those facts
  gaps       the questions the repo cannot answer, each with a recommended answer

Nothing is written anywhere. Exit codes: 0 ok, 2 usage error or root not a directory.
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _yamlio  # noqa: E402
from bib_check import resolve_bib_files, strip_comment, tex_sources  # noqa: E402
from pdf_pages import page_count  # noqa: E402
import profiles  # noqa: E402

CLASS_TO_VENUE: dict[str, str] = {
    "llncs": "llncs-conference", "sn-jnl": "springer-ml", "svjour3": "springer-ml",
    "IEEEtran": "ieee-conference", "acmart": "acm-sigconf", "elsarticle": "elsevier",
    "article": "generic-journal", "amsart": "generic-journal", "revtex4-2": "generic-journal",
}

# The twenty traces harness skill names, each with the ploma skill it would collide with.
LEGACY_SKILL_NAMES: dict[str, str] = {
    "research-ideation": "/ploma:brainstorm", "lit-review": "/ploma:lit-review",
    "interview-me": "/ploma:spec", "compile-latex": "/ploma:compile", "proofread": "/ploma:proofread",
    "validate-bib": "/ploma:validate-bib", "verify-claims": "/ploma:verify-claims",
    "audit-reproducibility": "/ploma:audit-reproducibility", "review-paper": "/ploma:review",
    "seven-pass-review": "/ploma:review", "devils-advocate": "/ploma:devils-advocate",
    "respond-to-referees": "/ploma:respond", "commit": "/ploma:commit", "checkpoint": "/ploma:checkpoint",
    "compress-session": "/ploma:compress-session", "context-status": "/ploma:status", "learn": "/ploma:learn",
    "promote-memory": "/ploma:learn", "deep-audit": "/ploma:deep-audit", "data-analysis": "/ploma:audit-reproducibility",
}

OUTPUTS_DIR = "quality_reports"
SKIP_DIRS = {".git", "node_modules", ".ploma", OUTPUTS_DIR, "build", "_build", "__pycache__", ".venv", "venv"}
MAX_DEPTH = 4
REVIEW_EXTS = {".md", ".txt", ".pdf", ".docx"}
RESULT_EXTS = {".json", ".csv"}
CODE_MARKERS = (("pyproject.toml", "python"), ("requirements.txt", "python"), ("DESCRIPTION", "r"),
                ("Project.toml", "julia"), ("package.json", "javascript"))

_DOCCLASS_RE = re.compile(r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")
_BEGIN_DOC_RE = re.compile(r"\\begin\s*\{document\}")
_INPUT_RE = re.compile(r"\\(?:input|include)\s*\{")
_USEPACKAGE_RE = re.compile(r"\\(?:usepackage|RequirePackage)\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}")
_AUTHOR_RE = re.compile(r"\\author(?![A-Za-z])")
_ANON_CMD_RE = re.compile(r"\\anonymous(?![A-Za-z])")
_PLACEHOLDER_AUTHOR_RE = re.compile(r"anonymi[sz]ed|anonymous", re.I)
NON_MAIN_CLASSES = {"standalone", "subfiles"}
_TITLE_RE = re.compile(r"\\title(?![A-Za-z])\s*")
_GRAPHICS_RE = re.compile(r"\\includegraphics\*?\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
_AUTHOR_YEAR_CITE_RE = re.compile(r"\\[Cc]ite[tp]\*?\s*[\[{]")
_MAKE_MAIN_RE = re.compile(r"^\s*MAIN\s*[:?]?=\s*([^\s#]+)", re.M)
_LATEXMK_FILES_RE = re.compile(r"@default_files\s*=\s*\(\s*['\"]([^'\"]+)['\"]")

# Command-shaped lines in legacy rules; prose such as "make sure" never matches.
_RULE_FACT_RES = (
    re.compile(r"\\documentclass"),
    re.compile(r"\bcd\s+\S+\s*&&\s*make\b"),
    re.compile(r"\b(?:pdflatex|bibtex|biber) "),
    re.compile(r"(?<![\w.])[\w./-]+\.bib(?![\w])"),
)
_RULE_MAKE_RE = re.compile(r"^\s*(?:\$\s*)?make\s+([A-Za-z][\w.-]*)")
_PROSE_AFTER_MAKE = {"sure", "certain", "the", "a", "an", "it", "this", "that", "these", "those", "every", "all",
                     "each", "any", "no", "use", "sense", "room", "way", "them", "us", "you", "one", "up", "clear",
                     "good", "do", "changes", "edits", "progress"}
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")


# ---------------------------------------------------------------- small helpers

def _rel(path: Path, root: Path) -> str:
    try:
        rel = Path(path).resolve().relative_to(root.resolve())
    except ValueError:
        return str(path)
    return rel.as_posix() or "."


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _code_text(path: Path) -> str:
    text = _read(path) or ""
    return "\n".join(strip_comment(line) for line in text.splitlines())


def _skip_dir(name: str) -> bool:
    return name in SKIP_DIRS or name.endswith("_backup") or name.startswith(".")


def _walk(root: Path):
    """(dirpath, dirnames, filenames) under root, pruned of skipped dirs and capped at MAX_DEPTH."""
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = len(Path(dirpath).relative_to(root).parts)
        dirnames[:] = sorted(d for d in dirnames if not _skip_dir(d)) if depth < MAX_DEPTH else []
        yield Path(dirpath), dirnames, sorted(filenames)


def _braced(text: str, i: int) -> tuple[str, int] | None:
    """Content of the brace group opening at text[i] and the index after it; None when unbalanced."""
    if i >= len(text) or text[i] != "{":
        return None
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j], j + 1
    return None


def _plain(tex: str) -> str:
    """LaTeX fragment to plain text: drop notes, unwrap commands, remove braces."""
    out = tex
    for cmd in ("thanks", "footnote", "label"):
        while True:
            m = re.search(r"\\" + cmd + r"(?![A-Za-z])\s*", out)
            if not m:
                break
            group = _braced(out, m.end())
            out = out[:m.start()] + (out[group[1]:] if group else out[m.end():])
    out = re.sub(r"\\\\(\[[^\]]*\])?", " ", out)
    out = re.sub(r"\\([&%$#_{}])", r"\1", out)
    out = re.sub(r"\\[A-Za-z]+\*?(\[[^\]]*\])?", "", out)
    out = out.replace("~", " ").replace("{", "").replace("}", "")
    return re.sub(r"\s+", " ", out).strip()


# ---------------------------------------------------------------- detection

def _main_candidates(root: Path) -> list[str]:
    out = []
    for dirpath, _dirs, files in _walk(root):
        for name in files:
            if name.endswith(".tex"):
                text = _code_text(dirpath / name)
                m = _DOCCLASS_RE.search(text)
                if m and m.group(2).strip() not in NON_MAIN_CLASSES and _BEGIN_DOC_RE.search(text):
                    out.append(_rel(dirpath / name, root))
    return sorted(out)


_NO_BUILD = {"kind": None, "command": None, "cwd": None, "main_from_makefile": None}


def _build_in(root: Path, d: str) -> dict | None:
    """Makefile or latexmkrc in repo-relative dir ``d``, with the main file it names (stem, no .tex)."""
    base = root / d
    for name in ("Makefile", "makefile", "GNUmakefile"):
        if (base / name).is_file():
            m = _MAKE_MAIN_RE.search(_read(base / name) or "")
            named = m.group(1) if m else None
            return {"kind": "make", "command": "make", "cwd": d,
                    "main_from_makefile": named[:-4] if named and named.endswith(".tex") else named}
    for name in (".latexmkrc", "latexmkrc"):
        if (base / name).is_file():
            m = _LATEXMK_FILES_RE.search(_read(base / name) or "")
            named = m.group(1) if m else None
            return {"kind": "latexmk", "command": "latexmk", "cwd": d,
                    "main_from_makefile": named[:-4] if named and named.endswith(".tex") else named}
    return None


def _named_main(build: dict) -> str | None:
    named = build.get("main_from_makefile")
    return posixpath.normpath(posixpath.join(build["cwd"], named + ".tex")) if named else None


def _build_files(root: Path, candidates: list[str]) -> list[dict]:
    """Build files in each candidate's directory, then the root."""
    dirs = list(dict.fromkeys([posixpath.dirname(c) or "." for c in candidates] + ["."]))
    return [b for b in (_build_in(root, d) for d in dirs) if b]


def _pick_main(candidates: list[str], builds: list[dict]) -> str | None:
    for b in builds:
        if _named_main(b) in candidates:
            return _named_main(b)
    return candidates[0] if len(candidates) == 1 else None


def _build_for(main: str | None, builds: list[dict]) -> dict:
    """Rulings R46/R48/R77: a build file in the main's own dir unless its MAIN or @default_files
    names a different file, else one elsewhere whose MAIN or @default_files resolves to this
    main; any other build file is never used (kind None).
    """
    if main is None:
        root_b = next((b for b in builds if b["cwd"] == "."), None)
        return dict(root_b or _NO_BUILD)
    main_dir = posixpath.dirname(main) or "."
    for b in builds:
        if b["cwd"] == main_dir and _named_main(b) in (None, main):
            return dict(b)
    for b in builds:
        if _named_main(b) == main:
            return dict(b)
    return dict(_NO_BUILD)


def _packages(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for opts, names in _USEPACKAGE_RE.findall(text):
        for n in names.split(","):
            out.setdefault(n.strip(), []).extend(o.strip() for o in opts.split(",") if o.strip())
    return out


def _title(text: str) -> str | None:
    m = _TITLE_RE.search(text)
    if not m:
        return None
    i = m.end()
    if i < len(text) and text[i] == "[":
        close = text.find("]", i)
        if close < 0:
            return None
        i = close + 1
        while i < len(text) and text[i].isspace():
            i += 1
    group = _braced(text, i)
    return _plain(group[0]) or None if group else None


def _live_authors(code: str) -> list[str]:
    """Text of every uncommented \\author{...} (optional [..] skipped)."""
    out = []
    for m in _AUTHOR_RE.finditer(code):
        i = m.end()
        while i < len(code) and code[i].isspace():
            i += 1
        if i < len(code) and code[i] == "[":
            close = code.find("]", i)
            i = len(code) if close < 0 else close + 1
            while i < len(code) and code[i].isspace():
                i += 1
        group = _braced(code, i)
        out.append(group[0] if group else "")
    return out


def _anonymized(code: str, options: list[str]) -> bool:
    """No live \\author, \\anonymous, class option anonymous, or a placeholder author name."""
    if "anonymous" in options or _ANON_CMD_RE.search(code):
        return True
    authors = _live_authors(code)
    return not authors or any(_PLACEHOLDER_AUTHOR_RE.search(a) for a in authors)


def _figures(sources: list[Path], root: Path) -> list[dict]:
    figs = []
    for src in sources:
        lines = (_read(src) or "").splitlines()
        prev = ""
        for n, line in enumerate(lines, 1):
            for path in _GRAPHICS_RE.findall(strip_comment(line)):
                figs.append({"path": path.strip(), "source": _rel(src, root), "line": n,
                             "has_provenance": prev.lstrip().startswith("% ploma:source")})
            if line.strip():
                prev = line.strip()
    return figs


def _find_dir(root: Path, match, exts: set[str]) -> str | None:
    for dirpath, dirs, _files in _walk(root):
        for d in dirs:
            if match(d.lower()):
                p = dirpath / d
                if any(f.is_file() and f.suffix.lower() in exts for f in p.rglob("*")):
                    return _rel(p, root)
    return None


def _code(root: Path, doc_root: str | None) -> dict | None:
    for child in sorted(p for p in root.iterdir() if p.is_dir() and not _skip_dir(p.name)):
        if doc_root and _rel(child, root) == doc_root:
            continue
        for marker, lang in CODE_MARKERS:
            if (child / marker).is_file():
                return {"dir": _rel(child, root), "language": lang}
    for marker, lang in CODE_MARKERS:
        if (root / marker).is_file():
            return {"dir": ".", "language": lang}
    return None


def _git_remote(root: Path) -> str | None:
    text = _read(root / ".git" / "config") if (root / ".git").is_dir() else None
    if not text:
        return None
    remotes: dict[str, str] = {}
    current = None
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r'\[remote\s+"([^"]+)"\]', s)
        if m:
            current = m.group(1)
        elif s.startswith("["):
            current = None
        elif current and s.startswith("url"):
            remotes.setdefault(current, s.split("=", 1)[1].strip())
    return remotes.get("origin") or next(iter(remotes.values()), None)


def _load_json(path: Path) -> Any:
    text = _read(path) if path.is_file() else None
    if text is None:
        return None
    try:
        return json.loads(text)
    except ValueError:
        return None


def _superpowers(root: Path, home: Path) -> dict:
    for path in (home / ".claude" / "settings.json", root / ".claude" / "settings.json",
                 root / ".claude" / "settings.local.json"):
        data = _load_json(path)
        plugins = data.get("enabledPlugins") if isinstance(data, dict) else None
        if isinstance(plugins, dict):
            for key, val in plugins.items():
                if isinstance(key, str) and key.startswith("superpowers@") and val is True:
                    return {"enabled": True, "id": key}
    return {"enabled": False, "id": None}


def _metric_keys(root: Path, results_dir: str | None) -> list[str]:
    if not results_dir:
        return []
    for path in sorted((root / results_dir).rglob("*.json")):
        data = _load_json(path)
        if isinstance(data, dict):
            return sorted(k for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool))
        return []
    return []


# ---------------------------------------------------------------- legacy harness

def _rule_line_is_fact(line: str) -> bool:
    for chunk in [line] + _CODE_SPAN_RE.findall(line):
        if any(r.search(chunk) for r in _RULE_FACT_RES):
            return True
        m = _RULE_MAKE_RE.match(chunk)
        if m and m.group(1).lower() not in _PROSE_AFTER_MAKE:
            return True
    return False


def detect_legacy_harness(root: Path) -> list[dict]:
    """Vendored harness pieces that would collide with ploma; reported, never removed."""
    root = Path(root)
    claude = root / ".claude"
    found: list[dict] = []
    skills = claude / "skills"
    if skills.is_dir():
        for d in sorted(p for p in skills.iterdir() if p.is_dir() and p.name in LEGACY_SKILL_NAMES):
            found.append({"kind": "skill_name_conflict", "path": _rel(d, root),
                          "consequence": f"duplicate skill name: /{d.name} would shadow or confuse "
                                         f"{LEGACY_SKILL_NAMES[d.name]}"})
    settings = _load_json(claude / "settings.json")
    settings = settings if isinstance(settings, dict) else {}
    hooks = settings.get("hooks")
    if isinstance(hooks, dict) and ".claude/hooks/" in json.dumps(hooks):
        found.append({"kind": "hook_entry", "path": ".claude/settings.json",
                      "consequence": "hook entry runs alongside ploma's hooks and double-fires"})
    if (claude / "scripts" / "statusline.sh").is_file() or "statusLine" in settings:
        path = ".claude/scripts/statusline.sh" if (claude / "scripts" / "statusline.sh").is_file() \
            else ".claude/settings.json"
        found.append({"kind": "statusline", "path": path,
                      "consequence": "legacy status line replaces the one that shows ploma's lifecycle stage"})
    rules = claude / "rules"
    if rules.is_dir():
        for md in sorted(rules.glob("*.md")):
            if md.name.startswith("ploma-"):
                continue
            if any(_rule_line_is_fact(line) for line in (_read(md) or "").splitlines()):
                found.append({"kind": "rule_restates_facts", "path": _rel(md, root),
                              "consequence": "rule restates build facts that ploma.yaml now owns"})
    return found


# ---------------------------------------------------------------- public API

def _valid_main(root: Path, main: str | None) -> str | None:
    if not main:
        return None
    path = (root / main).resolve()
    if path.suffix != ".tex" or not path.is_file():
        return None
    return _rel(path, root)


def inventory(root: Path, home: Path | None = None, main: str | None = None) -> dict:
    """Facts about the repo at ``root``. Reads only; writes nothing.

    ``main`` (repo-relative .tex) overrides detection, e.g. once the user answers the document.main gap.
    """
    root = Path(root).resolve()
    home = Path.home() if home is None else Path(home)
    candidates = _main_candidates(root)
    chosen = _valid_main(root, main)
    builds = _build_files(root, candidates + ([chosen] if chosen and chosen not in candidates else []))
    main = chosen or _pick_main(candidates, builds)
    build = _build_for(main, builds)
    inv: dict[str, Any] = {
        "main_candidates": candidates, "main": main, "doc_class": None, "doc_class_options": [],
        "engine_hint": "pdflatex", "bib_tool": "bibtex", "bib_files": [], "build": build, "pdf": None,
        "pdf_pages": None, "title": None, "anonymized": False, "figures": [], "uses_author_year": False,
    }
    doc_root = None
    if main:
        main_path = root / main
        doc_root = posixpath.dirname(main) or "."
        sources = tex_sources(main_path)
        code = "\n".join(_code_text(p) for p in sources)
        m = _DOCCLASS_RE.search(_code_text(main_path))
        if m:
            inv["doc_class"] = m.group(2).strip()
            inv["doc_class_options"] = [o.strip() for o in (m.group(1) or "").split(",") if o.strip()]
        pkgs = _packages(code)
        if "fontspec" in pkgs or "polyglossia" in pkgs:
            inv["engine_hint"] = "lualatex" if ("luacode" in pkgs or "luatexja" in pkgs) else "xelatex"
        if "biblatex" in pkgs and "backend=bibtex" not in pkgs["biblatex"]:
            inv["bib_tool"] = "biber"
        bl_style = any(o.startswith("style=authoryear") or o.startswith("citestyle=authoryear")
                       for o in pkgs.get("biblatex", []))
        inv["uses_author_year"] = bl_style or bool(_AUTHOR_YEAR_CITE_RE.search(code))
        inv["bib_files"] = [_rel(p, root) for p in resolve_bib_files(main_path, [])]
        cwd = build["cwd"] or doc_root
        stem = Path(main).stem
        inv["pdf"] = posixpath.normpath(posixpath.join(cwd, stem + ".pdf"))
        if (root / inv["pdf"]).is_file():
            inv["pdf_pages"] = page_count(root / inv["pdf"])[0]
        inv["title"] = _title(code)
        inv["anonymized"] = _anonymized(code, inv["doc_class_options"])
        inv["figures"] = _figures(sources, root)
    inv["reviews_dir"] = _find_dir(root, lambda n: n in ("review", "reviews") or n.startswith("referee"),
                                   REVIEW_EXTS)
    inv["results_dir"] = _find_dir(root, lambda n: n in ("results", "outputs"), RESULT_EXTS)
    inv["code"] = _code(root, doc_root if doc_root != "." else None)
    inv["git_remote"] = _git_remote(root)
    inv["superpowers"] = _superpowers(root, home)
    inv["legacy_harness"] = detect_legacy_harness(root)
    inv["_root"] = str(root)
    return inv


def _inv_root(inv: dict) -> Path | None:
    """The inventoried repo root, so its ploma.d/venues profiles are offered too."""
    return Path(inv["_root"]) if inv.get("_root") else None


def _venue_options(doc_class: str | None, root: Path | None = None) -> list[str]:
    """Venue profile keys offered for a class, recommended first, generics always offered (Ruling R7)."""
    opts = profiles.venues_for_class(doc_class, root) + ["generic-journal", "generic-conference"]
    return list(dict.fromkeys(opts))


def propose_config(inv: dict) -> dict:
    """The ploma.yaml proposal. Unknown values are omitted; venue.page_budget stays null."""
    main = inv.get("main")
    document: dict[str, Any] = {"type": "paper"}
    if main:
        document["main"] = main
        document["root"] = posixpath.dirname(main) or "."
    if inv.get("title"):
        document["title"] = inv["title"]
    if main:
        document["slug"] = Path(main).stem
    document["anonymized"] = bool(inv.get("anonymized"))

    b = inv.get("build") or {}
    build: dict[str, Any] = {}
    if b.get("command"):
        build["command"] = b["command"]
    cwd = b.get("cwd") or document.get("root")
    if cwd:
        build["cwd"] = cwd
    build["engine"] = inv.get("engine_hint") or "pdflatex"
    build["bib_tool"] = inv.get("bib_tool") or "bibtex"
    build["bib_files"] = list(inv.get("bib_files") or [])
    if main and cwd:
        stem = Path(main).stem
        build["pdf"] = posixpath.normpath(posixpath.join(cwd, stem + ".pdf"))
        build["log"] = posixpath.normpath(posixpath.join(cwd, stem + ".log"))

    venue: dict[str, Any] = {"profile": _venue_options(inv.get("doc_class"), _inv_root(inv))[0]}
    if inv.get("doc_class"):
        venue["doc_class"] = inv["doc_class"]
    venue["page_budget"] = None
    venue["cite_style"] = "author-year" if inv.get("uses_author_year") else "numeric"

    proposal: dict[str, Any] = {"ploma": "0.1", "document": document, "build": build, "venue": venue}
    if inv.get("reviews_dir"):
        proposal["reviews"] = {"glob": f"{inv['reviews_dir']}/*"}
    proposal["outputs"] = {"dir": OUTPUTS_DIR}
    code = inv.get("code")
    if code and inv.get("results_dir"):
        proposal["pipeline"] = {"enabled": True, "language": code["language"], "run_from": code["dir"],
                                "outputs_dir": inv["results_dir"], "metric_keys": [], "gotchas": []}
    return proposal


def _input_count(root: Path, rel: str) -> int:
    return len(_INPUT_RE.findall(_code_text(root / rel)))


def gaps(inv: dict, proposal: dict) -> list[dict]:
    """Questions the repo cannot answer, each with a recommended answer and options."""
    out: list[dict] = []
    root = Path(inv.get("_root") or ".")
    if not inv.get("main"):
        cands = inv.get("main_candidates") or []
        ranked = sorted(cands, key=lambda c: -_input_count(root, c))
        out.append({"key": "document.main", "question": "Which .tex file is the main manuscript?",
                    "recommended": ranked[0] if ranked else None, "options": cands})
    opts = _venue_options(inv.get("doc_class"), _inv_root(inv))
    out.append({"key": "venue.profile",
                "question": f"Which venue profile fits this paper (document class {inv.get('doc_class') or 'unknown'})?",
                "recommended": opts[0], "options": opts})
    try:
        budget = profiles.load_venue(opts[0], _inv_root(inv)).get("page_budget")
    except profiles.ProfileError:
        budget = None
    out.append({"key": "venue.page_budget", "question": "What is the page budget for this venue (null for none)?",
                "recommended": budget, "options": []})
    if inv.get("code"):
        out.append({"key": "pipeline.enabled",
                    "question": f"Is the code tree in {inv['code']['dir']} the pipeline that produces this paper's numbers?",
                    "recommended": bool(inv.get("results_dir")), "options": [True, False]})
    if (proposal.get("pipeline") or {}).get("enabled"):
        keys = _metric_keys(root, inv.get("results_dir"))
        out.append({"key": "pipeline.metric_keys",
                    "question": "Which result keys are metrics the manuscript reports?",
                    "recommended": keys, "options": keys})
    return out


# ---------------------------------------------------------------- CLI

def _public(inv: dict) -> dict:
    return {k: v for k, v in inv.items() if not k.startswith("_")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only repository inventory for ploma onboarding.")
    parser.add_argument("action", nargs="?", default="inventory", choices=("inventory", "propose", "gaps"))
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--main", default=None, help="main .tex file, repo-relative (overrides detection)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    root = Path(args.root)
    if not root.is_dir():
        print(f"inventory: {root} is not a directory", file=sys.stderr)
        return 2
    if args.main and not _valid_main(root.resolve(), args.main):
        print(f"inventory: --main {args.main} is not a .tex file under {root}", file=sys.stderr)
        return 2
    inv = inventory(root, main=args.main)
    if args.action == "inventory":
        data: Any = _public(inv)
    else:
        proposal = propose_config(inv)
        data = proposal if args.action == "propose" else gaps(inv, proposal)
    if args.json:
        print(json.dumps(data, indent=2))
    elif args.action == "propose":
        print(_yamlio.dump_yaml(data), end="")
    elif args.action == "gaps":
        for g in data:
            print(f"- {g['key']}: {g['question']}\n  Recommended: {g['recommended']!r}; options: {g['options']}")
    else:
        for key, val in data.items():
            print(f"{key}: {json.dumps(val)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
