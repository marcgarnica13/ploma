#!/usr/bin/env python3
"""Count PDF pages, map section headings to pages, and check a page budget.

Usage: python3 scripts/pdf_pages.py <pdf> [--budget N] [--headings h1,h2] [--json]
Exit codes: 0 within budget or no budget, 1 over budget, 2 usage error or page count unavailable.
Uses pdfinfo and pdftotext (poppler) when present; counts page objects in the raw file otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# "/Type /Page" or "/Type/Page" not followed by another name character (so "/Pages" is excluded).
_PAGE_OBJ = re.compile(rb"/Type\s*/Page(?![A-Za-z0-9_.#-])")
_PAGES_COUNT = re.compile(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)|/Count\s+(\d+)[^>]*?/Type\s*/Pages\b")
_PDFINFO_PAGES = re.compile(r"^Pages:\s+(\d+)\s*$", re.M)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout


def page_count(pdf: Path) -> tuple[int | None, str]:
    """Return (pages, method) where method is "pdfinfo" or "scan"; (None, reason) on failure."""
    pdf = Path(pdf)
    if not pdf.is_file():
        return None, f"PDF not found: {pdf}"
    if _which("pdfinfo"):
        try:
            m = _PDFINFO_PAGES.search(_run(["pdfinfo", str(pdf)]))
        except (OSError, subprocess.SubprocessError):
            m = None
        if m:
            return int(m.group(1)), "pdfinfo"
    try:
        data = pdf.read_bytes()
    except OSError as exc:
        return None, f"cannot read {pdf}: {exc.strerror or exc}"
    if not data.startswith(b"%PDF"):
        return None, f"not a PDF file: {pdf}"
    n = len(_PAGE_OBJ.findall(data))
    if n:
        return n, "scan"
    # Page objects may sit inside compressed object streams; the page tree root's /Count can
    # still be visible.
    counts = [int(a or b) for a, b in _PAGES_COUNT.findall(data)]
    if counts:
        return max(counts), "scan"
    return None, f"could not count pages in {pdf} (compressed objects; install pdfinfo)"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def section_page_map(pdf: Path, headings: list[str]) -> tuple[dict[str, int] | None, str]:
    """First 1-based page on which each heading appears, via pdftotext -layout.

    Headings not found are left out of the map. Returns (None, reason) without pdftotext.
    """
    if not _which("pdftotext"):
        return None, "pdftotext not found (install poppler-utils for the section page map)"
    try:
        text = _run(["pdftotext", "-layout", str(pdf), "-"])
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"pdftotext failed: {exc}"
    pages = [_norm(p) for p in text.split("\f")]
    found: dict[str, int] = {}
    for heading in headings:
        needle = _norm(heading)
        if not needle:
            continue
        for i, page in enumerate(pages, 1):
            if needle in page:
                found[heading] = i
                break
    return found, "pdftotext"


def budget_report(pages: int, budget: int | None) -> dict:
    """PASS when pages <= budget, FAIL when over, SKIP when there is no budget."""
    if budget is None:
        return {"pages": pages, "budget": None, "over_by": None, "status": "SKIP"}
    over_by = max(0, pages - budget)
    return {"pages": pages, "budget": budget, "over_by": over_by, "status": "FAIL" if over_by else "PASS"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Count PDF pages and check a page budget.")
    parser.add_argument("pdf", help="path to the PDF")
    parser.add_argument("--budget", type=int, default=None, help="maximum allowed pages")
    parser.add_argument("--headings", default="", help="comma-separated headings to locate")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    pages, method = page_count(Path(args.pdf))
    if pages is None:
        if args.json:
            print(json.dumps({"error": method}))
        else:
            print(f"pdf_pages: {method}", file=sys.stderr)
        return 2
    report = budget_report(pages, args.budget)
    headings = [h.strip() for h in args.headings.split(",") if h.strip()]
    sections, sections_how = (None, "") if not headings else section_page_map(Path(args.pdf), headings)
    if args.json:
        out = {"pages": pages, "method": method, "budget": report}
        if headings:
            out["sections"] = sections
            out["sections_method"] = sections_how
        print(json.dumps(out, indent=2))
    else:
        print(f"pages: {pages} (via {method})")
        if args.budget is None:
            print("budget: SKIP (no page budget set)")
        else:
            extra = f", over by {report['over_by']}" if report["over_by"] else ""
            print(f"budget: {report['status']} ({pages}/{args.budget}{extra})")
        if headings:
            if sections is None:
                print(f"sections: unavailable ({sections_how})")
            else:
                for h in headings:
                    print(f"- {h}: page {sections[h]}" if h in sections else f"- {h}: not found")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
