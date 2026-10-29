"""Tests for scripts/inventory.py: the read-only repository inventory behind /ploma:onboard."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import inventory
import ploma_config

FIX = Path(__file__).resolve().parent / "fixtures"
FIX_TEX = FIX / "tex"
FIX_HARNESS = FIX / "harness"


def _tree_hash(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file()}


def _gaps(inv: dict) -> dict[str, dict]:
    return {x["key"]: x for x in inventory.gaps(inv, inventory.propose_config(inv))}


def test_sample_paper_inventory(sample_paper):
    inv = inventory.inventory(sample_paper, home=sample_paper / "nohome")
    assert inv["main"] == "main.tex" and inv["doc_class"] == "article" and inv["bib_tool"] == "bibtex"
    assert inv["bib_files"] == ["refs.bib"] and inv["build"]["kind"] == "make" and inv["build"]["main_from_makefile"] == "main"
    assert inv["figures"][0]["has_provenance"] is True and inv["reviews_dir"] == "review" and inv["results_dir"] == "results"


def test_sample_paper_details(sample_paper):
    inv = inventory.inventory(sample_paper, home=sample_paper / "nohome")
    assert inv["main_candidates"] == ["main.tex"]
    assert inv["title"] == "A Method for Ranking Things"
    assert inv["engine_hint"] == "pdflatex" and inv["doc_class_options"] == ["11pt"]
    assert inv["build"] == {"kind": "make", "command": "make", "cwd": ".", "main_from_makefile": "main"}
    assert inv["figures"] == [{"path": "figures/fig1.pdf", "source": "sections/method.tex", "line": 12,
                               "has_provenance": True}]
    assert inv["code"] is None and inv["git_remote"] is None
    assert inv["superpowers"] == {"enabled": False, "id": None}
    assert inv["pdf"] == "main.pdf" and inv["pdf_pages"] is None
    assert inv["legacy_harness"] == []


def test_sample_paper_is_untouched(sample_paper):
    before = _tree_hash(sample_paper)
    inv = inventory.inventory(sample_paper, home=sample_paper / "nohome")
    inventory.gaps(inv, inventory.propose_config(inv))
    assert _tree_hash(sample_paper) == before


def test_proposal_validates_on_sample(sample_paper):
    inv = inventory.inventory(sample_paper, home=sample_paper / "nohome")
    prop = inventory.propose_config(inv)
    assert prop["ploma"] == "0.1"
    assert prop["document"] == {"type": "paper", "main": "main.tex", "root": ".", "title": "A Method for Ranking Things",
                                "slug": "main", "anonymized": True, "discipline": "generic"}
    assert prop["build"]["command"] == "make" and prop["build"]["bib_files"] == ["refs.bib"]
    assert prop["build"]["pdf"] == "main.pdf" and prop["build"]["log"] == "main.log"
    assert prop["venue"] == {"profile": "generic-journal", "doc_class": "article", "page_budget": None,
                             "page_budget_includes_refs": False, "cite_style": "numeric"}
    assert prop["reviews"] == {"glob": "review/*"} and prop["outputs"] == {"dir": "quality_reports"}
    assert "pipeline" not in prop  # no code tree in the sample
    fails = [f for f in ploma_config.validate(prop, sample_paper) if f.status == "FAIL"]
    assert fails == []


def test_llncs_fixture_maps_to_llncs_conference(tmp_path):
    shutil.copy(FIX_TEX / "llncs_main.tex", tmp_path / "paper.tex")
    inv = inventory.inventory(tmp_path); g = _gaps(inv)
    assert inv["doc_class"] == "llncs" and inv["anonymized"] is True
    assert g["venue.profile"]["recommended"] == "llncs-conference" and "springer-ml" in g["venue.profile"]["options"]
    assert g["venue.profile"]["options"][0] == "llncs-conference"
    assert {"generic-journal", "generic-conference"} <= set(g["venue.profile"]["options"])
    assert g["venue.page_budget"]["recommended"] == 12
    assert inv["title"] == "A Method for Ranking Things"


def test_two_main_candidates_become_a_gap(tmp_path):
    for n in ("two_mains_a", "two_mains_b"): shutil.copy(FIX_TEX / f"{n}.tex", tmp_path / f"{n}.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] is None and len(inv["main_candidates"]) == 2
    g = _gaps(inv)
    assert "document.main" in g and set(g["document.main"]["options"]) == {"two_mains_a.tex", "two_mains_b.tex"}
    assert "main" not in inventory.propose_config(inv).get("document", {})


def test_makefile_main_breaks_a_tie(tmp_path):
    for n in ("two_mains_a", "two_mains_b"): shutil.copy(FIX_TEX / f"{n}.tex", tmp_path / f"{n}.tex")
    (tmp_path / "Makefile").write_text("MAIN := two_mains_b\n\nall:\n\tpdflatex $(MAIN)\n")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] == "two_mains_b.tex" and inv["build"]["main_from_makefile"] == "two_mains_b"
    assert inv["title"] == "Draft B"


def test_latexmkrc_build(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    (tmp_path / ".latexmkrc").write_text("@default_files = ('paper.tex');\n$pdf_mode = 1;\n")
    inv = inventory.inventory(tmp_path)
    assert inv["build"]["kind"] == "latexmk" and inv["build"]["command"] == "latexmk"


def test_no_build_file(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["build"]["kind"] is None and inv["build"]["command"] is None
    assert "command" not in inventory.propose_config(inv)["build"]


def test_backup_and_build_dirs_are_skipped(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    for d in ("old_backup", "build", "quality_reports", "node_modules"):
        (tmp_path / d).mkdir()
        shutil.copy(FIX_TEX / "two_mains_b.tex", tmp_path / d / "copy.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main_candidates"] == ["paper.tex"] and inv["main"] == "paper.tex"


def test_biblatex_means_biber(tmp_path):
    shutil.copy(FIX_TEX / "biblatex_main.tex", tmp_path / "main.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["bib_tool"] == "biber" and inv["bib_files"] == ["refs.bib"]
    assert inventory.propose_config(inv)["venue"]["cite_style"] == "numeric"


def test_bib_via_included_file(tmp_path):
    shutil.copy(FIX_TEX / "included_bib.tex", tmp_path / "main.tex")
    shutil.copy(FIX_TEX / "included_bib_back.tex", tmp_path / "included_bib_back.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main_candidates"] == ["main.tex"] and inv["bib_files"] == ["refs.bib", "extra.bib"]


def test_engine_and_author_year(tmp_path):
    (tmp_path / "paper.tex").write_text(
        "\\documentclass[review]{elsarticle}\n\\usepackage{fontspec}\n\\usepackage[authoryear]{natbib}\n"
        "\\title[Short]{A \\emph{Long} Title\\thanks{Funded.}}\n\\author{X}\n"
        "\\begin{document}\n\\citet{a} shows it.\n\\end{document}\n")
    inv = inventory.inventory(tmp_path)
    assert inv["engine_hint"] == "xelatex" and inv["anonymized"] is False and inv["title"] == "A Long Title"
    prop = inventory.propose_config(inv)
    assert prop["venue"]["cite_style"] == "author-year" and prop["venue"]["profile"] == "elsevier"


def test_author_present_is_not_anonymized(tmp_path):
    (tmp_path / "paper.tex").write_text(
        "\\documentclass{article}\n\\title{T}\n\\author{Jane Doe}\n\\begin{document}\n\\end{document}\n")
    assert inventory.inventory(tmp_path)["anonymized"] is False


def _paper(tmp_path, preamble: str, cls: str = "{article}", name: str = "paper.tex") -> None:
    (tmp_path / name).write_text(f"\\documentclass{cls}\n{preamble}\n\\begin{{document}}\nText.\n\\end{{document}}\n")


def test_commented_old_author_with_live_author_is_not_anonymized(tmp_path):
    _paper(tmp_path, "% \\author{Old Name}\n\\author{Jane Doe}")
    assert inventory.inventory(tmp_path)["anonymized"] is False


def test_acmart_review_option_is_not_anonymized(tmp_path):
    _paper(tmp_path, "\\author{Jane}", cls="[review]{acmart}")
    assert inventory.inventory(tmp_path)["anonymized"] is False


def test_acmart_anonymous_option_is_anonymized(tmp_path):
    _paper(tmp_path, "\\author{Jane}", cls="[review,anonymous]{acmart}")
    assert inventory.inventory(tmp_path)["anonymized"] is True


def test_placeholder_author_is_anonymized(tmp_path):
    _paper(tmp_path, "\\author{Anonymous Author(s)}")
    assert inventory.inventory(tmp_path)["anonymized"] is True


def test_only_commented_author_is_anonymized(tmp_path):
    _paper(tmp_path, "% \\author{Jane Doe}")
    assert inventory.inventory(tmp_path)["anonymized"] is True


def test_anonymous_command_is_anonymized(tmp_path):
    _paper(tmp_path, "\\author{Jane Doe}\n\\anonymous")
    assert inventory.inventory(tmp_path)["anonymized"] is True


def test_standalone_figure_is_not_a_main(tmp_path):
    _paper(tmp_path, "\\author{J}", name="main.tex")
    (tmp_path / "figs").mkdir()
    _paper(tmp_path / "figs", "\\usepackage{tikz}", cls="[tikz]{standalone}", name="diagram.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main_candidates"] == ["main.tex"] and inv["main"] == "main.tex"


def test_subfiles_chapters_are_not_mains(tmp_path):
    _paper(tmp_path, "\\usepackage{subfiles}", name="main.tex")
    for n in ("ch1.tex", "ch2.tex"):
        _paper(tmp_path, "", cls="[main.tex]{subfiles}", name=n)
    assert inventory.inventory(tmp_path)["main"] == "main.tex"


def test_makefile_main_with_comment_picks_main(tmp_path):
    _paper(tmp_path, "\\author{J}", name="main.tex")
    _paper(tmp_path, "\\author{J}", cls="{letter}", name="response_letter.tex")
    (tmp_path / "Makefile").write_text("MAIN = main # the paper\n\nall:\n\tpdflatex $(MAIN)\n")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] == "main.tex" and inv["build"]["main_from_makefile"] == "main"


def test_makefile_main_variants(tmp_path):
    for line in ("MAIN ?= main", "MAIN := main", "MAIN=main.tex", "MAIN = main.tex # x"):
        _paper(tmp_path, "", name="main.tex")
        _paper(tmp_path, "", name="other.tex")
        (tmp_path / "Makefile").write_text(line + "\n")
        inv = inventory.inventory(tmp_path)
        assert inv["main"] == "main.tex" and inv["build"]["main_from_makefile"] == "main", line


def test_explicit_main_recomputes_facts(tmp_path):
    for n in ("two_mains_a", "two_mains_b"): shutil.copy(FIX_TEX / f"{n}.tex", tmp_path / f"{n}.tex")
    (tmp_path / "two_mains_a.tex").write_text((tmp_path / "two_mains_a.tex").read_text().replace(
        "\\end{document}", "\\bibliographystyle{plain}\n\\bibliography{refs}\n\\end{document}"))
    (tmp_path / "refs.bib").write_text("@article{k, title={T}, author={A}, year={2020}}\n")
    inv = inventory.inventory(tmp_path, main="two_mains_a.tex")
    assert inv["main"] == "two_mains_a.tex" and len(inv["main_candidates"]) == 2
    assert inv["doc_class"] == "article" and inv["bib_files"] == ["refs.bib"] and inv["bib_tool"] == "bibtex"
    assert inv["title"] == "Draft A" and inv["pdf"] == "two_mains_a.pdf"
    prop = inventory.propose_config(inv)
    assert "document.main" not in {g["key"] for g in inventory.gaps(inv, prop)}
    assert [f for f in ploma_config.validate(prop, tmp_path) if f.status == "FAIL"] == []


def test_cli_main_flag(tmp_path, capsys):
    for n in ("two_mains_a", "two_mains_b"): shutil.copy(FIX_TEX / f"{n}.tex", tmp_path / f"{n}.tex")
    assert inventory.main(["--root", str(tmp_path), "--main", "two_mains_b.tex", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["title"] == "Draft B"
    assert inventory.main(["--root", str(tmp_path), "--main", "nope.tex"]) == 2


def test_root_makefile_without_main_is_not_used_for_subdir_paper(tmp_path):
    (tmp_path / "Makefile").write_text("all:\n\tpython3 run.py\n")
    (tmp_path / "paper").mkdir()
    _paper(tmp_path / "paper", "\\author{J}", name="main.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] == "paper/main.tex" and inv["build"]["kind"] is None
    assert "command" not in inventory.propose_config(inv)["build"]
    (tmp_path / "paper" / "Makefile").write_text("MAIN = main\n")
    inv = inventory.inventory(tmp_path)
    assert inv["build"]["kind"] == "make" and inv["build"]["cwd"] == "paper"
    assert inventory.propose_config(inv)["build"]["pdf"] == "paper/main.pdf"


def test_root_makefile_naming_another_file_is_not_used(tmp_path):
    (tmp_path / "Makefile").write_text("MAIN = other\n")
    (tmp_path / "paper").mkdir()
    _paper(tmp_path / "paper", "\\author{J}", name="main.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] == "paper/main.tex" and inv["build"]["kind"] is None


def test_root_makefile_naming_subdir_main_is_used(tmp_path):
    (tmp_path / "Makefile").write_text("MAIN = paper/main\n")
    (tmp_path / "paper").mkdir()
    _paper(tmp_path / "paper", "", name="main.tex")
    _paper(tmp_path / "paper", "", name="draft.tex")
    inv = inventory.inventory(tmp_path)
    assert inv["main"] == "paper/main.tex" and inv["build"]["cwd"] == "."


def test_root_level_r_code(tmp_path):
    _paper(tmp_path, "\\author{J}")
    (tmp_path / "DESCRIPTION").write_text("Package: x\n")
    assert inventory.inventory(tmp_path)["code"] == {"dir": ".", "language": "r"}


def test_figure_without_provenance(tmp_path):
    (tmp_path / "paper.tex").write_text(
        "\\documentclass{article}\n\\begin{document}\n% a plain comment\n\\includegraphics{a.png}\n"
        "% \\includegraphics{commented.png}\n\\end{document}\n")
    figs = inventory.inventory(tmp_path)["figures"]
    assert figs == [{"path": "a.png", "source": "paper.tex", "line": 4, "has_provenance": False}]


def test_code_and_results_enable_pipeline(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    (tmp_path / "analysis").mkdir()
    (tmp_path / "analysis" / "pyproject.toml").write_text("[project]\nname='x'\n")
    (tmp_path / "analysis" / "results").mkdir()
    (tmp_path / "analysis" / "results" / "m.json").write_text(json.dumps({"f1": 0.5, "n": 3, "ok": True, "name": "x"}))
    inv = inventory.inventory(tmp_path)
    assert inv["code"] == {"dir": "analysis", "language": "python"} and inv["results_dir"] == "analysis/results"
    prop = inventory.propose_config(inv)
    assert prop["pipeline"] == {"enabled": True, "language": "python", "run_from": "analysis",
                                "outputs_dir": "analysis/results", "metric_keys": [], "gotchas": []}
    g = _gaps(inv)
    assert g["pipeline.enabled"]["recommended"] is True
    assert g["pipeline.metric_keys"]["recommended"] == ["f1"]  # "n" is a count (R127 D3)


def test_r_code_tree(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    (tmp_path / "rpkg").mkdir()
    (tmp_path / "rpkg" / "DESCRIPTION").write_text("Package: x\n")
    inv = inventory.inventory(tmp_path)
    assert inv["code"] == {"dir": "rpkg", "language": "r"} and inv["results_dir"] is None
    assert "pipeline" not in inventory.propose_config(inv)
    assert "pipeline.enabled" in _gaps(inv) and "pipeline.metric_keys" not in _gaps(inv)


def test_git_remote_read_from_config(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text(
        '[core]\n\tbare = false\n[remote "origin"]\n\turl = git@example.org:me/paper.git\n')
    assert inventory.inventory(tmp_path)["git_remote"] == "git@example.org:me/paper.git"


def test_superpowers_detected_on_either_marketplace(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"superpowers@superpowers-marketplace": True}}))
    inv = inventory.inventory(tmp_path, home=home)
    assert inv["superpowers"] == {"enabled": True, "id": "superpowers@superpowers-marketplace"}
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"superpowers@claude-plugins-official": True}}))
    assert inventory.inventory(tmp_path, home=home)["superpowers"]["id"] == "superpowers@claude-plugins-official"


def test_superpowers_disabled_is_not_enabled(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"enabledPlugins": {"superpowers@claude-plugins-official": False}}))
    assert inventory.inventory(tmp_path, home=tmp_path / "nohome")["superpowers"] == {"enabled": False, "id": None}


def test_superpowers_in_settings_local(tmp_path):
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.local.json").write_text(
        json.dumps({"enabledPlugins": {"superpowers@claude-plugins-official": True}}))
    inv = inventory.inventory(tmp_path, home=tmp_path / "nohome")
    assert inv["superpowers"] == {"enabled": True, "id": "superpowers@claude-plugins-official"}


def test_legacy_harness_detected(repo_root):
    found = inventory.detect_legacy_harness(FIX_HARNESS / "legacy")
    kinds = {c["kind"] for c in found}
    assert kinds == {"skill_name_conflict", "hook_entry", "rule_restates_facts"}
    by_kind = {c["kind"]: c for c in found}
    assert by_kind["skill_name_conflict"]["path"] == ".claude/skills/compile-latex"
    assert "/ploma:compile" in by_kind["skill_name_conflict"]["consequence"]
    assert by_kind["rule_restates_facts"]["path"] == ".claude/rules/content-invariants.md"
    assert by_kind["hook_entry"]["path"] == ".claude/settings.json"
    assert all(c["consequence"] for c in found)


def test_statusline_detected(tmp_path):
    (tmp_path / ".claude" / "scripts").mkdir(parents=True)
    (tmp_path / ".claude" / "scripts" / "statusline.sh").write_text("#!/bin/sh\n")
    assert [c["kind"] for c in inventory.detect_legacy_harness(tmp_path)] == ["statusline"]
    shutil.rmtree(tmp_path / ".claude" / "scripts")
    (tmp_path / ".claude" / "settings.json").write_text(json.dumps({"statusLine": {"type": "command", "command": "x"}}))
    assert [c["kind"] for c in inventory.detect_legacy_harness(tmp_path)] == ["statusline"]


def test_make_sure_prose_is_not_a_fact(tmp_path):
    (tmp_path / ".claude/rules").mkdir(parents=True)
    (tmp_path / ".claude/rules/style.md").write_text("Make sure every figure has a caption. We make the case briefly.")
    assert inventory.detect_legacy_harness(tmp_path) == []


def test_command_shaped_rule_lines(tmp_path):
    rules = tmp_path / ".claude/rules"
    rules.mkdir(parents=True)
    for i, line in enumerate(["make clean", "Run pdflatex paper.tex twice.", "\\documentclass{article}",
                              "Then biber main.", "Keys come from refs.bib."]):
        (rules / f"r{i}.md").write_text(f"Intro prose.\n{line}\n")
        assert len(inventory.detect_legacy_harness(tmp_path)) == 1, line
        (rules / f"r{i}.md").unlink()
    (rules / "ploma-manuscript.md").write_text("cd paper && make\n")
    assert inventory.detect_legacy_harness(tmp_path) == []


def test_no_legacy_on_sample(sample_paper):
    assert inventory.detect_legacy_harness(sample_paper) == []


def test_cli_json(sample_paper, capsys):
    assert inventory.main(["--root", str(sample_paper), "--json", "gaps"]) == 0
    keys = {g["key"] for g in json.loads(capsys.readouterr().out)}
    assert {"venue.profile", "venue.page_budget"} <= keys
    assert inventory.main(["--root", str(sample_paper / "missing")]) == 2


def test_build_file_in_main_dir_naming_another_main_is_not_used(tmp_path):
    """Ruling R77: make would build the other file, so the build file is not this main's build."""
    for n in ("two_mains_a", "two_mains_b"): shutil.copy(FIX_TEX / f"{n}.tex", tmp_path / f"{n}.tex")
    (tmp_path / "Makefile").write_text("MAIN := two_mains_b\n\nall:\n\tpdflatex $(MAIN)\n")
    inv = inventory.inventory(tmp_path, main="two_mains_a.tex")
    assert inv["main"] == "two_mains_a.tex" and inv["build"]["kind"] is None
    assert "command" not in inventory.propose_config(inv)["build"]
    assert inventory.inventory(tmp_path, main="two_mains_b.tex")["build"]["kind"] == "make"


