"""Bibliography structural checks: cite keys against entries, near misses, unused entries, duplicates.

Usage: python3 scripts/bib_check.py <main.tex> [--bib a.bib ...] [--json]
Exit codes: 0 no FAIL findings, 1 at least one FAIL, 2 usage error or unreadable main file.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from _findings import FAIL, INFO, WARN, Finding, render

SKIPPED_TYPES = {"comment", "preamble", "string"}
# Style families for bib.cite_style_mix; everything else in CITE_COMMANDS is neutral.
NATBIB = {"citep", "citet", "citealp", "citeyearpar", "Citep", "Citet", "Citealp"}
BIBLATEX = {"parencite", "textcite", "autocite", "footcite", "smartcite", "supercite", "fullcite", "cites",
            "Parencite", "Textcite", "Autocite", "Footcite", "Smartcite", "Cites"}
NEUTRAL = {"cite", "nocite", "citealt", "citeauthor", "Citeauthor", "citeyear", "citenum", "citetitle"}
CITE_COMMANDS = NEUTRAL | NATBIB | BIBLATEX
MULTI_CITE = {"cites", "Cites"}  # every braced group after the command holds keys

_CMD_RE = re.compile(r"\\([A-Za-z]+)\*?")
_ARG_RE = re.compile(r"\s*(?:\[([^\]]*)\]|\{([^}]*)\})")
_INCLUDE_RE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
_BIBLIO_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
_ADDBIB_RE = re.compile(r"\\addbibresource\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
_REF_FIELDS = {"doi", "url"}  # LaTeX escapes and braces removed at parse time (R127 D1)
_ESCAPE_RE = re.compile(r"\\([_%&#$])")
_DOI_PREFIXES = ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "http://dx.doi.org/", "doi:")


@dataclass
class Entry:
    key: str
    type: str
    fields: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------- bib parsing

def _match_close(text: str, start: int, opener: str) -> int:
    """Index of the delimiter closing the one at ``start`` (``{`` or ``(``); len(text) when unbalanced."""
    depth = 0
    i = start + 1
    while i < len(text):
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            if depth == 0 and opener == "{":
                return i
            depth -= 1
        elif c == ")" and opener == "(" and depth == 0:
            return i
        i += 1
    return len(text)


def _split_top(body: str, sep: str) -> list[str]:
    """Split on ``sep`` at brace depth 0 and outside double-quoted strings."""
    parts, depth, quoted, cur = [], 0, False, []
    for c in body:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == '"' and depth == 0:
            quoted = not quoted
        if c == sep and depth == 0 and not quoted:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    parts.append("".join(cur))
    return parts


def _value(raw: str, macros: dict[str, str]) -> str:
    """Field value with outer braces or quotes stripped, ``#`` pieces joined, macros expanded."""
    out = []
    for piece in _split_top(raw, "#"):
        piece = piece.strip()
        if len(piece) >= 2 and ((piece[0] == "{" and piece[-1] == "}") or (piece[0] == '"' and piece[-1] == '"')):
            out.append(piece[1:-1])
        else:
            out.append(macros.get(piece.lower(), piece))
    return "".join(out)


def unescape_ref(value: str) -> str:
    """``doi``/``url`` value as a resolver needs it: ``\\_ \\% \\& \\# \\$`` unescaped, braces removed."""
    return _ESCAPE_RE.sub(r"\1", value).replace("{", "").replace("}", "").strip()


def _fields(chunks: list[str], macros: dict[str, str]) -> dict[str, str]:
    fields: dict[str, str] = {}
    for chunk in chunks:
        if "=" not in chunk:
            continue
        name, raw = chunk.split("=", 1)
        name = name.strip().lower()
        if name:
            value = _value(raw, macros)
            fields[name] = unescape_ref(value) if name in _REF_FIELDS else value
    return fields


def parse_bib(text: str) -> list[Entry]:
    """Entries of a BibTeX file; ``@comment``, ``@preamble`` and ``@string`` are skipped (strings expanded)."""
    entries: list[Entry] = []
    macros: dict[str, str] = {}
    i = 0
    while True:
        at = text.find("@", i)
        if at < 0:
            break
        m = re.match(r"@\s*([A-Za-z]+)\s*([{(])", text[at:])
        if not m:
            i = at + 1
            continue
        etype = m.group(1).lower()
        open_at = at + m.end() - 1
        close = _match_close(text, open_at, m.group(2))
        body = text[open_at + 1:close]
        i = close + 1
        if etype == "string":
            macros.update((k, v) for k, v in _fields([body], macros).items())
            continue
        if etype in SKIPPED_TYPES:
            continue
        chunks = _split_top(body, ",")
        key = chunks[0].strip()
        if not key or "=" in key:
            continue
        entries.append(Entry(key, etype, _fields(chunks[1:], macros)))
    return entries


# ---------------------------------------------------------------- tex scanning

def strip_comment(line: str) -> str:
    """Line text before the first unescaped ``%`` (``\\%`` is a literal percent)."""
    i = 0
    while i < len(line):
        if line[i] == "\\":
            i += 2
            continue
        if line[i] == "%":
            return line[:i]
        i += 1
    return line


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _code_lines(path: Path) -> list[str]:
    text = _read(path)
    return [] if text is None else [strip_comment(line) for line in text.splitlines()]


def tex_sources(main: Path) -> list[Path]:
    """``main`` plus every file reached through ``\\input``/``\\include``, depth first, existing files only.

    Names resolve from the main file's directory, as LaTeX does; ``.tex`` is appended when missing.
    """
    main = Path(main).resolve()
    base = main.parent
    seen: list[Path] = []

    def visit(path: Path) -> None:
        if path in seen or not path.is_file():
            return
        seen.append(path)
        for line in _code_lines(path):
            for name in _INCLUDE_RE.findall(line):
                name = name.strip()
                if not name.endswith(".tex"):
                    name += ".tex"
                visit((base / name).resolve())

    visit(main)
    return seen


def _cite_groups(line: str) -> list[tuple[str, list[str]]]:
    """(command, [key group, ...]) per citation command on a comment-stripped line.

    Optional ``[...]`` arguments are skipped; ordinary commands take their first braced group,
    multi-citation commands (``\\cites``) take every braced group that follows.
    """
    out = []
    for m in _CMD_RE.finditer(line):
        cmd = m.group(1)
        if cmd not in CITE_COMMANDS:
            continue
        pos, groups = m.end(), []
        while True:
            a = _ARG_RE.match(line, pos)
            if not a:
                break
            pos = a.end()
            if a.group(2) is not None:
                groups.append(a.group(2))
                if cmd not in MULTI_CITE:
                    break
        if groups:
            out.append((cmd, groups))
    return out


def _citations(tex_files: list[Path]) -> list[tuple[str, str, Path, int]]:
    """(command, key, path, line) for every citation outside comments."""
    out = []
    for path in tex_files:
        for n, line in enumerate(_code_lines(Path(path)), 1):
            for cmd, groups in _cite_groups(line):
                for keys in groups:
                    for key in keys.split(","):
                        key = key.strip()
                        if key:
                            out.append((cmd, key, Path(path), n))
    return out


def cite_keys(tex_files: list[Path]) -> dict[str, list[tuple[Path, int]]]:
    """Cited key -> [(file, line number), ...] in reading order."""
    keys: dict[str, list[tuple[Path, int]]] = {}
    for _cmd, key, path, n in _citations(tex_files):
        keys.setdefault(key, []).append((path, n))
    return keys


def resolve_bib_files(main: Path, declared: list[Path]) -> list[Path]:
    """Declared bib files first, then ``\\bibliography``/``\\addbibresource`` targets from every source.

    Relative names resolve from the main file's directory; ``.bib`` is appended when missing.
    Files that do not exist are kept so the caller can report them.
    """
    base = Path(main).resolve().parent
    names: list[str | Path] = list(declared)
    for path in tex_sources(main):
        for line in _code_lines(path):
            for group in _BIBLIO_RE.findall(line):
                names.extend(n.strip() for n in group.split(",") if n.strip())
            names.extend(n.strip() for n in _ADDBIB_RE.findall(line) if n.strip())
    out: list[Path] = []
    for name in names:
        p = Path(name)
        if p.suffix != ".bib":
            p = p.with_name(p.name + ".bib")
        p = (base / p).resolve()
        if p not in out:
            out.append(p)
    return out


# ---------------------------------------------------------------- checks

def levenshtein(a: str, b: str) -> int:
    """Edit distance (insertions, deletions, substitutions)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _norm_doi(doi: str) -> str:
    d = unescape_ref(doi).lower()
    for prefix in _DOI_PREFIXES:
        if d.startswith(prefix):
            d = d[len(prefix):]
    return d.strip()


def _norm_title(title: str) -> str:
    return re.sub(r"[^0-9a-z]", "", title.lower())


def check_entries(entries: list[Entry]) -> list[Finding]:
    """Bib-only checks: duplicate keys, duplicate DOIs and duplicate normalised titles (later entry against the first)."""
    findings: list[Finding] = []
    seen_keys: set[str] = set()
    reported: set[str] = set()
    for e in entries:
        if e.key in seen_keys and e.key not in reported:
            reported.add(e.key)
            findings.append(Finding(
                f"bib.duplicate_key.{e.key}", WARN, f"key {e.key} is defined more than once",
                observed=f"{sum(x.key == e.key for x in entries)} entries with key {e.key}",
                remediation="keep one entry per key; BibTeX uses the first and ignores the rest",
                group="bib"))
        seen_keys.add(e.key)
    for fld, norm, kind in (("doi", _norm_doi, "doi"), ("title", _norm_title, "title")):
        first: dict[str, Entry] = {}
        for e in entries:
            value = norm(e.fields.get(fld, ""))
            if not value:
                continue
            if value in first and first[value].key != e.key:
                a = first[value]
                findings.append(Finding(
                    f"bib.duplicate_{kind}.{a.key}+{e.key}", WARN,
                    f"{a.key} and {e.key} share the same {kind}",
                    observed=f"{fld} = {e.fields[fld]}",
                    remediation=f"keep one entry and cite it everywhere; remove or merge {e.key}",
                    group="bib"))
            else:
                first.setdefault(value, e)
    return findings


def check(main: Path, bib_files: list[Path]) -> list[Finding]:
    """Cite keys against entries across all resolved bib files, plus duplicate checks on those entries."""
    findings: list[Finding] = []
    entries: list[Entry] = []
    for bib in resolve_bib_files(main, bib_files):
        text = _read(bib) if bib.is_file() else None
        if text is None:
            findings.append(Finding(f"bib.file_missing.{bib.name}", FAIL, f"bibliography file {bib.name} not found",
                                    observed=str(bib), remediation="create the file or fix the declared path",
                                    group="bib"))
            continue
        entries.extend(parse_bib(text))
    known: dict[str, Entry] = {}
    for e in entries:
        known.setdefault(e.key, e)
    lower = {k.lower(): k for k in known}

    cites = _citations(tex_sources(main))
    cited: dict[str, tuple[Path, int]] = {}
    for _cmd, key, path, n in cites:
        cited.setdefault(key, (path, n))
    for key, (path, n) in cited.items():
        if key == "*" or key in known:
            continue
        where = f"{path.name}:{n}"
        findings.append(Finding(f"bib.missing.{key}", FAIL, f"cite key {key} has no bibliography entry",
                                observed=where, remediation="add the entry or fix the key", group="bib"))
        near = lower.get(key.lower())
        if near is None:
            scored = sorted((levenshtein(key.lower(), k.lower()), k) for k in known)
            near = scored[0][1] if scored and scored[0][0] <= 2 else None
        if near is not None:
            findings.append(Finding(f"bib.near_miss.{key}", WARN, f"cite key {key} is close to existing key {near}",
                                    observed=where, remediation=f"did you mean {near}?", group="bib"))
    if "*" not in cited:
        for key in known:
            if key not in cited:
                findings.append(Finding(f"bib.unused.{key}", INFO, f"entry {key} is never cited",
                                        remediation="remove it or cite it", group="bib"))
    findings.extend(check_entries(entries))

    commands = {cmd for cmd, *_ in cites}
    natbib, biblatex = commands & NATBIB, commands & BIBLATEX
    if natbib and biblatex:
        findings.append(Finding("bib.cite_style_mix", WARN, "natbib and biblatex citation commands are mixed",
                                observed=", ".join(sorted("\\" + c for c in natbib | biblatex)),
                                remediation="use one citation package's commands throughout", group="bib"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Structural bibliography checks.")
    parser.add_argument("main", help="main .tex file")
    parser.add_argument("--bib", action="append", default=[], help="bib file (repeatable)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    main_path = Path(args.main)
    if not main_path.is_file() or _read(main_path) is None:
        msg = f"cannot read main file {main_path}"
        print(json.dumps({"error": msg}) if args.json else f"bib_check: {msg}", file=sys.stdout if args.json else sys.stderr)
        return 2
    findings = check(main_path, [Path(b).resolve() for b in args.bib])
    if args.json:
        print(json.dumps({"findings": [f.to_dict() for f in findings]}, indent=2))
    else:
        print(render(findings) if findings else "bib: no findings")
    return 1 if any(f.status == FAIL for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
