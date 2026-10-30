"""Ported hooks: pre_compact, context_monitor, verify_reminder, log_reminder, plus the silence rule."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import time

import pytest

import _hookutil as hu
import context_monitor
import log_reminder
import pre_compact
import session_context
import verify_reminder

HOOK_FILES = ("session_context", "pre_compact", "context_monitor", "verify_reminder", "log_reminder")
MAINS = (session_context.main, pre_compact.main, context_monitor.main, verify_reminder.main, log_reminder.main)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("PLOMA_PRECOMPACT_BLOCK_ON_DRAFT", "PLOMA_CONTEXT_WINDOW_TOKENS",
                 "PLOMA_CONTEXT_MAX_TOOL_CALLS", "CLAUDE_PROJECT_DIR"):
        monkeypatch.delenv(name, raising=False)


def _payload(root, **kw):
    return json.dumps(dict(cwd=str(root), **kw))


def _plans(root, *items):
    d = root / "quality_reports" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    for i, (name, text) in enumerate(items):
        p = d / name
        p.write_text(text)
        os.utime(p, (1000 + i, 1000 + i))   # later items are newer
    return d


def _logs(root):
    d = root / "quality_reports" / "session_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---------- silence rule ----------

def test_hooks_noop_without_config(tmp_path, capsys):
    payload = _payload(tmp_path, hook_event_name="SessionStart", source="startup",
                       tool_input={"file_path": str(tmp_path / "a.tex")})
    assert session_context.main(payload, argv=[]) == 0
    for main in MAINS[1:]:
        assert main(payload, tmp_path) == 0
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    assert not (tmp_path / ".ploma").exists()


def test_all_hooks_exit_zero_on_garbage_stdin(sample_paper, capsys, monkeypatch):
    monkeypatch.chdir(sample_paper)
    for main in MAINS:
        kwargs = {"argv": []} if main is session_context.main else {}
        assert main(io.StringIO("not json"), **kwargs) == 0
        out = capsys.readouterr().out
        assert out == "" or (out.count("\n") == 1 and isinstance(json.loads(out), dict)), (main.__module__, out)


@pytest.mark.parametrize("name", HOOK_FILES)
def test_script_silent_and_lean_without_config(name, repo_root, tmp_path):
    """Run as a script on a bare dir: exit 0, no output, and ploma_config never imported."""
    probe = (
        "import runpy, sys, atexit\n"
        "atexit.register(lambda: sys.__stderr__.write('LOADED' if 'ploma_config' in sys.modules else ''))\n"
        f"sys.argv = [{str(repo_root / 'hooks' / (name + '.py'))!r}]\n"
        "runpy.run_path(sys.argv[0], run_name='__main__')\n"
    )
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(repo_root))
    env.pop("CLAUDE_PROJECT_DIR", None)
    r = subprocess.run([sys.executable, "-c", probe], input=_payload(tmp_path), capture_output=True,
                       text=True, cwd=str(tmp_path), env=env, timeout=30)
    assert r.returncode == 0 and r.stdout == "" and r.stderr == ""


@pytest.mark.parametrize("name", HOOK_FILES)
def test_import_does_not_load_ploma_config(name, repo_root, tmp_path):
    code = (f"import sys; sys.path.insert(0, {str(repo_root / 'hooks')!r}); import {name}; "
            "print('ploma_config' in sys.modules, 'yaml' in sys.modules, '_yamlio' in sys.modules)")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(tmp_path), timeout=30)
    assert r.returncode == 0 and r.stdout.strip() == "False False False"


def test_scripts_run_with_config(onboarded_sample, repo_root, tmp_path):
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(repo_root))
    for name in HOOK_FILES[1:]:
        r = subprocess.run([sys.executable, str(repo_root / "hooks" / f"{name}.py")],
                           input=_payload(onboarded_sample, tool_input={"file_path": "main.tex"}),
                           capture_output=True, text=True, cwd=str(tmp_path), env=env, timeout=30)
        assert r.returncode == 0, (name, r.stderr)
    assert (onboarded_sample / ".ploma" / "pre-compact-state.json").is_file()


@pytest.mark.parametrize("name,kind", [("Bash", "shell"), ("Write", "edit"), ("Edit", "edit"), ("MultiEdit", "edit"),
    ("apply_patch", "edit"), ("Task", "spawn"), ("Agent", "spawn"), ("collaborationspawn_agent", "spawn"),
    ("collaborationwait_agent", "other"), ("Read", "other"), (None, "other")])
def test_classify_tool(name, kind):
    assert hu.classify_tool(name) == kind


def test_apply_patch_tex_recommends_compile(onboarded_sample, capsys):
    payload = {"hook_event_name": "PostToolUse", "tool_name": "apply_patch", "cwd": str(onboarded_sample),
               "tool_input": {"file_path": str(onboarded_sample / "main.tex")}}
    verify_reminder.main(json.dumps(payload), root=onboarded_sample)
    assert "/ploma:compile" in capsys.readouterr().out


def test_apply_patch_without_file_path_is_silent(onboarded_sample, capsys):
    payload = {"hook_event_name": "PostToolUse", "tool_name": "apply_patch", "cwd": str(onboarded_sample),
               "tool_input": {"command": "*** Begin Patch ..."}}
    assert verify_reminder.main(json.dumps(payload), root=onboarded_sample) == 0 and capsys.readouterr().out == ""


def test_read_tool_is_ignored_by_both_post_tool_hooks(onboarded_sample, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_MAX_TOOL_CALLS", "4")
    cache_path = onboarded_sample / ".ploma" / "context-monitor-cache.json"
    payload = {"hook_event_name": "PostToolUse", "tool_name": "Read", "cwd": str(onboarded_sample),
               "tool_input": {"file_path": str(onboarded_sample / "main.tex")}}
    assert verify_reminder.main(json.dumps(payload), root=onboarded_sample) == 0
    assert capsys.readouterr().out == ""
    assert not (onboarded_sample / ".ploma" / "verify-reminder-cache.json").exists()
    context_monitor.main(_payload(onboarded_sample, tool_name="Bash"), onboarded_sample)
    assert json.loads(cache_path.read_text())["tool_calls"] == 1
    assert context_monitor.main(json.dumps(payload), onboarded_sample) == 0
    assert capsys.readouterr().out == ""
    assert json.loads(cache_path.read_text())["tool_calls"] == 1
    for edit in ("Edit", "apply_patch"):  # edits are not counted by the monitor either
        context_monitor.main(_payload(onboarded_sample, tool_name=edit), onboarded_sample)
    assert json.loads(cache_path.read_text())["tool_calls"] == 1


def test_context_monitor_counts_codex_spawn(onboarded_sample, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_MAX_TOOL_CALLS", "400")
    cache_path = onboarded_sample / ".ploma" / "context-monitor-cache.json"
    context_monitor.main(_payload(onboarded_sample, tool_name="Task"), onboarded_sample)
    assert json.loads(cache_path.read_text())["tool_calls"] == 1
    context_monitor.main(_payload(onboarded_sample, tool_name="collaborationspawn_agent"), onboarded_sample)
    assert json.loads(cache_path.read_text())["tool_calls"] == 2
    context_monitor.main(_payload(onboarded_sample, tool_name="collaborationwait_agent"), onboarded_sample)
    assert json.loads(cache_path.read_text())["tool_calls"] == 2


def test_no_state_dir_without_config(tmp_path, repo_root):
    (tmp_path / "main.tex").write_text(r"\documentclass{article}")
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(repo_root))
    env.pop("CLAUDE_PROJECT_DIR", None)
    r = subprocess.run([sys.executable, str(repo_root / "hooks" / "session_context.py")],
                       input=_payload(tmp_path, hook_event_name="SessionStart", source="startup"),
                       capture_output=True, text=True, cwd=str(tmp_path), env=env, timeout=30)
    assert r.returncode == 0 and "onboard" in r.stdout
    assert not (tmp_path / ".ploma").exists()


def test_hooks_json_wires_all_events(repo_root):
    h = json.loads((repo_root / "hooks/hooks.json").read_text())["hooks"]
    assert set(h) == {"SessionStart", "SubagentStart", "PreCompact", "PostToolUse", "Stop"}
    assert all("matcher" not in e for e in h["PostToolUse"])
    post = [e["hooks"][0]["command"] for e in h["PostToolUse"]]
    assert post[0].endswith('hooks/context_monitor.py"')
    assert post[1].endswith('hooks/verify_reminder.py"')
    assert h["PreCompact"][0]["hooks"][0]["command"].endswith('hooks/pre_compact.py"')
    assert h["Stop"][0]["hooks"][0]["command"].endswith('hooks/log_reminder.py"')
    for entries in h.values():
        for e in entries:
            for hook in e["hooks"]:
                assert hook["command"].startswith('python3 "${CLAUDE_PLUGIN_ROOT}/hooks/')
                assert 0 < hook["timeout"] <= 10
                script = hook["command"].split("/hooks/")[1].split('"')[0]
                assert (repo_root / "hooks" / script).is_file()


# ---------- pre_compact ----------

def test_pre_compact_saves_state(sample_paper, capsys):
    _plans(sample_paper,
           ("a.md", "**Status:** APPROVED\n- [ ] old task\n"),
           ("b.md", "Intro mentions DRAFT and APPROVED in prose.\n**Status:** DRAFT\n- [x] done\n  - [ ] write methods\n"))
    log = _logs(sample_paper) / "2026-10-29_s.md"
    log.write_text("noise\nDecision: drop figure 4\n- Chose: ignored marker\nDecided: keep 8 pages\n")
    assert pre_compact.main(_payload(sample_paper, trigger="manual"), sample_paper) == 0
    st = json.loads((sample_paper / ".ploma" / "pre-compact-state.json").read_text())
    assert st["plan_path"].endswith("b.md") and st["plan_status"] == "draft"
    assert st["current_task"] == "write methods"
    assert st["decisions"] == ["drop figure 4", "keep 8 pages"]
    assert st["trigger"] == "manual"
    captured = capsys.readouterr()
    assert captured.out == "" and "b.md" in captured.err


def test_pre_compact_status_from_line_not_substring(sample_paper):
    _plans(sample_paper, ("p.md", "We keep this APPROVED-looking word.\nStatus: APPROVED\n- [ ] t\n"))
    pre_compact.main(_payload(sample_paper), sample_paper)
    assert json.loads((sample_paper / ".ploma" / "pre-compact-state.json").read_text())["plan_status"] == "unknown"


def test_pre_compact_skips_completed_and_looks_at_three_newest(sample_paper):
    _plans(sample_paper,
           ("old.md", "**Status:** APPROVED\n"),
           ("n3.md", "**Status:** COMPLETED\n"), ("n2.md", "**Status:** COMPLETED\n"),
           ("n1.md", "**Status:** COMPLETED\n"))
    pre_compact.main(_payload(sample_paper), sample_paper)
    assert json.loads((sample_paper / ".ploma" / "pre-compact-state.json").read_text())["plan_path"] is None


def test_pre_compact_never_writes_project_files(sample_paper):
    _plans(sample_paper, ("p.md", "**Status:** DRAFT\n"))
    log = _logs(sample_paper) / "s.md"
    log.write_text("Decision: something long enough\n")
    before = {p: p.read_bytes() for p in sample_paper.rglob("*") if p.is_file()}
    pre_compact.main(_payload(sample_paper), sample_paper)
    after = {p: p.read_bytes() for p in sample_paper.rglob("*") if p.is_file() and ".ploma" not in p.parts}
    assert after == before


def test_pre_compact_blocks_once_per_draft(sample_paper, capsys, monkeypatch):
    _plans(sample_paper, ("p.md", "**Status:** DRAFT\n- [ ] t\n"))
    monkeypatch.setenv("PLOMA_PRECOMPACT_BLOCK_ON_DRAFT", "1")
    pre_compact.main(_payload(sample_paper), sample_paper)
    out = json.loads(capsys.readouterr().out)
    assert out["decision"] == "block" and "p.md" in out["reason"]
    assert (sample_paper / ".ploma" / "precompact-block-sentinel.json").is_file()
    pre_compact.main(_payload(sample_paper), sample_paper)
    assert capsys.readouterr().out == ""


def test_pre_compact_no_block_without_env(sample_paper, capsys):
    _plans(sample_paper, ("p.md", "**Status:** DRAFT\n"))
    pre_compact.main(_payload(sample_paper), sample_paper)
    assert capsys.readouterr().out == ""


# ---------- context_monitor ----------

def _transcript(tmp_path, nbytes):
    p = tmp_path / "t.jsonl"
    p.write_bytes(b"x" * nbytes)
    return str(p)


def test_context_monitor_nudges_at_threshold(sample_paper, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_WINDOW_TOKENS", "1000")
    tr = _transcript(tmp_path, 4 * 420)  # 42 %
    assert context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr), sample_paper) == 0
    out = json.loads(capsys.readouterr().out)
    assert "/ploma:checkpoint" in out["systemMessage"]
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "/ploma:checkpoint" in out["hookSpecificOutput"]["additionalContext"]
    # R148: /ploma:checkpoint is disable-model-invocation; the model suggests it rather than runs it.
    assert "suggest the user run /ploma:checkpoint" in out["hookSpecificOutput"]["additionalContext"]
    assert "opus" not in json.dumps(out).lower() and "sonnet" not in json.dumps(out).lower()
    cache = json.loads((sample_paper / ".ploma" / "context-monitor-cache.json").read_text())
    assert cache["shown_checkpoint"] == [40]


def test_context_monitor_throttle_and_dedupe(sample_paper, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_WINDOW_TOKENS", "1000")
    tr = _transcript(tmp_path, 4 * 420)
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr), sample_paper)
    capsys.readouterr()
    tr = _transcript(tmp_path, 4 * 560)  # 56 %, but within 60 s
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr), sample_paper)
    assert capsys.readouterr().out == ""
    cache_path = sample_paper / ".ploma" / "context-monitor-cache.json"
    cache = json.loads(cache_path.read_text())
    cache["last_check_time"] = time.time() - 61
    cache_path.write_text(json.dumps(cache))
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr), sample_paper)
    assert "/ploma:checkpoint" in capsys.readouterr().out
    cache = json.loads(cache_path.read_text())
    cache["last_check_time"] = 0
    cache_path.write_text(json.dumps(cache))
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr), sample_paper)
    assert capsys.readouterr().out == ""  # 40 and 55 already shown


def test_context_monitor_high_thresholds_not_throttled(sample_paper, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_WINDOW_TOKENS", "1000")
    cache = sample_paper / ".ploma"
    cache.mkdir()
    (cache / "context-monitor-cache.json").write_text(json.dumps(
        {"shown_checkpoint": [40, 55, 65], "last_check_time": time.time()}))
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=_transcript(tmp_path, 4 * 850)), sample_paper)
    assert "soon" in json.loads(capsys.readouterr().out)["systemMessage"]
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=_transcript(tmp_path, 4 * 950)), sample_paper)
    msg = json.loads(capsys.readouterr().out)
    assert "full quality" in msg["systemMessage"] and "/ploma:status" in msg["hookSpecificOutput"]["additionalContext"]
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=_transcript(tmp_path, 4 * 960)), sample_paper)
    assert capsys.readouterr().out == ""


def test_context_monitor_tool_call_fallback(sample_paper, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_MAX_TOOL_CALLS", "4")
    context_monitor.main(_payload(sample_paper, tool_name="Bash"), sample_paper)   # 1 of 4 calls: 25 %, no nudge
    assert capsys.readouterr().out == ""
    context_monitor.main(_payload(sample_paper, tool_name="Bash"), sample_paper)   # 50 % but throttled (within 60 s)
    assert capsys.readouterr().out == ""
    cache_path = sample_paper / ".ploma" / "context-monitor-cache.json"
    cache = json.loads(cache_path.read_text())
    assert cache["tool_calls"] == 2
    cache["last_check_time"] = 0
    cache_path.write_text(json.dumps(cache))
    context_monitor.main(_payload(sample_paper, tool_name="Bash"), sample_paper)   # 75 %
    assert "/ploma:checkpoint" in capsys.readouterr().out


def test_context_monitor_env_defaults(monkeypatch):
    assert context_monitor._env_int("PLOMA_CONTEXT_WINDOW_TOKENS", context_monitor.DEFAULT_CONTEXT_WINDOW_TOKENS) == 1_000_000
    assert context_monitor._env_int("PLOMA_CONTEXT_MAX_TOOL_CALLS", context_monitor.DEFAULT_MAX_TOOL_CALLS) == 400
    monkeypatch.setenv("PLOMA_CONTEXT_MAX_TOOL_CALLS", "-3")
    assert context_monitor._env_int("PLOMA_CONTEXT_MAX_TOOL_CALLS", 400) == 400


# ---------- verify_reminder ----------

def _edit(root, path):
    return _payload(root, tool_name="Edit", tool_input={"file_path": path})


@pytest.mark.parametrize("rel,expected", [
    ("sections/intro.tex", "Run /ploma:compile"),
    ("sections/INTRO.TEX", "Run /ploma:compile"),
    ("refs.bib", "Run /ploma:validate-bib"),
    ("src/run.py", "Run the code reviewer"),
    ("src/Run.PY", "Run the code reviewer"),
])
def test_verify_reminder_maps_suffix(sample_paper, cfg, capsys, rel, expected):
    assert verify_reminder.main(_edit(sample_paper, str(sample_paper / rel)), sample_paper, cfg) == 0
    out = json.loads(capsys.readouterr().out)
    assert expected in out["systemMessage"] and expected in out["hookSpecificOutput"]["additionalContext"]
    assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"


@pytest.mark.parametrize("rel", ["quality_reports/x.tex", ".claude/rules/a.tex", ".ploma/x.bib",
                                 "docs/notes.tex", "notes.md", "data.R", "ploma.yaml", "../outside.tex"])
def test_verify_reminder_skips(sample_paper, cfg, capsys, rel):
    verify_reminder.main(_edit(sample_paper, str(sample_paper / rel)), sample_paper, cfg)
    assert capsys.readouterr().out == ""


def test_verify_reminder_language_from_config(sample_paper, cfg, capsys):
    cfg = dict(cfg, pipeline=dict(cfg["pipeline"], language="r"))
    verify_reminder.main(_edit(sample_paper, "analysis/model.R"), sample_paper, cfg)
    assert "code reviewer" in capsys.readouterr().out
    verify_reminder.main(_edit(sample_paper, "analysis/model.py"), sample_paper, cfg)
    assert capsys.readouterr().out == ""
    off = dict(cfg, pipeline=dict(cfg["pipeline"], enabled=False))
    verify_reminder.main(_edit(sample_paper, "analysis/other.R"), sample_paper, off)
    assert capsys.readouterr().out == ""


def test_verify_reminder_dedupes_for_300s(sample_paper, cfg, capsys):
    path = str(sample_paper / "main.tex")
    verify_reminder.main(_edit(sample_paper, path), sample_paper, cfg)
    assert capsys.readouterr().out
    verify_reminder.main(_edit(sample_paper, "main.tex"), sample_paper, cfg)  # relative form, same file
    assert capsys.readouterr().out == ""
    cache_path = sample_paper / ".ploma" / "verify-reminder-cache.json"
    cache = json.loads(cache_path.read_text())
    cache["main.tex"] = time.time() - 301
    cache_path.write_text(json.dumps(cache))
    verify_reminder.main(_edit(sample_paper, path), sample_paper, cfg)
    assert capsys.readouterr().out


def test_verify_reminder_loads_config_when_not_given(sample_paper, capsys):
    verify_reminder.main(_edit(sample_paper, "main.tex"), sample_paper)
    assert "/ploma:compile" in capsys.readouterr().out


# ---------- log_reminder ----------

def test_log_reminder_no_log_once(sample_paper, cfg, capsys):
    assert log_reminder.main(_payload(sample_paper), sample_paper, cfg) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    msg = json.loads(captured.out)["systemMessage"]       # a Stop hook's stderr is not shown on exit 0
    assert "No session log yet" in msg and "quality_reports/session_logs/" in msg
    log_reminder.main(_payload(sample_paper), sample_paper, cfg)
    assert capsys.readouterr().out == ""


def test_log_reminder_after_threshold(sample_paper, cfg, capsys):
    (_logs(sample_paper) / "s.md").write_text("x")
    for _ in range(log_reminder.THRESHOLD):
        log_reminder.main(_payload(sample_paper), sample_paper, cfg)
    assert capsys.readouterr().out == ""   # first call records mtime, then 49 increments
    log_reminder.main(_payload(sample_paper), sample_paper, cfg)
    captured = capsys.readouterr()
    assert "50 responses without updating s.md" in json.loads(captured.out)["systemMessage"] and captured.err == ""
    log_reminder.main(_payload(sample_paper), sample_paper, cfg)
    assert capsys.readouterr().out == ""


def test_log_reminder_resets_when_log_changes(sample_paper, cfg):
    log = _logs(sample_paper) / "s.md"
    log.write_text("x")
    for _ in range(10):
        log_reminder.main(_payload(sample_paper), sample_paper, cfg)
    os.utime(log, (time.time() + 5, time.time() + 5))
    log_reminder.main(_payload(sample_paper), sample_paper, cfg)
    st = json.loads((sample_paper / ".ploma" / "log-reminder-state.json").read_text())
    assert st["counter"] == 0 and st["reminded"] is False


def test_log_reminder_respects_stop_hook_active(sample_paper, cfg, capsys):
    log_reminder.main(_payload(sample_paper, stop_hook_active=True), sample_paper, cfg)
    assert capsys.readouterr().out == ""
    assert not (sample_paper / ".ploma").exists()


# ---------- fix round 1 ----------

def test_project_dir_found_from_subdirectory(onboarded_sample, repo_root, tmp_path, capsys):
    """R67: cwd a subdirectory of the project, no CLAUDE_PROJECT_DIR: the hooks still find ploma.yaml."""
    sub = onboarded_sample / "sections"
    assert hu.project_dir({"cwd": str(sub)}) == onboarded_sample
    verify_reminder.main(_payload(sub, tool_name="Edit", tool_input={"file_path": str(sub / "intro.tex")}))
    assert "/ploma:compile" in capsys.readouterr().out
    env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(repo_root))
    env.pop("CLAUDE_PROJECT_DIR", None)
    r = subprocess.run([sys.executable, str(repo_root / "hooks/session_context.py")],
                       input=json.dumps({"source": "startup", "cwd": str(sub)}), capture_output=True,
                       text=True, cwd=str(tmp_path), env=env, timeout=30)
    assert r.returncode == 0 and "## ploma status" in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    r = subprocess.run([sys.executable, str(repo_root / "hooks/pre_compact.py")],
                       input=json.dumps({"cwd": str(sub)}), capture_output=True, text=True,
                       cwd=str(tmp_path), env=env, timeout=30)
    assert r.returncode == 0 and (onboarded_sample / ".ploma" / "pre-compact-state.json").is_file()
    assert not (sub / ".ploma").exists()


def test_project_dir_env_first_and_walk_limits(sample_paper, tmp_path, monkeypatch):
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(sample_paper))
    assert hu.project_dir({"cwd": str(other)}) == sample_paper
    monkeypatch.delenv("CLAUDE_PROJECT_DIR")
    deep = sample_paper / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    assert hu.project_dir({"cwd": str(deep)}) == sample_paper           # 4 levels up
    assert hu.project_dir({"cwd": str(deep / "e")}) == deep / "e"       # 5 levels: not found
    (sample_paper / "a" / ".git").mkdir()
    assert hu.project_dir({"cwd": str(deep)}) == deep                   # stops at the .git dir


def test_find_project_dir_identical_in_every_hook(repo_root):
    import ast
    def src(path):
        tree = ast.parse(path.read_text())
        return next(ast.unparse(n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_find_project_dir")
    ref = src(repo_root / "hooks/_hookutil.py")
    for name in HOOK_FILES:
        assert src(repo_root / "hooks" / f"{name}.py") == ref, name


def test_context_monitor_resets_on_new_session(sample_paper, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_WINDOW_TOKENS", "1000")
    tr = _transcript(tmp_path, 4 * 420)
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr, session_id="s1"), sample_paper)
    assert "/ploma:checkpoint" in capsys.readouterr().out
    cache_path = sample_paper / ".ploma" / "context-monitor-cache.json"
    cache = json.loads(cache_path.read_text())
    cache["last_check_time"] = 0
    cache_path.write_text(json.dumps(cache))
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr, session_id="s1"), sample_paper)
    assert capsys.readouterr().out == ""                                # same session: already shown
    context_monitor.main(_payload(sample_paper, tool_name="Bash", transcript_path=tr, session_id="s2"), sample_paper)
    assert "/ploma:checkpoint" in capsys.readouterr().out               # new session: shown again
    assert json.loads(cache_path.read_text())["session_id"] == "s2"


def test_context_monitor_without_session_id_keeps_cache(sample_paper, capsys, monkeypatch):
    monkeypatch.setenv("PLOMA_CONTEXT_MAX_TOOL_CALLS", "100")
    context_monitor.main(_payload(sample_paper, tool_name="Bash", session_id="s1"), sample_paper)
    context_monitor.main(_payload(sample_paper, tool_name="Bash"), sample_paper)
    cache = json.loads((sample_paper / ".ploma" / "context-monitor-cache.json").read_text())
    assert cache["tool_calls"] == 2 and cache["session_id"] == "s1"


def test_log_reminder_resets_on_new_session(sample_paper, cfg, capsys):
    log_reminder.main(_payload(sample_paper, session_id="s1"), sample_paper, cfg)
    assert "No session log yet" in capsys.readouterr().out
    log_reminder.main(_payload(sample_paper, session_id="s1"), sample_paper, cfg)
    assert capsys.readouterr().out == ""
    log_reminder.main(_payload(sample_paper, session_id="s2"), sample_paper, cfg)
    assert "No session log yet" in capsys.readouterr().out
    log = _logs(sample_paper) / "s.md"
    log.write_text("x")
    for _ in range(log_reminder.THRESHOLD + 1):
        log_reminder.main(_payload(sample_paper, session_id="s2"), sample_paper, cfg)
    assert "50 responses" in capsys.readouterr().out
    st = json.loads((sample_paper / ".ploma" / "log-reminder-state.json").read_text())
    assert st["session_id"] == "s2" and st["reminded"] is True
    log_reminder.main(_payload(sample_paper, session_id="s3"), sample_paper, cfg)
    st = json.loads((sample_paper / ".ploma" / "log-reminder-state.json").read_text())
    assert st["session_id"] == "s3" and st["counter"] == 0 and st["reminded"] is False


def test_plan_completed_in_body_but_approved_status(sample_paper, repo_root):
    """R69: status comes from the first **Status:** line, not a substring search for COMPLETED."""
    _plans(sample_paper,
           ("old.md", "**Status:** APPROVED\n- [ ] older\n"),
           ("new.md", "# Plan\n**Status:** APPROVED\nStep 1 COMPLETED yesterday.\n- [x] a\n- [ ] b\n"))
    pre_compact.main(_payload(sample_paper), sample_paper)
    st = json.loads((sample_paper / ".ploma" / "pre-compact-state.json").read_text())
    assert st["plan_path"].endswith("new.md") and st["plan_status"] == "approved" and st["current_task"] == "b"
    ctx = session_context.build_context(sample_paper, subagent=False, source="compact", plugin_root=repo_root)
    assert "plans/new.md (status APPROVED)" in ctx and "Next unchecked item: b" in ctx


def test_plan_with_completed_status_is_skipped_by_both(sample_paper, repo_root):
    _plans(sample_paper, ("old.md", "**Status:** DRAFT\n"), ("new.md", "**Status:** COMPLETED\nall APPROVED\n"))
    pre_compact.main(_payload(sample_paper), sample_paper)
    assert json.loads((sample_paper / ".ploma" / "pre-compact-state.json").read_text())["plan_path"].endswith("old.md")
    ctx = session_context.build_context(sample_paper, subagent=False, source="compact", plugin_root=repo_root)
    assert "plans/old.md (status DRAFT)" in ctx
