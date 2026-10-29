# ploma multi-host design: Claude Code, Codex, Gemini CLI (0.2.0)

Amends `2026-10-29-ploma-design.md` (the base spec). Where this document and the base spec disagree, this document wins for 0.2.0. Section numbers of the base spec are cited as "base §N".

## 1. Intent

ploma is a harness for a paper repo, not for one coding agent. An author picks the agent they work with (Claude Code, OpenAI Codex or Gemini CLI), installs ploma there, onboards the repo once, and gets the same lifecycle, the same scripts and the same commit gate. One host at a time: the repo is onboarded for the agent in use. Switching agents is an explicit re-onboard on the new host, and the previous host's files stay in place.

Marc's framing (2026-10-29): "this academic harness is meant for a coding agent, no matter which one", and "the user will not switch between agents often; if he decides to switch to Codex he should know that he needs to onboard". Old host files are kept, not deleted.

## 2. Goals, non-goals, anti-goals

Goals

- Install from the same GitHub repo on each host with the host's own install command.
- Every skill, script, profile and the commit gate work on every host with the same behaviour.
- Onboard writes the project files the active host reads, and nothing for other hosts.
- Doctor says which host the repo is onboarded for and whether that is the host running now.
- Hooks (session context, reminders, pre-compaction snapshot) run wherever the host has the event; they stay silent where it does not.
- One source of truth per artifact. A fix to a skill, a script or an agent body lands once.

Non-goals

- A repo onboarded for two hosts at once.
- Feature parity for hooks and subagent context on hosts that lack the event.
- A Gemini field test in this milestone: Gemini CLI is not installed on the development machine, and its docs say the product was replaced by Antigravity CLI for free tiers on 2026-06-18. Gemini gets the unit tests, a build-time check of its generated files, and a documented manual field test.
- Billed eval runs (R166 stands).

Anti-goals

- Three copies of the skills tree, one per host, however they are produced.
- Host names scattered through skill prose. Host differences live in one shared note, the eager host block, and the scripts.
- Onboard or doctor deleting or moving another host's files.

## 3. Facts established on 2026-10-29

From the research reports in the session scratchpad (Codex: `codex-research.md`; Gemini: `gemini-research.md`) and three headless Codex spikes run on Codex CLI 0.155.1 with an isolated `CODEX_HOME`.

Codex (verified by spike unless marked docs)

1. A plugin in Claude's layout (`.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `skills/`, `hooks/hooks.json`) installs with `codex plugin marketplace add <path|owner/repo>` then `codex plugin add <plugin>@<marketplace>`. Skills load as `plugin:skill` and are invoked as `$ploma:<name>`.
2. `hooks/hooks.json` has the same shape, event names and stdin JSON as Claude Code. SessionStart, SubagentStart, PreCompact, PostToolUse and Stop all exist. Unknown event names in the file are ignored. The hook process has `CLAUDE_PLUGIN_ROOT`, `PLUGIN_ROOT`, `CLAUDE_PLUGIN_DATA`, `PLUGIN_DATA` and `CODEX_HOME`. A command written as `python3 "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/x.py"` runs.
3. The model's shell does not have `CLAUDE_PLUGIN_ROOT`. A project `.codex/config.toml` with `[shell_environment_policy] set = { CLAUDE_PLUGIN_ROOT = "<root>" }` puts it there (the project must be trusted). The shell does have `CODEX_HOME`, `CODEX_SESSION_ID`, `CODEX_THREAD_ID`, `CODEX_VERSION`, `CODEX_CI`. When Codex is launched from inside a Claude Code session the Claude variables leak into that shell too, so Codex signals must be checked before Claude's.
4. PostToolUse `tool_name` is `Bash` for the shell (Codex normalises it), `apply_patch` for edits, `collaborationspawn_agent` and `collaborationwait_agent` for subagents. SubagentStart carries `agent_id` and `agent_type`.
5. Plugin hooks run only after the user trusts them (`/hooks` in the TUI); `codex exec` needs `--dangerously-bypass-hook-trust`. No `--plugin-dir`: a local checkout is installed through a local marketplace add. The installed root is `$CODEX_HOME/plugins/cache/<marketplace>/<plugin>/<version>/`, so it changes on every update.
6. Docs: `$ARGUMENTS` is not substituted in skills; `allowed-tools` and `argument-hint` are ignored; custom agents are TOML files in `<repo>/.codex/agents/` or `~/.codex/agents/` with `name`, `description`, `developer_instructions` and optional `model`; plugins cannot ship agents or prompts; `userConfig` is ignored; `AGENTS.md` is read from the git root down to the cwd, 32 KiB cap per file; `.agents/skills/` is a skills directory shared with Gemini.

