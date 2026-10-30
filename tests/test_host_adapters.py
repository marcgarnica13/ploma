"""Codex agent rendering (spec section 9): TOML role files, the host context block, build-check."""
from __future__ import annotations

import json
import subprocess
import sys

import host
import host_adapters

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    tomllib = None


def _unescape(s: str) -> str:
    """TOML basic-string escapes are JSON escapes; quote any raw `"` first."""
    out, i = [], 0
    while i < len(s):
        if s[i] == "\\":
            out.append(s[i:i + 2])
            i += 2
            continue
        out.append('\\"' if s[i] == '"' else s[i])
        i += 1
    return json.loads('"' + "".join(out) + '"', strict=False)


def _toml(text: str) -> dict:
    """tomllib on 3.11+; otherwise a minimal reader for `key = "..."` and `key = \"\"\"...\"\"\"`."""
    if tomllib is not None:
        return tomllib.loads(text)
    out, i = {}, 0
    while i < len(text):
        nl = text.find("\n", i)
        line = text[i:] if nl < 0 else text[i:nl]
        if not line.strip():
            i = len(text) if nl < 0 else nl + 1
            continue
        key, rest = line.split(" = ", 1)
        if rest.startswith('"""'):
            start = i + len(key) + 3 + 3
            if text[start] == "\n":
                start += 1
            j = start
            while True:
                j = text.index('"""', j)
                back = 0
                while text[j - 1 - back] == "\\":
                    back += 1
                if back % 2 == 0:
                    while text[j + 3:j + 4] == '"':
                        j += 1
                    break
                j += 1
            out[key] = _unescape(text[start:j])
            i = j + 3
            i = text.find("\n", i) + 1 if text.find("\n", i) >= 0 else len(text)
        else:
            out[key] = json.loads(rest)
            i = len(text) if nl < 0 else nl + 1
    return out


def test_sources_are_the_eight_agents():
    assert sorted(p.stem for p in host_adapters.SOURCES.glob("*.md")) == ["claim-verifier", "code-reviewer", "domain-referee", "domain-reviewer", "editor", "methods-referee", "proofreader", "verifier"]


def test_codex_agents_parse_and_carry_body(sample_paper, cfg, repo_root):
    specs = host_adapters.render_agents(host.HOSTS["codex"], cfg, sample_paper)
    assert [s.path for s in specs][0] == ".codex/agents/ploma-claim-verifier.toml" and all(s.mode == "enforced" for s in specs)
    data = _toml(specs[0].content)
    assert data["name"] == "ploma-claim-verifier" and "## Role" in data["developer_instructions"]
    assert data["developer_instructions"].startswith("## ploma host context") and str(repo_root) not in specs[0].content


def test_codex_toml_escapes_triple_quotes_and_backslashes():
    body = 'x \\ y """ z'
    assert _toml("v = " + host_adapters._toml_multiline(body))["v"] == body


def test_codex_toml_round_trips_awkward_bodies():
    for body in ('"', '""', '"""', '""""', '"""""', 'a\\', 'a\\"""b', '\n\nlead', 'tab\there', 'end"'):
        assert _toml("v = " + host_adapters._toml_multiline(body))["v"] == body, body


def test_codex_description_with_newline_and_quotes_stays_one_line(sample_paper, cfg, tmp_path):
    src = tmp_path / "agents"
    src.mkdir()
    (src / "x.md").write_text('---\nname: x\ndescription: "say \\"hi\\" \\\\ there"\ntools: Read\n---\n\n## Role\nbody\n',
                              encoding="utf-8")
    [spec] = host_adapters.render_agents(host.HOSTS["codex"], cfg, sample_paper, sources=src)
    data = _toml(spec.content)
    assert data["description"] == 'say "hi" \\ there'
    assert spec.content.splitlines()[:2] == ['name = "ploma-x"', 'description = "say \\"hi\\" \\\\ there"']
    assert data["developer_instructions"].endswith("\n\n## Role\nbody\n")


def test_every_codex_agent_parses_with_the_exact_body(sample_paper, cfg):
    specs = host_adapters.render_agents(host.HOSTS["codex"], cfg, sample_paper)
    assert [s.path for s in specs] == sorted(s.path for s in specs) and len(specs) == 8
    for spec in specs:
        name = spec.path.rsplit("ploma-", 1)[1][:-len(".toml")]
        fm, body = host_adapters.parse_agent(host_adapters.SOURCES / f"{name}.md")
        data = _toml(spec.content)
        assert list(data) == ["name", "description", "developer_instructions"]
        assert data["description"] == fm["description"]
        assert data["developer_instructions"] == host_adapters.host_context(cfg, sample_paper) + "\n\n" + body.lstrip("\n")


def test_host_context_prefers_project_override(sample_paper, cfg):
    key = cfg["venue"]["profile"]
    (sample_paper / "ploma.d/venues").mkdir(parents=True); (sample_paper / f"ploma.d/venues/{key}.yaml").write_text("x: 1\n")
    block = host_adapters.host_context(cfg, sample_paper)
    assert f"venue profile: ploma.d/venues/{key}.yaml" in block and "ploma root: .ploma/plugin" in block
    assert "discipline card: .ploma/plugin/disciplines/" in block


def test_host_context_lines_exact(sample_paper, cfg):
    cfg = {**cfg, "document": {**cfg["document"], "discipline": None}}
    key = cfg["venue"]["profile"]
    assert host_adapters.host_context(cfg, sample_paper).splitlines() == [
        "## ploma host context", "", "ploma root: .ploma/plugin", "ploma scripts: .ploma/plugin/scripts",
        f"venue profile: .ploma/plugin/venues/{key}.yaml", "discipline card: .ploma/plugin/disciplines/generic.yaml",
        "Paths are relative to the repo root. Read ploma.yaml there for the project facts."]


def test_claude_renders_nothing(sample_paper, cfg):
    assert host_adapters.render_agents(host.HOSTS["claude"], cfg, sample_paper) == []


def test_build_check_passes(repo_root):
    assert subprocess.run([sys.executable, "scripts/host_adapters.py", "build-check"], cwd=repo_root).returncode == 0


def test_build_check_json_lists_files(repo_root):
    out = subprocess.run([sys.executable, "scripts/host_adapters.py", "--json", "build-check"], cwd=repo_root,
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["ok"] is True and ".codex/agents/ploma-editor.toml" in data["files"]
