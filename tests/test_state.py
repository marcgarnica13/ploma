"""Tests for scripts/state.py (lifecycle state file)."""
from __future__ import annotations

import json

import _yamlmini
import ploma_config
import state


def test_record_and_next(sample_paper):
    cfg = ploma_config.load(sample_paper)
    st = state.record(sample_paper, cfg, "compile", "PASS", artifact="quality_reports/compile_main.md", pages=7)
    assert st["stage"] == "compile" and st["events"][-1]["pages"] == 7
    assert state.next_stage(st, cfg)["stage"] == "format"


def test_review_round_increments(sample_paper):
    cfg = ploma_config.load(sample_paper)
    state.record(sample_paper, cfg, "review", "PASS"); st = state.record(sample_paper, cfg, "review", "PASS")
    assert st["rounds"]["review"] == 2


def test_next_before_any_event(sample_paper):
    cfg = ploma_config.load(sample_paper)
    assert state.next_stage(state.load(sample_paper, cfg), cfg)["stage"] == "compile"
    assert state.next_stage(state.load(sample_paper, cfg), None)["stage"] == "onboard"


def test_render_is_short(sample_paper, cfg):
    for _ in range(10):
        state.record(sample_paper, cfg, "validate-bib", "WARN", artifact="quality_reports/" + "x" * 80 + ".md")
    st = state.record(sample_paper, cfg, "compile", "FAIL")
    text = state.render(st, cfg)
    assert len(text) < 600
    assert "compile FAIL" in text and "compile" in text.splitlines()[0]
    assert text.count("validate-bib WARN") == 4  # last five events only


def test_load_absent_is_empty(sample_paper, cfg):
    assert state.load(sample_paper, cfg) == {"ploma_state": "0.1", "stage": None, "rounds": {}, "events": []}
    assert state.path(sample_paper, cfg) == (sample_paper / "quality_reports" / "ploma-state.yaml").resolve()


def test_persisted_round_trip(sample_paper, cfg):
    state.record(sample_paper, cfg, "compile", "PASS", artifact="a.md", pages=7)
    st = state.load(sample_paper, cfg)
    ev = st["events"][-1]
    assert ev["skill"] == "compile" and ev["status"] == "PASS" and ev["artifact"] == "a.md" and ev["pages"] == 7
    assert isinstance(ev["at"], str) and ev["at"].endswith("Z")
    assert not list(state.path(sample_paper, cfg).parent.glob("*.tmp"))


def test_yamlmini_round_trip(sample_paper, cfg):
    st = state.record(sample_paper, cfg, "respond", "WARN", artifact="r.md", round=1)
    again = _yamlmini.load(_yamlmini.dump(st))
    assert again["events"][-1]["at"] == st["events"][-1]["at"]
    assert again["rounds"] == {"respond": 1}


def test_failed_stage_is_recommended_again(sample_paper, cfg):
    st = state.record(sample_paper, cfg, "compile", "FAIL")
    rec = state.next_stage(st, cfg)
    assert rec["stage"] == "compile" and "FAIL" in rec["reason"]


def test_validate_stage_uses_latest_of_any_validate_skill(sample_paper, cfg):
    state.record(sample_paper, cfg, "validate-bib", "FAIL")
    st = state.record(sample_paper, cfg, "proofread", "PASS")
    assert st["stage"] == "validate"
    assert state.next_stage(st, cfg)["stage"] == "review"


def test_session_skills_do_not_change_stage(sample_paper, cfg):
    state.record(sample_paper, cfg, "format", "PASS")
    st = state.record(sample_paper, cfg, "doctor", "PASS")
    assert st["stage"] == "format" and len(st["events"]) == 2
    assert state.next_stage(st, cfg)["stage"] == "validate"


def test_only_session_events_falls_back(sample_paper, cfg):
    st = state.record(sample_paper, cfg, "status", "PASS")
    assert st["stage"] is None
    assert state.next_stage(st, cfg)["stage"] == "compile"


def test_cycle_complete(sample_paper, cfg):
    st = state.record(sample_paper, cfg, "commit", "PASS")
    rec = state.next_stage(st, cfg)
    assert rec["stage"] == "commit" and "cycle complete" in rec["reason"]


def test_every_skill_maps_to_a_stage_or_none():
    assert set(v for v in state.SKILL_TO_STAGE.values() if v) <= set(state.STAGES)
    for skill in ("validate-bib", "verify-claims", "audit-reproducibility", "proofread"):
        assert state.SKILL_TO_STAGE[skill] == "validate"
    assert state.SKILL_TO_STAGE["devils-advocate"] == "review"
    assert state.SKILL_TO_STAGE["help"] is None


def test_unknown_skill_or_status_rejected(sample_paper, cfg):
    import pytest
    with pytest.raises(ValueError):
        state.record(sample_paper, cfg, "nonsense", "PASS")
    with pytest.raises(ValueError):
        state.record(sample_paper, cfg, "compile", "GREAT")


def test_state_matches_schema(sample_paper, cfg, repo_root):
    st = state.record(sample_paper, cfg, "review", "PASS", artifact="r.md", round=1)
    schema = json.loads((repo_root / "schemas" / "state.schema.json").read_text())
    out = []
    ploma_config._check(st, schema, "", out)
    assert out == []


def test_cli(sample_paper, capsys):
    root = str(sample_paper)
    assert state.main(["--root", root, "record", "compile", "PASS", "--artifact", "c.md", "--extra", "pages=9"]) == 0
    capsys.readouterr()
    assert state.main(["--root", root, "next", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["stage"] == "format"
    assert state.main(["--root", root, "render"]) == 0
    assert "compile PASS" in capsys.readouterr().out
    assert state.load(sample_paper, ploma_config.load(sample_paper))["events"][-1]["pages"] == 9
    assert state.main(["--root", root, "record", "nope", "PASS"]) == 2
    assert state.main(["--root", root, "bogus"]) == 2


def test_cli_without_config_recommends_onboard(tmp_path, capsys):
    assert state.main(["--root", str(tmp_path), "next", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["stage"] == "onboard"