def test_latexmkrc_in_main_dir_naming_another_main_is_not_used(tmp_path):
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    (tmp_path / ".latexmkrc").write_text("@default_files = ('other.tex');\n")
    assert inventory.inventory(tmp_path)["build"]["kind"] is None


def test_page_budget_question_folds_in_whether_references_count(tmp_path):
    shutil.copy(FIX_TEX / "llncs_main.tex", tmp_path / "paper.tex")
    g = _gaps(inventory.inventory(tmp_path))
    pb = g["venue.page_budget"]
    assert "references" in pb["question"]
    refs = pb["includes_refs"]
    assert refs["key"] == "venue.page_budget_includes_refs" and refs["recommended"] is False
    assert refs["options"][0] == {"value": False, "label": "references do not count toward the limit"}
    assert {"value": True, "label": "references count toward the limit"} in refs["options"]
    assert "venue.page_budget_includes_refs" not in g, "folded into the page-budget question, not asked separately"


def test_proposed_slug_matches_the_schema_pattern(tmp_path):
    shutil.copy(FIX_TEX / "llncs_main.tex", tmp_path / "my paper (v2).tex")
    prop = inventory.propose_config(inventory.inventory(tmp_path))
    assert prop["document"]["slug"] == "my-paper-v2"


def _pipeline_repo(tmp_path: Path, results: dict[str, object]) -> dict:
    shutil.copy(FIX_TEX / "two_mains_a.tex", tmp_path / "paper.tex")
    (tmp_path / "analysis" / "results").mkdir(parents=True)
    (tmp_path / "analysis" / "pyproject.toml").write_text("[project]\nname='x'\n")
    for name, data in results.items():
        (tmp_path / "analysis" / "results" / name).write_text(json.dumps(data))
    return inventory.inventory(tmp_path)


