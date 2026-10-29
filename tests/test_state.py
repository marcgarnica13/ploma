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


import pytest  # noqa: E402


@pytest.mark.parametrize("body, key, action", [
    ("events: {a: 1}\n", "events", "record"),
    ("rounds: [1]\n", "rounds", "record_review"),
    ("rounds: {review: many}\n", "rounds.review", "record_review"),
    ("events: [hello]\n", "events.0", "next"),
    ("events: [hello]\n", "events.0", "render"),
    ("stage: nowhere\n", "stage", "next"),
])
def test_corrupt_state_file_raises_value_error(sample_paper, cfg, body, key, action):
    p = state.path(sample_paper, cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('ploma_state: "0.1"\n' + body)
    with pytest.raises(ValueError) as exc:
        if action == "record":
            state.record(sample_paper, cfg, "compile", "PASS")
        elif action == "record_review":
            state.record(sample_paper, cfg, "review", "PASS")
        elif action == "next":
            state.next_stage(state.load(sample_paper, cfg), cfg)
        else:
            state.render(state.load(sample_paper, cfg), cfg)
    assert str(p) in str(exc.value) and f"'{key}'" in str(exc.value)


@pytest.mark.parametrize("action", [["next"], ["render"], ["record", "compile", "PASS"]])
def test_corrupt_state_file_cli_exits_2(sample_paper, cfg, action):
    p = state.path(sample_paper, cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('ploma_state: "0.1"\nevents: [hello]\n')
    assert state.main(["--root", str(sample_paper)] + action) == 2


def test_in_memory_non_dict_events_are_skipped(cfg):
    st = {"ploma_state": "0.1", "stage": "compile", "rounds": {}, "events": ["hello", {"skill": "compile", "status": "PASS", "at": "2026-10-29T00:00:00Z"}]}
    assert state.next_stage(st, cfg)["stage"] == "format"
    assert "compile PASS" in state.render(st, cfg)


def test_explicit_round_sets_the_round_without_incrementing(sample_paper, cfg):
    """R142: an explicit round wins (max with the current); re-recording the same round does not bump it."""
    st = state.record(sample_paper, cfg, "respond", "WARN", round=2)
    assert st["rounds"]["respond"] == 2
    st = state.record(sample_paper, cfg, "respond", "PASS", round=2)
    assert st["rounds"]["respond"] == 2
    st = state.record(sample_paper, cfg, "respond", "PASS", round=1)
    assert st["rounds"]["respond"] == 2  # never goes down
    st = state.record(sample_paper, cfg, "review", "PASS", round=3)
    assert st["rounds"]["review"] == 3


def test_round_increments_only_without_an_explicit_round(sample_paper, cfg):
    state.record(sample_paper, cfg, "review", "PASS")
    st = state.record(sample_paper, cfg, "review", "PASS")
    assert st["rounds"]["review"] == 2
    # The CLI parses --extra round=2 as an int: same round, no bump.
    assert state.main(["--root", str(sample_paper), "record", "review", "PASS", "--extra", "round=2"]) == 0
    assert state.load(sample_paper, cfg)["rounds"]["review"] == 2
    # A respond audit (mode=audit, no round) checks a draft and never moves the round.
    st = state.record(sample_paper, cfg, "respond", "PASS", round=1)
    st = state.record(sample_paper, cfg, "respond", "WARN", mode="audit")
    assert st["rounds"]["respond"] == 1 and st["events"][-1]["mode"] == "audit"


# ---------------------------------------------------------------- respond needs referee reports

def test_review_passed_goes_to_respond_only_with_reports(sample_paper, cfg):
    st = state.record(sample_paper, cfg, "review", "PASS")
    assert state.next_stage(st, cfg, root=sample_paper)["stage"] == "respond"  # review/review1.md exists
    for p in (sample_paper / "review").glob("*.md"):
        p.unlink()
    rec = state.next_stage(st, cfg, root=sample_paper)
    assert rec["stage"] == "commit" and "reviews.glob" in rec["reason"]
    cfg["reviews"]["glob"] = None
    assert state.next_stage(st, cfg, root=sample_paper)["stage"] == "commit"


def test_render_skips_respond_without_reports(sample_paper, cfg):
    st = state.record(sample_paper, cfg, "review", "PASS")
    (sample_paper / "review" / "review1.md").unlink()
    assert "next: commit" in state.render(st, cfg, root=sample_paper)
