"""Tests for scripts/placeholders.py: leftover TODOs, unresolved references and filler text."""
from __future__ import annotations

import json

import placeholders
from placeholders import run


def _write(tmp_path, text, name="a.tex"):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_placeholders_finds_todo_with_line(tmp_path):
    p = _write(tmp_path, "Line one.\nWe TODO fix this.\n")
    f = run([p])
    assert [x.id for x in f] == [f"placeholder.todo.{p.as_posix()}:2"]
    assert f[0].status == "FAIL"


def test_all_kinds(tmp_path):
    p = _write(tmp_path, "XXX here\nFIXME there\n\\todo{later}\nSee Table ??.\nhttp://example.com/x\n"
                         "\\today\nLorem  ipsum dolor\n\\TODO\n\\todo[inline]{x}\n")
    got = [(x.id.split(".")[1], x.status, x.id.rsplit(":", 1)[1]) for x in run([p])]
    assert got == [("xxx", "FAIL", "1"), ("fixme", "FAIL", "2"), ("todo_macro", "FAIL", "3"),
                   ("unresolved_ref", "FAIL", "4"), ("example_com", "FAIL", "5"), ("today", "WARN", "6"),
                   ("lorem_ipsum", "FAIL", "7"), ("todo_macro", "FAIL", "8"), ("todo_macro", "FAIL", "9")]


def test_question_marks_inside_math_ignored(tmp_path):
    p = _write(tmp_path, "We ask $a ?? b$ and \\[x ?? y\\].\n")
    assert run([p]) == []


def test_comments_ignored(tmp_path):
    p = _write(tmp_path, "Clean. % TODO later, XXX, ??\n")
    assert run([p]) == []


def test_words_containing_markers_ignored(tmp_path):
    p = _write(tmp_path, "TODOS and XXXL and todolist and \\todostyle and \\todayish.\n")
    assert run([p]) == []


def test_bib_example_com(tmp_path):
    p = _write(tmp_path, "@misc{a, url = {https://example.com/%20x}}\n", name="refs.bib")
    assert [x.id.split(".")[1] for x in run([p])] == ["example_com"]


def test_placeholders_sample_clean(sample_paper):
    import bib_check
    files = bib_check.tex_sources(sample_paper / "main.tex") + [sample_paper / "refs.bib"]
    assert run(files) == []


def test_cli_root_json(sample_paper, capsys):
    intro = sample_paper / "sections" / "intro.tex"
    base = intro.read_text()
    intro.write_text(base + "TODO cite more.\n")
    line = base.count("\n") + 1
    assert placeholders.main(["--root", str(sample_paper), "--json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert [f["id"] for f in data["findings"]] == [f"placeholder.todo.sections/intro.tex:{line}"]
    assert data["verdict"] == "FAIL"


def test_cli_root_clean(sample_paper, capsys):
    assert placeholders.main(["--root", str(sample_paper)]) == 0


def test_cli_today_only_warns(tmp_path, capsys):
    p = _write(tmp_path, "\\date{\\today}\n")
    assert placeholders.main([str(p)]) == 0
    assert "WARN" in capsys.readouterr().out


def test_cli_usage(tmp_path, monkeypatch):
    assert placeholders.main([str(tmp_path / "missing.tex")]) == 2
    monkeypatch.chdir(tmp_path)
    assert placeholders.main([]) == 2
