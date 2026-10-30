"""session_context hook: build_context content, caps, no-config behaviour, hooks.json wiring."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys

import pytest

import host
import session_context


@pytest.fixture(autouse=True)
def _no_project_env(monkeypatch):
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)


def _ctx(root, repo_root, **kw):
    kw.setdefault("subagent", False)
    kw.setdefault("source", "startup")
    return session_context.build_context(root, plugin_root=repo_root, **kw)


def test_context_under_cap_on_sample(onboarded_sample, repo_root):
    out = _ctx(onboarded_sample, repo_root)
    assert len(out) < 10000 and "## ploma project" in out and "## ploma status" in out
    assert out.startswith("# ploma core rules")
    assert out.index("# ploma core rules") < out.index("## ploma project") < out.index("## ploma status")
    assert "commit gate:" in out and "ploma stage:" in out
    assert "## Resuming" not in out


def test_bare_repo_is_silent(tmp_path, repo_root):
    assert _ctx(tmp_path, repo_root) == ""


def test_no_config_one_liner(tmp_path, repo_root):
    (tmp_path / "paper.tex").write_text(r"\documentclass{article}")
    out = _ctx(tmp_path, repo_root)
    assert out.strip().startswith("ploma is installed but") and "/ploma:onboard" in out
    assert "\n" not in out.strip()


def test_no_config_tex_two_levels_deep_counts_three_does_not(tmp_path, repo_root):
    deep = tmp_path / "a" / "b"
    deep.mkdir(parents=True)
    (deep / "x.tex").write_text("")
    assert _ctx(tmp_path, repo_root).startswith("ploma is installed but")
    (deep / "x.tex").unlink()
    (deep / "c").mkdir()
    (deep / "c" / "x.tex").write_text("")
    assert _ctx(tmp_path, repo_root) == ""


def test_no_config_hidden_dirs_skipped(tmp_path, repo_root):
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "x.tex").write_text("")
    assert _ctx(tmp_path, repo_root) == ""


def test_invalid_yaml_yields_notice_and_exit_zero(tmp_path, repo_root, capsys):
    (tmp_path / "ploma.yaml").write_text("document: [unclosed")
    rc = session_context.main(stdin=io.StringIO(json.dumps(
        {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(tmp_path)})), plugin_root=repo_root, argv=[])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "could not be parsed" in payload["hookSpecificOutput"]["additionalContext"]


def test_main_emits_single_json_object(onboarded_sample, repo_root, capsys):
    rc = session_context.main(stdin=json.dumps({"hook_event_name": "SessionStart", "source": "startup",
                                                "cwd": str(onboarded_sample)}), plugin_root=repo_root, argv=[])
    out = capsys.readouterr().out
    assert rc == 0 and out.count("\n") == 1
    assert set(json.loads(out)) == {"hookSpecificOutput"}


def test_subagent_mode_omits_status(onboarded_sample, repo_root):
    out = _ctx(onboarded_sample, repo_root, subagent=True, source="compact")
    assert "## ploma project" in out and "# ploma core rules" in out
    assert "## ploma status" not in out and "## Resuming" not in out


def test_subagent_main_uses_subagent_event(onboarded_sample, repo_root, capsys):
    session_context.main(stdin=json.dumps({"cwd": str(onboarded_sample)}), plugin_root=repo_root, argv=["--subagent"])
    payload = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "SubagentStart" and "## ploma status" not in payload["additionalContext"]


def test_resume_block_on_compact(onboarded_sample, repo_root):
    plans = onboarded_sample / "quality_reports" / "plans"
    plans.mkdir(parents=True)
    old = plans / "2026-10-01_old.md"
    old.write_text("**Status:** COMPLETED\n- [x] done\n")
    new = plans / "2026-10-28_intro.md"
    new.write_text("# Plan\n**Status:** APPROVED\n- [x] outline\n- [ ] draft the introduction\n")
    os.utime(old, (1, 1))
    logs = onboarded_sample / "quality_reports" / "session_logs"
    logs.mkdir(parents=True)
    (logs / "2026-10-28_intro.md").write_text("Decision: keep it short\n")
    for source in ("compact", "resume"):
        out = _ctx(onboarded_sample, repo_root, source=source)
        assert "## Resuming" in out
        assert "2026-10-28_intro.md (status APPROVED)" in out
        assert "draft the introduction" in out
        assert "session_logs/2026-10-28_intro.md" in out
        assert out.index("## ploma status") < out.index("## Resuming")
    assert "## Resuming" not in _ctx(onboarded_sample, repo_root, source="clear")


def test_resume_block_reads_pre_compact_state(onboarded_sample, repo_root):
    state = onboarded_sample / ".ploma"
    state.mkdir()
    (state / "pre-compact-state.json").write_text(json.dumps(
        {"plan_path": "p.md", "plan_status": "draft", "current_task": "fix table 2", "decisions": ["use 8 pages"]}))
    out = _ctx(onboarded_sample, repo_root, source="compact")
    assert "fix table 2" in out and "use 8 pages" in out


def test_cap_truncates_status_then_resume_never_rules(repo_root):
    head = "R" * 6000
    out = session_context._fit(head, "S" * 3000, "M" * 2000)
    assert len(out) < 9500 and out.startswith(head) and "M" * 2000 in out and "[truncated]" in out
    out = session_context._fit(head, "S" * 3000, "M" * 5000)
    assert len(out) < 9500 and out.startswith(head) and "S" not in out
    out = session_context._fit("R" * 9600, "S" * 10, "M" * 10)
    assert out == "R" * 9600


def test_cap_enforced_on_oversized_status(onboarded_sample, repo_root, monkeypatch):
    monkeypatch.setattr(session_context, "_status_block", lambda root, cfg: "## ploma status\n" + "x" * 20000)
    out = _ctx(onboarded_sample, repo_root, source="compact")
    assert len(out) < 9500 and "## ploma project" in out and "## Resuming" in out


def test_hooks_json_wires_session_events(repo_root):
    h = json.loads((repo_root / "hooks/hooks.json").read_text())["hooks"]
    assert "SessionStart" in h and "SubagentStart" in h
    start = h["SessionStart"][0]
    assert start["matcher"] == "startup|resume|clear|compact"
    cmd = start["hooks"][0]
    assert cmd["command"] == 'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/session_context.py"' and cmd["timeout"] == 10
    sub = h["SubagentStart"][0]
    assert "matcher" not in sub
    assert sub["hooks"][0]["command"].endswith("session_context.py\" --subagent") and sub["hooks"][0]["timeout"] == 10


def _run_script(repo_root, cwd, payload, *args):
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(repo_root))
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run([sys.executable, str(repo_root / "hooks/session_context.py"), *args],
                          input=json.dumps(payload), capture_output=True, text=True, cwd=str(cwd), env=env, timeout=30)


def test_script_end_to_end(onboarded_sample, repo_root, tmp_path):
    r = _run_script(repo_root, tmp_path, {"hook_event_name": "SessionStart", "source": "startup", "cwd": str(onboarded_sample)})
    assert r.returncode == 0
    ctx = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "## ploma status" in ctx and len(ctx) < 10000
    bare = tmp_path / "bare"
    bare.mkdir()
    r = _run_script(repo_root, bare, {"source": "startup", "cwd": str(bare)})
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""
    (bare / "p.tex").write_text("")
    r = _run_script(repo_root, bare, {"source": "startup", "cwd": str(bare)})
    assert r.returncode == 0
    assert json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"].startswith("ploma is installed but")
    r = _run_script(repo_root, bare, {"cwd": str(bare)}, "--subagent")
    assert r.returncode == 0 and r.stdout == ""


def test_gate_import_failure_keeps_rules(onboarded_sample, repo_root, monkeypatch):
    """R68: a failing import of gate (or state) loses only status lines, never the rules or project block."""
    monkeypatch.setitem(sys.modules, "gate", None)    # makes `import gate` raise ImportError
    monkeypatch.setitem(sys.modules, "state", None)
    out = _ctx(onboarded_sample, repo_root, source="compact")
    assert out.startswith("# ploma core rules") and "## ploma project" in out
    assert "commit gate unavailable" in out and "lifecycle state unavailable" in out
    assert "## Resuming" in out


def test_status_block_crash_keeps_rules(onboarded_sample, repo_root, monkeypatch):
    def boom(root, cfg):
        raise RuntimeError("kaput")
    monkeypatch.setattr(session_context, "_status_block", boom)
    out = _ctx(onboarded_sample, repo_root)
    assert out.startswith("# ploma core rules") and "status unavailable: kaput" in out


def test_subagent_context_names_plugin_paths(onboarded_sample, repo_root):
    """R108: agents get absolute plugin paths after the summary; the main session does not."""
    out = _ctx(onboarded_sample, repo_root, subagent=True)
    lines = out.splitlines()
    root_line = next(l for l in lines if l.startswith("ploma root: "))
    scripts_line = next(l for l in lines if l.startswith("ploma scripts: "))
    root = root_line.split(": ", 1)[1]
    scripts = scripts_line.split(": ", 1)[1]
    assert os.path.isabs(root) and os.path.samefile(root, repo_root)
    assert os.path.isfile(os.path.join(scripts, "ploma_config.py")) and scripts == os.path.join(root, "scripts")
    assert out.index("## ploma project") < out.index(root_line) < out.index(scripts_line)
    assert "ploma root: " not in _ctx(onboarded_sample, repo_root)


def test_subagent_paths_survive_a_broken_config(tmp_path, repo_root):
    (tmp_path / "ploma.yaml").write_text("document: [unclosed\n")
    out = _ctx(tmp_path, repo_root, subagent=True)
    assert "## ploma project" in out and "ploma scripts: " in out


def test_session_start_refreshes_link_and_host_json(onboarded_sample, repo_root, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    session_context.main("{}", plugin_root=repo_root, root=onboarded_sample)
    assert (onboarded_sample / ".ploma/plugin").resolve() == repo_root.resolve()
    assert host.read_host_json(onboarded_sample)["host"] == "codex"


def test_host_block_present_on_codex_absent_on_claude(onboarded_sample, repo_root, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    text = session_context.build_context(onboarded_sample, subagent=False, source="startup", plugin_root=repo_root)
    assert "$ploma:" in text and "agent_type" in text
    monkeypatch.setenv("PLOMA_HOST", "claude")
    assert "## ploma host" not in session_context.build_context(onboarded_sample, subagent=False, source="startup", plugin_root=repo_root)


def test_subagent_context_also_carries_host_block_on_codex(onboarded_sample, repo_root, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    text = _ctx(onboarded_sample, repo_root, subagent=True)
    assert "## ploma host: Codex" in text and "ploma scripts: " in text
    assert text.index("ploma scripts: ") < text.index("## ploma host: Codex")
    monkeypatch.setenv("PLOMA_HOST", "claude")
    assert "## ploma host" not in _ctx(onboarded_sample, repo_root, subagent=True)


def test_onboard_line_is_localized(tmp_path, repo_root):
    (tmp_path / "main.tex").write_text(r"\documentclass{article}")
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(repo_root), CODEX_SESSION_ID="s1")
    env.pop("CLAUDE_PROJECT_DIR", None)
    env.pop("PLOMA_HOST", None)
    r = subprocess.run([sys.executable, str(repo_root / "hooks/session_context.py")],
                       input=json.dumps({"source": "startup", "cwd": str(tmp_path)}),
                       capture_output=True, text=True, cwd=str(tmp_path), env=env, timeout=30)
    assert r.returncode == 0
    out = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "$ploma:onboard" in out and "/ploma:" not in out
    assert not (tmp_path / ".ploma").exists()
