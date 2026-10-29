# ploma Multi-Host Implementation Plan (0.2.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the same ploma repo install and run on Claude Code, OpenAI Codex and Gemini CLI, one host at a time per paper repo, with host-aware onboard and doctor, and ship it as 0.2.0.

**Architecture:** The shared core (skills, scripts, rules, profiles, templates, hook scripts) stays single-source. A host layer (`scripts/host.py`, `scripts/host_adapters.py`, three manifests, `hosts/claude/agents/`) knows the differences. Onboard writes per-host project files that refer to the plugin only through the machine-local symlink `.ploma/plugin`, which the session hook refreshes. One `hooks/hooks.json` carries the events of all three hosts.

**Tech Stack:** Python 3.10+ stdlib, pytest; Claude Code plugin format; Codex CLI 0.155 plugin install (Claude layout); Gemini CLI extension format (`gemini-extension.json`, `commands/*.toml`).

**Spec:** `docs/superpowers/specs/2026-10-29-ploma-multihost-design.md` (amends `2026-10-29-ploma-design.md`).

## Global Constraints

- Everything in the milestone 1 and 2 plans still applies (fail-open hooks; nothing imported beyond `sys`, `os`, `json` before the `ploma.yaml` check; skills under 500 lines; no domain words; no em-dashes; `tests/_banned.py` lint).
- No project file holds an absolute plugin path. The only plugin reference in project files is `.ploma/plugin` (spec §7).
- Onboard and doctor never delete or move another host's files (spec §1, §11).
- `hooks/hooks.json` entries carry no `timeout` field (spec §8).
- Host names appear in skill prose only in the bootstrap line, the onboard and help skills, and the host block templates `rules/host/*.md` (spec §10).
- Version 0.2.0 in `.claude-plugin/plugin.json` and `gemini-extension.json`, pinned equal by a test.
- Field tests on Codex and Claude Code run headless with the recipes in README Testing; no `claude plugin eval` (R166). The controller runs Tasks 1 and 9 inline; they spend model calls on Marc's accounts.

## Review Focus

1. A Codex session started from a shell that exports `CODEX_HOME` while the repo is onboarded for Claude Code: doctor must not FAIL `host_mismatch` on that alone (Task 2 test `test_codex_home_alone_is_not_a_signal`).
2. A user-scope install opened in a repo with no `ploma.yaml`: the session hook must write no `.ploma/` directory (Task 3 test `test_no_state_dir_without_config`).
3. An `AGENTS.md` that already has a hand-written `<!-- ploma-learnings:begin -->` block when onboard re-runs: the block must survive byte for byte (Task 5 test `test_onboard_merge_keeps_learnings_block`).
4. An agent body that contains `"""` or a backslash: the Codex TOML must still parse (Task 4 test `test_codex_toml_escapes_triple_quotes_and_backslashes`).
5. A hook payload from Gemini's `AfterTool` with `tool_name: replace` and a `.tex` path under `tool_input.file_path`: `verify_reminder` must recommend compile exactly as on Claude (Task 3 test `test_after_tool_replace_tex_recommends_compile`).

---

## File structure

```
scripts/host.py                     # new: Host facts, detect, skill_ref, localize, link, host.json, superpowers
scripts/host_adapters.py            # new: render_agents (codex, gemini), build (gemini commands), build-check
scripts/project_files.py            # host-aware render_all, generic marker merge, export blocks, record targets
scripts/receipt.py                  # host field
scripts/doctor.py                   # host group, host-aware project-files group
scripts/_findings.py                # render passes through host.localize
scripts/commit_gate.py, state.py    # messages localized
hooks/_hookutil.py                  # classify_tool
hooks/hooks.json                    # one file, eight events, no matchers, no timeouts
hooks/session_context.py            # link refresh, host.json, host block
hooks/context_monitor.py, verify_reminder.py, log_reminder.py, pre_compact.py   # classify_tool, Gemini payloads
hosts/claude/agents/*.md            # moved from agents/
rules/host/codex.md, rules/host/gemini.md     # eager host blocks (not under rules/eager/)
commands/ploma/<skill>.toml         # generated, 23 files
gemini-extension.json               # new
.claude-plugin/plugin.json          # version, agents path, description
templates/instructions-section.md   # replaces templates/claude-md-section.md
templates/codex-config.toml, templates/gemini-env   # export blocks
skills/*/SKILL.md                   # bootstrap line; onboard, help, learn, deep-audit, brainstorm, commit wording
tests/test_host.py, tests/test_host_adapters.py   # new
tests/test_*.py                     # updated as each task says
README.md, CHANGELOG.md, docs/superpowers/specs/2026-10-29-ploma-design.md (pointers)
```

---

### Task 1: Verifications and housekeeping (controller, inline)

**Files:**
- Delete: `d10dir/main.tex`
- Ledger: record the three results as rulings.

- [ ] **Step 1: Remove the field-test leftover**

```bash
git rm -q d10dir/main.tex && git commit -qm "chore: remove field-test leftover d10dir"
```

- [ ] **Step 2: Claude Code runtime with the shell-default form in a hook command**

Build a probe plugin in the scratchpad: `.claude-plugin/plugin.json` (`name` probe, `hooks` `./hooks/hooks.json`) and a `hooks/hooks.json` whose single SessionStart command is `python3 "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/mark.py"`, where `mark.py` writes the file `<scratchpad>/claude-mark.txt` with `os.environ.get("CLAUDE_PLUGIN_ROOT")`. Run from an empty directory:

```bash
claude -p --plugin-dir <probe> --max-turns 1 "reply with the word ok"
```

Expected: `claude-mark.txt` exists and holds the probe path. If it does not, use the fallback of spec §17.1 (`CLAUDE_PLUGIN_ROOT=${extensionPath} python3 "${CLAUDE_PLUGIN_ROOT}/hooks/x.py"` form) in Task 3 and ledger it.

- [ ] **Step 3: Codex accepts the repo root as a marketplace source**

