# ploma multi-host design: Claude Code and Codex (0.2.0)

Amends `2026-10-29-ploma-design.md` (the base spec). Where this document and the base spec disagree, this document wins for 0.2.0. Section numbers of the base spec are cited as "base §N".

Scope note (2026-10-30, Marc): Gemini CLI was in the first draft of this design and is dropped. The facts gathered about it are kept in the session scratchpad report `gemini-research.md` for a later milestone; nothing in this document or the plan builds for it.

## 1. Intent

ploma is a harness for a paper repo, not for one coding agent. An author picks the agent they work with (Claude Code or OpenAI Codex), installs ploma there, onboards the repo once, and gets the same lifecycle, the same scripts and the same commit gate. One host at a time: the repo is onboarded for the agent in use. Switching agents is an explicit re-onboard on the new host, and the previous host's files stay in place.

Marc's framing (2026-10-29): "this academic harness is meant for a coding agent, no matter which one", and "the user will not switch between agents often; if he decides to switch to Codex he should know that he needs to onboard". Old host files are kept, not deleted.

## 2. Goals, non-goals, anti-goals

Goals

- Install from the same GitHub repo on each host with the host's own install command.
- Every skill, script, profile and the commit gate work on both hosts with the same behaviour.
- Onboard writes the project files the active host reads, and nothing for the other host.
- Doctor says which host the repo is onboarded for and whether that is the host running now.
- Hooks (session context, reminders, pre-compaction snapshot) run on both hosts.
- One source of truth per artifact. A fix to a skill, a script or an agent body lands once.

Non-goals

- A repo onboarded for two hosts at once.
- Gemini CLI or any third host in this milestone.
- Billed eval runs (R166 stands).

Anti-goals

- Two copies of the skills tree, however they are produced.
- Host names scattered through skill prose. Host differences live in one bootstrap line, the eager host block, and the scripts.
- Onboard or doctor deleting or moving another host's files.

## 3. Facts established on 2026-10-29

From the research report `codex-research.md` in the session scratchpad and four headless Codex spikes on Codex CLI 0.155.1 with an isolated `CODEX_HOME`. Verified by spike unless marked docs.

