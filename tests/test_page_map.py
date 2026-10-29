"""Tests for scripts/page_map.py and pdf_pages.heading_positions (no poppler needed: tools are faked)."""
from __future__ import annotations

import json
import os
import shutil

import pdf_pages
import page_map

PAGES = [
    "A Method for Ranking Things\nAbstract\nWe present a method for ranking. The method works.\n"
    "1  Introduction\nRanking is common.\nMore text.\n",
    "Still the introduction.\n2   Method\nEach item has a score.\nMore.\nMore.\n",
    "3 Results\nTable 1.\nReferences\n[1] A. Author.\n",
    "[2] B. Author.\n",
]


def _fake_tools(monkeypatch, pages=PAGES, pdftotext=True):
    def which(name):
        return f"/usr/bin/{name}" if (name != "pdftotext" or pdftotext) else None

    def run(cmd):
        if cmd[0] == "pdfinfo":
            return f"Pages:          {len(pages)}\n"
        return "\f".join(pages)
    monkeypatch.setattr(pdf_pages, "_which", which)
    monkeypatch.setattr(pdf_pages, "_run", run)


def _pdf(sample_paper, newer=True):
    pdf = sample_paper / "main.pdf"
    shutil.copyfile(sample_paper / "figures" / "fig1.pdf", pdf)
    newest = max(p.stat().st_mtime for p in sample_paper.rglob("*.tex"))
    t = newest + (60 if newer else -60)
    os.utime(pdf, (t, t))
    return pdf


def test_heading_positions_are_ordered_and_skip_earlier_mentions():
    hits = pdf_pages.heading_positions(PAGES, [["1 Introduction"], ["2 Method"], ["9 Nowhere"], ["3 Results"]])
    assert [h and h["page"] for h in hits] == [1, 2, None, 3]
    assert hits[0]["line"] == 4 and 0 < hits[0]["position"] < 1
    assert 1 < hits[1]["position"] < 2


def test_heading_positions_fall_back_to_the_bare_title():
    pages = [PAGES[0], "II. METHOD\nText.\n", PAGES[2]]
    hits = pdf_pages.heading_positions(pages, [["1 Introduction", "Introduction"], ["2 Method", "Method"]])
    assert hits[1]["page"] == 2 and hits[1]["needle"] == "Method"  # not the "method" in the abstract


def test_page_map_of_the_sample(sample_paper, monkeypatch):
    _fake_tools(monkeypatch)
    _pdf(sample_paper)
    rep = page_map.build(sample_paper)
    assert rep["pages"] == 4 and rep["stale"] is False
    assert [(s["title"], s["start_page"]) for s in rep["sections"]] == [("Introduction", 1), ("Method", 2),
                                                                        ("Results", 3)]
    assert rep["references"]["page"] == 3
    assert rep["budget"]["counted"] == 3 and rep["budget"]["budget"] == 8 and rep["budget"]["status"] == "PASS"
    est = [s["est_pages"] for s in rep["sections"]]
    assert all(e > 0 for e in est)
    assert abs(sum(est) - (rep["references"]["position"] - rep["sections"][0]["position"])) <= 0.15  # each estimate is rounded to 0.1
    assert rep["sections"][1]["figures"] == 1 and rep["sections"][2]["tables"] == 1


def test_over_budget_exits_one(sample_paper, monkeypatch, capsys):
    _fake_tools(monkeypatch)
    _pdf(sample_paper)
    assert page_map.main(["--root", str(sample_paper), "--budget", "2", "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert data["budget"]["status"] == "FAIL" and data["budget"]["over_by"] == 1


def test_budget_including_references_counts_every_page(sample_paper, monkeypatch):
    p = sample_paper / "ploma.yaml"
    p.write_text(p.read_text().replace("page_budget_includes_refs: false", "page_budget_includes_refs: true"))
    _fake_tools(monkeypatch)
    _pdf(sample_paper)
    rep = page_map.build(sample_paper, budget=3)
    assert rep["budget"]["counted"] == 4 and rep["budget"]["status"] == "FAIL"


def test_without_pdftotext_the_budget_is_unverified(sample_paper, monkeypatch):
    _fake_tools(monkeypatch, pdftotext=False)
    _pdf(sample_paper)
    rep = page_map.build(sample_paper)
    assert rep["sections_method"].startswith("pdftotext not found")
    assert all(s["start_page"] is None for s in rep["sections"])
    assert rep["budget"]["status"] == "SKIP" and rep["budget"]["unverified"] is True


def test_stale_pdf_is_flagged(sample_paper, monkeypatch):
    _fake_tools(monkeypatch)
    _pdf(sample_paper, newer=False)
    assert page_map.build(sample_paper)["stale"] is True


def test_missing_pdf_is_a_usage_error(sample_paper, capsys):
    assert page_map.main(["--root", str(sample_paper)]) == 2
    assert "main.pdf" in capsys.readouterr().err


def test_text_output_has_a_table(sample_paper, monkeypatch, capsys):
    _fake_tools(monkeypatch)
    _pdf(sample_paper)
    assert page_map.main(["--root", str(sample_paper)]) == 0
    out = capsys.readouterr().out
    assert "| 2 | Method | 2 |" in out and "budget: PASS (3/8;" in out
