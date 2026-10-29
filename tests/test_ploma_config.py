"""Tests for the ploma.yaml loader, validator and summary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import _yamlio
import ploma_config
from _findings import FAIL, WARN

FIXTURES = Path(__file__).parent / "fixtures" / "yaml"
MINIMAL = (FIXTURES / "ploma_minimal.yaml").read_text()
BAD_TYPE = (FIXTURES / "ploma_bad_type.yaml").read_text()
FULL = (FIXTURES / "ploma_full.yaml").read_text()


def _ids(cfg, root):
    return {x.id: x for x in ploma_config.validate(cfg, root)}


def _minimal_repo(tmp_path: Path, text: str = MINIMAL) -> Path:
    (tmp_path / "ploma.yaml").write_text(text)
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text("\\documentclass{article}\n")
    return tmp_path


def test_load_minimal_applies_defaults(tmp_path):
    (tmp_path / "ploma.yaml").write_text(MINIMAL)
    cfg = ploma_config.load(tmp_path)
    assert cfg["outputs"]["dir"] == "quality_reports"
    assert cfg["limits"]["review_rounds"] == 5
    assert cfg["pipeline"]["enabled"] is False


def test_missing_config_raises(tmp_path):
    with pytest.raises(ploma_config.ConfigError):
        ploma_config.load(tmp_path)


def test_unparseable_config_raises(tmp_path):
    (tmp_path / "ploma.yaml").write_text("a: [unclosed\nb: *alias\n")
    with pytest.raises(ploma_config.ConfigError):
        ploma_config.load(tmp_path)


def test_missing_path_is_a_finding(sample_paper):
    cfg = ploma_config.load(sample_paper)
    cfg["build"]["bib_files"] = ["gone.bib"]
    f = _ids(cfg, sample_paper)
    assert f["config.path.build.bib_files"].status == FAIL
    assert "gone.bib" in f["config.path.build.bib_files"].observed


def test_unsupported_document_type(sample_paper):
    cfg = ploma_config.load(sample_paper)
    cfg["document"]["type"] = "proposal"
    f = _ids(cfg, sample_paper)
    assert f["config.document_type_unsupported"].status == FAIL
    assert "not supported in ploma v0.1" in f["config.document_type_unsupported"].summary


def test_unsupported_document_type_minimal(tmp_path):
    root = _minimal_repo(tmp_path)
    cfg = ploma_config.load(root)
    cfg["document"]["type"] = "proposal"
    f = _ids(cfg, root)
    assert f["config.document_type_unsupported"].status == FAIL
    assert f["config.document_type_unsupported"].summary == \
        "document.type 'proposal' is not supported in ploma v0.1"


def test_bad_type_is_a_finding(tmp_path):
    (tmp_path / "ploma.yaml").write_text(BAD_TYPE)
    cfg = ploma_config.load(tmp_path)
    ids = [x.id for x in ploma_config.validate(cfg, tmp_path)]
    assert "config.type.build.overfull_threshold_pt" in ids


def test_enum_and_required_findings(tmp_path):
    root = _minimal_repo(tmp_path)
    cfg = ploma_config.load(root)
    cfg["build"]["engine"] = "tectonic"
    del cfg["venue"]["profile"]
    f = _ids(cfg, root)
    assert f["config.enum.build.engine"].status == FAIL
    assert f["config.required.venue.profile"].status == FAIL


def test_valid_minimal_passes(tmp_path):
    root = _minimal_repo(tmp_path)
    findings = ploma_config.validate(ploma_config.load(root), root)
    assert [x.status for x in findings if x.status == FAIL] == []


def test_missing_main_and_bib_flagged(tmp_path):
    (tmp_path / "ploma.yaml").write_text(MINIMAL)
    cfg = ploma_config.load(tmp_path)
    cfg["build"]["bib_files"] = ["refs/a.bib"]
    f = _ids(cfg, tmp_path)
    assert f["config.path.document.main"].status == FAIL
    assert "refs/a.bib" in f["config.path.build.bib_files"].observed


def test_outputs_are_not_path_checked(tmp_path):
    root = _minimal_repo(tmp_path)
    cfg = ploma_config.load(root)
    cfg["build"]["pdf"] = "nowhere/out.pdf"
    cfg["build"]["log"] = "nowhere/out.log"
    cfg["outputs"]["dir"] = "not/yet"
    f = _ids(cfg, root)
    assert not [i for i in f if i.startswith("config.path.")]


def test_reviews_glob_prefix_checked(tmp_path):
    root = _minimal_repo(tmp_path)
    cfg = ploma_config.load(root)
    cfg["reviews"]["glob"] = "review/round*/*.md"
    f = _ids(cfg, root)
    assert f["config.path.reviews.glob"].status == WARN
    assert f["config.path.reviews.glob"].observed == "review"
    (root / "review").mkdir()
    assert "config.path.reviews.glob" not in _ids(cfg, root)
    cfg["reviews"]["glob"] = "*.md"
    assert "config.path.reviews.glob" not in _ids(cfg, root)


def test_ploma_version_accepts_number(tmp_path):
    root = _minimal_repo(tmp_path, MINIMAL.replace('"0.1"', "0.1"))
    f = _ids(ploma_config.load(root), root)
    assert "config.type.ploma" not in f


def test_full_spec_example_is_schema_valid(tmp_path):
    (tmp_path / "ploma.yaml").write_text(FULL)
    cfg = ploma_config.load(tmp_path)
    ids = _ids(cfg, tmp_path)
    assert not [i for i in ids if i.startswith(("config.type.", "config.enum.", "config.required.", "config.unknown."))]
    assert cfg["pipeline"]["figure_provenance"] == "optional"


def test_load_with_fallback_loader(tmp_path, monkeypatch):
    monkeypatch.setattr(_yamlio, "_yaml", None)
    (tmp_path / "ploma.yaml").write_text(FULL)
    cfg = ploma_config.load(tmp_path)
    assert cfg["pipeline"]["tolerances"]["metrics"] == 0.01


def test_derived_defaults_and_resolve(tmp_path):
    root = _minimal_repo(tmp_path)
    cfg = ploma_config.load(root)
    assert cfg["document"]["root"] == "paper"
    assert cfg["build"]["cwd"] == "paper"
    assert cfg["build"]["pdf"] == "paper/main.pdf"
    paths = ploma_config.resolve(cfg, root)["_paths"]
    assert paths["main"] == str((root / "paper" / "main.tex").resolve())
    assert paths["outputs_dir"] == str((root / "quality_reports").resolve())
    assert set(paths) >= {"main", "root", "bib_files", "pdf", "log", "outputs_dir", "build_cwd"}
    assert "_paths" not in cfg


def test_summary_mentions_key_facts(tmp_path):
    (tmp_path / "ploma.yaml").write_text(FULL)
    s = ploma_config.summary(ploma_config.load(tmp_path))
    assert len(s) < 1500
    for needle in ("manuscript/samplepaper.tex", "pdflatex", "bibtex", "springer-ml", "13", "quality_reports", "make"):
        assert needle in s


def test_summary_is_short(sample_paper):
    assert len(ploma_config.summary(ploma_config.load(sample_paper))) < 1500


def test_cli_validate_json_and_exit_codes(tmp_path, capsys):
    root = _minimal_repo(tmp_path)
    assert ploma_config.main(["--root", str(root), "--json", "validate"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] in ("PASS", "INFO", "WARN")
    (root / "paper" / "main.tex").unlink()
    assert ploma_config.main(["--root", str(root), "validate"]) == 1
    assert "config.path.document.main" in capsys.readouterr().out
    assert ploma_config.main(["--root", str(tmp_path / "nope"), "summary"]) == 2


def test_cli_json_dump_is_resolved(tmp_path, capsys):
    root = _minimal_repo(tmp_path)
    assert ploma_config.main(["--root", str(root), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["_paths"]["main"].endswith("main.tex")


def test_summary_never_prints_none(sample_paper):
    """R65: clauses whose value is None or empty are omitted."""
    cfg = ploma_config.load(sample_paper)
    assert cfg["pipeline"]["rerun"] is None
    s = ploma_config.summary(cfg)
    assert "None" not in s and "pipeline: enabled; language python; run from .; outputs results" in s
    cfg["venue"]["profile"] = None
    cfg["build"]["cwd"] = None
    cfg["limits"]["review_rounds"] = None
    s = ploma_config.summary(cfg)
    assert "None" not in s and "venue: page budget 8" in s


def test_missing_pipeline_outputs_dir_is_warn(sample_paper):
    """pipeline.outputs_dir is generated and often gitignored: absent on a fresh clone is a WARN, not a FAIL."""
    cfg = ploma_config.load(sample_paper)
    cfg["pipeline"]["outputs_dir"] = "results/not_yet"
    f = _ids(cfg, sample_paper)["config.path.pipeline.outputs_dir"]
    assert f.status == WARN and "results/not_yet" in f.observed
    cfg["pipeline"]["run_from"] = "gone"
    assert _ids(cfg, sample_paper)["config.path.pipeline.run_from"].status == FAIL


@pytest.mark.parametrize("slug,ok", [("main", True), ("paper-v2.final_1", True), ("my paper", False),
                                     ("a/b", False), ("café", False), ("", False)])
def test_document_slug_pattern(sample_paper, slug, ok):
    cfg = ploma_config.load(sample_paper)
    cfg["document"]["slug"] = slug
    f = _ids(cfg, sample_paper).get("config.pattern.document.slug")
    assert (f is None) == ok
    if f is not None:
        assert f.status == FAIL and "^[A-Za-z0-9._-]+$" in f.summary


def test_schema_declares_the_slug_pattern(repo_root):
    schema = json.loads((repo_root / "schemas" / "ploma.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["document"]["properties"]["slug"]["pattern"] == "^[A-Za-z0-9._-]+$"


def test_summary_carries_agent_facts(sample_paper):
    """R107: agents without a shell read discipline, slug, style, language, env contract and gotchas here."""
    cfg = ploma_config.load(sample_paper)
    cfg["document"]["discipline"] = "ml"
    cfg["style"]["forbid_phrases"] = ["very unique"]
    cfg["pipeline"]["env_contract"] = ["DATA_DIR", "API_TOKEN"]
    cfg["pipeline"]["gotchas"] = ["Config is read at import time", "Keys use a double-hash separator"]
    s = ploma_config.summary(cfg)
    for needle in ("slug main", "discipline ml", "anonymized", "em-dash forbidden", "very unique",
                   "language python", "env contract: DATA_DIR, API_TOKEN",
                   "(1) Config is read at import time", "(2) Keys use a double-hash separator"):
        assert needle in s, needle
    cfg["document"]["discipline"] = None
    assert "discipline generic (unset)" in ploma_config.summary(cfg)


def test_summary_truncates_long_gotchas_under_cap(sample_paper):
    cfg = ploma_config.load(sample_paper)
    cfg["pipeline"]["gotchas"] = [f"gotcha number {i} " + "x" * 300 for i in range(20)]
    s = ploma_config.summary(cfg)
    assert len(s) < 1500
    assert "- pipeline gotchas: (1) gotcha number 0" in s and "(truncated; 20 in ploma.yaml)" in s
    assert s.splitlines()[-1].startswith("- pipeline gotchas:")
    assert "- limits:" in s  # earlier lines are never cut for gotchas


def test_summary_omits_gotchas_when_pipeline_disabled(sample_paper):
    cfg = ploma_config.load(sample_paper)
    cfg["pipeline"]["enabled"] = False
    cfg["pipeline"]["gotchas"] = ["something"]
    assert "gotchas" not in ploma_config.summary(cfg)
