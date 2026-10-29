"""Tests for bibliography structural checks."""
from __future__ import annotations

import json
from pathlib import Path

import bib_check
from _findings import FAIL, INFO, WARN
from bib_check import check, check_entries, cite_keys, parse_bib, resolve_bib_files, tex_sources

FIX = Path(__file__).resolve().parent / "fixtures"
BIB = {p.stem: p.read_text(encoding="utf-8") for p in (FIX / "bib").glob("*.bib")}


def test_parse_nested_braces():
    e = parse_bib(BIB["nested_braces"])[0]
    assert e.fields["title"] == "A {Nested} Title with {{Double}} Braces"


def test_parse_skips_comment_string_and_reads_quotes():
    entries = parse_bib(BIB["nested_braces"])
    assert [e.key for e in entries] == ["Nested2019", "Quoted2020"]
    nested, quoted = entries
    assert nested.type == "article"
    assert nested.fields["author"] == "M{\\\"u}ller, Hans and {The Ranking Group}"
    assert nested.fields["journal"] == "Journal of Data Studies"     # @string macro expanded
    assert quoted.fields["title"] == "A Title in {Quotes}"
    assert quoted.fields["year"] == "2020"


def test_parse_lowercases_field_names_and_handles_parens():
    e = parse_bib("@Article(K1, TITLE = {T}, Year = 1999)")[0]
    assert (e.key, e.type, e.fields) == ("K1", "article", {"title": "T", "year": "1999"})


def test_cite_keys_variants(tmp_path):
    t = tmp_path / "a.tex"; t.write_text(r"\cite{a} \citep[p.~3]{b,c} \textcite{d} % \cite{ignored}")
    assert set(cite_keys([t])) == {"a", "b", "c", "d"}


def test_cite_keys_locations_and_escaped_percent(tmp_path):
    t = tmp_path / "a.tex"
    t.write_text("x\n50\\% of \\parencite[see][12]{ a , b } and \\nocite{c}\n%\\cite{z}\n")
    keys = cite_keys([t])
    assert set(keys) == {"a", "b", "c"}
    assert keys["a"] == [(t, 2)]


def test_tex_sources_follows_inputs_and_skips_comments(tmp_path):
    (tmp_path / "sec").mkdir()
    (tmp_path / "main.tex").write_text("\\input{sec/a}\n% \\input{sec/gone}\n\\include{sec/b.tex}\n\\input{missing}\n")
    (tmp_path / "sec/a.tex").write_text("\\input{sec/c}\n")            # resolved from the main dir
    (tmp_path / "sec/b.tex").write_text("\\input{main}\n")             # cycle back to main
    (tmp_path / "sec/c.tex").write_text("leaf\n")
    (tmp_path / "sec/gone.tex").write_text("never\n")
    names = [p.relative_to(tmp_path).as_posix() for p in tex_sources(tmp_path / "main.tex")]
    assert names == ["main.tex", "sec/a.tex", "sec/c.tex", "sec/b.tex"]


def test_bib_files_declared_in_included_file(tmp_path):
    (tmp_path / "main.tex").write_text(r"\documentclass{article}\begin{document}\input{back}\end{document}")
    (tmp_path / "back.tex").write_text(r"\bibliography{refs,extra}")
    assert [p.name for p in resolve_bib_files(tmp_path / "main.tex", [])] == ["refs.bib", "extra.bib"]


def test_bib_files_fixture_and_biblatex(tmp_path):
    for name in ("included_bib", "included_bib_back", "biblatex_main"):
        (tmp_path / f"{name}.tex").write_text((FIX / "tex" / f"{name}.tex").read_text())
    assert [p.name for p in resolve_bib_files(tmp_path / "included_bib.tex", [])] == ["refs.bib", "extra.bib"]
    got = resolve_bib_files(tmp_path / "biblatex_main.tex", [tmp_path / "own.bib", Path("refs")])
    assert got == [tmp_path / "own.bib", tmp_path / "refs.bib"]          # declared first, deduplicated


