"""Tests for scripts/style_check.py: em-dashes, slop phrases and long sentences in prose."""
from __future__ import annotations

import json

import style_check
from style_check import SLOP_PHRASES, run

EM = "\u2014"
EN = "\u2013"


def _ids(findings):
    return [f.id for f in findings]


def test_seed_phrases_present():
    for p in ("delve", "leverage", "it is worth noting", "in this paper we", "crucial", "robust framework",
              "paradigm", "in today's", "a testament to", "landscape"):
        assert p in SLOP_PHRASES


def test_em_dash_in_prose_is_flagged():
    text = f"First line.\nThe method works{EM}mostly.\nIt also works --- sometimes.\nA pause {EN} here."
    f = run(text, forbid_em_dash=True, extra_phrases=[])
    assert _ids(f) == ["style.em_dash.stdin:2:17", "style.em_dash.stdin:3:15", "style.em_dash.stdin:4:9"]
    assert all(x.status == "WARN" for x in f)


def test_em_dash_inside_macro_argument_is_ignored():
    text = (f"See \\cite{{a{EM}b}} and \\ref{{x---y}} and \\url{{http://a.b/{EM}}} and \\label{{l---m}}.\n"
            f"\\href{{http://x---y}}{{text}} and \\includegraphics{{f{EM}g.pdf}} and $a {EM} b$.\n"
            f"% a comment {EM} here\n\\begin{{equation}}x --- y\\end{{equation}} and \\(a---b\\).")
    assert run(text, forbid_em_dash=True, extra_phrases=[]) == []


def test_en_dash_ranges_and_compounds_allowed():
    assert run(f"Pages 3{EN}5 and the Smith{EN}Jones model, 10--20 items.", forbid_em_dash=True,
               extra_phrases=[]) == []


def test_em_dash_allowed_when_not_forbidden():
    assert run(f"It works{EM}mostly.", forbid_em_dash=False, extra_phrases=[]) == []


def test_slop_phrases_case_insensitive_with_line():
    text = "Intro.\nIn this paper we Delve into the topic.\nWe leverage data.\n"
    ids = _ids(run(text, forbid_em_dash=True, extra_phrases=[]))
    assert ids == ["style.slop.stdin:2:1", "style.slop.stdin:2:18", "style.slop.stdin:3:4"]


def test_slop_phrase_across_line_break_and_inflection():
    text = "It is worth\nnoting that we leveraged it."
    ids = _ids(run(text, forbid_em_dash=True, extra_phrases=[]))
    assert ids == ["style.slop.stdin:1:1", "style.slop.stdin:2:16"]


def test_slop_not_matched_inside_words_or_macro_args():
    text = "The pleverage \\cite{delve2020} and \\label{sec:landscape}."
    assert run(text, forbid_em_dash=True, extra_phrases=[]) == []


def test_extra_phrases():
    f = run("This is a game changer.", forbid_em_dash=True, extra_phrases=["game changer"])
    assert _ids(f) == ["style.slop.stdin:1:11"] and f[0].status == "WARN"


def test_long_sentence_is_info():
    words = " ".join(["word"] * 31)
    text = f"Short one.\n{words}.\nAnother short one."
    f = run(text, forbid_em_dash=True, extra_phrases=[])
    assert _ids(f) == ["style.long_sentence.stdin:2:1"] and f[0].status == "INFO"
    assert run(text, forbid_em_dash=True, extra_phrases=[], max_sentence_words=40) == []


def test_long_sentence_ignores_math_and_tables():
    text = ("We have $" + " + ".join(["x"] * 40) + "$ here.\n"
            "\\begin{tabular}{ll}\n" + " & ".join(["cell"] * 40) + "\n\\end{tabular}\n")
    assert run(text, forbid_em_dash=True, extra_phrases=[]) == []


def test_preamble_skipped():
    text = f"\\title{{A{EM}B}}\n\\begin{{document}}\nClean text.\n\\end{{document}}\n"
    assert run(text, forbid_em_dash=True, extra_phrases=[]) == []


def test_findings_carry_file_and_line():
    f = run(f"x\nIt works{EM}mostly.", forbid_em_dash=True, extra_phrases=[], file="sec/a.tex")
    assert f[0].observed.startswith("sec/a.tex:2")


def test_sample_paper_clean(sample_paper):
    import bib_check
    for src in bib_check.tex_sources(sample_paper / "main.tex"):
        assert run(src.read_text(), forbid_em_dash=True, extra_phrases=[]) == [], src


def test_cli_file_and_json(tmp_path, capsys):
    p = tmp_path / "a.tex"
    p.write_text(f"It works{EM}mostly. We delve.\n")
    assert style_check.main([str(p), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [f["id"] for f in data["findings"]] == [f"style.em_dash.{p}:1:9", f"style.slop.{p}:1:21"]


def test_cli_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("We leverage it.\n"))
    assert style_check.main([]) == 0
    assert "style.slop.stdin:1:4" in capsys.readouterr().out


def test_cli_root_uses_config(sample_paper, capsys):
    intro = sample_paper / "sections" / "intro.tex"
    base = intro.read_text()
    intro.write_text(base + f"This is a game changer{EM}really.\n")
    line = base.count("\n") + 1
    y = sample_paper / "ploma.yaml"
    y.write_text(y.read_text() + "style:\n  forbid_em_dash: false\n  forbid_phrases: [game changer]\n")
    assert style_check.main(["--root", str(sample_paper), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    ids = [f["id"] for f in data["findings"]]
    assert ids == [f"style.slop.sections/intro.tex:{line}:11"]
    assert data["findings"][0]["observed"].startswith(f"sections/intro.tex:{line}")


def test_cli_usage(tmp_path):
    assert style_check.main([str(tmp_path / "missing.tex")]) == 2
    assert style_check.main(["--root", str(tmp_path)]) == 2


def test_two_hits_on_one_line_have_distinct_ids():
    f = run(f"A{EM}b and c{EM}d.", forbid_em_dash=True, extra_phrases=[], file="sec/a.tex")
    assert _ids(f) == ["style.em_dash.sec/a.tex:1:2", "style.em_dash.sec/a.tex:1:10"]
    assert "delve" in run("We delve.", forbid_em_dash=True, extra_phrases=[])[0].summary