def test_metric_keys_skip_config_and_read_nested_children(tmp_path):
    """R127 D3: config-like top-level keys are excluded; metrics nested under teams.<id> are recommended."""
    real = json.loads((FIX / "results" / "team_metrics.json").read_text(encoding="utf-8"))
    g = _gaps(_pipeline_repo(tmp_path, {"a_summary.json": real}))["pipeline.metric_keys"]
    assert g["recommended"] == ["avg_fitness", "dependency", "generalization"]
    assert g["options"] == g["recommended"]


def test_metric_keys_none_plausible_recommends_nothing(tmp_path):
    """R127 D3: only config-like keys left: no recommendation and an open question."""
    cfg = {"competition_id": 1, "season": 2022, "seed": 7, "num_runs": 3, "version": 2, "year": 2021,
           "threshold": 0.5}
    g = _gaps(_pipeline_repo(tmp_path, {"config.json": cfg}))["pipeline.metric_keys"]
    assert g["recommended"] == [] and g["options"] == []
    assert "could not" in g["question"].lower()


def test_discipline_gap_generic_for_plain_article(sample_paper):
    """R127 D4: onboard proposes document.discipline; a plain article without a pipeline gets generic."""
    inv = inventory.inventory(sample_paper, home=sample_paper / "nohome")
    g = _gaps(inv)["document.discipline"]
    assert g["recommended"] == "generic" and g["options"][0] == "generic"
    assert set(g["options"]) == {"generic", "ml", "social-science"}
    assert inventory.propose_config(inv)["document"]["discipline"] == "generic"


