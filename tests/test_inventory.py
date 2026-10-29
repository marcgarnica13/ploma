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
                                "slug": "main", "anonymized": False}
    assert prop["build"]["command"] == "make" and prop["build"]["bib_files"] == ["refs.bib"]
    assert prop["build"]["pdf"] == "main.pdf" and prop["build"]["log"] == "main.log"
    assert prop["venue"] == {"profile": "generic-journal", "doc_class": "article", "page_budget": None,
                             "cite_style": "numeric"}
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
    assert g["venue.page_budget"]["recommended"] is None
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
    assert inv["engine_hint"] == "xelatex" and inv["anonymized"] is True and inv["title"] == "A Long Title"
    prop = inventory.propose_config(inv)
    assert prop["venue"]["cite_style"] == "author-year" and prop["venue"]["profile"] == "elsevier"


def test_author_present_is_not_anonymized(tmp_path):
    (tmp_path / "paper.tex").write_text(
        "\\documentclass{article}\n\\title{T}\n\\author{Jane Doe}\n\\begin{document}\n\\end{document}\n")
    assert inventory.inventory(tmp_path)["anonymized"] is False


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
    assert g["pipeline.metric_keys"]["recommended"] == ["f1", "n"]


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
