"""Tests for scripts/arxiv_rules.py (the venue submission check arxiv_rules)."""
from __future__ import annotations

import json

import arxiv_rules


def _ids(findings):
    return [f.id for f in findings]


def _main(sample_paper):
    return sample_paper / "main.tex"


def _edit(path, old, new):
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new, 1))


def test_sample_needs_pdfoutput_and_a_bbl(sample_paper):
    found = arxiv_rules.run(sample_paper)
    ids = _ids(found)
    assert "arxiv.pdfoutput" in ids and "arxiv.bbl_missing" in ids
    assert {f.status for f in found if f.id in ("arxiv.pdfoutput", "arxiv.bbl_missing")} == {"WARN"}
    assert not [i for i in ids if i.startswith("arxiv.figure")]
    assert "arxiv.today" not in ids


def test_pdfoutput_on_the_first_lines_passes(sample_paper):
    p = _main(sample_paper)
    p.write_text("\\pdfoutput=1\n" + p.read_text())
    assert "arxiv.pdfoutput" not in _ids(arxiv_rules.run(sample_paper))


def test_pdfoutput_too_late_warns(sample_paper):
    p = _main(sample_paper)
    _edit(p, "\\begin{document}", "\\pdfoutput=1\n\\begin{document}")
    f = [x for x in arxiv_rules.run(sample_paper) if x.id == "arxiv.pdfoutput"]
    assert f and "first 5 lines" in f[0].summary


def test_figure_formats(sample_paper):
    (sample_paper / "figures" / "plot.eps").write_text("%!PS")
    _edit(sample_paper / "sections" / "method.tex", "\\includegraphics[width=0.6\\linewidth]{figures/fig1.pdf}",
          "\\includegraphics{figures/fig1.pdf}\n\\includegraphics{figures/plot.eps}\n\\includegraphics{figures/gone}")
    found = {f.id: f.status for f in arxiv_rules.run(sample_paper)}
    assert found["arxiv.figure_format.figures/plot.eps"] == "FAIL"
    assert found["arxiv.figure_missing.figures/gone"] == "WARN"


def test_graphicspath_and_extensionless_targets(sample_paper):
    _edit(_main(sample_paper), "\\begin{document}", "\\graphicspath{{figures/}}\n\\begin{document}")
    _edit(sample_paper / "sections" / "method.tex", "{figures/fig1.pdf}", "{fig1}")
    assert not [i for i in _ids(arxiv_rules.run(sample_paper)) if i.startswith("arxiv.figure")]


def test_hidden_files_warn_but_git_is_ignored(sample_paper):
    (sample_paper / ".DS_Store").write_text("x")
    (sample_paper / ".git").mkdir()
    ids = _ids(arxiv_rules.run(sample_paper))
    assert "arxiv.hidden..DS_Store" in ids and not any(".git/" in i or i.endswith(".git") for i in ids)


def test_bbl_present_or_biber(sample_paper):
    (sample_paper / "main.bbl").write_text("\\begin{thebibliography}{1}\\end{thebibliography}")
    assert "arxiv.bbl_missing" not in _ids(arxiv_rules.run(sample_paper))
    (sample_paper / "main.bbl").unlink()
    _edit(sample_paper / "ploma.yaml", "bib_tool: bibtex", "bib_tool: biber")
    f = [x for x in arxiv_rules.run(sample_paper) if x.id == "arxiv.bbl_missing"]
    assert f and f[0].status == "FAIL"


def test_today_and_comments(sample_paper):
    _edit(_main(sample_paper), "\\date{}", "\\date{\\today}")
    found = {f.id: f for f in arxiv_rules.run(sample_paper)}
    assert found["arxiv.today"].status == "WARN"
    assert found["arxiv.comments"].status == "INFO" and "1 comment line" in found["arxiv.comments"].summary


def test_cli(sample_paper, capsys):
    assert arxiv_rules.main(["--root", str(sample_paper), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verdict"] == "WARN" and data["findings"]
    (sample_paper / "figures" / "plot.svg").write_text("<svg/>")
    _edit(sample_paper / "sections" / "method.tex", "{figures/fig1.pdf}", "{figures/plot.svg}")
    assert arxiv_rules.main(["--root", str(sample_paper)]) == 1
    assert arxiv_rules.main(["--root", str(sample_paper / "nope")]) == 2