def test_discipline_gap_ml_for_ml_venue():
    inv = {"doc_class": "llncs", "code": None, "results_dir": None}
    opts = inventory._discipline_options(inv, "springer-ml")
    assert opts[0] == "ml" and "generic" in opts


def test_discipline_ml_for_python_pipeline(tmp_path):
    inv = _pipeline_repo(tmp_path, {"m.json": {"f1": 0.5}})
    assert _gaps(inv)["document.discipline"]["recommended"] == "ml"


def test_ml_venue_names():
    assert inventory._ml_venue("springer-ml") and not inventory._ml_venue("llncs-conference")
    assert inventory._ml_venue("neurips-2026") and inventory._ml_venue("ICLR") and inventory._ml_venue("deep-learning-ws")
    for name in ("aaai-26", "ijcai", "kdd-2027"):
        assert inventory._ml_venue(name), name
    assert not inventory._ml_venue("generic-journal") and not inventory._ml_venue(None)


def test_metric_keys_skip_hyperparameters_counts_and_config_blocks(tmp_path):
    """R127 fix round 1: counts and hyperparameters are not metrics; config-like parent dicts are not read."""
    data = {"accuracy": 0.9, "f1": 0.8, "match_count": 64, "count": 3, "total": 10, "batch_size": 32, "lr": 0.01,
            "epochs": 5, "idx": 2, "random_state": 0, "k": 5,
            "config": {"lr": 0.001, "batch_size": 64, "epochs": 10, "dropout": 0.1},
            "hparams": {"steps": 100, "patience": 3, "workers": 4, "auc": 0.7}}
    g = _gaps(_pipeline_repo(tmp_path, {"m.json": data}))["pipeline.metric_keys"]
    assert g["recommended"] == ["accuracy", "f1"]


def test_config_like_tokens():
    for key in ("match_count", "count", "total", "batch_size", "lr", "learning_rate", "epochs", "epoch", "idx",
                "index", "random_state", "k", "steps", "iterations", "patience", "workers", "dropout"):
        assert inventory._config_like(key), key
    for key in ("accuracy", "avg_fitness", "generalization", "dependency"):
        assert not inventory._config_like(key), key


def test_plain_llncs_paper_without_code_gets_generic(tmp_path):
    """R135: LNCS spans all of computer science; without a Python pipeline the discipline is generic."""
    shutil.copy(FIX_TEX / "llncs_main.tex", tmp_path / "paper.tex")
    inv = inventory.inventory(tmp_path)
    assert _gaps(inv)["document.discipline"]["recommended"] == "generic"
    assert inventory.propose_config(inv)["document"]["discipline"] == "generic"