Gemini CLI (docs only, extension reference dated 2026-05-14, hooks reference 2026-04-10)

7. An extension is a git repo with `gemini-extension.json` at its root (`name`, `version`, `description`, `contextFileName`, `mcpServers`, `excludeTools`, `settings[]` with `name`, `description`, `envVar`, `sensitive`). It may hold `commands/`, `hooks/hooks.json`, `skills/`, `agents/` (preview) and `GEMINI.md`. Install: `gemini extensions install <git url>`; `gemini extensions link <path>` for a checkout; no release needed. Installed at `~/.gemini/extensions/<name>`.
8. `commands/ploma/<name>.toml` gives `/ploma:<name>`; fields `prompt`, `description`; `{{args}}` is the text after the command. Skills are model-activated (`activate_skill`), with no slash invocation and no arguments; only `name` and `description` are honoured.
9. Hook events: SessionStart, SessionEnd, BeforeAgent, AfterAgent, BeforeModel, AfterModel, BeforeToolSelection, BeforeTool, AfterTool, PreCompress, Notification. No SubagentStart. Stdin carries `session_id`, `transcript_path`, `cwd`, `hook_event_name`, plus `tool_name`, `tool_input`, `tool_response` for tool events and `stop_hook_active` for AfterAgent. Stdout contract is the same JSON (`hookSpecificOutput.additionalContext`). `${extensionPath}` is substituted in `hooks/hooks.json`. Tool names: `run_shell_command`, `write_file`, `replace`, `read_file`, `grep_search`, `glob`, `web_fetch`, `google_web_search`, `invoke_agent`.
10. Subagents: `agents/*.md` in the extension or `.gemini/agents/*.md` in the project, frontmatter `name`, `description`, `tools`, `model`, `temperature`, `max_turns`, `timeout_mins`; body is the system prompt; invoked by description or `@name`.
11. Context file `GEMINI.md`, hierarchical. `.env` files are loaded from the cwd upwards and from the extension directory.

Claude Code

12. `claude plugin validate` accepts a `hooks/hooks.json` that contains the Gemini event names and the `${CLAUDE_PLUGIN_ROOT:-${extensionPath}}` form (verified locally). Whether the runtime still substitutes and runs that form is verified in the plan's first task with one headless run.

## 4. Architecture

Three layers in one repo.