def test_missing_and_near_miss(sample_paper):
    (sample_paper / "sections/intro.tex").write_text(r"\cite{Fernandeznavarro2016}")
    ids = {f.id: f for f in check(sample_paper / "main.tex", [sample_paper / "refs.bib"])}
    assert ids["bib.missing.Fernandeznavarro2016"].status == FAIL
    assert "bib.near_miss.Fernandeznavarro2016" in ids       # refs.bib holds FernandezNavarro2016
    assert ids["bib.near_miss.Fernandeznavarro2016"].status == WARN
    assert "FernandezNavarro2016" in ids["bib.near_miss.Fernandeznavarro2016"].remediation


def test_far_key_is_missing_without_near_miss(sample_paper):
    (sample_paper / "sections/intro.tex").write_text(r"\cite{Totally2099}")
    ids = {f.id for f in check(sample_paper / "main.tex", [])}
    assert "bib.missing.Totally2099" in ids
    assert not any(i.startswith("bib.near_miss.") for i in ids)


def test_clean_sample_has_no_fail_and_reports_unused(sample_paper):
    fs = check(sample_paper / "main.tex", [])
    assert not [f for f in fs if f.status == FAIL]
    unused = [f for f in fs if f.id.startswith("bib.unused.")]
    assert unused and all(f.status == INFO for f in unused)
    assert "bib.unused.Bradley1952" not in {f.id for f in fs}


def test_nocite_star_suppresses_unused(sample_paper):
    (sample_paper / "sections/results.tex").write_text(r"\nocite{*}")
    assert not any(f.id.startswith(("bib.unused.", "bib.missing.")) for f in check(sample_paper / "main.tex", []))


def test_declared_missing_bib_file_fails(sample_paper):
    ids = {f.id: f for f in check(sample_paper / "main.tex", [sample_paper / "nope.bib"])}
    assert ids["bib.file_missing.nope.bib"].status == FAIL


def test_cite_style_mix(sample_paper):
    (sample_paper / "sections/results.tex").write_text(r"\citep{Bradley1952}")
    ids = {f.id: f for f in check(sample_paper / "main.tex", [])}
    assert ids["bib.cite_style_mix"].status == WARN


def test_no_style_mix_on_plain_cite(sample_paper):
    assert "bib.cite_style_mix" not in {f.id for f in check(sample_paper / "main.tex", [])}


def test_duplicates():
    fs = {f.id for f in check_entries(parse_bib(BIB["duplicates"]))}
    assert any(i.startswith("bib.duplicate_doi.") for i in fs)
    assert any(i.startswith("bib.duplicate_title.") for i in fs)
    assert "bib.duplicate_doi.Hunter2004+Hunter2004b" in fs
    assert "bib.duplicate_title.Lee2021+Lee2021arxiv" in fs


def test_doi_prefixes_normalised():
    text = "@misc{A, doi = {10.1/X}}\n@misc{B, doi = {https://doi.org/10.1/x}}\n@misc{C, doi = {doi:10.1/X}}"
    fs = {f.id for f in check_entries(parse_bib(text))}
    assert {"bib.duplicate_doi.A+B", "bib.duplicate_doi.A+C"} <= fs


def test_shared_booktitle_is_not_a_duplicate():
    assert not any(i.startswith("bib.duplicate_title.") for i in {f.id for f in check_entries(parse_bib(BIB["simple"]))})


def test_levenshtein():
    assert bib_check.levenshtein("kitten", "sitting") == 3
    assert bib_check.levenshtein("", "abc") == 3
    assert bib_check.levenshtein("abc", "abc") == 0


def test_cli_exit_codes(sample_paper, tmp_path, capsys):
    assert bib_check.main([str(sample_paper / "main.tex"), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert any(f["id"].startswith("bib.unused.") for f in data["findings"])
    (sample_paper / "sections/intro.tex").write_text(r"\cite{Nope}")
    assert bib_check.main([str(sample_paper / "main.tex")]) == 1
    assert "bib.missing.Nope" in capsys.readouterr().out
    assert bib_check.main([str(tmp_path / "absent.tex")]) == 2
