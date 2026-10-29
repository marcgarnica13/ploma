#!/usr/bin/env python3
"""Section outline of the manuscript, section lookup, and the self-check of a /ploma:write draft.

Usage:
  python3 scripts/sections.py [--root R] [--json] list
  python3 scripts/sections.py [--root R] [--json] resolve <query>
  python3 scripts/sections.py [--root R] [--json] check <query> <draft.tex>

A query is a \\section title (case-insensitive), a \\label (for example sec:intro), or a .tex path
under document.root. A section runs from its \\section line to the line before the next \\section,
\\appendix, \\chapter, \\part, \\bibliographystyle, \\bibliography, \\printbibliography,
\\begin{thebibliography}, an acknowledgments environment (acks, acknowledgments) or \\end{document}, or
before the \\input line that leads to the next section; trailing blank lines and page or column breaks
(\\clearpage, \\newpage, \\cleardoublepage, \\onecolumn, \\twocolumn) are left out. A file under
document.root with no \\section is one span covering the whole file.

check splices the draft body (the draft without its leading comment header) over the section in a
copy of the manuscript under .ploma/tmp/ (first removing write-* copies older than an hour), runs the consistency pass on that copy and on an unspliced
copy, deletes the copies, and reports: consistency findings (marked new or unchanged against the
current manuscript, with draft lines mapped to the draft file), numbers the draft introduces that
appear nowhere else in the manuscript or the results files, new \\includegraphics without a
preceding "% ploma:source" line (when pipeline.enabled), whether the section changed since the draft
header's "Source sha", and a unified diff of the current section against the draft body. The real
manuscript files are only read.

Exit codes: 0 ok, 2 usage error, unknown or ambiguous section, unreadable config or draft.
"""
from __future__ import annotations

import argparse
import datetime
import difflib
import hashlib
import json
import re
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _texmask  # noqa: E402
import bib_check  # noqa: E402
import consistency  # noqa: E402
import ploma_config  # noqa: E402
import style_check  # noqa: E402

_SECTION_RE = re.compile(r"\\section(\*?)\s*(?:\[[^\]]*\])?\s*\{")
_BOUNDARY_RE = re.compile(r"\\(?:appendix|chapter|part|bibliography|bibliographystyle|printbibliography)(?![A-Za-z])"
                          r"|\\(?:begin|end)\s*\{document\}"
                          r"|\\begin\s*\{(?:thebibliography|acks|acknowledgments|acknowledgements)\}")
_NON_PROSE_RE = re.compile(r"^\s*(?:\\(?:clearpage|newpage|cleardoublepage|onecolumn|twocolumn)\b\s*)*$")
_APPENDIX_RE = re.compile(r"\\appendix(?![A-Za-z])")
_BEGIN_DOC_RE = re.compile(r"\\begin\s*\{document\}")
_LABEL_RE = re.compile(r"\\label\s*\{([^}]*)\}")
_FIGURE_RE = re.compile(r"\\begin\s*\{figure\*?\}")
_TABLE_RE = re.compile(r"\\begin\s*\{table\*?\}")
_GRAPHICS_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\])?\s*\{([^}]+)\}")
_SHA_RE = re.compile(r"^%\s*Source sha:\s*([0-9a-f]{12})\b", re.M)
SOURCE_PREFIX = "% ploma:source"


@dataclass
class Section:
    title: str
    number: str | None
    label: str | None
    file: Path
    start: int
    end: int
    figures: int = 0
    tables: int = 0
    words: int = 0
    whole_file: bool = False

    def to_dict(self, root: Path) -> dict:
        return {"title": self.title, "number": self.number, "label": self.label, "file": _rel(self.file, root),
                "start": self.start, "end": self.end, "figures": self.figures, "tables": self.tables,
                "words": self.words, "whole_file": self.whole_file}


@dataclass
class _Event:
    file: Path
    line: int
    code: str
    stack: tuple[tuple[Path, int], ...]


