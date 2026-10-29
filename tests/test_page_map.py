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


def test_heading_match_ignores_prose_mentions():
    pages = ["1 Introduction\nOur method is new.\nII. METHOD\nText.\n"]
    hits = pdf_pages.heading_positions(pages, [["1 Introduction", "Introduction"], ["2 Method", "Method"]])
    assert hits[1]["line"] == 3
    pages = ["1 Introduction\nSee Section 2 Method for details.\n2 Method\nText.\n"]
    hits = pdf_pages.heading_positions(pages, [["1 Introduction"], ["2 Method", "Method"]])
    assert hits[1]["line"] == 3 and hits[1]["needle"] == "2 Method"


def test_heading_match_allows_numbers_and_trailing_space():
    pages = ["2.1 Setup   \nA.\nB. Method\n"]
    hits = pdf_pages.heading_positions(pages, [["Setup"], ["Method"]])
    assert [h and h["line"] for h in hits] == [1, 3]
    assert pdf_pages.heading_positions(["Methods and data\n"], [["Method"]]) == [None]


def test_heading_in_the_right_column_is_found():
    pages = ["1 Introduction\nWe study things in the left column.        2 Method\nMore left text.        Text.\n",
             "x\n", "y\n", "3 Results\n"]
    hits = pdf_pages.heading_positions(pages, [["1 Introduction"], ["2 Method", "Method"], ["3 Results"]])
    assert [(h["page"], h["needle"]) if h else None for h in hits] == [(1, "1 Introduction"), (1, "2 Method"),
                                                                      (4, "3 Results")]
    assert hits[1]["line"] == 2


def test_lower_case_words_are_not_a_numeral_prefix():
    assert pdf_pages.heading_positions(["mild method\n"], [["Method"]]) == [None]
    assert pdf_pages.heading_positions(["II. METHOD\n"], [["Method"]])[0]["line"] == 1


# ---------------------------------------------------------------- R162: column-aware positions

def _two_column_page(left: dict[int, str], right: dict[int, str], n: int = 40) -> str:
    """n lines of a two-column page; left/right map a 1-based line to its text, other lines are filler."""
    rows = []
    for i in range(1, n + 1):
        lt = left.get(i, "left column text goes on here")
        rt = right.get(i, "right column text goes on too")
        rows.append(f"{lt:<44}{rt}")
    return "\n".join(rows) + "\n"


TWO_COL = [
    _two_column_page({3: "1 Introduction"}, {}),
    _two_column_page({25: "2 Method"}, {10: "3 Results"}),
    _two_column_page({30: "References"}, {30: ""}),
    "[1] A. Author.\n",
]


def test_two_column_right_heading_above_left_one_keeps_positive_sizes(sample_paper, monkeypatch):
    _fake_tools(monkeypatch, pages=TWO_COL)
    _pdf(sample_paper)
    rep = page_map.build(sample_paper)
    rows = {s["title"]: s for s in rep["sections"]}
    assert rows["Method"]["start_page"] == 2 and rows["Results"]["start_page"] == 2
    assert rows["Method"]["est_pages"] > 0, rows["Method"]
    assert rows["Method"]["position"] < rows["Results"]["position"]
    assert 1.5 <= rows["Results"]["position"] < 2  # right column: page - 1 + 0.5 + line / (2 * lines)
    assert 1 <= rows["Method"]["position"] < 1.5   # left column: page - 1 + line / (2 * lines)
    assert 2 <= rep["references"]["position"] < 2.5  # left column of page 3, line 30 of 40


def test_one_column_positions_are_unchanged():
    hits = pdf_pages.heading_positions(PAGES, [["1 Introduction"], ["2 Method"], ["3 Results"]])
    lines = [len(p.split("\n")) for p in PAGES]
    assert hits[1]["position"] == round(1 + 1 / lines[1], 3)


def test_justified_one_column_page_is_not_two_columns():
    import random
    rng = random.Random(3)
    words = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "iota", "kappa", "lambda", "mu"]
    rows = []
    for i in range(30):  # every other line has one wide justification gap at a random word
        w = rng.sample(words, len(words))
        k = rng.randrange(3, 9)
        rows.append(" ".join(w[:k]) + "   " + " ".join(w[k:]) if i % 2 else " ".join(w))
    assert pdf_pages._gutter(rows) is None
    assert pdf_pages._gutter(TWO_COL[1].split("\n")) == 44