- Shared core (unchanged): `skills/`, `scripts/`, `rules/`, `venues/`, `disciplines/`, `templates/`, `schemas/`, `hooks/*.py`. Everything here is host-neutral. The only host-specific text in a skill is one bootstrap line (§10).
- Host layer (new): `scripts/host.py` (detection, facts, paths), `scripts/host_adapters.py` (rendering of agents and commands per host), the three manifests, and `hosts/claude/agents/` (the agent sources, in Claude's format because Claude reads it natively).
- Project layer (per host, written by onboard): the instructions-file section, the enforced files, the created-once files, and for Codex and Gemini the generated agent files and the plugin-root export. §11 has the table.

The plugin root problem is solved per host (§7), hooks ship as one file (§8), agents are generated per host (§9), and skills stay single-source (§10).

## 5. Repository layout (delta to base §4)

```
ploma/
  .claude-plugin/plugin.json        # version 0.2.0; "agents": "./hosts/claude/agents/"
  .claude-plugin/marketplace.json   # unchanged; Codex reads it too
  gemini-extension.json             # new
  commands/ploma/<skill>.toml       # new, generated, 23 files, committed
  hooks/hooks.json                  # one file, all three hosts (§8)
  hooks/*.py                        # unchanged scripts, tool classification added
  hosts/claude/agents/<name>.md     # moved from agents/; the agent sources
  scripts/host.py                   # new
  scripts/host_adapters.py          # new
  templates/instructions-section.md # replaces claude-md-section.md
  templates/codex-config.toml       # new: the .codex/config.toml block
  templates/gemini-env              # new: the .gemini/.env block
  tests/test_host.py, tests/test_host_adapters.py
```

`agents/` at the repo root is removed. Gemini loads every `agents/*.md` of an extension as a Gemini agent and would choke on Claude's `tools:` names and `model: opus`; keeping the sources out of that path removes the risk without a per-host copy. No `.codex-plugin/plugin.json`: Codex accepts the Claude layout, and a second manifest would be a second thing to keep in sync. Revisit if a Codex release stops reading `.claude-plugin/`.

`d10dir/main.tex` (a tracked field-test leftover at the repo root) is deleted in the first task.

## 6. Host detection: `scripts/host.py`

`detect(env: Mapping[str, str] | None = None, root: Path | None = None) -> Host` where `Host` is a frozen dataclass with `name` in `{"claude", "codex", "gemini", "unknown"}` and the facts below. Order:

1. `PLOMA_HOST` when set to a known name (tests and field tests).
2. Codex: any of `CODEX_SESSION_ID`, `CODEX_THREAD_ID`, `CODEX_VERSION` (the model's shell) or `PLUGIN_ROOT` without a `CLAUDE_` prefix (Codex hooks). Never `CODEX_HOME`: users export it in shell profiles, and the field-test recipe sets it, so it would misdetect a Claude or Gemini session started from that shell.
3. Gemini: any of `GEMINI_SESSION_ID`, `GEMINI_CLI`, `GEMINI_PROJECT_DIR`, `GEMINI_CWD`.
4. Claude: `CLAUDECODE` or `CLAUDE_CODE_SESSION_ID` or `CLAUDE_PLUGIN_ROOT`.
5. `<root>/.ploma/host.json` when `root` is given and the file parses (written by the session hook, §8).
6. `unknown`.

Codex and Gemini before Claude because of the leak in fact 3. `unknown` renders like Claude for skill references and never blocks a script.

`host.localize(text) -> str` rewrites every `/ploma:<name>` in a message to the host's form. `_findings.render`, `session_context`, `commit_gate` messages and `state.summary` pass their text through it, so printed advice is right for the running host; JSON output keeps `/ploma:` (skills read it, and the host block gives them the rule).

`host.superpowers_installed(home: Path) -> bool` checks the host's install locations: Claude as today (`~/.claude/settings.json` and project settings); Codex `~/.codex/superpowers` or `~/.agents/skills/superpowers*`; Gemini `~/.gemini/extensions/superpowers` or `~/.agents/skills/superpowers*`. Doctor keeps the WARN on every host; the brainstorm skill's check reads `host.py --json` instead of listing Claude paths.

Facts per host (a table in `host.py`, the single place that knows them):

| fact | claude | codex | gemini |
|---|---|---|---|
| display | Claude Code | Codex | Gemini CLI |
| skill_ref(name) | `/ploma:<name>` | `$ploma:<name>` | `/ploma:<name>` |
| instructions_file | `CLAUDE.md` | `AGENTS.md` | `GEMINI.md` |
| host_dir | `.claude` | `.codex` | `.gemini` |
| rules_dir | `.claude/rules` | none (inlined) | none (inlined) |
| project_skills_dir | `.claude/skills` | `.agents/skills` | `.agents/skills` |
| agents_dir | none (plugin ships them) | `.codex/agents` | `.gemini/agents` |
| root_export | none | `.codex/config.toml` | `.gemini/.env` |
| learnings_target | `.claude/rules/ploma-learnings.md` | `AGENTS.md` learnings block | `GEMINI.md` learnings block |
| has_subagent_start | yes | yes | no |
| settings_suggestion | yes | no | no |
| statusline | yes | no | no |

CLI: `python3 scripts/host.py --json` prints the detected host and its facts; `python3 scripts/host.py --json files` lists, per host, which ploma-owned project files exist in the repo (by path and, for merged files, by marker). Doctor and onboard use the latter.

## 7. Plugin root in the model's shell

Every skill runs scripts as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<x>.py"`. That stays. No project file ever holds an absolute plugin path: the Codex root carries the plugin version and every root carries a home directory, so an absolute path committed to a shared paper repo would break on a co-author's machine and drift after every update.

The stable indirection is a symlink, `<repo>/.ploma/plugin`, pointing at the real plugin root. `.ploma/` is machine-local and gitignored already. The session hook refreshes the link on every start (it knows its own root), and onboard creates it from its own `CLAUDE_PLUGIN_ROOT` when the hook has not run (Codex hooks untrusted, first run). Every project file refers to `.ploma/plugin`, relative to the repo root, which is where the hosts run the model's shell (verified on Codex: `pwd` is the session directory and a relative `CLAUDE_PLUGIN_ROOT=.ploma/plugin` resolves through the link). Symlinks need no privilege on Linux and macOS, ploma's platforms; Windows is out of scope.

Per host:

- Claude Code substitutes the token in skill text. The link is still created, so generated text can use one form everywhere.
- Codex: onboard writes `.codex/config.toml` with a marker-delimited block (`# ploma:begin` / `# ploma:end`) holding `[shell_environment_policy]` and `set = { CLAUDE_PLUGIN_ROOT = ".ploma/plugin" }`. The file is machine-neutral and may be committed. If the user's file already has a `[shell_environment_policy]` table outside the markers, onboard does not write the block; it prints the line for the user to merge and doctor reports WARN `root_export_manual`.
- Gemini: the block is `CLAUDE_PLUGIN_ROOT=.ploma/plugin` between `# ploma:begin` and `# ploma:end` lines. Gemini loads only the first `.env` it finds and looks at `.gemini/.env` before the repo's `.env`, so a new `.gemini/.env` would hide a project `.env` holding keys or pipeline variables. Rule: when `<repo>/.env` exists, the block is merged into it; otherwise it goes to `.gemini/.env`. Whether Gemini's shell tool inherits the file is a manual field-test item (§17).

After a plugin update the link is refreshed by the next session start, and nothing else changes. When the link is missing or dangling and `ploma.yaml` exists, doctor reports WARN `plugin_link` ("start a new session, or run onboard").

Before the link exists, each SKILL.md carries one bootstrap line (§10) so the first `$ploma:onboard` on Codex or Gemini can run its scripts.

## 8. Hooks: one `hooks/hooks.json` for three hosts

Commands use `python3 "${CLAUDE_PLUGIN_ROOT:-${extensionPath}}/hooks/<x>.py"`. Claude and Codex have the variable in the hook environment; Gemini substitutes `${extensionPath}` and the shell default takes it. Events in the file:

| event | hosts | script | matcher |
|---|---|---|---|
| SessionStart | all | `session_context.py` | none (the script reads `source`) |
| SubagentStart | claude, codex | `session_context.py --subagent` | none |
| PreCompact | claude, codex | `pre_compact.py` | none |
| PostToolUse | claude, codex | `context_monitor.py`, `verify_reminder.py` | none (scripts classify) |
| Stop | claude, codex | `log_reminder.py` | none |
| AfterTool | gemini | `context_monitor.py`, `verify_reminder.py` | none |
| AfterAgent | gemini | `log_reminder.py` | none |
| PreCompress | gemini | `pre_compact.py` | none |

The SessionStart matcher `startup|resume|clear|compact` is dropped: Gemini matches lifecycle matchers as exact strings, and the script already branches on `source`. Matchers on tool events are dropped for the same reason and because tool names differ per host; `_hookutil.classify_tool(name) -> {"shell", "edit", "spawn", "other"}` does the filtering: shell = `Bash`, `run_shell_command`; edit = `Write`, `Edit`, `MultiEdit`, `apply_patch`, `write_file`, `replace`; spawn = `Task`, `Agent`, `collaborationspawn_agent`, `invoke_agent`. Hooks exit at once on `other`. The per-call cost is one Python start.

The `timeout` field is dropped from every entry: Claude and Codex read it in seconds, Gemini in milliseconds, so no one value fits. The defaults (60 s on Claude and Gemini, 600 s on Codex) are far above what fail-open hooks that finish in well under a second need.

`session_context.py` additionally, and only when `ploma.yaml` exists (base §11's silence outside paper repos stands, and nothing is imported before that check):

- refreshes the `.ploma/plugin` symlink (§7) and writes `.ploma/host.json` (`host`, `plugin_root`, `plugin_version`, `written`). Host comes from `host.detect` with the hook environment (Codex hooks have unprefixed `PLUGIN_ROOT`; Gemini hooks have `GEMINI_PROJECT_DIR`; Claude hooks have `CLAUDE_PLUGIN_ROOT` and none of the others).
- appends an eager host block (§10) for Codex and Gemini. Claude gets no block.

`pre_compact.py` on Gemini (PreCompress) cannot inject context; it still writes its snapshot under `.ploma/`, which the next SessionStart reads. `--subagent` context on Gemini is replaced by the rendered Project context in the generated agents (§9).

Stdin field differences are tolerated by `read_input` already (missing keys give defaults); the AfterAgent payload has `stop_hook_active`, which `log_reminder.py` reads the same way.

## 9. Agents per host

Sources: `hosts/claude/agents/<name>.md`, Claude's format (frontmatter `name`, `description`, `tools`, `model`; body). Claude loads them from the path in `plugin.json`.

`host_adapters.render_agents(host, cfg, plugin_root) -> list[FileSpec]` produces, for Codex and Gemini, one project file per agent with mode `enforced`:

- Codex: `.codex/agents/ploma-<name>.toml` with `name = "ploma-<name>"`, `description`, and `developer_instructions` as a TOML multi-line literal string holding the body. No `model`: the user's `[agents] default_subagent_model` applies. Body text that contains `'''` is escaped by the renderer (test).
- Gemini: `.gemini/agents/ploma-<name>.md` with frontmatter `name: ploma-<name>`, `description`, `tools` mapped through `host_adapters.TOOL_MAP` (`Read` to `read_file`, `Grep` to `grep_search`, `Glob` to `glob`, `Bash` to `run_shell_command`, `WebFetch` to `web_fetch`, `WebSearch` to `google_web_search`), no `model`.

In both, the body is kept verbatim and a rendered `## ploma host context` block is prepended before it. The block holds the lines the Project context block already knows how to use when the hook summary is absent (`ploma root: .ploma/plugin`, `ploma scripts: .ploma/plugin/scripts`, both relative to the repo root), plus the venue profile path and the discipline card path resolved for this project (project override in `ploma.d/` when present, else under `.ploma/plugin/`), and the line "paths are relative to the repo root; read `ploma.yaml` there". No absolute path, so the files are machine-neutral and committed like the other project files. On Codex the SubagentStart hook still adds the live summary; the rendered block is the floor, not a duplicate.

Skill prose keeps "Spawn `ploma:editor` (Agent tool, `subagent_type: ploma:editor`)". The eager host block (§10) tells Codex to use `spawn_agent` with `agent_type: ploma-editor` and `fork_turns: "none"`, and Gemini to use `invoke_agent` with `agent_name: ploma-editor`. Agent names differ by one character across hosts (`ploma:editor` vs `ploma-editor`); the host block states the rule once.

Onboard regenerates the agent files on every run (they are enforced), and doctor reports drift like the rules. `host_adapters.py build-check` is a test-time command that renders every agent and command and fails on any error, so a broken source cannot reach a release.

## 10. Skills on three hosts

Invocation: Claude `/ploma:<name>`; Codex `$ploma:<name>`; Gemini `/ploma:<name>` through `commands/ploma/<name>.toml`, whose prompt is: "Activate the ploma skill named `<name>` with the activate_skill tool and follow it. Arguments: {{args}}" and whose `description` is the skill's. Generated by `host_adapters.py build` from the skill frontmatter; `tests/test_host_adapters.py` fails when a committed command is stale or a skill lacks one.

Arguments: skills keep `Arguments: $ARGUMENTS`. The host block says: "This host does not substitute `$ARGUMENTS`: the arguments are the text after the skill name in the user's message (on Gemini, the text the command passes)".

Bootstrap line: every SKILL.md gains, right after the frontmatter, the line: `Plugin root: if your shell lacks CLAUDE_PLUGIN_ROOT, prefix every command below with CLAUDE_PLUGIN_ROOT=<the directory two levels above this SKILL.md> (each shell call is a new process; an export does not carry over).` The skill lint (`tests/test_skills.py`) requires it. On Claude Code the line is harmless.

Skill references in prose (`/ploma:onboard` and the like, hundreds of them) stay as written. The host block says "`/ploma:<name>` in ploma text is typed `$ploma:<name>` on Codex". Scripts that print a skill reference (doctor remediation, state next, gate, onboard verdicts) call `host.skill_ref(name)` so printed advice is right for the running host.

The eager host block is rendered by `session_context.py` from `rules/eager/host-<name>.md` templates (Codex, Gemini; none for Claude), under 900 characters each, counted in the context cap. Content: invocation form, arguments rule, subagent dispatch form and agent-name rule, plugin root and the export file, hook trust note (Codex), and the switch rule ("this repo is onboarded for <host>; if that is not this host, run onboard").

Skills whose text names Claude-only paths are reworded host-neutrally with `host.py` output or the phrase "the host's instructions file": onboard, help, commit, learn (promotion target), deep-audit (`references/checks.md`), brainstorm. The host-specific `.claude/settings.json` suggestion and the statusline stay Claude-only and are offered only when `host.name == "claude"`.

## 11. Onboard per host (delta to base §8)

Onboard detects the host first (`host.py --json`) and says it in its first line: "Onboarding for Codex". `project_files.render_all(cfg, root, host)` takes the host and renders this table:

| ownership | claude | codex | gemini |
|---|---|---|---|
| enforced | `.claude/rules/ploma-manuscript.md`, `.claude/rules/ploma-pipeline.md` | `.codex/agents/ploma-*.toml` (8) | `.gemini/agents/ploma-*.md` (8) |
| created-once | `<outputs>/README.md`, `learnings.md`, `ploma-state.yaml`; `.claude/skills/analysis-pipeline/SKILL.md` | same outputs files; `.agents/skills/analysis-pipeline/SKILL.md` | same outputs files; `.agents/skills/analysis-pipeline/SKILL.md` |
| merged | `CLAUDE.md` section, `.gitignore` | `AGENTS.md` section (rule bodies inlined), `.gitignore`, `.codex/config.toml` block | `GEMINI.md` section (rule bodies inlined), `.gitignore`, `.gemini/.env` block |
| proposed | `.claude/settings.json` additions | none | none |

The instructions-file section comes from one template, `templates/instructions-section.md`, with a `host` context (`display`, `instructions_file`, `skill_prefix`, `rules_sentence`). On Codex and Gemini the enforced rule bodies (manuscript, and pipeline when enabled) are rendered inside the section between the ploma markers, because neither host auto-loads a rules directory. Doctor checks the section's size against the 32 KiB cap on Codex (WARN at 28 KiB).

Promoted learnings on Codex and Gemini: `/ploma:learn --promote` writes them into the same instructions file between a second marker pair, `<!-- ploma-learnings:begin -->` and `<!-- ploma-learnings:end -->`, placed right after the onboard section's end marker. Onboard never touches that span (its merge replaces only its own span), so R103 holds. `project_files.py record` accepts the host's `learnings_target`, and the receipt records the instructions file as `merged` as it does today; merged files are re-merged on every run and never counted as hand-edited. On Claude the target stays `.claude/rules/ploma-learnings.md`.

Enforced rule bodies inlined in the section are checked for drift the same way as rule files: doctor re-renders the section from `ploma.yaml` and compares it with the span on disk (WARN `drift:<file>` with the diff excerpt), so a config change without a re-onboard is reported on every host.

The receipt gains `"host": "<name>"`. That field is what "onboarded for" means. An absorption run on a different host than the receipt's is the switch case:

1. Onboard says: "This repo is onboarded for Claude Code. You are running Codex. Onboard will write the Codex files and leave the Claude Code files in place (<list from host.py files>)."
2. It proceeds as a normal run for the new host. The receipt's `host` becomes the new host; the receipt's file list is replaced by the new host's files, so the old host's files are no longer ploma-owned (doctor stops checking them for drift and lists them as INFO).
3. Nothing is deleted or moved.

Host-specific extras in the flow: on Codex, after writing, onboard prints "Codex runs plugin hooks only after you trust them: open /hooks in the Codex TUI and enable ploma's hooks, then restart the session" (doctor cannot check trust). On every host, onboard creates or refreshes the `.ploma/plugin` link from `CLAUDE_PLUGIN_ROOT` in its own environment (the bootstrap line supplies it when the hook has not run) and records the host in `.ploma/host.json` when the hook has not written it. Co-authors on Codex or Gemini run onboard once on their machine; it is an absorption run that creates the link and writes nothing the repo already has.

Legacy-harness detection (base §8 1b) stays Claude-centric and unchanged.

## 12. Doctor (delta to base §9)

New group `host`, before `project-files`:

- PASS `host_match`: "running under Codex; repo onboarded for Codex".
- FAIL `host_mismatch` when the receipt's host differs from the detected one: "repo is onboarded for Claude Code; you are running Codex: run $ploma:onboard". This is the first finding and the verdict is NOT_READY.
- INFO `other_host_files` listing another host's ploma files found by `host.py files` (left in place).
- WARN `root_export_missing` (Codex, Gemini) when the export block is absent; WARN `root_export_manual` when onboard withheld the block (§7); WARN `plugin_link` when `.ploma/plugin` is missing or dangling.
- INFO `host_unknown` when detection gives `unknown`; the rest of doctor runs with Claude's paths.

The `project-files` group checks the active host's files: instructions-file section present (by marker, in the host's file), enforced files match (rules on Claude; agents on Codex and Gemini), receipt present. `claude_md` findings are renamed `instructions_section`.

## 13. Gemini extension files

`gemini-extension.json`: `name` ploma, `version` equal to `plugin.json` (test), `description`, `settings` for `OPENALEX_API_KEY` (sensitive), `SEMANTIC_SCHOLAR_API_KEY` (sensitive) and `CROSSREF_MAILTO`, each with `envVar` equal to its name so the scripts' existing environment fallbacks pick them up. No `contextFileName`, no `mcpServers`, no `excludeTools`. No `GEMINI.md` in the extension root: the session hook delivers context, and a second channel would duplicate it.

`commands/ploma/*.toml`: §10. `hooks/hooks.json`: §8. `skills/`: shared.

## 14. Codex specifics

- Install: `codex plugin marketplace add marcgarnica13/ploma` then `codex plugin add ploma@ploma`. The marketplace entry's `source: "./"` is verified in the first task against a local checkout; if Codex rejects a root source, the entry gains a second form Codex accepts and the test pins both.
- Hooks trust: README and onboard say it; `codex exec` field tests pass `--dangerously-bypass-hook-trust`.
- API keys: environment variables (`OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`, `CROSSREF_MAILTO`), which the scripts already read when the Claude option variables are absent. README documents a `~/.codex/config.toml` `shell_environment_policy` example for users who want them per machine. ploma never writes secrets into project files.
- `.codex/config.toml` is read only for trusted projects; onboard says so once.

## 15. Scripts, tests, field tests

- `tests/test_host.py`: detection order with the leaked-Claude case; facts table completeness (every host has every fact); `files` listing on fixtures for each host.
- `tests/test_host_adapters.py`: TOML agent rendering (escaping, required keys, parses with `tomllib` on 3.11+ and with a minimal line parser on 3.10); Gemini agent frontmatter and tool map; command generation up to date for all 23 skills; `build-check` passes.
- `tests/test_project_files.py`: `render_all` per host gives exactly the table in §11; the switch case rewrites the receipt and touches no old-host file; the withheld-block case.
- `tests/test_doctor.py`: `host_mismatch` is first and gives NOT_READY; `other_host_files` INFO; `root_export_*` cases.
- `tests/test_hooks.py`, `tests/test_session_context.py`: `classify_tool` for every name in §8; `host.json` written before the early exit; host block present for Codex and Gemini and absent for Claude; root-drift line; AfterTool and AfterAgent payloads drive the same reminders as PostToolUse and Stop.
- `tests/test_manifest.py`: three manifests, equal versions, `agents` path in `plugin.json`, every skill has a command.
- `tests/test_skills.py`: bootstrap line present in every skill.
- CI unchanged (pytest 3.10 and 3.12). `claude plugin validate .` locally.
- Field tests, documented in README under Testing: Claude Code as today; Codex with an isolated `CODEX_HOME`, a local marketplace add, and `codex exec -C <paper> --skip-git-repo-check --dangerously-bypass-hook-trust '$ploma:doctor'`; Gemini with `gemini extensions link <checkout>` and `gemini -p "/ploma:doctor" -e ploma`. The Codex field test runs in this milestone on the traces paper through the peer session; the Gemini one is written down and not run.

## 16. Docs and release

- README: "Install" becomes three blocks (Claude Code, Codex, Gemini CLI); a "Switching hosts" section; Testing per host; the status line says 0.2.0.
- `skills/help/SKILL.md`: the same three install blocks and the switch rule.
- CHANGELOG 0.2.0: multi-host, the moved agents directory, the one-file hooks, the per-host project files, the Gemini caveat.
- `plugin.json` description: "A harness for writing, validating, reviewing and formatting LaTeX academic papers with a coding agent (Claude Code, Codex, Gemini CLI)".
- Base spec §4, §8, §9, §10, §11 get a one-line pointer to this document.

## 17. Risks and unverified items

1. Claude Code runtime with `${CLAUDE_PLUGIN_ROOT:-${extensionPath}}` in hook commands: validator accepts it; one headless run in the first task confirms the hooks still fire. Fallback: keep `${CLAUDE_PLUGIN_ROOT}` in the command and set `CLAUDE_PLUGIN_ROOT=${extensionPath}` as an inline environment prefix instead.
2. Gemini: whether the extension `hooks/hooks.json` with Claude event names present is accepted (unknown events are presumably ignored, as on Codex), whether the `.env` block reaches the shell tool, whether extension-level `settings` reach hook and shell processes, whether the shell runs from the repo root (the relative link depends on it), and whether the activate_skill name for an extension skill is `<name>` or namespaced. All are items of the manual Gemini field test; none changes the code shape.
3. Codex marketplace `source: "./"`: verified in the first task.
4. Codex plugin root changes per version: the next session start refreshes the link; a session whose hooks are untrusted falls back to the bootstrap prefix.
5. The 32 KiB `AGENTS.md` cap with inlined rules: doctor warns at 28 KiB; the manuscript rule is well under 4 KiB today.
6. Hook timeouts rely on host defaults (§8); a hung Python on a slow disk would stall a tool call for up to the host default. The hooks are fail-open and read only small state files.

## 18. Decisions taken in this design (my calls, open to correction)

1. One `hooks/hooks.json` for three hosts rather than per-host files, because Claude and Codex read the same path and Gemini's path is fixed.
2. Agent sources move to `hosts/claude/agents/`; generated Codex and Gemini agents are project files written by onboard, not plugin files, because Codex cannot ship agents and Gemini would load Claude's format.
3. Enforced rules are inlined into the Codex and Gemini instructions sections rather than written to a rules directory those hosts do not auto-load.
4. `$ARGUMENTS`, `/ploma:` references and `allowed-tools` stay in the skills; the host block explains the two differences once. No per-host skill text.
5. Switching hosts is report-and-write, never delete (Marc, 2026-10-29).
6. `unknown` host behaves like Claude Code in rendering and never blocks.
7. Gemini commands are generated and committed, with a staleness test, instead of hand-written.
8. The receipt's `host` field defines "onboarded for"; file presence alone does not.
9. The Gemini extension ships no `GEMINI.md` and no MCP servers.
10. Version 0.2.0; `consistency` becoming required is still the 0.1.1 item and is not bundled here.
11. From the builder check (2026-10-29): project files hold only the relative `.ploma/plugin` path, refreshed by the session hook; `host.json` and the link are written only in repos with `ploma.yaml`; hook `timeout` fields are dropped; promoted learnings get a second marker pair on Codex and Gemini; the Gemini `.env` block goes into an existing repo `.env` rather than shadowing it; `CODEX_HOME` is not a host signal; doctor re-renders the inlined rules for drift; superpowers detection is per host and stays a WARN; the bootstrap line says prefix, not export.

## 19. What is left to the builder

- Exact wording of the host blocks, the bootstrap line placement in skills that start with an `Arguments:` line, and the switch messages.
- The TOML writer for `.codex/config.toml` merging (marker-delimited text merge, like `CLAUDE.md`).
- The 3.10-compatible TOML read used only by tests.
- The exact set of doctor messages and their remediation lines.
- README wording for the three install blocks.
