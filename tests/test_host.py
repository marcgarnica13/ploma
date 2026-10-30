"""Tests for host detection, facts and the plugin link (scripts/host.py)."""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

import host

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def test_detect_order_codex_wins_over_leaked_claude():
    assert host.detect({"CLAUDECODE": "1", "CODEX_SESSION_ID": "x"}).name == "codex"

def test_codex_home_alone_is_not_a_signal():
    assert host.detect({"CODEX_HOME": "/h/.codex", "CLAUDECODE": "1"}).name == "claude"
    assert host.detect({"CODEX_HOME": "/h/.codex"}).name == "unknown"

def test_codex_hook_env_detected_by_unprefixed_plugin_root():
    assert host.detect({"PLUGIN_ROOT": "/p", "CLAUDE_PLUGIN_ROOT": "/p"}).name == "codex"
    assert host.detect({"CLAUDE_PLUGIN_ROOT": "/p"}).name == "claude"

def test_ploma_host_override():
    assert host.detect({"PLOMA_HOST": "claude", "CODEX_VERSION": "1"}).name == "claude"
    assert host.detect({"PLOMA_HOST": "nonsense", "CODEX_VERSION": "1"}).name == "codex"

def test_host_json_fallback(tmp_path):
    host.write_host_json(tmp_path, host.HOSTS["codex"], Path("/p"), "0.2.0")
    assert host.detect({}, tmp_path).name == "codex"
    assert host.read_host_json(tmp_path)["plugin_version"] == "0.2.0"
    (tmp_path / ".ploma" / "host.json").write_text("{", encoding="utf-8")
    assert host.detect({}, tmp_path).name == "unknown" and host.read_host_json(tmp_path) is None

def test_facts_table_complete():
    for h in host.HOSTS.values():
        for f in dataclasses.fields(host.Host):
            assert getattr(h, f.name) is not None or f.name in ("rules_dir", "agents_dir", "root_export")
    assert host.HOSTS["codex"].skill_prefix == "$ploma:" and host.HOSTS["codex"].instructions_file == "AGENTS.md"
    assert host.HOSTS["unknown"].instructions_file == "CLAUDE.md"

def test_skill_ref_and_localize():
    c = host.HOSTS["codex"]
    assert host.skill_ref("onboard", c) == "$ploma:onboard"
    assert host.localize("Run /ploma:compile then /ploma:status.", c) == "Run $ploma:compile then $ploma:status."
    assert host.localize("Run /ploma:compile", host.HOSTS["claude"]) == "Run /ploma:compile"

def test_ensure_plugin_link_creates_replaces_keeps(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"; a.mkdir(); b.mkdir()
    link = host.ensure_plugin_link(tmp_path / "repo", a)
    assert link == tmp_path / "repo" / ".ploma" / "plugin" and link.resolve() == a.resolve()
    host.ensure_plugin_link(tmp_path / "repo", b)
    assert link.resolve() == b.resolve()
    before = os.lstat(link).st_mtime_ns
    host.ensure_plugin_link(tmp_path / "repo", b)
    assert os.lstat(link).st_mtime_ns == before

def test_host_files_lists_only_present_owned_files(onboarded_sample, cfg):
    files = host.host_files(onboarded_sample, cfg)
    assert "CLAUDE.md" in files["claude"] and ".claude/rules/ploma-manuscript.md" in files["claude"]
    assert files["codex"] == []

def test_host_files_lists_codex_files_after_codex_onboard(onboarded_for, cfg):
    root = onboarded_for("codex")
    files = host.host_files(root, cfg)
    for rel in ("AGENTS.md", ".codex/config.toml", ".codex/agents/ploma-editor.toml"):
        assert rel in files["codex"], rel
    assert "CLAUDE.md" in files["claude"]

def test_superpowers_detection_per_host(tmp_path):
    home = tmp_path / "home"; (home / ".agents" / "skills" / "superpowers").mkdir(parents=True)
    assert host.superpowers_installed(host.HOSTS["codex"], home, tmp_path)
    assert not host.superpowers_installed(host.HOSTS["claude"], home, tmp_path)

def test_cli_facts_json(tmp_path, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    out = subprocess.run([sys.executable, str(SCRIPTS / "host.py"), "--json", "--root", str(tmp_path)],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out); assert data["name"] == "codex" and data["plugin_link"] is None
