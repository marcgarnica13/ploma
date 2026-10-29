"""Tests for scripts/gate.py (commit gate verdict file)."""
from __future__ import annotations

import json
import shutil
import subprocess

import pytest

import gate
import ploma_config


def test_incomplete_until_required_present(sample_paper, cfg):
    assert gate.check(sample_paper, cfg).verdict == "INCOMPLETE"


def test_pass_when_required_pass(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    r = gate.check(sample_paper, cfg); assert r.verdict == "PASS" and "claims" in " ".join(r.warnings)


def test_stale_after_manuscript_edit(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    (sample_paper / "sections/intro.tex").write_text("changed")
    r = gate.check(sample_paper, cfg); assert r.verdict == "INCOMPLETE" and not r.checks["compile"]["fresh"]


def test_suggestion_files_do_not_stale_the_gate(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    (sample_paper / "sections/intro_suggestion.tex").write_text("draft")
    assert gate.check(sample_paper, cfg).verdict == "PASS"


def test_override_streak_hard_stop(sample_paper, cfg):
    gate.record(sample_paper, cfg, "compile", "FAIL", "x.md")
    for _ in range(3): gate.override(sample_paper, cfg, "deadline", ["compile"])
    assert gate.check(sample_paper, cfg).can_override is False


def test_required_pass_resets_streak(sample_paper, cfg):
    gate.override(sample_paper, cfg, "r", ["compile"]); gate.record(sample_paper, cfg, "compile", "PASS", "x.md")
    assert gate.check(sample_paper, cfg).override_streak == 0


def test_fresh_required_fail_is_fail(sample_paper, cfg):
    gate.record(sample_paper, cfg, "compile", "FAIL", "x.md")
    gate.record(sample_paper, cfg, "bib", "PASS", "x.md")
    assert gate.check(sample_paper, cfg).verdict == "FAIL"


def test_stale_required_fail_is_incomplete(sample_paper, cfg):
    gate.record(sample_paper, cfg, "compile", "FAIL", "x.md")
    gate.record(sample_paper, cfg, "bib", "PASS", "x.md")
    (sample_paper / "refs.bib").write_text("@misc{k, title={t}}\n")
    r = gate.check(sample_paper, cfg)
    assert r.verdict == "INCOMPLETE" and not r.checks["bib"]["fresh"]


def test_per_entry_sha_freshness(sample_paper, cfg):
    gate.record(sample_paper, cfg, "compile", "PASS", "x.md")
    (sample_paper / "sections/intro.tex").write_text("changed")
    gate.record(sample_paper, cfg, "bib", "PASS", "x.md")
    r = gate.check(sample_paper, cfg)
    assert r.checks["bib"]["fresh"] and not r.checks["compile"]["fresh"]
    assert r.verdict == "INCOMPLETE"


def test_warnings_for_recommended(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    gate.record(sample_paper, cfg, "proofread", "WARN", "p.md", open_high=2)
    gate.record(sample_paper, cfg, "claims", "PASS", "c.md")
    r = gate.check(sample_paper, cfg)
    assert r.verdict == "PASS"
    assert len(r.warnings) == 2
    joined = " ".join(r.warnings)
    assert "consistency" in joined and "proofread" in joined and "claims" not in joined


def test_recommended_fail_never_blocks(sample_paper, cfg):
    for c in gate.REQUIRED: gate.record(sample_paper, cfg, c, "PASS", "x.md")
    gate.record(sample_paper, cfg, "consistency", "FAIL", "c.md")
    assert gate.check(sample_paper, cfg).verdict == "PASS"


def test_file_shape(sample_paper, cfg, repo_root):
    gate.record(sample_paper, cfg, "compile", "PASS", "c.md", pages=14, overfull=0)
    gate.override(sample_paper, cfg, "camera-ready deadline", ["proofread"])
    p = gate.path(sample_paper, cfg)
    assert p == (sample_paper / "quality_reports" / "verdicts" / "commit-gate.json").resolve()
    data = json.loads(p.read_text())
    assert set(data) == {"schema", "manuscript_sha", "checks", "overrides", "override_streak"}
    entry = data["checks"]["compile"]
    assert entry["status"] == "PASS" and entry["artifact"] == "c.md" and entry["pages"] == 14
    assert entry["at"].endswith("Z") and entry["manuscript_sha"] == data["manuscript_sha"]
    assert data["overrides"][0]["reason"] == "camera-ready deadline" and data["overrides"][0]["checks"] == ["proofread"]
    schema = json.loads((repo_root / "schemas" / "verdict.schema.json").read_text())
    out = []
    ploma_config._check(data, schema, "", out)
    assert out == []


def test_manuscript_sha_covers_tex_and_bib_only(sample_paper, cfg):
    before = gate.manuscript_sha(sample_paper, cfg)
    assert len(before) == 64
    (sample_paper / "notes.txt").write_text("x")
    assert gate.manuscript_sha(sample_paper, cfg) == before
    (sample_paper / "extra.bib").write_text("@misc{a, title={b}}")
    assert gate.manuscript_sha(sample_paper, cfg) != before


def test_manuscript_sha_skips_gitignored(sample_paper, cfg):
    if shutil.which("git") is None:
        pytest.skip("git not available")
    subprocess.run(["git", "init", "-q", str(sample_paper)], check=True)
    (sample_paper / ".gitignore").write_text("build/\n")
    before = gate.manuscript_sha(sample_paper, cfg)
    (sample_paper / "build").mkdir()
    (sample_paper / "build" / "main.tex").write_text("generated copy")
    assert gate.manuscript_sha(sample_paper, cfg) == before
    (sample_paper / "tracked.tex").write_text("new")
    assert gate.manuscript_sha(sample_paper, cfg) != before


def test_override_refused_at_cap(sample_paper, cfg):
    for _ in range(gate.MAX_CONSECUTIVE_OVERRIDES):
        gate.override(sample_paper, cfg, "deadline", ["compile"])
    with pytest.raises(ValueError):
        gate.override(sample_paper, cfg, "again", ["compile"])


def test_reset_streak(sample_paper, cfg):
    gate.override(sample_paper, cfg, "r", ["compile"])
    gate.reset_streak(sample_paper, cfg)
    assert gate.check(sample_paper, cfg).override_streak == 0


def test_recommended_pass_does_not_reset_streak(sample_paper, cfg):
    gate.override(sample_paper, cfg, "r", ["compile"])
    gate.record(sample_paper, cfg, "claims", "PASS", "c.md")
    assert gate.check(sample_paper, cfg).override_streak == 1


def test_invalid_inputs(sample_paper, cfg):
    with pytest.raises(ValueError):
        gate.record(sample_paper, cfg, "nope", "PASS", "x.md")
    with pytest.raises(ValueError):
        gate.record(sample_paper, cfg, "compile", "MAYBE", "x.md")
    with pytest.raises(ValueError):
        gate.override(sample_paper, cfg, "  ", ["compile"])


def test_to_dict(sample_paper, cfg):
    d = gate.check(sample_paper, cfg).to_dict()
    assert d["verdict"] == "INCOMPLETE" and d["can_override"] is True
    assert d["checks"]["compile"] == {"status": None, "fresh": False, "required": True, "present": False}
    json.dumps(d)


def test_cli(sample_paper, capsys):
    root = str(sample_paper)
    assert gate.main(["--root", root, "check"]) == 1
    capsys.readouterr()
    assert gate.main(["--root", root, "record", "compile", "PASS", "--artifact", "c.md",
                      "--extra", "pages=14", "--extra", "note=ok"]) == 0
    assert gate.main(["--root", root, "record", "bib", "PASS", "--artifact", "b.md"]) == 0
    capsys.readouterr()
    assert gate.main(["--root", root, "check", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["verdict"] == "PASS"
    data = json.loads(gate.path(sample_paper, ploma_config.load(sample_paper)).read_text())
    assert data["checks"]["compile"]["pages"] == 14 and data["checks"]["compile"]["note"] == "ok"
    assert gate.main(["--root", root, "override", "--reason", "deadline", "--checks", "compile,bib"]) == 0
    capsys.readouterr()
    assert gate.main(["--root", root, "check", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["override_streak"] == 1
    assert gate.main(["--root", root, "record", "compile", "PASS"]) == 2  # --artifact required
    assert gate.main(["--root", root, "record", "zzz", "PASS", "--artifact", "a"]) == 2


def test_cli_without_config(tmp_path):
    assert gate.main(["--root", str(tmp_path), "check"]) == 2
