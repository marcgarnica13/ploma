"""Tests for scripts/sections.py: section outline, resolution, and the write self-check on a copy."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sections


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------- outline

def test_outline_of_the_sample(sample_paper):
    out = sections.outline(sample_paper / "main.tex")
    assert [s.title for s in out] == ["Introduction", "Method", "Results"]
    assert [s.number for s in out] == ["1", "2", "3"]
    intro = out[0]
    assert intro.file == (sample_paper / "sections" / "intro.tex").resolve()
    assert (intro.start, intro.end) == (1, 7) and intro.label == "sec:intro" and intro.whole_file
    assert out[1].figures == 1 and out[1].tables == 0
    assert out[2].tables == 1 and out[2].figures == 0
    assert all(s.words > 0 for s in out)


def test_outline_inline_sections_end_before_the_next_input_or_boundary(tmp_path):
    main = _write(tmp_path / "main.tex", "\n".join([
        r"\documentclass{article}",
        r"\begin{document}",
        r"\section{First \emph{Part}}\label{sec:first}",
        "Text one.",
        "",
        r"\input{b}",
        r"\section*{Unnumbered}",
        "Text three.",
        r"\appendix",
        r"\section{Extra}",
        "More.",
        "",
        r"\bibliography{refs}",
        r"\end{document}",
    ]) + "\n")
    _write(tmp_path / "b.tex", "\\section{Second}\nText two.\n\n")
    out = sections.outline(main)
    assert [(s.title, s.number) for s in out] == [("First Part", "1"), ("Second", "2"), ("Unnumbered", None),
                                                    ("Extra", "A")]
    first, second, unnumbered, extra = out
    assert (first.start, first.end) == (3, 4)           # trailing blank trimmed, stops before \input
    assert (second.start, second.end) == (1, 2) and second.whole_file
    assert (unnumbered.start, unnumbered.end) == (7, 8)  # stops before \appendix
    assert (extra.start, extra.end) == (10, 11)          # stops before \bibliography
    assert not first.whole_file and first.label == "sec:first"


def test_outline_ignores_commented_sections_and_the_preamble(tmp_path):
    main = _write(tmp_path / "main.tex", "\\documentclass{article}\n\\newcommand{\\x}{\\section{Fake}}\n"
                  "\\begin{document}\n% \\section{Commented}\n\\section{Real}\nText.\n\\end{document}\n")
    assert [s.title for s in sections.outline(main)] == ["Real"]


# ---------------------------------------------------------------- resolve

def test_resolve_by_title_label_and_path(sample_paper):
    main = sample_paper / "main.tex"
    by_title = sections.resolve(sample_paper, main, "introduction")
    by_label = sections.resolve(sample_paper, main, "sec:intro")
    by_path = sections.resolve(sample_paper, main, "sections/intro.tex")
    assert by_title == by_label == by_path
    assert sections.sibling_path(by_title) == (sample_paper / "sections" / "intro_suggestion.tex").resolve()


def test_resolve_inline_section_uses_a_title_slug(tmp_path):
    main = _write(tmp_path / "main.tex", "\\begin{document}\n\\section{Related Work: an Overview}\nA.\n"
                  "\\section{Two}\nB.\n\\end{document}\n")
    sec = sections.resolve(tmp_path, main, "related work: an overview")
    assert sections.sibling_path(sec) == (tmp_path / "related_work_an_overview_suggestion.tex").resolve()


def test_resolve_errors_list_candidates(sample_paper):
    with pytest.raises(LookupError) as err:
        sections.resolve(sample_paper, sample_paper / "main.tex", "Discussion")
    assert "Introduction" in str(err.value) and "sec:results" in str(err.value)


def test_resolve_refuses_a_path_outside_document_root(sample_paper, tmp_path):
    outside = _write(tmp_path / "elsewhere.tex", "\\section{X}\n")
    with pytest.raises(LookupError):
        sections.resolve(sample_paper, sample_paper / "main.tex", str(outside))


def test_resolve_fragment_file_is_the_whole_file(sample_paper):
    frag = _write(sample_paper / "sections" / "frag.tex", "Only a paragraph.\nSecond line.\n")
    p = sample_paper / "main.tex"
    p.write_text(p.read_text().replace("\\input{sections/results}", "\\input{sections/results}\n\\input{sections/frag}"))
    sec = sections.resolve(sample_paper, p, "sections/frag.tex")
    assert sec.file == frag.resolve() and (sec.start, sec.end) == (1, 2) and sec.whole_file


def test_cli_resolve_json(sample_paper, capsys):
    rc = sections.main(["--root", str(sample_paper), "--json", "resolve", "Introduction"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert data["file"] == "sections/intro.tex" and data["start"] == 1 and data["end"] == 7
    assert data["sibling"] == "sections/intro_suggestion.tex" and data["sibling_exists"] is False
    assert len(data["sha"]) == 12 and data["date"]
    assert data["spec"] == "quality_reports/paper_spec.md" and data["spec_exists"] is False


def test_cli_resolve_unknown_is_a_usage_error(sample_paper, capsys):
    assert sections.main(["--root", str(sample_paper), "resolve", "Nope"]) == 2
    assert "Introduction" in capsys.readouterr().err


# ---------------------------------------------------------------- check

DRAFT_HEADER = "% ploma:write draft\n% Source: sections/intro.tex lines 1-7\n% Source sha: {sha}\n%\n"


def _draft(sample_paper, body: str, sha: str | None = None) -> Path:
    sec = sections.resolve(sample_paper, sample_paper / "main.tex", "Introduction")
    path = sections.sibling_path(sec)
    path.write_text(DRAFT_HEADER.format(sha=sha or sections.section_sha(sec)) + body, encoding="utf-8")
    return path


def _snapshot(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="replace")
            for p in root.rglob("*") if p.is_file() and p.suffix in (".tex", ".bib", ".yaml", ".json")}


def test_check_flags_new_unplaced_numbers_and_leaves_the_manuscript_alone(sample_paper):
    before = _snapshot(sample_paper)
    body = ("\\section{Introduction}\n\\label{sec:intro}\n\n"
            "Ranking items is common~\\cite{Bradley1952}.\n"
            "On 12 teams the method reaches an average fitness of 0.81.\n"
            "It runs 37 times faster.\n")
    draft = _draft(sample_paper, body)
    rep = sections.check(sample_paper, sample_paper / "main.tex", "Introduction", draft)
    assert [n["raw"] for n in rep["new_numbers_unplaced"]] == ["37"]
    assert rep["new_numbers_unplaced"][0]["location"] == "sections/intro_suggestion.tex:10"
    assert rep["stale"] is False
    new = [f["id"] for f in rep["consistency"]["findings"] if f["change"] == "new"]
    assert new == ["consistency.intro_number_not_in_body.37"]  # an intro number must appear in the body
    assert rep["consistency"]["current_verdict"] == "PASS"
    after = _snapshot(sample_paper)
    after.pop("sections/intro_suggestion.tex")
    assert after == before  # the manuscript files are untouched
    assert not any((sample_paper / ".ploma" / "tmp").glob("*")) if (sample_paper / ".ploma" / "tmp").exists() else True


def test_check_maps_consistency_findings_to_the_draft(sample_paper):
    body = ("\\section{Introduction}\n\\label{sec:intro}\n\n"
            "On 13 teams it reaches an average fitness of 0.81 (Section~\\ref{sec:results}).\n")
    draft = _draft(sample_paper, body)
    rep = sections.check(sample_paper, sample_paper / "main.tex", "Introduction", draft)
    new = [f for f in rep["consistency"]["findings"] if f["change"] == "new"]
    assert any("13" in f["id"] and "sections/intro_suggestion.tex:8" in f["observed"] for f in new), new
    assert rep["consistency"]["verdict"] == "FAIL"


def test_check_reports_stale_source_and_diff(sample_paper):
    draft = _draft(sample_paper, "\\section{Introduction}\n\\label{sec:intro}\n\nShort text.\n", sha="0" * 12)
    rep = sections.check(sample_paper, sample_paper / "main.tex", "Introduction", draft)
    assert rep["stale"] is True
    assert rep["diff"].startswith("--- sections/intro.tex (lines 1-7)\n+++ sections/intro_suggestion.tex\n")
    assert "+Short text." in rep["diff"] and "-Rating systems update a score after each outcome~\\cite{Elo1978}." in rep["diff"]


def test_check_flags_new_figures_without_provenance(sample_paper):
    body = ("\\section{Introduction}\n\\label{sec:intro}\n\nText.\n"
            "\\begin{figure}\n\\includegraphics{figures/new.pdf}\n\\end{figure}\n"
            "\\begin{figure}\n% ploma:source scripts/make.py --x 1\n\\includegraphics{figures/other.pdf}\n\\end{figure}\n")
    draft = _draft(sample_paper, body)
    rep = sections.check(sample_paper, sample_paper / "main.tex", "Introduction", draft)
    assert [f["target"] for f in rep["figures_without_source"]] == ["figures/new.pdf"]
    assert rep["figures_without_source"][0]["location"] == "sections/intro_suggestion.tex:10"


def test_check_skips_provenance_when_pipeline_disabled(sample_paper):
    p = sample_paper / "ploma.yaml"
    p.write_text(p.read_text().replace("enabled: true", "enabled: false"))
    body = "\\section{Introduction}\n\\begin{figure}\n\\includegraphics{figures/new.pdf}\n\\end{figure}\n"
    rep = sections.check(sample_paper, sample_paper / "main.tex", "Introduction", _draft(sample_paper, body))
    assert rep["figures_without_source"] == []


def test_draft_body_strips_the_header():
    header, body = sections.split_draft("% a\n% b\n%\n\n\\section{X}\nText.\n")
    assert header == 4 and body == ["\\section{X}", "Text."]


def test_cli_check_json_and_bad_draft(sample_paper, capsys):
    draft = _draft(sample_paper, "\\section{Introduction}\n\\label{sec:intro}\n\nShort.\n")
    rc = sections.main(["--root", str(sample_paper), "--json", "check", "Introduction", str(draft)])
    data = json.loads(capsys.readouterr().out)
    assert rc == 0 and "diff" in data and "consistency" in data
    assert sections.main(["--root", str(sample_paper), "check", "Introduction", "missing.tex"]) == 2