With `CODEX_HOME` set to the isolated home in the scratchpad (it holds a copy of `auth.json`):

```bash
codex plugin marketplace add /home/mgarnica/papers && codex plugin add ploma@ploma && codex plugin list
```

Expected: `ploma@ploma` listed, installed root printed. No model call. If `source: "./"` is rejected, ledger the accepted form and add it to Task 8's marketplace change.

- [ ] **Step 4: Ledger** the three outcomes under `Task 1`.

---

### Task 2: `scripts/host.py`

**Files:**
- Create: `scripts/host.py`, `tests/test_host.py`

**Interfaces:**
- Produces:
  - `@dataclass(frozen=True) class Host` with fields `name, display, skill_prefix, instructions_file, host_dir, rules_dir: str | None, project_skills_dir, agents_dir: str | None, root_export: str | None, learnings_target, has_subagent_start: bool, settings_suggestion: bool, statusline: bool`, values exactly as the spec §6 table (`unknown` copies `claude` with `name="unknown"`, `display="unknown host"`).
  - `HOSTS: dict[str, Host]` with keys `claude, codex, gemini, unknown`.
  - `detect(env: Mapping[str, str] | None = None, root: Path | None = None) -> Host` (order spec §6; `env` defaults to `os.environ`).
  - `skill_ref(name: str, host: Host | None = None) -> str` and `localize(text: str, host: Host | None = None) -> str` (regex `/ploma:([a-z-]+)`; `host=None` means `detect()`).
  - `LINK = ".ploma/plugin"`, `HOST_JSON = ".ploma/host.json"`.
  - `ensure_plugin_link(root: Path, plugin_root: Path) -> Path`: creates `.ploma/` if needed, replaces a wrong or dangling link, leaves a correct one untouched, raises `OSError` through (callers are fail-open).
  - `write_host_json(root: Path, host: Host, plugin_root: Path, version: str) -> Path` and `read_host_json(root: Path) -> dict | None` (`{"host", "plugin_root", "plugin_version", "written"}`; malformed gives `None`).
  - `host_files(root: Path, cfg: dict | None) -> dict[str, list[str]]`: for every host in `claude, codex, gemini`, the ploma-owned project files present: the instructions file when its ploma span exists, `rules_dir/ploma-*.md`, `agents_dir/ploma-*.toml|md`, `project_skills_dir/analysis-pipeline/SKILL.md`, and the export file when it holds the `# ploma:begin` marker. Uses `project_files.marker_span` for the span check (import inside the function; `project_files` imports `host`, so avoid a module-level cycle).
  - `superpowers_installed(host: Host, home: Path, root: Path) -> bool` (spec §6 paths; Claude reuses `inventory._superpowers(root, home)["enabled"]`).
  - CLI: `python3 scripts/host.py --json [facts|files|superpowers] [--root DIR]`; `facts` is the default and prints the detected host as a dict plus `plugin_link` (the link's target or null).

- [ ] **Step 1: Write the failing tests** in `tests/test_host.py`:

```python
def test_detect_order_codex_wins_over_leaked_claude():
    env = {"CLAUDECODE": "1", "CODEX_SESSION_ID": "x"}
    assert host.detect(env).name == "codex"

def test_codex_home_alone_is_not_a_signal():
    assert host.detect({"CODEX_HOME": "/h/.codex", "CLAUDECODE": "1"}).name == "claude"
    assert host.detect({"CODEX_HOME": "/h/.codex"}).name == "unknown"

def test_codex_hook_env_detected_by_unprefixed_plugin_root():
    assert host.detect({"PLUGIN_ROOT": "/p", "CLAUDE_PLUGIN_ROOT": "/p"}).name == "codex"

def test_gemini_signals_and_ploma_host_override():
    assert host.detect({"GEMINI_SESSION_ID": "g"}).name == "gemini"
    assert host.detect({"PLOMA_HOST": "gemini", "CODEX_VERSION": "1"}).name == "gemini"

def test_host_json_fallback(tmp_path):
    host.write_host_json(tmp_path, host.HOSTS["codex"], Path("/p"), "0.2.0")
    assert host.detect({}, tmp_path).name == "codex"
    (tmp_path / ".ploma" / "host.json").write_text("{", encoding="utf-8")
    assert host.detect({}, tmp_path).name == "unknown"

def test_facts_table_complete():
    for h in host.HOSTS.values():
        for f in dataclasses.fields(host.Host):
            assert getattr(h, f.name) is not None or f.name in ("rules_dir", "agents_dir", "root_export")
    assert host.HOSTS["codex"].skill_prefix == "$ploma:" and host.HOSTS["gemini"].instructions_file == "GEMINI.md"

def test_skill_ref_and_localize():
    c = host.HOSTS["codex"]
    assert host.skill_ref("onboard", c) == "$ploma:onboard"
    assert host.localize("Run /ploma:compile then /ploma:status.", c) == "Run $ploma:compile then $ploma:status."
    assert host.localize("Run /ploma:compile", host.HOSTS["gemini"]) == "Run /ploma:compile"

def test_ensure_plugin_link_creates_replaces_keeps(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"; a.mkdir(); b.mkdir()
    link = host.ensure_plugin_link(tmp_path / "repo", a)
    assert link.resolve() == a.resolve()
    host.ensure_plugin_link(tmp_path / "repo", b)
    assert link.resolve() == b.resolve()
    before = os.lstat(link).st_mtime_ns
    host.ensure_plugin_link(tmp_path / "repo", b)
    assert os.lstat(link).st_mtime_ns == before

def test_host_files_lists_only_present_owned_files(onboarded_sample, cfg):
    files = host.host_files(onboarded_sample, cfg)
    assert "CLAUDE.md" in files["claude"] and ".claude/rules/ploma-manuscript.md" in files["claude"]
    assert files["codex"] == [] and files["gemini"] == []

def test_superpowers_detection_per_host(tmp_path):
    home = tmp_path / "home"; (home / ".agents" / "skills" / "superpowers").mkdir(parents=True)
    assert host.superpowers_installed(host.HOSTS["codex"], home, tmp_path)
    assert host.superpowers_installed(host.HOSTS["gemini"], home, tmp_path)
    assert not host.superpowers_installed(host.HOSTS["claude"], home, tmp_path)

def test_cli_facts_json(tmp_path, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    out = subprocess.run([sys.executable, str(SCRIPTS / "host.py"), "--json", "--root", str(tmp_path)], capture_output=True, text=True, check=True).stdout
    data = json.loads(out); assert data["name"] == "codex" and data["plugin_link"] is None
```

- [ ] **Step 2: Run tests, expect ImportError / failures.** `python3 -m pytest tests/test_host.py -q`
- [ ] **Step 3: Implement `scripts/host.py`** per the Interfaces block. `detect` reads `root/.ploma/host.json` only when `root` is given. `host_files` returns sorted repo-relative POSIX paths.
- [ ] **Step 4: Run tests, expect PASS.**
- [ ] **Step 5: Commit** `feat(host): host detection, facts and plugin link`

---

### Task 3: Hooks on three hosts

**Files:**
- Modify: `hooks/_hookutil.py`, `hooks/hooks.json`, `hooks/session_context.py`, `hooks/context_monitor.py`, `hooks/verify_reminder.py`, `hooks/log_reminder.py`, `hooks/pre_compact.py`
- Create: `rules/host/codex.md`, `rules/host/gemini.md`
- Test: `tests/test_hooks.py`, `tests/test_session_context.py`, `tests/test_rules.py`

**Interfaces:**
- Consumes: `host.detect`, `host.ensure_plugin_link`, `host.write_host_json`, `host.localize` (Task 2); `receipt.plugin_version()`.
- Produces:
  - `_hookutil.classify_tool(name: object) -> str` returning `shell | edit | spawn | other` with the sets of spec §8.
  - `session_context.host_block(host: Host, plugin_root: Path) -> str`: contents of `rules/host/<name>.md` for codex and gemini, `""` for claude and unknown; each file under 900 characters (test).
  - `hooks/hooks.json` shape: events `SessionStart, SubagentStart, PreCompact, PostToolUse, Stop, AfterTool, AfterAgent, PreCompress`; every command `python3 "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/<script>.py[ --subagent]"` (or the Task 1 fallback form); no `matcher`, no `timeout`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_hooks.py` replace `test_hooks_json_wires_all_events` with:

```python
def test_hooks_json_wires_all_hosts(repo_root):
    hooks = json.loads((repo_root / "hooks/hooks.json").read_text())["hooks"]
    assert set(hooks) == {"SessionStart", "SubagentStart", "PreCompact", "PostToolUse", "Stop", "AfterTool", "AfterAgent", "PreCompress"}
    scripts = {e: sorted(h["command"].split("/hooks/")[1].split('"')[0] for g in hooks[e] for h in g["hooks"]) for e in hooks}
    assert scripts["PostToolUse"] == scripts["AfterTool"] == ["context_monitor.py", "verify_reminder.py"]
    assert scripts["Stop"] == scripts["AfterAgent"] == ["log_reminder.py"] and scripts["PreCompact"] == scripts["PreCompress"]
    for g in (g for e in hooks.values() for g in e):
        assert "matcher" not in g
        for h in g["hooks"]:
            assert "timeout" not in h and h["command"].startswith('python3 "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/')

@pytest.mark.parametrize("name,kind", [("Bash", "shell"), ("run_shell_command", "shell"), ("Write", "edit"), ("Edit", "edit"), ("MultiEdit", "edit"), ("apply_patch", "edit"), ("write_file", "edit"), ("replace", "edit"), ("Task", "spawn"), ("Agent", "spawn"), ("collaborationspawn_agent", "spawn"), ("invoke_agent", "spawn"), ("Read", "other"), (None, "other")])
def test_classify_tool(name, kind):
    assert hu.classify_tool(name) == kind

def test_after_tool_replace_tex_recommends_compile(onboarded_sample, capsys):
    payload = {"hook_event_name": "AfterTool", "tool_name": "replace", "cwd": str(onboarded_sample), "tool_input": {"file_path": str(onboarded_sample / "main.tex")}}
    verify_reminder.main(json.dumps(payload), root=onboarded_sample)
    assert "/ploma:compile" in capsys.readouterr().out

def test_context_monitor_counts_gemini_shell_and_ignores_read(onboarded_sample):
    # two run_shell_command calls increment the counter twice; a read_file call does not
    ...

def test_after_agent_drives_log_reminder_like_stop(onboarded_sample, capsys):
    ...

def test_no_state_dir_without_config(tmp_path, repo_root):
    run session_context.py as a subprocess with cwd=tmp_path (no ploma.yaml, one main.tex)
    assert not (tmp_path / ".ploma").exists()
```

In `tests/test_session_context.py`:

```python
def test_session_start_refreshes_link_and_host_json(onboarded_sample, repo_root, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    session_context.main("{}", plugin_root=repo_root, root=onboarded_sample)
    assert (onboarded_sample / ".ploma/plugin").resolve() == repo_root.resolve()
    assert host.read_host_json(onboarded_sample)["host"] == "codex"

def test_host_block_present_for_codex_and_gemini_absent_for_claude(onboarded_sample, repo_root, monkeypatch):
    for name, expected in (("codex", "$ploma:"), ("gemini", "invoke_agent")):
        monkeypatch.setenv("PLOMA_HOST", name)
        assert expected in session_context.build_context(onboarded_sample, subagent=False, source="startup", plugin_root=repo_root)
    monkeypatch.setenv("PLOMA_HOST", "claude")
    assert "## ploma host" not in session_context.build_context(...)

def test_onboard_line_is_localized(tmp_path, repo_root, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex"); (tmp_path / "main.tex").write_text("\\documentclass{article}")
    assert "$ploma:onboard" in <run session_context subprocess with cwd tmp_path>
```

In `tests/test_rules.py` add `test_host_blocks_short_and_outside_eager`: each `rules/host/*.md` under 900 characters; `rules/eager/` has no `host-*` file.

- [ ] **Step 2: Run tests, expect failures.**
- [ ] **Step 3: Implement**
  - `classify_tool` in `_hookutil.py`.
  - `hooks.json` as in Interfaces.
  - `session_context.py`: after `_early_exit_if_no_config` (unchanged), in `build_context`: `hu.add_scripts_path`, `import host`, `h = host.detect(os.environ, root)`; `host.ensure_plugin_link(root, plugin_root)` and `host.write_host_json(root, h, plugin_root, receipt.plugin_version())` inside a `try` that swallows `OSError`; append `host_block(h, plugin_root)` after the status block in the non-subagent branch and after `_plugin_paths` in the subagent branch; `ONBOARD_LINE` emitted through `host.localize` in the no-config path (that path may import nothing heavy: do the `/ploma:` to `$ploma:` rewrite there with a three-line inline check of `CODEX_SESSION_ID|CODEX_THREAD_ID|CODEX_VERSION|PLUGIN_ROOT` in `os.environ`, not by importing `host`).
  - `context_monitor.py`: count only `classify_tool(tool_name) in ("shell", "spawn")`; `verify_reminder.py`: act only on `"edit"`; both exit 0 otherwise. `log_reminder.py` and `pre_compact.py`: accept `AfterAgent` and `PreCompress` event names wherever they check `hook_event_name`.
  - `rules/host/codex.md` and `gemini.md`: the content list of spec §10 (invocation form, arguments rule, subagent dispatch with the agent-name rule, plugin root and export file, hook trust on Codex, the switch rule).
- [ ] **Step 4: Run the full hook tests, expect PASS.** `python3 -m pytest tests/test_hooks.py tests/test_session_context.py tests/test_rules.py -q`
- [ ] **Step 5: Commit** `feat(hooks): one hooks.json for Claude Code, Codex and Gemini`

---

### Task 4: Agents per host, Gemini commands and manifests

**Files:**
- Move: `agents/*.md` to `hosts/claude/agents/*.md` (`git mv`)
- Create: `scripts/host_adapters.py`, `commands/ploma/<skill>.toml` (23), `gemini-extension.json`, `tests/test_host_adapters.py`
- Modify: `.claude-plugin/plugin.json` (`"agents": "./hosts/claude/agents/"`, version `0.2.0`, description per spec §16), `tests/test_agents.py` (`AGENTS_DIR = REPO / "hosts/claude/agents"`, every path), `tests/test_manifest.py`, `tests/test_skills.py` (`test_plugin_paths_exist` must accept `hosts/claude/agents/`)

**Interfaces:**
- Consumes: `host.HOSTS`, `host.LINK`; `profiles._dirs(kind, root)` logic for the venue and discipline file resolution (project `ploma.d/<kind>/<key>.yaml` first, else plugin); `project_files.FileSpec`; `_yamlio.dump_yaml`.
- Produces:
  - `host_adapters.SOURCES = Path(__file__).resolve().parent.parent / "hosts/claude/agents"`.
  - `host_adapters.TOOL_MAP = {"Read": "read_file", "Grep": "grep_search", "Glob": "glob", "Bash": "run_shell_command", "WebFetch": "web_fetch", "WebSearch": "google_web_search"}`.
  - `host_adapters.parse_agent(path: Path) -> tuple[dict, str]` (frontmatter, body; reuse the frontmatter reader in `tests/test_agents.py` logic, moved into the script).
  - `host_adapters.host_context(cfg: dict, root: Path) -> str`: the `## ploma host context` block of spec §9, paths relative to the repo root, venue path `ploma.d/venues/<key>.yaml` when that file exists under `root` else `.ploma/plugin/venues/<key>.yaml`; same for the discipline (`generic` when unset).
  - `host_adapters.render_agents(host: Host, cfg: dict, root: Path) -> list[FileSpec]`: Codex gives `.codex/agents/ploma-<name>.toml` (`name`, `description`, `developer_instructions` as a `"""` basic multi-line string with `\` doubled and `"""` written as `""\"`); Gemini gives `.gemini/agents/ploma-<name>.md` (frontmatter `name`, `description`, `tools` mapped; a source tool with no mapping raises `ValueError` naming it); both `mode="enforced"`, content = host context block, blank line, body. Claude and unknown give `[]`.
  - `host_adapters.render_commands() -> dict[str, str]`: `commands/ploma/<skill>.toml` text per skill: `description = "<frontmatter description>"` (TOML basic string escaping) and `prompt = """Activate the ploma skill named `<skill>` with the activate_skill tool and follow it exactly.\nArguments: {{args}}"""`.
  - CLI: `python3 scripts/host_adapters.py build` writes the commands; `build-check` renders every agent for codex and gemini against `examples/sample-paper` config and every command, exits 1 on any error or on a stale committed command.

- [ ] **Step 1: Write the failing tests** in `tests/test_host_adapters.py`:

```python
def test_sources_are_the_eight_agents():
    assert sorted(p.stem for p in host_adapters.SOURCES.glob("*.md")) == ["claim-verifier", "code-reviewer", "domain-referee", "domain-reviewer", "editor", "methods-referee", "proofreader", "verifier"]

def test_codex_agents_parse_and_carry_body(sample_paper, cfg):
    specs = host_adapters.render_agents(host.HOSTS["codex"], cfg, sample_paper)
    assert [s.path for s in specs][:1] == [".codex/agents/ploma-claim-verifier.toml"] and all(s.mode == "enforced" for s in specs)
    data = _toml(specs[0].content)   # tomllib on 3.11+, else a minimal key = """...""" reader in the test file
    assert data["name"] == "ploma-claim-verifier" and "## Role" in data["developer_instructions"]
    assert "## ploma host context" in data["developer_instructions"] and "/home/" not in specs[0].content

def test_codex_toml_escapes_triple_quotes_and_backslashes(tmp_path):
    body = 'x \\ y """ z'
    text = host_adapters._toml_multiline(body)
    assert _toml("v = " + text)["v"] == body

def test_gemini_agents_map_tools_and_drop_model(sample_paper, cfg):
    spec = next(s for s in host_adapters.render_agents(host.HOSTS["gemini"], cfg, sample_paper) if s.path.endswith("ploma-claim-verifier.md"))
    fm = _frontmatter(spec.content)
    assert fm["name"] == "ploma-claim-verifier" and "model" not in fm
    assert fm["tools"] == ["read_file", "grep_search", "glob", "web_fetch", "google_web_search", "run_shell_command"]

def test_unknown_tool_name_raises(tmp_path, cfg):
    (tmp_path / "x.md").write_text("---\nname: x\ndescription: d\ntools: Read, Teleport\n---\nbody\n")
    with pytest.raises(ValueError, match="Teleport"):
        host_adapters.render_agents(host.HOSTS["gemini"], cfg, tmp_path, sources=tmp_path)

def test_host_context_prefers_project_override(sample_paper, cfg):
    (sample_paper / "ploma.d/venues").mkdir(parents=True); (sample_paper / f"ploma.d/venues/{cfg['venue']['profile']}.yaml").write_text("x: 1\n")
    block = host_adapters.host_context(cfg, sample_paper)
    assert f"ploma.d/venues/{cfg['venue']['profile']}.yaml" in block and "ploma root: .ploma/plugin" in block

def test_claude_renders_nothing(sample_paper, cfg):
    assert host_adapters.render_agents(host.HOSTS["claude"], cfg, sample_paper) == []

def test_gemini_commands_cover_every_skill_and_are_committed(repo_root):
    rendered = host_adapters.render_commands()
    skills = {d.name for d in (repo_root / "skills").iterdir() if d.is_dir() and not d.name.startswith("_")}
    assert set(rendered) == {f"commands/ploma/{s}.toml" for s in skills}
    for rel, text in rendered.items():
        assert (repo_root / rel).read_text() == text, f"{rel} is stale: run scripts/host_adapters.py build"
        assert "{{args}}" in text and "activate_skill" in text

def test_build_check_passes(repo_root):
    assert subprocess.run([sys.executable, "scripts/host_adapters.py", "build-check"], cwd=repo_root).returncode == 0
```

In `tests/test_manifest.py`: version `0.2.0`; `m["agents"] == "./hosts/claude/agents/"`; new `test_gemini_manifest_matches_plugin` (`name == "ploma"`, equal `version`, `settings` names `{"OPENALEX_API_KEY", "SEMANTIC_SCHOLAR_API_KEY", "CROSSREF_MAILTO"}` each with `envVar == name`, the two keys `sensitive: true`); `test_no_root_agents_dir` (`not (repo_root / "agents").exists()`).

- [ ] **Step 2: Run tests, expect failures.**
- [ ] **Step 3: Move the agents, update `plugin.json`, write `host_adapters.py`, run `build`, write `gemini-extension.json`.** Update `tests/test_agents.py` paths (every `REPO / "agents"`), and `tests/test_skills.py::test_plugin_paths_exist` if it resolves `agents/` paths.
- [ ] **Step 4: Run** `python3 -m pytest tests/test_host_adapters.py tests/test_agents.py tests/test_manifest.py tests/test_skills.py -q` and `claude plugin validate .`; expect PASS and "Validation passed".
- [ ] **Step 5: Commit** `feat(hosts): per-host agents, Gemini commands and manifest`

---

### Task 5: Project files per host

**Files:**
- Create: `templates/instructions-section.md`, `templates/codex-config.toml`, `templates/gemini-env`
- Delete: `templates/claude-md-section.md`
- Modify: `scripts/project_files.py`, `scripts/receipt.py`, `tests/test_project_files.py`, `tests/test_receipt.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: `host.Host`, `host.detect`, `host.HOSTS`, `host.read_host_json`; `host_adapters.render_agents`; `receipt.load`.
- Produces:
  - `project_files.marker_span(text, begin=MARKER_BEGIN, end=MARKER_END)` and `project_files.merge_marked(existing: str | None, block: str, begin: str, end: str) -> str` (the current `merge_claude_md` becomes `merge_marked` with the HTML markers; `merge_claude_md` stays as a one-line alias).
  - `LEARNINGS_BEGIN = "<!-- ploma-learnings:begin -->"`, `LEARNINGS_END = "<!-- ploma-learnings:end -->"`, `TOML_BEGIN = "# ploma:begin"`, `TOML_END = "# ploma:end"`.
  - `project_files.export_target(root: Path, host: Host) -> str | None`: Codex `.codex/config.toml`; Gemini `.env` when `root/.env` exists else `.gemini/.env`; else `None`.
  - `project_files.render_all(cfg: dict, root: Path, host: Host | None = None) -> list[FileSpec]` (host `None` means `host.detect(root=root)`), per the spec §11 table. The instructions-file spec is `merged` and its content is `merge_marked(existing, section, MARKER_BEGIN, MARKER_END)`; the section on Codex and Gemini includes the enforced rule bodies (rendered from `templates/rules/*.md` with the frontmatter stripped) under `### Manuscript facts` and `### Pipeline facts`. The export file spec is `merged` with `merge_marked(existing, block, TOML_BEGIN, TOML_END)`; when the existing Codex file contains `[shell_environment_policy]` outside the span, the spec is omitted and `render_all` records it in `project_files.withheld(cfg, root, host) -> list[str]`.
  - `project_files.plan(root, cfg, host=None)` and `apply(root, cfg, plan, host=None)`: unchanged signatures plus `host`; `apply` passes `host.name` to `receipt.write`, and after writing calls `host.ensure_plugin_link(root, Path(os.environ["CLAUDE_PLUGIN_ROOT"]))` when that variable is set, and writes `host.json` when absent.
  - `project_files.switch_notice(root, cfg, host) -> str | None`: when the receipt's host differs from `host.name`, the spec §11 sentence listing the old host's files from `host.host_files`.
  - `receipt.write(root, cfg, files, host: str)` adds `"host"`; `receipt.load` returns `host` defaulting to `"claude"` for older receipts.
  - `record <path>` accepts the detected host's `learnings_target` and `project_skills_dir` paths (currently only the Claude paths).
  - `templates/instructions-section.md` context keys: `host.display`, `host.instructions_file`, `host.rules_sentence`, `skills_line` (the skill list rendered with `host.skill_prefix`), `inline_rules` (empty on Claude).
  - CLI gains `--host <name>` on `plan`, `apply`, `settings`, `files`, overriding detection (field tests and the onboard skill pass it through).

- [ ] **Step 1: Write the failing tests** in `tests/test_project_files.py` (keep the existing ones; `test_claude_md_section_is_short_and_has_the_facts_rule` becomes host-parametrised):

```python
@pytest.mark.parametrize("name,expected", [
    ("claude", {".claude/rules/ploma-manuscript.md": "enforced", "CLAUDE.md": "merged"}),
    ("codex", {".codex/agents/ploma-editor.toml": "enforced", "AGENTS.md": "merged", ".codex/config.toml": "merged"}),
    ("gemini", {".gemini/agents/ploma-editor.md": "enforced", "GEMINI.md": "merged", ".gemini/.env": "merged"})])
def test_render_all_per_host(sample_paper, cfg, name, expected):
    specs = {s.path: s.mode for s in project_files.render_all(cfg, sample_paper, host.HOSTS[name])}
    for path, mode in expected.items():
        assert specs[path] == mode
    assert (".claude/rules/ploma-manuscript.md" in specs) == (name == "claude")
    assert (".agents/skills/analysis-pipeline/SKILL.md" in specs) == False  # pipeline disabled in the sample

def test_codex_section_inlines_rules_and_uses_dollar_prefix(sample_paper, cfg):
    text = next(s.content for s in project_files.render_all(cfg, sample_paper, host.HOSTS["codex"]) if s.path == "AGENTS.md")
    assert "### Manuscript facts" in text and "$ploma:compile" in text and "/ploma:" not in text and "Claude Code" not in text

def test_no_absolute_plugin_paths_in_any_project_file(sample_paper, cfg, repo_root):
    for name in ("codex", "gemini"):
        for s in project_files.render_all(cfg, sample_paper, host.HOSTS[name]):
            assert str(repo_root) not in s.content and ".ploma/plugin" in (s.content if s.path.startswith((".codex/", ".gemini/")) else ".ploma/plugin")

def test_gemini_env_goes_into_existing_dotenv(sample_paper, cfg):
    assert project_files.export_target(sample_paper, host.HOSTS["gemini"]) == ".gemini/.env"
    (sample_paper / ".env").write_text("API=1\n")
    assert project_files.export_target(sample_paper, host.HOSTS["gemini"]) == ".env"
    text = next(s.content for s in project_files.render_all(cfg, sample_paper, host.HOSTS["gemini"]) if s.path == ".env")
    assert text.startswith("API=1\n") and "CLAUDE_PLUGIN_ROOT=.ploma/plugin" in text

def test_codex_config_withheld_when_policy_table_exists(sample_paper, cfg):
    (sample_paper / ".codex").mkdir(); (sample_paper / ".codex/config.toml").write_text("[shell_environment_policy]\ninherit = \"all\"\n")
    paths = [s.path for s in project_files.render_all(cfg, sample_paper, host.HOSTS["codex"])]
    assert ".codex/config.toml" not in paths and project_files.withheld(cfg, sample_paper, host.HOSTS["codex"]) == [".codex/config.toml"]

def test_onboard_merge_keeps_learnings_block(sample_paper, cfg):
    h = host.HOSTS["codex"]
    project_files.apply(sample_paper, cfg, project_files.plan(sample_paper, cfg, h), h)
    p = sample_paper / "AGENTS.md"
    p.write_text(p.read_text() + "\n<!-- ploma-learnings:begin -->\n- keep me\n<!-- ploma-learnings:end -->\n")
    project_files.apply(sample_paper, cfg, project_files.plan(sample_paper, cfg, h), h)
    assert "- keep me" in p.read_text() and p.read_text().count("ploma-learnings:begin") == 1

def test_switch_rewrites_receipt_and_touches_no_old_file(onboarded_sample, cfg):
    before = {p: p.read_bytes() for p in onboarded_sample.rglob("*") if p.is_file() and ".claude" in p.parts or p.name == "CLAUDE.md"}
    h = host.HOSTS["codex"]
    assert "onboarded for Claude Code" in project_files.switch_notice(onboarded_sample, cfg, h)
    project_files.apply(onboarded_sample, cfg, project_files.plan(onboarded_sample, cfg, h), h)
    assert receipt.load(onboarded_sample, cfg)["host"] == "codex"
    assert all(p.read_bytes() == b for p, b in before.items())
    assert not any(e["path"].startswith(".claude/") for e in receipt.load(onboarded_sample, cfg)["files"])

def test_record_accepts_host_learnings_target(sample_paper, cfg, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "gemini")
    ... record "GEMINI.md" succeeds; record ".claude/rules/ploma-learnings.md" is rejected on gemini
```

`tests/test_receipt.py`: `write` stores `host`; `load` of a receipt without `host` gives `"claude"`.
`tests/conftest.py`: `onboarded_sample` passes `host.HOSTS["claude"]` explicitly; add fixture `onboarded_for(name)` factory used by Task 6.

- [ ] **Step 2: Run tests, expect failures.**
- [ ] **Step 3: Implement** per Interfaces. The section template replaces `claude-md-section.md`; `rules_sentence` is "The rules under `.claude/rules/ploma-*.md` are generated from it." on Claude and "The facts below are generated from it." elsewhere. The settings suggestion and statusline rendering are untouched; the onboard skill decides when to show them (Task 7).
- [ ] **Step 4: Run** `python3 -m pytest tests/test_project_files.py tests/test_receipt.py tests/test_inventory.py -q`; expect PASS.
- [ ] **Step 5: Commit** `feat(project-files): per-host project files, exports and switch`

---

### Task 6: Doctor per host

**Files:**
- Modify: `scripts/doctor.py`, `scripts/_findings.py`, `scripts/commit_gate.py`, `scripts/state.py`, `tests/test_doctor.py`, `tests/test_findings.py`

**Interfaces:**
- Consumes: `host.detect`, `host.host_files`, `host.read_host_json`, `host.localize`, `host.superpowers_installed`; `project_files.render_all(cfg, root, host)`, `project_files.export_target`, `project_files.withheld`, `project_files.marker_span`; `receipt.load(...)["host"]`.
- Produces:
  - Group `host` (`GROUPS` gains `("host", "Host")` before `project-files`; `NEEDS_CONFIG` includes it for everything except the `running` INFO): findings `running` (INFO "running under <display>"), `host_match` PASS / `host_mismatch` FAIL (spec §12 wording, remediation through `host.localize`), `other_host_files` INFO, `root_export_missing` WARN, `root_export_manual` WARN, `plugin_link` WARN, `host_unknown` INFO, `agents_md_size` WARN (Codex, instructions file over 28 KiB).
  - `project-files` group reads the active host: `instructions_section` replaces `claude_md`; enforced files are whichever `render_all` gives (rules on Claude, agents elsewhere); on Codex and Gemini the merged section is re-rendered and its span compared (`drift:<file>`); `superpowers` uses `host.superpowers_installed`.
  - `_findings.render` applies `host.localize` to `summary`, `observed` and `remediation`; `commit_gate.NEXT_COMMAND` values and the two `SEMANTIC_*` strings and `state.summary` go through `host.localize` at print time.
  - Verdict: `host_mismatch` is the first finding printed and gives NOT_READY.

- [ ] **Step 1: Write the failing tests** in `tests/test_doctor.py`:

```python
def test_host_mismatch_is_first_and_not_ready(onboarded_sample, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex")
    report = doctor.run(onboarded_sample)
    assert report["verdict"] == "NOT_READY" and report["findings"][0]["id"] == "host_mismatch"
    assert "$ploma:onboard" in report["findings"][0]["remediation"]

def test_host_match_and_other_host_files_info(onboarded_for, monkeypatch):
    root = onboarded_for("codex")          # from a Claude-onboarded copy: both file sets present, receipt says codex
    monkeypatch.setenv("PLOMA_HOST", "codex")
    f = {x["id"]: x for x in doctor.run(root)["findings"]}
    assert f["host_match"]["status"] == "PASS" and f["other_host_files"]["status"] == "INFO" and "CLAUDE.md" in f["other_host_files"]["observed"]

def test_root_export_and_link_warnings(onboarded_for, monkeypatch):
    root = onboarded_for("codex"); monkeypatch.setenv("PLOMA_HOST", "codex")
    (root / ".codex/config.toml").unlink(); shutil.rmtree(root / ".ploma", ignore_errors=True)
    ids = {x["id"]: x["status"] for x in doctor.run(root)["findings"]}
    assert ids["root_export_missing"] == "WARN" and ids["plugin_link"] == "WARN"

def test_inlined_rules_drift_reported_on_codex(onboarded_for, monkeypatch):
    root = onboarded_for("codex"); monkeypatch.setenv("PLOMA_HOST", "codex")
    change ploma.yaml page budget; assert a WARN whose id startswith "drift:AGENTS.md"

def test_codex_ready_on_onboarded_sample(onboarded_for, monkeypatch, tmp_path):
    root = onboarded_for("codex"); monkeypatch.setenv("PLOMA_HOST", "codex")
    point HOME at a tmp home holding .agents/skills/superpowers; create the link
    assert doctor.run(root)["verdict"] == "READY"

def test_remediation_is_localized(onboarded_sample, monkeypatch):
    monkeypatch.setenv("PLOMA_HOST", "codex"); monkeypatch host match
    text = doctor.render(...); assert "/ploma:" not in text
```

`tests/test_findings.py`: `render` with `PLOMA_HOST=codex` rewrites `/ploma:x` in all three fields.

- [ ] **Step 2: Run tests, expect failures.**
- [ ] **Step 3: Implement.** Keep `doctor.run` reading only; the link check uses `os.path.islink` and `os.path.isdir` on `.ploma/plugin`.
- [ ] **Step 4: Run** `python3 -m pytest tests/test_doctor.py tests/test_findings.py tests/test_commit_gate.py tests/test_state.py -q`; expect PASS.
- [ ] **Step 5: Commit** `feat(doctor): host group and host-aware project-files checks`

---

### Task 7: Skills on three hosts

**Files:**
- Modify: every `skills/*/SKILL.md` (bootstrap line); `skills/onboard/SKILL.md`; `skills/help/SKILL.md`; `skills/learn/SKILL.md` and `references/ledger-format.md`; `skills/deep-audit/SKILL.md` and `references/checks.md`; `skills/brainstorm/SKILL.md`; `skills/commit/SKILL.md`; `tests/test_skills.py`

**Interfaces:**
- Consumes: `host.py --json [facts|files|superpowers]`, `project_files.py --host`, `switch_notice` (exposed as `project_files.py --json switch`), `withheld` (in the `plan` JSON as `"withheld": [...]`).
- Produces: the exact bootstrap line of spec §10 as line 1 of every skill body (after the frontmatter, before `# ploma <name>`); `tests/test_skills.py::test_bootstrap_line_present`.

- [ ] **Step 1: Write the failing test**

```python
BOOTSTRAP = "Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over)."

@pytest.mark.parametrize("d", SKILLS, ids=lambda d: d.name)
def test_bootstrap_line_present(d):
    fm, body = read_skill(d / "SKILL.md")
    assert body.lstrip().splitlines()[0] == BOOTSTRAP

def test_skill_text_names_no_claude_paths(d):   # extend test_skill_text_is_generic_and_clean
    text = (d / "SKILL.md").read_text()
    if d.name not in ("onboard", "help"):
        assert ".claude/" not in text and "CLAUDE.md" not in text, d.name
```

- [ ] **Step 2: Run, expect failures.**
- [ ] **Step 3: Edit the skills.** One batch for the bootstrap line (23 files, same insertion). Then:
  - `onboard`: step 0 "Detect the host: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/host.py" --json`; say `Onboarding for <display>`"; the switch notice (`project_files.py --json switch`) printed before the proposal when non-empty; `plan`/`apply` called with `--host <name>`; the settings suggestion and statusline offered only when `settings_suggestion`/`statusline` are true; the `withheld` list printed with the one-line block to merge; the Codex trust sentence of spec §11 after apply; on every host, say that `.ploma/plugin` was created.
  - `help`: three install blocks (Claude Code as today; Codex `codex plugin marketplace add marcgarnica13/ploma` then `codex plugin add ploma@ploma`, then `/hooks` to trust; Gemini `gemini extensions install https://github.com/marcgarnica13/ploma`), the invocation forms, the switch rule.
  - `learn`: promotion target from `host.py --json` (`learnings_target`); on Codex and Gemini write between `LEARNINGS_BEGIN`/`LEARNINGS_END` after the onboard section's end marker; `--skill` drafts under `project_skills_dir`; `ledger-format.md` says "the host's learnings target" with the three paths listed once.
  - `deep-audit` and `checks.md`: "the host's rules and instructions file" with paths taken from `host.py --json files`; the check ids keep their names.
  - `brainstorm`: superpowers detection becomes `host.py --json superpowers`.
  - `commit`: the excluded local files line names `.claude/settings.local.json`, `.codex/config.toml` is not excluded (it is committed), `.env` stays excluded.
- [ ] **Step 4: Run** `python3 -m pytest tests/test_skills.py -q` and `claude plugin validate .`; expect PASS.
- [ ] **Step 5: Commit** `feat(skills): host bootstrap line and host-aware onboard, help, learn, deep-audit`

---

### Task 8: Docs, version and release prep

**Files:**
- Modify: `README.md`, `CHANGELOG.md`, `skills/help/SKILL.md` (status line), `docs/superpowers/specs/2026-10-29-ploma-design.md` (pointer lines at §4, §8, §9, §10, §11), `.claude-plugin/marketplace.json` (description), `tests/test_manifest.py` (already 0.2.0 from Task 4)

- [ ] **Step 1: README**: status "0.2.0, unreleased"; "Install" with three host blocks and the HTTPS note kept under Claude Code; new "Switching hosts" section (spec §1 and §11 in five lines); "Testing" with the three recipes of spec §15; the "What ploma is" paragraph says "a harness for coding agents (Claude Code, Codex, Gemini CLI)".
- [ ] **Step 2: CHANGELOG** `## 0.2.0 (unreleased)` with the spec §16 bullets and a "Gemini CLI: documented, not field-tested" line.
- [ ] **Step 3: Base spec pointers** (one line each: "0.2.0: see the multi-host design, §N").
- [ ] **Step 4: Full run**: `python3 -m pytest -q` (expect all green, count recorded in the ledger) and `claude plugin validate .`.
- [ ] **Step 5: Commit** `docs: multi-host install, switching and testing; 0.2.0 changelog`

---

### Task 9: Codex field test (controller, inline)

- [ ] **Step 1: Install the checkout into the isolated `CODEX_HOME`** (Task 1 Step 3 recipe; `codex plugin remove ploma@ploma` first if present).
- [ ] **Step 2: Prepare a paper**: copy `examples/sample-paper` to the scratchpad, `git init`, and onboard it for Codex without a model call: `PLOMA_HOST=codex CLAUDE_PLUGIN_ROOT=<repo> python3 scripts/project_files.py --json apply --host codex` after `plan`; trust the directory in the isolated `config.toml` (`[projects."<path>"] trust_level = "trusted"`).
- [ ] **Step 3: Run**, each with `codex exec -C <paper> --skip-git-repo-check --dangerously-bypass-hook-trust -s workspace-write`:
  1. `'$ploma:doctor'`: expected verdict READY or READY_WITH_WARNINGS with `host_match` PASS and no `root_export_missing`.
  2. `'$ploma:compile'`: expected a compile report and a gate entry under `quality_reports/verdicts/`.
  3. `'$ploma:status'`: expected the stage line, and `$ploma:` in the printed next step.
  4. `'Spawn the ploma-proofreader agent on main.tex and return its report'`: expected a `SubagentStart` with `agent_type` `ploma-proofreader` in a hook log (add the Task 1 probe logger as a project hook in `.codex/hooks.json` for this run only) and a report that quotes the manuscript.
- [ ] **Step 4: Ledger** each result; any failure becomes a fix round against the owning task.
- [ ] **Step 5**: ping the peer session with the Codex recipe and ask whether Codex is available on the paper host; a traces run is optional.

---

## Self-review

- Spec coverage: §6 Task 2; §7 Tasks 2, 3, 5; §8 Task 3; §9 Task 4; §10 Tasks 3 and 7; §11 Tasks 5 and 7; §12 Task 6; §13 Task 4; §14 Tasks 1, 8, 9; §15 every task's tests plus Tasks 1 and 9; §16 Task 8; §17 items 1 and 3 Task 1, item 2 documented in Task 8.
- Type consistency: `render_all(cfg, root, host)` (Task 5) is what Tasks 4 (through `FileSpec`), 6 and 7 consume; `host.HOSTS[name]` is the only way a test names a host; `receipt.write(..., host)` is called only from `project_files.apply`.
- Review Focus items map to Task 2 (`test_codex_home_alone_is_not_a_signal`), Task 3 (`test_no_state_dir_without_config`, `test_after_tool_replace_tex_recommends_compile`), Task 4 (`test_codex_toml_escapes_triple_quotes_and_backslashes`), Task 5 (`test_onboard_merge_keeps_learnings_block`).
- Proportion: the plan names signatures, values and tests; bodies are left to the implementer except the TOML escaping rule and the detection order, which the tests pin.