def _rel(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(path)


def _raw_lines(path: Path) -> list[str]:
    return Path(path).read_text(encoding="utf-8", errors="replace").split("\n")


def _events(main: Path) -> list[_Event]:
    """Every code line (comments stripped) in reading order, each \\input expanded after its line."""
    main = Path(main).resolve()
    base = main.parent
    seen: set[Path] = set()
    out: list[_Event] = []

    def visit(path: Path, stack: tuple[tuple[Path, int], ...]) -> None:
        if path in seen or not path.is_file():
            return
        seen.add(path)
        for i, code in enumerate(bib_check._code_lines(path), 1):
            out.append(_Event(path, i, code, stack))
            for name in bib_check._INCLUDE_RE.findall(code):
                name = name.strip()
                child = (base / (name if name.endswith(".tex") else name + ".tex")).resolve()
                visit(child, stack + ((path, i),))

    visit(main, ())
    return out


def clean_title(raw: str) -> str:
    text = _LABEL_RE.sub(" ", raw)
    text = re.sub(r"\\[A-Za-z]+\*?\s*(?:\[[^\]]*\])?", " ", text).replace("~", " ")
    text = re.sub(r"[{}$]", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _title_at(file_lines: list[str], idx: int, col: int) -> str:
    """The balanced-brace title opening at file_lines[idx][col - 1] ("{"), across up to five lines."""
    text = "\n".join(file_lines[idx: idx + 5])
    end = _texmask.group_end(text, col - 1)
    return text[col: end - 1] if end > 0 else text[col:].split("\n", 1)[0]


def _letters(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _end_index(events: list[_Event], i: int, is_stop) -> tuple[int, int]:
    """(index of the event that ends the span opened at events[i], last line of the span in its file)."""
    f = events[i].file
    n_lines = len(_raw_lines(f))
    for j in range(i + 1, len(events)):
        e = events[j]
        inside = e.file == f or any(p == f for p, _ in e.stack)
        if not inside:
            return j, n_lines
        if is_stop(j):
            if e.file == f:
                return j, e.line - 1
            inc = [line for p, line in e.stack if p == f][0]
            return j, max(inc - 1, events[i].line)
    return len(events), n_lines


def _trim(path: Path, start: int, end: int) -> int:
    lines = _raw_lines(path)
    end = min(end, len(lines))
    while end > start and _NON_PROSE_RE.match(bib_check.strip_comment(lines[end - 1])):
        end -= 1  # blank lines and page or column breaks belong to no section
    return max(end, start)


def _measure(events: list[_Event], i: int, j: int) -> tuple[int, int, int]:
    chunk = "\n".join(e.code for e in events[i:j])
    masked = style_check._CMD_NAME_RE.sub(" ", style_check.prose(chunk))
    return (len(_FIGURE_RE.findall(chunk)), len(_TABLE_RE.findall(chunk)),
            len(style_check._WORD_RE.findall(masked)))


def outline(main: Path) -> list[Section]:
    """Every \\section reached from main (after \\begin{document} when main has one), in reading order."""
    main = Path(main).resolve()
    events = _events(main)
    has_doc = any(e.file == main and _BEGIN_DOC_RE.search(e.code) for e in events)
    in_doc = not has_doc
    kinds: list[str | None] = []
    for e in events:
        kind = None
        if not in_doc:
            if e.file == main and _BEGIN_DOC_RE.search(e.code):
                in_doc = True
        elif _SECTION_RE.search(e.code):
            kind = "section"
        elif _BOUNDARY_RE.search(e.code):
            kind = "appendix" if _APPENDIX_RE.search(e.code) else "boundary"
        kinds.append(kind)

    out: list[Section] = []
    counter, appendix = 0, False
    lines_cache: dict[Path, list[str]] = {}
    for i, (e, kind) in enumerate(zip(events, kinds)):
        if kind == "appendix":
            counter, appendix = 0, True
        if kind != "section":
            continue
        m = _SECTION_RE.search(e.code)
        lines = lines_cache.setdefault(e.file, _raw_lines(e.file))
        raw_title = _title_at(lines, e.line - 1, m.end())
        number = None
        if not m.group(1):
            counter += 1
            number = _letters(counter) if appendix else str(counter)
        j, last = _end_index(events, i, lambda k: kinds[k] in ("section", "appendix", "boundary"))
        end = _trim(e.file, e.line, last)
        label = None
        for k in range(e.line - 1, min(e.line + 2, end)):
            lm = _LABEL_RE.search(bib_check.strip_comment(lines[k]))
            if lm:
                label = lm.group(1).strip()
                break
        figs, tabs, words = _measure(events, i, j)
        out.append(Section(clean_title(raw_title), number, label, e.file, e.line, end, figs, tabs, words))
    per_file: dict[Path, int] = {}
    for s in out:
        per_file[s.file] = per_file.get(s.file, 0) + 1
    for s in out:
        s.whole_file = s.file != main and per_file[s.file] == 1
    return out


def _fragment(main: Path, path: Path) -> Section:
    """A file under document.root with no \\section: one span over the whole file."""
    lines = _raw_lines(path)
    end = _trim(path, 1, len(lines))
    events = [_Event(path, i, code, ()) for i, code in enumerate(bib_check._code_lines(path), 1)]
    figs, tabs, words = _measure(events, 0, len(events))
    return Section(path.stem, None, None, path.resolve(), 1, end, figs, tabs, words, whole_file=True)


def _describe(s: Section, root: Path) -> str:
    bits = [b for b in (s.label, f"{_rel(s.file, root)}:{s.start}") if b]
    return f"{s.title} ({', '.join(bits)})"


def resolve(root: Path, main: Path, query: str, doc_root: Path | None = None) -> Section:
    """The one section matching query; LookupError naming the candidates otherwise."""
    root = Path(root).resolve()
    doc_root = Path(doc_root).resolve() if doc_root else root
    secs = outline(main)
    q = query.strip()
    candidates = "; ".join(_describe(s, root) for s in secs) or "no \\section found"
    if q.endswith(".tex") or "/" in q:
        path = Path(q) if Path(q).is_absolute() else root / q
        path = path.resolve()
        if not path.is_file():
            raise LookupError(f"no file {q}. Sections: {candidates}")
        try:
            path.relative_to(doc_root)
        except ValueError:
            raise LookupError(f"{q} is outside document.root ({_rel(doc_root, root) or '.'})") from None
        in_file = [s for s in secs if s.file == path]
        if not in_file and path != Path(main).resolve():
            in_file = [s for s in outline(path) if s.file == path]
        if len(in_file) == 1:
            return in_file[0]
        if not in_file:
            return _fragment(main, path)
        raise LookupError(f"{q} holds {len(in_file)} sections; name one: "
                          + "; ".join(_describe(s, root) for s in in_file))
    hits = [s for s in secs if s.label == q] or [s for s in secs if s.title.casefold() == q.casefold()]
    if len(hits) == 1:
        return hits[0]
    if hits:
        raise LookupError(f"{q!r} matches {len(hits)} sections; use a label or a path: "
                          + "; ".join(_describe(s, root) for s in hits))
    raise LookupError(f"no section matches {q!r}. Sections: {candidates}")


def slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return s[:40].rstrip("_") or "section"


def sibling_path(sec: Section) -> Path:
    stem = sec.file.stem if sec.whole_file else slug(sec.title)
    return (sec.file.parent / f"{stem}_suggestion.tex").resolve()


def section_lines(sec: Section) -> list[str]:
    return _raw_lines(sec.file)[sec.start - 1: sec.end]


def section_sha(sec: Section) -> str:
    return hashlib.sha256("\n".join(section_lines(sec)).encode("utf-8")).hexdigest()[:12]


def split_draft(text: str) -> tuple[int, list[str]]:
    """(lines taken by the leading comment header and the blank lines after it, body lines)."""
    lines = text.splitlines()
    n = 0
    while n < len(lines) and lines[n].lstrip().startswith("%"):
        n += 1
    if n:
        while n < len(lines) and not lines[n].strip():
            n += 1
    return n, lines[n:]


# ---------------------------------------------------------------- check

def _copy_manuscript(srcs: list[Path], base: Path, dest: Path, splice: tuple[Path, int, int, list[str]] | None) -> None:
    for src in srcs:
        try:
            rel = src.relative_to(base)
        except ValueError:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8", errors="replace")
        if splice and src == splice[0]:
            lines = text.split("\n")
            text = "\n".join(lines[: splice[1] - 1] + splice[3] + lines[splice[2]:])
        target.write_text(text, encoding="utf-8")


def _numbers_outside(srcs: list[Path], main: Path, sec: Section) -> list[dict]:
    out: list[dict] = []
    for src in srcs:
        text = _texmask.strip_comments(src.read_text(encoding="utf-8", errors="replace"))
        if src == main:
            text = _texmask.mask_before_document(text)
        if src == sec.file:
            lines = text.split("\n")
            for k in range(sec.start - 1, min(sec.end, len(lines))):
                lines[k] = ""
            text = "\n".join(lines)
        out += consistency.extract_numbers(text)
    return out


def _graphics(lines: list[str]) -> list[tuple[int, str, bool]]:
    """(1-based line, target, has a preceding "% ploma:source" line) for each \\includegraphics."""
    out = []
    for i, line in enumerate(lines):
        for m in _GRAPHICS_RE.finditer(bib_check.strip_comment(line)):
            prev = next((lines[k].strip() for k in range(i - 1, -1, -1) if lines[k].strip()), "")
            out.append((i + 1, m.group(1).strip(), prev.startswith(SOURCE_PREFIX)))
    return out


STALE_TMP_SECONDS = 3600


def _sweep(tmp_root: Path) -> None:
    """Remove write-* copies left by an interrupted check (older than STALE_TMP_SECONDS)."""
    cutoff = time.time() - STALE_TMP_SECONDS
    for d in tmp_root.glob("write-*"):
        try:
            if d.is_dir() and d.stat().st_mtime < cutoff:
                shutil.rmtree(d, ignore_errors=True)
        except OSError:
            pass


def check(root: Path, main: Path, query: str, draft: Path) -> dict:
    root = Path(root).resolve()
    cfg = ploma_config.load(root)
    paths = ploma_config.resolve(cfg, root)["_paths"]
    main = Path(main).resolve()
    sec = resolve(root, main, query, Path(paths["root"]) if paths.get("root") else None)
    draft = Path(draft).resolve()
    header_n, body = split_draft(draft.read_text(encoding="utf-8", errors="replace"))
    header_text = "\n".join(draft.read_text(encoding="utf-8", errors="replace").splitlines()[:header_n])
    sha_m = _SHA_RE.search(header_text)
    old = section_lines(sec)
    draft_rel, file_rel = _rel(draft, root), _rel(sec.file, root)

    pipe = cfg.get("pipeline") or {}
    results_dir = root / pipe["outputs_dir"] if pipe.get("enabled") and pipe.get("outputs_dir") else None
    keys = list(pipe.get("metric_keys") or [])
    tolerances = {**consistency.DEFAULT_TOLERANCES, **(pipe.get("tolerances") or {})}

    srcs = bib_check.tex_sources(main)
    base = main.parent
    main_rel_file = _rel(sec.file, base)
    _sweep(root / ".ploma" / "tmp")
    tmp = root / ".ploma" / "tmp" / f"write-{uuid.uuid4().hex[:8]}"
    try:
        _copy_manuscript(srcs, base, tmp / "current", None)
        _copy_manuscript(srcs, base, tmp / "draft", (sec.file, sec.start, sec.end, body))
        rel_main = main.relative_to(base)
        current = consistency.run(tmp / "current" / rel_main, results_dir=results_dir, metric_keys=keys,
                                  tolerances=tolerances)
        spliced = consistency.run(tmp / "draft" / rel_main, results_dir=results_dir, metric_keys=keys,
                                  tolerances=tolerances)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            tmp.parent.rmdir()
        except OSError:
            pass

    delta = len(body) - (sec.end - sec.start + 1)

    def remap(text: str) -> str:
        def sub(m: re.Match) -> str:
            n = int(m.group(1))
            if sec.start <= n < sec.start + len(body):
                return f"{draft_rel}:{n - sec.start + 1 + header_n}"
            return f"{file_rel}:{n - delta if n >= sec.start + len(body) else n}"
        return re.sub(re.escape(main_rel_file) + r":(\d+)", sub, text)

    before_ids = {f.id for f in current.findings}
    after_ids = {f.id for f in spliced.findings}
    findings = []
    for f in spliced.findings:
        d = f.to_dict()
        d["observed"], d["summary"] = remap(d["observed"]), remap(d["summary"])
        d["change"] = "unchanged" if f.id in before_ids else "new"
        findings.append(d)

    body_text = _texmask.strip_comments("\n".join(body))
    draft_nums = consistency.extract_numbers(body_text)
    old_nums = consistency.extract_numbers(_texmask.strip_comments("\n".join(old)))
    rest = _numbers_outside(srcs, main, sec)
    results = consistency.load_results(results_dir, keys) if results_dir else consistency.Results()
    unplaced, seen = [], set()
    for n in draft_nums:
        if n["raw"] in seen:
            continue
        if any(consistency.same_number(n, o) for o in old_nums + rest):
            continue
        if any(consistency.matches(n, v, tolerances) for v in results.values):
            continue
        seen.add(n["raw"])
        unplaced.append({"raw": n["raw"], "kind": n["kind"], "location": f"{draft_rel}:{n['line'] + header_n}"})

    no_source = []
    if pipe.get("enabled"):
        old_targets = {t for _, t, _ in _graphics(old)}
        for line, target, ok in _graphics(body):
            if not ok and target not in old_targets:
                no_source.append({"target": target, "location": f"{draft_rel}:{line + header_n}"})

    diff = "\n".join(difflib.unified_diff(old, body, fromfile=f"{file_rel} (lines {sec.start}-{sec.end})",
                                          tofile=draft_rel, lineterm=""))
    return {
        "section": sec.to_dict(root),
        "draft": draft_rel,
        "header_lines": header_n,
        "stale": None if not sha_m else sha_m.group(1) != section_sha(sec),
        "consistency": {"verdict": spliced.verdict, "current_verdict": current.verdict, "findings": findings,
                        "resolved": sorted(before_ids - after_ids)},
        "new_numbers_unplaced": unplaced,
        "figures_without_source": no_source,
        "diff": diff + "\n" if diff else "",
    }


# ---------------------------------------------------------------- CLI

def _resolve_info(root: Path, cfg: dict, paths: dict, sec: Section) -> dict:
    sib = sibling_path(sec)
    spec = Path(paths["outputs_dir"]) / "paper_spec.md"
    return {**sec.to_dict(root), "sha": section_sha(sec), "sibling": _rel(sib, root), "sibling_exists": sib.is_file(),
            "date": datetime.date.today().isoformat(), "spec": _rel(spec, root), "spec_exists": spec.is_file(),
            "pipeline_enabled": bool((cfg.get("pipeline") or {}).get("enabled"))}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Section outline, lookup and the write self-check.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    r = sub.add_parser("resolve")
    r.add_argument("query")
    c = sub.add_parser("check")
    c.add_argument("query")
    c.add_argument("draft")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    def fail(msg: str) -> int:
        print(json.dumps({"error": msg}) if args.json else f"sections: {msg}",
              file=sys.stdout if args.json else sys.stderr)
        return 2

    root = Path(args.root).resolve()
    try:
        cfg = ploma_config.load(root)
    except ploma_config.ConfigError as exc:
        return fail(exc.message)
    paths = ploma_config.resolve(cfg, root)["_paths"]
    main_path = Path(paths["main"]) if paths.get("main") else None
    if main_path is None or not main_path.is_file():
        return fail(f"cannot read main file {main_path or '(document.main not set)'}")
    doc_root = Path(paths["root"]) if paths.get("root") else root

    try:
        if args.action == "list":
            data = [s.to_dict(root) for s in outline(main_path)]
            if args.json:
                print(json.dumps(data, indent=2))
            else:
                for s in data:
                    print(f"{s['number'] or '-'} {s['title']}: {s['file']}:{s['start']}-{s['end']}"
                          + (f" ({s['label']})" if s["label"] else ""))
            return 0
        sec = resolve(root, main_path, args.query, doc_root)
        if args.action == "resolve":
            info = _resolve_info(root, cfg, paths, sec)
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"{info['title']}: {info['file']} lines {info['start']}-{info['end']} (sha {info['sha']})")
                print(f"sibling: {info['sibling']}" + (" (exists)" if info["sibling_exists"] else ""))
            return 0
        draft = Path(args.draft)
        draft = draft if draft.is_absolute() else root / draft
        if not draft.is_file():
            return fail(f"cannot read draft {args.draft}")
        rep = check(root, main_path, args.query, draft)
    except LookupError as exc:
        return fail(str(exc).strip("'\""))
    except (OSError, ValueError) as exc:
        return fail(str(exc))
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0
    print(f"draft {rep['draft']} for {rep['section']['file']} lines {rep['section']['start']}-{rep['section']['end']}")
    if rep["stale"]:
        print("STALE: the section changed since the draft was written")
    cons = rep["consistency"]
    print(f"consistency on the spliced copy: {cons['verdict']} (current manuscript: {cons['current_verdict']})")
    for f in cons["findings"]:
        print(f"- {f['status']} [{f['change']}] {f['id']}: {f['summary']}\n  Observed: {f['observed']}")
    for n in rep["new_numbers_unplaced"]:
        print(f"- number {n['raw']} at {n['location']} appears nowhere else in the manuscript or results")
    for g in rep["figures_without_source"]:
        print(f"- {g['location']}: \\includegraphics{{{g['target']}}} has no '{SOURCE_PREFIX}' line")
    print(rep["diff"], end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
