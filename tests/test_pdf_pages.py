"""Tests for PDF page counting and the page budget report."""
from __future__ import annotations

import json
from pathlib import Path

import pdf_pages

FIX = Path(__file__).resolve().parent / "fixtures" / "pdf"


def test_scan_counts_pages_without_pdfinfo(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    assert pdf_pages.page_count(FIX / "three_pages.pdf") == (3, "scan")


def test_scan_counts_sample_figure(monkeypatch, repo_root):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    assert pdf_pages.page_count(repo_root / "examples/sample-paper/figures/fig1.pdf") == (1, "scan")


def test_scan_handles_compact_type_page(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    p = tmp_path / "c.pdf"
    p.write_bytes(b"%PDF-1.4\n1 0 obj<</Type/Pages/Count 2>>endobj 2 0 obj<</Type/Page>>endobj"
                  b" 3 0 obj<</Type /Page /Parent 1 0 R>>endobj\n%%EOF\n")
    assert pdf_pages.page_count(p) == (2, "scan")


def test_pdfinfo_preferred_when_present(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: "/usr/bin/pdfinfo")
    monkeypatch.setattr(pdf_pages, "_run", lambda cmd: "Pages:          14\n")
    assert pdf_pages.page_count(FIX / "three_pages.pdf") == (14, "pdfinfo")


def test_missing_pdf_reports_error(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    n, why = pdf_pages.page_count(tmp_path / "nope.pdf")
    assert n is None and "nope.pdf" in why


def test_budget_report():
    assert pdf_pages.budget_report(14, 13)["status"] == "FAIL"
    assert pdf_pages.budget_report(13, 13)["status"] == "PASS"
    assert pdf_pages.budget_report(13, None)["status"] == "SKIP"
    assert pdf_pages.budget_report(14, 13) == {"pages": 14, "budget": 13, "over_by": 1, "status": "FAIL"}


def test_section_map_without_pdftotext(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    pages, reason = pdf_pages.section_page_map(FIX / "three_pages.pdf", ["Introduction"])
    assert pages is None and "pdftotext" in reason


def test_section_map_with_pdftotext(monkeypatch):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: "/usr/bin/pdftotext")
    monkeypatch.setattr(pdf_pages, "_run", lambda cmd: "Title\n1  Introduction\f2  Method\fMethod again\n3 Results\f")
    pages, how = pdf_pages.section_page_map(FIX / "three_pages.pdf", ["Introduction", "Method", "Results", "Missing"])
    assert pages == {"Introduction": 1, "Method": 2, "Results": 3} and how == "pdftotext"


def test_cli(monkeypatch, capsys):
    monkeypatch.setattr(pdf_pages, "_which", lambda name: None)
    assert pdf_pages.main([str(FIX / "three_pages.pdf"), "--budget", "3", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["budget"]["status"] == "PASS"
    assert pdf_pages.main([str(FIX / "three_pages.pdf"), "--budget", "2"]) == 1
    assert pdf_pages.main([str(FIX / "missing.pdf")]) == 2


def test_run_survives_non_utf8_output(tmp_path, monkeypatch):
    """pdftotext can emit Latin-1 bytes; _run must not raise UnicodeDecodeError under any locale."""
    import sys
    stub = tmp_path / "stub.py"
    stub.write_bytes(b"import sys\nsys.stdout.buffer.write(b'Page caf\\xe9 1\\n')\n")
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    monkeypatch.setenv("LC_ALL", "C.UTF-8")
    out = pdf_pages._run([sys.executable, str(stub)])
    assert out.startswith("Page caf") and "�" in out


def _two_column_page(rows: dict[int, tuple[str, str]], n: int = 40) -> str:
    """A pdftotext -layout page of n lines; rows maps a 1-based line to (left text, right text)."""
    out = []
    for i in range(1, n + 1):
        left, right = rows.get(i, ("Body text of the left column here.", "Body text of the right column."))
        out.append(f"{left:<48}{right}".rstrip())
    return "\n".join(out)


def test_right_column_heading_above_the_previous_hit_is_found():
    page1 = _two_column_page({3: ("1 Introduction", "Body text of the right column.")})
    page2 = _two_column_page({1: ("Body text of the left column here.", "4 Results"),
                              22: ("3 Method", "Body text of the right column.")})
    hits = pdf_pages.heading_positions([page1, page2], [["1 Introduction"], ["3 Method"], ["4 Results"]])
    assert [(h["page"], h["line"]) for h in hits] == [(1, 3), (2, 22), (2, 1)]
    assert hits[2]["column"] > hits[1]["column"]


def test_left_column_heading_above_the_previous_hit_is_not_taken():
    """Lines above the previous hit count only right of its column: a one-column page never goes back."""
    page = "\n".join(["2 Background", "text", "3 Method", "text", "more text"])
    hits = pdf_pages.heading_positions([page], [["3 Method"], ["2 Background"]])
    assert hits[0]["line"] == 3 and hits[1] is None


def test_both_columns_on_one_line_are_found_in_order():
    page = _two_column_page({5: ("2 Related Work", "3 Method")})
    hits = pdf_pages.heading_positions([page], [["2 Related Work"], ["3 Method"]])
    assert [(h["line"], h["column"]) for h in hits] == [(5, 0), (5, 48)]
