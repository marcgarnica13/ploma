#!/usr/bin/env python3
"""Per-section page map of the built PDF and the page budget check behind /ploma:format.

Usage: python3 scripts/page_map.py [--root R] [--pdf P] [--budget N] [--json]

Sections come from the manuscript (scripts/sections.py outline: every \\section reached from
document.main, numbered as LaTeX numbers them). Each is located in the PDF text (pdftotext -layout)
in reading order, first as "<number> <title>", then by its bare title; a section is never placed
before the one ahead of it. The start of the references is the last line that is only "References"
or "Bibliography" (the compile skill's rule). Estimated pages per section are the distance from
its heading to the next heading, or to the references, or to the end of the PDF. Positions are column-aware (R162): on a two-column page the left column
counts as the first half of the page and the right column as the second.

Budget: --budget, else venue.page_budget. When venue.page_budget_includes_refs is false, the pages
counted are those up to and including the page where the references start (as /ploma:compile
counts them); when that page cannot be found the budget is SKIP and marked unverified, never FAIL.

Exit codes: 0 within budget or no budget, 1 over budget, 2 usage error, unreadable config or no PDF.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bib_check  # noqa: E402
import pdf_pages  # noqa: E402
import ploma_config  # noqa: E402
import sections  # noqa: E402

# Same heading rule as scripts/compile.py.
_REFS_LINE = re.compile(r"^\s*(?:\d+\.?\s+)?(?:references|bibliography)\s*$", re.I)


def _rel(path: Path, root: Path) -> str:
    try:
        return Path(path).resolve().relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _references(pages: list[str]) -> dict | None:
    last = None
    for pi, page in enumerate(pages):
        lines = page.split("\n")
        for li, line in enumerate(lines):
            if _REFS_LINE.match(line):
                col = len(line) - len(line.lstrip())
                last = {"page": pi + 1, "line": li + 1,
                        "position": round(pi + pdf_pages.page_fraction(lines, li, col), 3)}
    return last


def build(root: Path, *, pdf: Path | None = None, budget: int | None = None) -> dict:
    """The page map and budget verdict. Raises ValueError when the PDF or the main file is unreadable."""
    root = Path(root).resolve()
    cfg = ploma_config.load(root)
    paths = ploma_config.resolve(cfg, root)["_paths"]
    venue = cfg.get("venue") or {}
    main = Path(paths["main"]) if paths.get("main") else None
    if main is None or not main.is_file():
        raise ValueError(f"cannot read main file {main or '(document.main not set)'}")
    pdf = Path(pdf) if pdf else (Path(paths["pdf"]) if paths.get("pdf") else main.with_suffix(".pdf"))
    if not pdf.is_absolute():
        pdf = root / pdf
    n_pages, method = pdf_pages.page_count(pdf)
    if n_pages is None:
        raise ValueError(method)
    newest = max(p.stat().st_mtime for p in bib_check.tex_sources(main))
    stale = pdf.stat().st_mtime < newest

    outline = sections.outline(main)
    texts, how = pdf_pages.page_texts(pdf)
    hits: list[dict | None] = [None] * len(outline)
    refs = None
    if texts is not None:
        wanted = [[f"{s.number} {s.title}", s.title] if s.number else [s.title] for s in outline]
        hits = pdf_pages.heading_positions(texts, wanted)
        refs = _references(texts)

    rows = []
    for k, (s, hit) in enumerate(zip(outline, hits)):
        est = None
        if hit:
            nxt = next((h["position"] for h in hits[k + 1:] if h), None)
            if nxt is None:
                nxt = refs["position"] if refs and refs["position"] > hit["position"] else float(n_pages)
            est = round(max(0.0, nxt - hit["position"]), 1)
        rows.append({"number": s.number, "title": s.title, "file": _rel(s.file, root), "line": s.start,
                     "label": s.label, "start_page": hit["page"] if hit else None,
                     "position": hit["position"] if hit else None, "est_pages": est,
                     "match": None if not hit else ("numbered" if s.number and hit["needle"] != s.title else "title"),
                     "figures": s.figures, "tables": s.tables, "words": s.words})

    limit = budget if budget is not None else venue.get("page_budget")
    limit = limit if isinstance(limit, int) else None
    includes_refs = bool(venue.get("page_budget_includes_refs", False))
    if limit is None or includes_refs:
        report = pdf_pages.budget_report(n_pages, limit)
        report.update(counted=n_pages, unverified=False,
                      note="every page counts" if limit is not None else "no page budget set")
    elif refs is None:
        report = {"pages": n_pages, "budget": limit, "over_by": None, "status": "SKIP", "counted": None,
                  "unverified": True,
                  "note": "the budget excludes references and their start could not be located: "
                          + ("no References or Bibliography heading in the PDF text" if texts is not None else how)}
    else:
        report = pdf_pages.budget_report(refs["page"], limit)
        report.update(counted=refs["page"], unverified=False,
                      note=f"references start on page {refs['page']}; pages 1 to {refs['page']} counted")
    report["includes_refs"] = includes_refs
    return {"pdf": _rel(pdf, root), "pages": n_pages, "method": method, "stale": stale,
            "sections_method": how, "references": refs, "sections": rows, "budget": report,
            "figures_total": sum(s.figures for s in outline), "tables_total": sum(s.tables for s in outline),
            "words_total": sum(s.words for s in outline)}


def render(rep: dict) -> str:
    out = [f"pages: {rep['pages']} (via {rep['method']}){' STALE: the PDF is older than the sources' if rep['stale'] else ''}",
           "", "| # | Section | Starts p. | Est. pages | Figures | Tables | Words |", "|---|---|---|---|---|---|---|"]
    for s in rep["sections"]:
        start = s["start_page"] if s["start_page"] is not None else "not found"
        est = s["est_pages"] if s["est_pages"] is not None else "?"
        out.append(f"| {s['number'] or '-'} | {s['title']} | {start} | {est} | {s['figures']} | {s['tables']} "
                   f"| {s['words']} |")
    if rep["sections_method"] != "pdftotext":
        out.append(f"section pages unavailable: {rep['sections_method']}")
    if rep["references"]:
        out.append(f"references start on page {rep['references']['page']}")
    b = rep["budget"]
    if b["budget"] is None:
        out.append("budget: SKIP (no page budget set)")
    elif b.get("unverified"):
        out.append(f"budget: SKIP, unverified ({b['note']})")
    else:
        extra = f", over by {b['over_by']}" if b["over_by"] else ""
        out.append(f"budget: {b['status']} ({b['counted']}/{b['budget']}{extra}; {b['note']})")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Per-section page map and page budget check.")
    parser.add_argument("--root", default=".", help="repo root holding ploma.yaml (default: cwd)")
    parser.add_argument("--pdf", help="PDF to map (default: build.pdf)")
    parser.add_argument("--budget", type=int, default=None, help="page budget (default: venue.page_budget)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    try:
        rep = build(Path(args.root), pdf=Path(args.pdf) if args.pdf else None, budget=args.budget)
    except ploma_config.ConfigError as exc:
        msg = exc.message
    except (OSError, ValueError) as exc:
        msg = str(exc)
    else:
        print(json.dumps(rep, indent=2) if args.json else render(rep))
        return 1 if rep["budget"]["status"] == "FAIL" else 0
    print(json.dumps({"error": msg}) if args.json else f"page_map: {msg}",
          file=sys.stdout if args.json else sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