1. A plugin in Claude's layout (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/`, `hooks/hooks.json`) installs with `codex plugin marketplace add <path|owner/repo>` then `codex plugin add <plugin>@<marketplace>`. Skills load as `plugin:skill` and are invoked as `$ploma:<name>`.
2. `hooks/hooks.json` has the same shape, event names and stdin JSON as Claude Code. SessionStart, SubagentStart, PreCompact, PostToolUse and Stop all exist. Unknown event names are ignored. The hook process has `CLAUDE_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `PLUGIN_DATA` and `CODEX_HOME`. Timeouts are in seconds on both hosts.
3. The model's shell does not have `CLAUDE_PLUGIN_ROOT`. A project `.codex/config.toml` with `[shell_environment_policy] set = { CLAUDE_PLUGIN_ROOT = "<value>" }` puts it there (the project must be trusted). A relative value `.ploma/plugin` works: the shell runs from the session directory (the repo root) and a symlink there resolves to the real plugin directory. The shell does have `CODEX_HOME`, `CODEX_SESSION_ID`, `CODEX_THREAD_ID`, `CODEX_VERSION`, `CODEX_CI`. When Codex is launched from inside a Claude Code session the Claude variables leak into that shell too, so Codex signals must be checked before Claude's.
4. PostToolUse `tool_name` is `Bash` for the shell (Codex normalises it), `apply_patch` for edits, `collaborationspawn_agent` and `collaborationwait_agent` for subagents. SubagentStart carries `agent_id` and `agent_type`.
5. Plugin hooks run only after the user trusts them (`/hooks` in the TUI); `codex exec` needs `--dangerously-bypass-hook-trust`. No `--plugin-dir`: a local checkout is installed through a local marketplace add. The installed root is `$CODEX_HOME/plugins/cache/<marketplace>/<plugin>/<version>/`, so it changes on every update.
6. Docs: `$ARGUMENTS` is not substituted in skills; `allowed-tools` and `argument-hint` are ignored; custom agents are TOML files in `<repo>/.codex/agents/` or `~/.codex/agents/` with `name`, `description`, `developer_instructions` and optional `model`; plugins cannot ship agents or prompts; `userConfig` is ignored; `AGENTS.md` is read from the git root down to the cwd, 32 KiB cap per file; `.agents/skills/` is the documented project skills directory.

## 4. Architecture

Three layers in one repo.

- Shared core (unchanged): `skills/`, `scripts/`, `rules/`, `venues/`, `disciplines/`, `templates/`, `schemas/`, `hooks/*.py`, `agents/`. Everything here is host-neutral. The only host-specific text in a skill is one bootstrap line (§10).
- Host layer (new): `scripts/host.py` (detection, facts, paths, plugin link), `scripts/host_adapters.py` (Codex agent rendering).
- Project layer (per host, written by onboard): the instructions-file section, the enforced files, the created-once files, and for Codex the generated agent files and the plugin-root export. §11 has the table.

## 5. Repository layout (delta to base §4)

```
ploma/
  .claude-plugin/plugin.json        # version 0.2.0, description names both hosts
  .claude-plugin/marketplace.json   # unchanged; Codex reads it too
  hooks/hooks.json                  # same events; no tool matchers (§8)
  hooks/*.py                        # tool classification added
  scripts/host.py                   # new
  scripts/host_adapters.py          # new
  rules/host/codex.md               # eager host block for Codex (not under rules/eager/)
  templates/instructions-section.md # replaces claude-md-section.md
  templates/codex-config.toml       # the .codex/config.toml block
  tests/test_host.py, tests/test_host_adapters.py
```

No `.codex-plugin/plugin.json`: Codex accepts the Claude layout, and a second manifest would be a second thing to keep in sync. Revisit if a Codex release stops reading `.claude-plugin/`. `agents/` stays where it is.

`d10dir/main.tex` (a tracked field-test leftover at the repo root) is deleted in the first task.

## 6. Host detection: `scripts/host.py`

`detect(env: Mapping[str, str] | None = None, root: Path | None = None) -> Host` where `Host` is a frozen dataclass with `name` in `{"claude", "codex", "unknown"}` and the facts below. Order:

1. `PLOMA_HOST` when set to a known name (tests and field tests).
2. Codex: any of `CODEX_SESSION_ID`, `CODEX_THREAD_ID`, `CODEX_VERSION` (the model's shell) or `PLUGIN_ROOT` without a `CLAUDE_` prefix (Codex hooks). Never `CODEX_HOME`: users export it in shell profiles, and the field-test recipe sets it, so it would misdetect a Claude session started from that shell.
3. Claude: `CLAUDECODE` or `CLAUDE_CODE_SESSION_ID` or `CLAUDE_PLUGIN_ROOT`.
4. `<root>/.ploma/host.json` when `root` is given and the file parses (written by the session hook, §8).
5. `unknown`.

Codex before Claude because of the leak in fact 3. `unknown` renders like Claude for skill references and never blocks a script.

Facts per host (a table in `host.py`, the single place that knows them):

| fact | claude | codex |
|---|---|---|
| display | Claude Code | Codex |
| skill_ref(name) | `/ploma:<name>` | `$ploma:<name>` |
| instructions_file | `CLAUDE.md` | `AGENTS.md` |
| host_dir | `.claude` | `.codex` |
| rules_dir | `.claude/rules` | none (inlined) |
| project_skills_dir | `.claude/skills` | `.agents/skills` |
| agents_dir | none (plugin ships them) | `.codex/agents` |
| root_export | none | `.codex/config.toml` |
| learnings_target | `.claude/rules/ploma-learnings.md` | `AGENTS.md` learnings block |
| settings_suggestion | yes | no |
| statusline | yes | no |

`host.localize(text) -> str` rewrites every `/ploma:<name>` in a message to the host's form. `_findings.render`, `session_context`, `commit_gate` messages and `state.summary` pass their text through it, so printed advice is right for the running host; JSON output keeps `/ploma:` (skills read it, and the host block gives them the rule).

`host.superpowers_installed(host, home, root) -> bool`: Claude as today (`~/.claude/settings.json` and project settings); Codex `~/.codex/superpowers` or `~/.agents/skills/superpowers*`. Doctor keeps the WARN on both hosts; the brainstorm skill's check reads `host.py --json superpowers` instead of listing Claude paths.

CLI: `python3 scripts/host.py --json [facts|files|superpowers] [--root DIR]`; `facts` (default) prints the detected host and the link target; `files` lists, per host, which ploma-owned project files exist (by path and, for merged files, by marker).

## 7. Plugin root in the model's shell

Every skill runs scripts as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<x>.py"`. That stays. No project file ever holds an absolute plugin path: the Codex root carries the plugin version and every root carries a home directory, so an absolute path committed to a shared paper repo would break on a co-author's machine and drift after every update.

The stable indirection is a symlink, `<repo>/.ploma/plugin`, pointing at the real plugin root. `.ploma/` is machine-local and gitignored already. The session hook refreshes the link on every start (it knows its own root), and onboard creates it from its own `CLAUDE_PLUGIN_ROOT` when the hook has not run (Codex hooks untrusted, first run). Every project file refers to `.ploma/plugin`, relative to the repo root, which is where the hosts run the model's shell (fact 3). Symlinks need no privilege on Linux and macOS, ploma's platforms; Windows is out of scope.

- Claude Code substitutes the token in skill text. The link is still created, so generated text can use one form everywhere.
- Codex: onboard writes `.codex/config.toml` with a marker-delimited block (`# ploma:begin` / `# ploma:end`) holding `[shell_environment_policy]` and `set = { CLAUDE_PLUGIN_ROOT = ".ploma/plugin" }`. The file is machine-neutral and may be committed. If the user's file already has a `[shell_environment_policy]` table outside the markers, onboard does not write the block; it prints the line for the user to merge and doctor reports WARN `root_export_manual`.

After a plugin update the link is refreshed by the next session start, and nothing else changes. When the link is missing or dangling and `ploma.yaml` exists, doctor reports WARN `plugin_link` ("start a new session, or run onboard").

Before the link exists, each SKILL.md carries one bootstrap line (§10) so the first `$ploma:onboard` on Codex can run its scripts.

## 8. Hooks

`hooks/hooks.json` keeps its five events and the `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/<x>.py"` commands. Changes:

- The PostToolUse matchers (`Bash|Task|Agent`, `Write|Edit`) are dropped, because Codex reports edits as `apply_patch` and subagents as `collaborationspawn_agent`. `_hookutil.classify_tool(name) -> {"shell", "edit", "spawn", "other"}` does the filtering: shell = `Bash`; edit = `Write`, `Edit`, `MultiEdit`, `apply_patch`; spawn = `Task`, `Agent`, `collaborationspawn_agent`. Hooks exit at once on `other`. The per-call cost is one Python start, under the 5 s timeout.
- The SessionStart matcher stays.

`session_context.py` additionally, and only when `ploma.yaml` exists (base §11's silence outside paper repos stands, and nothing is imported before that check):

- refreshes the `.ploma/plugin` symlink (§7) and writes `.ploma/host.json` (`host`, `plugin_root`, `plugin_version`, `written`). Host comes from `host.detect` with the hook environment (Codex hooks have unprefixed `PLUGIN_ROOT`; Claude hooks have `CLAUDE_PLUGIN_ROOT` and not that).
- appends the eager host block (§10) on Codex. Claude gets no block.
- localizes the no-config onboard line (`$ploma:onboard` on Codex) with an inline environment check, since that path imports nothing.

## 9. Agents on Codex

Sources stay `agents/<name>.md`, Claude's format. Claude loads them as today.

`host_adapters.render_agents(host, cfg, root) -> list[FileSpec]` produces, for Codex, one project file per agent with mode `enforced`: `.codex/agents/ploma-<name>.toml` with `name = "ploma-<name>"`, `description`, and `developer_instructions` as a TOML basic multi-line string holding a rendered `## ploma host context` block followed by the body verbatim. No `model`: the user's `[agents] default_subagent_model` applies. Backslashes and `"""` in the body are escaped (test).

The host context block holds the lines the Project context block already knows how to use when the hook summary is absent (`ploma root: .ploma/plugin`, `ploma scripts: .ploma/plugin/scripts`, both relative to the repo root), the venue profile path and the discipline card path resolved for this project (project override in `ploma.d/` when present, else under `.ploma/plugin/`), and the line "paths are relative to the repo root; read `ploma.yaml` there". No absolute path, so the files are machine-neutral and committed like the other project files. The SubagentStart hook still adds the live summary; the rendered block is the floor.

Skill prose keeps "Spawn `ploma:editor` (Agent tool, `subagent_type: ploma:editor`)". The host block tells Codex to use `spawn_agent` with `agent_type: ploma-editor` and `fork_turns: "none"`, and states the one-character naming rule (`ploma:editor` on Claude, `ploma-editor` on Codex).

Onboard regenerates the agent files on every run (they are enforced), and doctor reports drift like the rules. `host_adapters.py build-check` renders every agent against the sample paper and fails on any error, so a broken source cannot reach a release.

## 10. Skills on both hosts

Invocation: Claude `/ploma:<name>`; Codex `$ploma:<name>`.

Arguments: skills keep `Arguments: $ARGUMENTS`. The host block says: "Codex does not substitute `$ARGUMENTS`: the arguments are the text after the skill name in the user's message".

Bootstrap line: every SKILL.md gains, right after the frontmatter, the line: `Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).` The skill lint (`tests/test_skills.py`) requires it. On Claude Code the line is harmless.

Skill references in prose (`/ploma:onboard` and the like) stay as written. The host block says "`/ploma:<name>` in ploma text is typed `$ploma:<name>` on Codex". Scripts that print a skill reference call `host.localize`.

The eager host block is `rules/host/codex.md`, rendered into the session context by `session_context.py` on Codex, under 900 characters, counted in the context cap. Content: invocation form, arguments rule, subagent dispatch form and agent-name rule, plugin root and the export file, hook trust note, and the switch rule ("this repo is onboarded for <host>; if that is not this host, run onboard").

Skills whose text names Claude-only paths are reworded host-neutrally with `host.py` output or the phrase "the host's instructions file": onboard, help, commit, learn (promotion target), deep-audit (`references/checks.md`), brainstorm. The `.claude/settings.json` suggestion and the statusline stay Claude-only and are offered only when `host.name == "claude"`.

## 11. Onboard per host (delta to base §8)

Onboard detects the host first (`host.py --json`) and says it in its first line: "Onboarding for Codex". `project_files.render_all(cfg, root, host)` takes the host and renders this table:

| ownership | claude | codex |
|---|---|---|
| enforced | `.claude/rules/ploma-manuscript.md`, `.claude/rules/ploma-pipeline.md` | `.codex/agents/ploma-*.toml` (8) |
| created-once | `<outputs>/README.md`, `learnings.md`, `ploma-state.yaml`; `.claude/skills/analysis-pipeline/SKILL.md` | same outputs files; `.agents/skills/analysis-pipeline/SKILL.md` |
| merged | `CLAUDE.md` section, `.gitignore` | `AGENTS.md` section (rule bodies inlined), `.gitignore`, `.codex/config.toml` block |
| proposed | `.claude/settings.json` additions | none |

The instructions-file section comes from one template, `templates/instructions-section.md`, with a `host` context. On Codex the enforced rule bodies (manuscript, and pipeline when enabled) are rendered inside the section between the ploma markers, because Codex auto-loads no rules directory. Doctor checks the section's size against the 32 KiB cap on Codex (WARN at 28 KiB).

Promoted learnings on Codex: `/ploma:learn --promote` writes them into `AGENTS.md` between a second marker pair, `<!-- ploma-learnings:begin -->` and `<!-- ploma-learnings:end -->`, placed right after the onboard section's end marker. Onboard never touches that span (its merge replaces only its own span), so R103 holds. `project_files.py record` accepts the host's `learnings_target`; merged files are re-merged on every run and never counted as hand-edited.

Enforced rule bodies inlined in the section are checked for drift the same way as rule files: doctor re-renders the section from `ploma.yaml` and compares it with the span on disk (WARN `drift:<file>` with the diff excerpt).

The receipt gains `"host": "<name>"`. That field is what "onboarded for" means. An absorption run on a different host than the receipt's is the switch case:

1. Onboard says: "This repo is onboarded for Claude Code. You are running Codex. Onboard will write the Codex files and leave the Claude Code files in place (<list from host.py files>)."
2. It proceeds as a normal run for the new host. The receipt's `host` becomes the new host; the receipt's file list is replaced by the new host's files, so the old host's files are no longer ploma-owned (doctor stops checking them for drift and lists them as INFO).
3. Nothing is deleted or moved.

Host-specific extras: on Codex, after writing, onboard prints "Codex runs plugin hooks only after you trust them: open /hooks in the Codex TUI and enable ploma's hooks, then restart the session" (doctor cannot check trust). On both hosts, onboard creates or refreshes the `.ploma/plugin` link from `CLAUDE_PLUGIN_ROOT` in its own environment (the bootstrap line supplies it when the hook has not run) and records the host in `.ploma/host.json` when the hook has not written it. Co-authors on Codex run onboard once on their machine; it is an absorption run that creates the link and writes nothing the repo already has.

Legacy-harness detection (base §8 1b) stays Claude-centric and unchanged.

## 12. Doctor (delta to base §9)

New group `host`, before `project-files`:

- INFO `running`: "running under <display>".
- PASS `host_match`: "running under Codex; repo onboarded for Codex".
- FAIL `host_mismatch` when the receipt's host differs from the detected one: "repo is onboarded for Claude Code; you are running Codex: run $ploma:onboard". This is the first finding and the verdict is NOT_READY.
- INFO `other_host_files` listing the other host's ploma files found by `host.py files` (left in place).
- WARN `root_export_missing` (Codex) when the export block is absent; WARN `root_export_manual` when onboard withheld the block (§7); WARN `plugin_link` when `.ploma/plugin` is missing or dangling; WARN `agents_md_size` on Codex when `AGENTS.md` exceeds 28 KiB.
- INFO `host_unknown` when detection gives `unknown`; the rest of doctor runs with Claude's paths.

The `project-files` group checks the active host's files: instructions-file section present (by marker, in the host's file; finding id `instructions_section`, replacing `claude_md`), enforced files match (rules on Claude; agents on Codex), the inlined section unchanged on Codex, receipt present. `superpowers` uses `host.superpowers_installed`.

## 13. Codex specifics

- Install: `codex plugin marketplace add marcgarnica13/ploma` then `codex plugin add ploma@ploma`. The marketplace entry's `source: "./"` is verified in the first task against a local checkout; if Codex rejects a root source, the entry gains a form Codex accepts and the test pins it.
- Hooks trust: README and onboard say it; `codex exec` field tests pass `--dangerously-bypass-hook-trust`.
- API keys: environment variables (`OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CROSSREF_MAILTO`), which the scripts already read when the Claude option variables are absent. README documents a `~/.codex/config.toml` `shell_environment_policy` example for users who want them per machine. ploma never writes secrets into project files.
- `.codex/config.toml` is read only for trusted projects; onboard says so once.

## 14. Scripts, tests, field tests

- `tests/test_host.py`: detection order with the leaked-Claude case and the `CODEX_HOME`-alone case; facts table completeness; `files` listing on fixtures for each host; link creation; `host.json` round trip; `localize`.
- `tests/test_host_adapters.py`: TOML agent rendering (escaping, required keys, parses with `tomllib` on 3.11+ and with a minimal reader on 3.10); host context block; `build-check` passes.
- `tests/test_project_files.py`: `render_all` per host gives exactly the table in §11; the switch case rewrites the receipt and touches no old-host file; the withheld-block case; the learnings block survives a re-onboard; no absolute plugin path in any rendered file.
- `tests/test_doctor.py`: `host_mismatch` is first and gives NOT_READY; `other_host_files` INFO; `root_export_*` and `plugin_link` cases; inlined-rule drift; READY reachable on a Codex-onboarded sample.
- `tests/test_hooks.py`, `tests/test_session_context.py`: `classify_tool` for every name in §8; no `.ploma/` written without config; link and `host.json` written with config; host block present on Codex and absent on Claude; onboard line localized.
- `tests/test_manifest.py`: version 0.2.0; `tests/test_skills.py`: bootstrap line present in every skill and no Claude paths outside onboard and help.
- CI unchanged (pytest 3.10 and 3.12). `claude plugin validate .` locally.
- Field tests, documented in README under Testing: Claude Code as today; Codex with an isolated `CODEX_HOME`, a local marketplace add, and `codex exec -C <paper> --skip-git-repo-check --dangerously-bypass-hook-trust '$ploma:doctor'`. The Codex field test runs in this milestone on the sample paper, and on the traces paper through the peer session when Codex is available there.

## 15. Docs and release

- README: "Install" becomes two blocks (Claude Code, Codex); a "Switching hosts" section; Testing per host; the status line says 0.2.0.
- `skills/help/SKILL.md`: the same two install blocks and the switch rule.
- CHANGELOG 0.2.0: Codex support, the per-host project files, the plugin link, the one hooks change.
- `plugin.json` description: "A harness for writing, validating, reviewing and formatting LaTeX academic papers with a coding agent (Claude Code or Codex)".
- Base spec §4, §8, §9, §10, §11 get a one-line pointer to this document.

## 16. Risks and unverified items

1. Codex marketplace `source: "./"`: verified in the first task.
2. Codex plugin root changes per version: the next session start refreshes the link; a session whose hooks are untrusted falls back to the bootstrap prefix.
3. The 32 KiB `AGENTS.md` cap with inlined rules: doctor warns at 28 KiB; the manuscript rule is well under 4 KiB today.
4. Codex subagents spawned with `agent_type: ploma-<name>` from `.codex/agents/`: docs say role files attach to isolated forks; the field test (Task 9) checks it with a `SubagentStart` log.

## 17. Decisions taken in this design (my calls, open to correction)

1. The plugin keeps Claude's layout and one manifest; Codex reads it as is.
2. Codex agents are project files generated by onboard, not plugin files, because Codex cannot ship agents.
3. Enforced rules are inlined into the Codex instructions section rather than written to a rules directory Codex does not auto-load.
4. `$ARGUMENTS`, `/ploma:` references and `allowed-tools` stay in the skills; the host block explains the differences once. No per-host skill text.
5. Switching hosts is report-and-write, never delete (Marc, 2026-10-29).
6. `unknown` host behaves like Claude Code in rendering and never blocks.
7. The receipt's `host` field defines "onboarded for"; file presence alone does not.
8. Version 0.2.0; `consistency` becoming required is still the 0.1.1 item and is not bundled here.
9. From the builder check (2026-10-29): project files hold only the relative `.ploma/plugin` path, refreshed by the session hook; `host.json` and the link are written only in repos with `ploma.yaml`; promoted learnings get a second marker pair on Codex; `CODEX_HOME` is not a host signal; doctor re-renders the inlined rules for drift; superpowers detection is per host and stays a WARN; the bootstrap line says prefix, not export.
10. Gemini CLI dropped from scope (Marc, 2026-10-30).

## 18. What is left to the builder

- Exact wording of the host block, the bootstrap line placement in skills that start with an `Arguments:` line, and the switch messages.
- The marker-delimited text merge for `.codex/config.toml` (same mechanism as `CLAUDE.md`).
- The 3.10-compatible TOML read used only by tests.
- The exact set of doctor messages and their remediation lines.
- README wording for the two install blocks.
