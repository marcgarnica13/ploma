"""Tests for scripts/consistency.py: the deterministic text vs tables vs results pass."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import consistency
import gate
from consistency import extract_numbers, run

FIX = Path(__file__).resolve().parent / "fixtures"
TEX = FIX / "tex"
TOL = {"counts": "exact", "metrics": 0.01, "percentages_pp": 0.1}


def _run(main, **kw):
    args = {"results_dir": None, "metric_keys": [], "tolerances": TOL, "passport": None}
    args.update(kw)
    return run(main, **args)


def _ids(rep):
    return {f.id for f in rep.findings}


# ---------------------------------------------------------------- extract_numbers

def test_years_and_cite_numbers_ignored():
    assert [n["value"] for n in extract_numbers(r"In 2023 we \cite{a} report 12 teams")] == [12]


def test_extract_kinds_and_raw():
    nums = extract_numbers("We keep 12,430 rows, 38\\% of them, at 0.81 fitness.\nAlso 12\\,430 and 7%.")
    got = [(n["raw"], n["value"], n["kind"], n["line"]) for n in nums]
    assert got == [("12,430", 12430, "count", 1), ("38%", 38, "percent", 1), ("0.81", 0.81, "decimal", 1),
                   ("12,430", 12430, "count", 2), ("7%", 7, "percent", 2)]


def test_extract_ignores_refs_labels_urls_graphics_and_indices():
    text = (r"See Table~\ref{tab:3} and \eqref{eq:4}\label{x5} at \url{http://a.b/6} "
            r"\includegraphics[width=0.6\linewidth]{fig7.pdf} with $x_1 + y^2 = 9$ and \citep[p.~8]{k10}.")
    assert [n["value"] for n in extract_numbers(text)] == [9]


def test_extract_ignores_section_numbers_and_dimensions():
    text = "\\section{3.2 Results on 40 items}\n\\vspace{2mm} we had 5 runs\\\\[3pt]"
    assert [n["value"] for n in extract_numbers(text)] == [40, 5]


def test_extract_skips_identifiers_and_ordinals():
    assert extract_numbers("F1 and GPT-4 on the 3rd try") == []


# ---------------------------------------------------------------- abstract vs body

def test_consistent_fixture_passes():
    rep = _run(TEX / "consistent.tex")
    assert rep.verdict == "PASS", [f.id for f in rep.findings]


def test_abstract_number_missing_from_body():
    rep = _run(TEX / "inconsistent.tex")
    assert "consistency.abstract_number_not_in_body.550" in _ids(rep)
    assert "consistency.abstract_number_not_in_body.0.81" not in _ids(rep)
    assert rep.verdict == "FAIL"
    f = next(f for f in rep.findings if f.id.endswith(".550"))
    assert "inconsistent.tex:4" in f.observed


def test_number_in_caption_counts():
    rep = _run(TEX / "caption_number.tex")
    assert rep.verdict == "PASS", [f.id for f in rep.findings]


def test_rounding_and_tolerance(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{abstract}A 0.81 score and 41.3\\% share.\\end{abstract}\n"
                    "We got 0.8134 and 41.31\\%.\n\\end{document}\n")
    assert _run(main).verdict == "PASS"
    main.write_text("\\begin{document}\n\\begin{abstract}A 41.3\\% share.\\end{abstract}\n"
                    "We got 41.25\\%.\n\\end{document}\n")
    assert _run(main).verdict == "PASS", _ids(_run(main))


@pytest.mark.parametrize("abstract,body", [
    ("41.3\\%", "41.25\\%"), ("0.82", "0.815"), ("0.13", "0.125"), ("0.9", "0.85"), ("0.815", "0.82"),
])
def test_display_rounding_is_half_up(tmp_path, abstract, body):
    rep = _run(_doc(tmp_path, f"We reach {abstract}.", f"We reach {body}."))
    assert rep.verdict == "PASS", _ids(rep)


def test_display_rounding_still_fails_on_digit_typo(tmp_path):
    rep = _run(_doc(tmp_path, "We reach 0.85.", "We reach 0.84."))
    assert "consistency.abstract_number_not_in_body.0.85" in _ids(rep)


@pytest.mark.parametrize("raw,value", [("0.82", 0.815), ("0.13", 0.125), ("41.3%", 0.4125), ("2", 2.0)])
def test_results_rounding_is_half_up(raw, value):
    from consistency import _number, NUM_RE
    num = _number(NUM_RE.search(raw.replace("%", "\\%")))
    assert consistency.matches(num, value, {"counts": "exact", "metrics": 0.0, "percentages_pp": 0.0})


def _doc(tmp_path, abstract, body, name="m.tex"):
    main = tmp_path / name
    main.write_text("\\begin{document}\n\\begin{abstract}" + abstract + "\\end{abstract}\n" + body
                    + "\n\\end{document}\n")
    return main


@pytest.mark.parametrize("abstract,body,raw", [
    ("We reach 0.85.", "We reach 0.84.", "0.85"),
    ("A share of 45.2\\%.", "A share of 45.3\\%.", "45.2%"),
])
def test_manuscript_comparisons_use_display_rounding_only(tmp_path, abstract, body, raw):
    rep = _run(_doc(tmp_path, abstract, body))
    assert f"consistency.abstract_number_not_in_body.{raw}" in _ids(rep)


def test_results_comparisons_use_tolerance(tmp_path):
    main = _doc(tmp_path, "We reach 0.81.", "Body text.")
    res = tmp_path / "res"
    res.mkdir()
    (res / "m.json").write_text(json.dumps({"f": 0.8134, "g": 0.38}))
    assert _ids(_run(main, results_dir=res)) == {"consistency.abstract_number_only_in_results.0.81"}


def test_kinds_must_match_in_manuscript(tmp_path):
    rep = _run(_doc(tmp_path, "We gain 12\\%.", "On 12 teams."))
    assert "consistency.abstract_number_not_in_body.12%" in _ids(rep)


def test_percent_matches_results_fraction(tmp_path):
    main = _doc(tmp_path, "We keep 38\\%.", "Body text.")
    res = tmp_path / "res"
    res.mkdir()
    (res / "m.json").write_text(json.dumps({"share": 0.38}))
    assert _ids(_run(main, results_dir=res)) == {"consistency.abstract_number_only_in_results.38%"}


def test_en_dash_range_has_no_sign():
    assert [(n["raw"], n["kind"]) for n in extract_numbers("between 10--20\\% and 3-4 runs, x -5")] == [
        ("10", "count"), ("20%", "percent"), ("3", "count"), ("4", "count"), ("-5", "count")]


def test_siunitx_numbers():
    nums = extract_numbers("\\num{0.81} and \\num{1.2e3} and \\qty{38}{\\percent} and \\SI{4.5}{\\percent} "
                           "and \\SI{12}{\\metre} and \\qty[mode=text]{0.5}{\\second}")
    assert [(n["value"], n["kind"]) for n in nums] == [(0.81, "decimal"), (1200.0, "decimal"), (38, "percent"),
                                                        (4.5, "percent"), (12, "count"), (0.5, "decimal")]


def test_siunitx_and_pm_table_cells(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{tabular}{lrr}\nA & \\num{0.81} & 0.76 $\\pm$ 0.02 \\\\\n"
                    "\\end{tabular}\n\\end{document}\n")
    rep = _run(main)
    assert [(c["raw"], c["value"]) for c in rep.table_cells] == [("0.81", 0.81), ("0.76", 0.76)]


def test_first_column_integer_cells_skipped(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{tabular}{rr}\n1 & 0.5 \\\\\n2 & 0.25 \\\\\n"
                    "0.3 & 7 \\\\\n\\end{tabular}\n\\end{document}\n")
    rep = _run(main)
    assert sorted(c["raw"] for c in rep.table_cells) == ["0.25", "0.3", "0.5", "7"]


def test_wrapped_table_is_kept(tmp_path):
    main = _doc(tmp_path, "We reach 0.85.",
                "\\resizebox{\\linewidth}{!}{\\begin{tabular}{lr}\nOurs & 0.85 \\\\\n\\end{tabular}}")
    rep = _run(main)
    assert rep.verdict == "PASS" and len(rep.table_cells) == 1


def test_box_size_arguments_are_masked():
    text = "\\scalebox{0.8}{a 5} \\raisebox{2ex}[1ex][1ex]{b 6} \\makebox[3cm][l]{c 7} \\parbox[t]{0.4\\linewidth}{d 8}"
    assert [n["value"] for n in extract_numbers(text)] == [5, 6, 7, 8]


def test_intro_number_not_in_body(tmp_path):
    (tmp_path / "intro.tex").write_text("\\section{Introduction}\nWe study 550 matches and 0.81 fitness.\n")
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{abstract}Abstract.\\end{abstract}\n\\input{intro}\n"
                    "\\section{Data}\nWe study 340 matches.\n\\begin{table}\\caption{Fitness 0.81.}\\end{table}\n"
                    "\\end{document}\n")
    rep = _run(main)
    assert _ids(rep) == {"consistency.intro_number_not_in_body.550"}
    f = rep.findings[0]
    assert f.status == "FAIL" and "intro.tex:2" in f.observed


def test_intro_number_only_in_results(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\section{Introduction}\nWe study 99 items.\n\\section{Data}\nNone.\n"
                    "\\end{document}\n")
    res = tmp_path / "res"
    res.mkdir()
    (res / "m.json").write_text(json.dumps({"n": 99}))
    rep = _run(main, results_dir=res)
    assert _ids(rep) == {"consistency.intro_number_only_in_results.99"}
    assert rep.verdict == "WARN"


def test_numbers_defined_by_newcommand_are_masked():
    text = "\\newcommand\\nteams{88} and \\renewcommand{\\x}[1]{77} ok 5"
    assert [n["value"] for n in extract_numbers(text)] == [5]


def test_counts_are_exact(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{abstract}We use 120 items.\\end{abstract}\n"
                    "We use 121 items.\n\\end{document}\n")
    assert "consistency.abstract_number_not_in_body.120" in _ids(_run(main))


def test_follows_input_and_ignores_comments_and_preamble(tmp_path):
    (tmp_path / "sec").mkdir()
    (tmp_path / "sec" / "a.tex").write_text("Here 77 items appear. % and 88 in a comment\n")
    main = tmp_path / "m.tex"
    main.write_text("\\usepackage{x}\\setlength{\\parindent}{88pt}\n\\newcommand{\\n}{88}\n\\begin{document}\n"
                    "\\begin{abstract}We have 77 and 88 items.\\end{abstract}\n\\input{sec/a}\n\\end{document}\n")
    rep = _run(main)
    assert _ids(rep) == {"consistency.abstract_number_not_in_body.88"}


def test_abstract_number_only_in_results_warns(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{abstract}We use 99 items.\\end{abstract}\nBody.\n\\end{document}\n")
    res = tmp_path / "res"
    res.mkdir()
    (res / "m.json").write_text(json.dumps({"n": 99}))
    rep = _run(main, results_dir=res)
    assert "consistency.abstract_number_only_in_results.99" in _ids(rep)
    assert rep.verdict == "WARN"


# ---------------------------------------------------------------- tables vs results

def test_sample_paper_is_clean(sample_paper):
    rep = _run(sample_paper / "main.tex", results_dir=sample_paper / "results",
               metric_keys=["avg_fitness", "n_teams"])
    assert rep.verdict == "PASS", [(f.id, f.observed) for f in rep.findings]
    assert sorted(c["raw"] for c in rep.table_cells) == ["0.72", "0.76", "0.81", "12", "12", "12"]


def test_table_cell_vs_results(sample_paper):
    res = sample_paper / "sections" / "results.tex"
    res.write_text(res.read_text().replace("Ours & 12 & 0.81", "Ours & 12 & 0.85"))
    rep = _run(sample_paper / "main.tex", results_dir=sample_paper / "results", metric_keys=["avg_fitness"])
    f = next(f for f in rep.findings if f.id == "consistency.table_cell_not_in_results.0.85")
    assert f.status == "WARN" and "results.tex:" in f.observed
    assert rep.verdict == "WARN"


def test_table_cells_unchecked_without_results(sample_paper):
    res = sample_paper / "sections" / "results.tex"
    res.write_text(res.read_text().replace("Ours & 12 & 0.81", "Ours & 12 & 0.85"))
    rep = _run(sample_paper / "main.tex")
    assert not any(f.id.startswith("consistency.table_cell") for f in rep.findings)


def test_table_cell_matches_nested_json_and_csv(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{tabular}{lrr}\nA & \\textbf{0.5} & 1{,}000 \\\\\n"
                    "B & $0.333$ & 45.2\\% \\\\\n\\end{tabular}\n\\end{document}\n")
    res = tmp_path / "res"
    (res / "deep").mkdir(parents=True)
    (res / "deep" / "x.json").write_text(json.dumps({"runs": [{"m": {"score": 0.4981}}]}))
    (res / "t.csv").write_text("name,share\nb,0.4523\nc,0.3329\n")
    rep = _run(main, results_dir=res)
    raws = {c["raw"] for c in rep.table_cells}
    assert {"0.5", "0.333", "45.2%"} <= raws
    assert _ids(rep) == {"consistency.table_cell_not_in_results.1,000"}


def test_metric_key_missing_warns(sample_paper):
    rep = _run(sample_paper / "main.tex", results_dir=sample_paper / "results", metric_keys=["avg_fitness", "nope"])
    assert "consistency.metric_key_missing.nope" in _ids(rep)


def test_unreadable_results_file_warns(tmp_path, sample_paper):
    (sample_paper / "results" / "bad.json").write_text("{not json")
    rep = _run(sample_paper / "main.tex", results_dir=sample_paper / "results")
    assert "consistency.results_unreadable.bad.json" in _ids(rep)


# ---------------------------------------------------------------- passport

def test_passport_fail_blocks(sample_paper):
    rep = _run(sample_paper / "main.tex", passport=FIX / "passport" / "sample.yaml")
    by_id = {f.id: f for f in rep.findings}
    assert by_id["consistency.passport.C2"].status == "FAIL"
    assert by_id["consistency.passport.C3"].status == "FAIL"
    assert by_id["consistency.passport.C4"].status == "INFO"
    assert "consistency.passport.C1" not in by_id
    assert rep.verdict == "FAIL"
    assert rep.passport["claims"] == 4


@pytest.mark.parametrize("body,needle", [
    ("claims: []\n", "paper"),
    ("paper: {slug: m}\nclaims:\n  - {id: C1, claim: x, status: MAYBE}\n", "status"),
    ("paper: {slug: m}\nclaims:\n  - {claim: x, status: PASS}\n", "id"),
    ("- a\n- b\n", "mapping"),
    ("paper: [unclosed\n", "parse"),
])
def test_passport_invalid(tmp_path, sample_paper, body, needle):
    p = tmp_path / "p.yaml"
    p.write_text(body)
    rep = _run(sample_paper / "main.tex", passport=p)
    f = next(f for f in rep.findings if f.id == "consistency.passport_invalid")
    assert f.status == "FAIL" and needle in (f.summary + " " + f.observed)


def test_passport_schema_file_is_valid_json(repo_root):
    schema = json.loads((repo_root / "schemas" / "passport.schema.json").read_text())
    assert set(schema["properties"]) == {"paper", "claims"}
    item = schema["properties"]["claims"]["items"]
    assert item["properties"]["status"]["enum"] == ["PASS", "FAIL", "STALE", "UNVERIFIED"]
    for key in ("id", "claim", "location", "source_file", "output_file", "output_field", "tolerance",
                "last_verified_on", "last_verified_by", "status", "notes"):
        assert key in item["properties"]


# ---------------------------------------------------------------- report and CLI

def test_to_dict_is_json(sample_paper):
    d = _run(sample_paper / "main.tex").to_dict()
    json.dumps(d)
    assert d["verdict"] == "PASS" and isinstance(d["findings"], list)


def test_cli_root_records_gate_and_report(sample_paper, cfg, capsys):
    rc = consistency.main(["--root", str(sample_paper), "--record"])
    out = capsys.readouterr().out
    assert rc == 0, out
    report = sample_paper / "quality_reports" / "consistency_main.md"
    text = report.read_text()
    for h in ("## Summary", "## Abstract vs body", "## Tables vs results", "## Passport", "## Next steps"):
        assert h in text
    entry = gate.load(sample_paper, cfg)["checks"]["consistency"]
    assert entry["status"] == "PASS" and entry["artifact"] == "quality_reports/consistency_main.md"


def test_cli_root_reads_default_passport(sample_paper, capsys):
    pdir = sample_paper / "quality_reports" / "passports"
    pdir.mkdir(parents=True)
    shutil.copy(FIX / "passport" / "sample.yaml", pdir / "main.yaml")
    rc = consistency.main(["--root", str(sample_paper), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1 and data["verdict"] == "FAIL"
    assert "consistency.passport.C2" in {f["id"] for f in data["findings"]}


def test_cli_fail_exit_and_record_status(sample_paper, cfg, capsys):
    main = sample_paper / "main.tex"
    main.write_text(main.read_text().replace("records from 12 teams", "records from 13 teams"))
    rc = consistency.main(["--root", str(sample_paper), "--record"])
    assert rc == 1
    assert gate.load(sample_paper, cfg)["checks"]["consistency"]["status"] == "FAIL"


def test_cli_main_file_with_options(capsys):
    rc = consistency.main([str(TEX / "inconsistent.tex"), "--json"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 1 and data["verdict"] == "FAIL"


def test_cli_metric_keys_and_results(sample_paper, capsys):
    rc = consistency.main([str(sample_paper / "main.tex"), "--results", str(sample_paper / "results"),
                           "--metric-keys", "avg_fitness,missing_key"])
    out = capsys.readouterr().out
    assert rc == 0 and "consistency.metric_key_missing.missing_key" in out


def test_cli_usage_errors(tmp_path, capsys):
    assert consistency.main([str(tmp_path / "nope.tex")]) == 2
    assert consistency.main(["--root", str(tmp_path)]) == 2
    assert consistency.main(["--bogus"]) == 2


def test_non_finite_results_values_are_ignored(tmp_path):
    main = tmp_path / "m.tex"
    main.write_text("\\begin{document}\n\\begin{tabular}{lr}\nA & 0.5 \\\\\n\\end{tabular}\n\\end{document}\n")
    res = tmp_path / "res"
    res.mkdir()
    (res / "m.json").write_text('{"a": NaN, "b": Infinity, "c": 0.5}')
    (res / "t.csv").write_text("x\nnan\ninf\n")
    assert _run(main, results_dir=res).verdict == "PASS"
