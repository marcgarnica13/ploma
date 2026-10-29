# Claude Code plugin packaging facts (official docs, checked 2026-10-29)

**Note:** One fetched page contained an embedded instruction to enter plan mode and write a plan file. I ignored it and wrote nothing.

Sources are the official Claude Code docs (code.claude.com). Where I say "not documented," I checked the pages and found nothing. The hooks and eval pages came back truncated in places, and I say so where it matters.

## 1. Plugin layout, manifests, and install

Documented layout ([manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference.md), [components](https://code.claude.com/docs/en/plugins/components.md)):

```text
paper-harness/                      # repo root
├── .claude-plugin/
│   ├── plugin.json                 # plugin manifest
│   └── marketplace.json            # catalog, only for distribution
├── skills/<name>/SKILL.md
├── agents/<name>.md
├── hooks/hooks.json
├── bin/                            # optional; added to Bash PATH
├── settings.json                   # only `agent` and `subagentStatusLine` take effect
├── .mcp.json
└── (rules/ and a root CLAUDE.md are NOT loaded; see Q2)
```

**plugin.json.** Only `name` is required. It must be kebab-case with no spaces, `@`, or `:`. Names starting with `claude-`, `anthropic-`, `anthropics-`, or `cc-plugin-` fail validation, so avoid that prefix. Other fields:
- `version`: a free-form string, not checked against semver. It pins users to that version until you change it.
- `description`, `author` (`name` required; `email`, `url` optional), `homepage`, `repository`, `license`, `keywords`.
- `skills`: adds directories to the default `skills/` scan.
- `commands`, `agents`, `outputStyles`: these replace their default folder scans.
- `hooks`, `mcpServers`, `lspServers`: these merge with the default files.
- `userConfig`, `dependencies`, `defaultEnabled`, `settings`, `experimental.evals`.

Component paths must start with `./`.

**marketplace.json** ([create a marketplace](https://code.claude.com/docs/en/plugins/create-marketplace.md), [marketplace reference](https://code.claude.com/docs/en/plugins/marketplace-reference.md)). Required top-level keys are `name`, `owner` (`{ "name": ... }`), and `plugins` (array of `{ name, source, description }`). The docs show plugins in a subfolder with `"source": "./plugins/<name>"`. They also say a plugin can sit at the marketplace root, but I did not find an explicit `"./"` example. Validate it before you rely on it:

```json
{
  "name": "marcgarnica13-academic",
  "owner": { "name": "Marc Garnica Caparros" },
  "plugins": [
    { "name": "paper-harness", "source": "./", "description": "Academic paper-writing harness" }
  ]
}
```

Run `claude plugin validate .` on the repo to check it.

**Install commands** ([install](https://code.claude.com/docs/en/plugins/install.md)):
```text
/plugin marketplace add marcgarnica13/paper-harness     # shell: claude plugin marketplace add ...
/plugin install paper-harness@marcgarnica13-academic    # the @ part is the marketplace's "name", not the repo name
```
The entry `name` must match the manifest `name`, or install fails.

**Private repo: yes, with conditions.** Claude Code runs `git` on the user's machine with prompts disabled and has no token of its own. `marketplace.json` has no credential field. Access therefore follows the user's git setup:
- HTTPS: `gh auth login` followed by `gh auth setup-git`.
- SSH: a key that works without a passphrase, loaded in `ssh-agent`.
- `owner/repo` shorthand probes SSH first. Set `CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1` to skip the probe.
- Background auto-update uses stored credentials and never prompts. Setting `GITHUB_TOKEN` alone does not authenticate it.
- Users without access to the repo cannot install a plugin whose source is that private repo.

## 2. rules/ and always-on guidance

- **`rules/` is not a documented plugin component.** It is absent from the standard layout. Plugin `CLAUDE.md` files are not loaded, and `claude plugin validate` warns about them. A plugin cannot auto-load path-scoped rules the way `.claude/rules/` works in a project.
- **Options that are documented:**
  - **SessionStart hook** with `hookSpecificOutput.additionalContext`. This is always-on: it injects text at the start of every session. Each string is capped at 10,000 characters.
  - **Skill with `paths:`** globs. It loads when Claude works on matching files, but it is description-driven, not guaranteed.
  - **Skill with `user-invocable: false`.** This hides it from the `/` menu, but Claude can still load it by description. It is not always-on.
- **Recommended for your case:** have the onboard skill copy the rules into the project's `.claude/rules/` (committed to the repo, scoped the way your own rules are) and add a short pointer section to the project CLAUDE.md. Avoid `@${CLAUDE_PLUGIN_ROOT}/...` imports in CLAUDE.md. The cache path changes with each version, and imports from outside the working directory trigger an approval dialog ([memory](https://code.claude.com/docs/en/memory.md)).

## 3. Hooks

- **File:** `hooks/hooks.json` with a top-level `"hooks"` key. Structure is event → matcher group → handler list. Handler types: `command`, `http`, `mcp_tool`, `prompt`, `agent`.
- **Variables:** `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${CLAUDE_PROJECT_DIR}`. Quote the root path in shell-form commands, or use exec form with `args`.
- **Events** (from the [hooks reference](https://code.claude.com/docs/en/hooks.md)): SessionStart, Setup, UserPromptSubmit, UserPromptExpansion, PreToolUse, PermissionRequest, PermissionDenied, PostToolUse, PostToolUseFailure, PostToolBatch, Notification, MessageDisplay, SubagentStart, SubagentStop, TaskCreated, TaskCompleted, Stop, StopFailure, TeammateIdle, InstructionsLoaded, ConfigChange, CwdChanged, DirectoryAdded, FileChanged, WorktreeCreate, WorktreeRemove, PreCompact, PostCompact, PreModelSwitch, PostModelSwitch, Elicitation, ElicitationResult, SessionEnd.
- **PreCompact** fires before compaction, with matcher `manual` or `auto`. Exit code 2 blocks it. I read this from a truncated page, so verify the decision format.
- **Notification** exists. It has no decision control.
- **Context injection:** yes.
  - SessionStart: `hookSpecificOutput.additionalContext`, with `hookEventName` set to `"SessionStart"`. Plain stdout is also added as context.
  - UserPromptSubmit: `additionalContext` is injected alongside the prompt. I could not confirm the exact JSON shape because that section was truncated.
  - Output must be only the JSON object on stdout.
- Plugin hooks fire whenever the plugin is enabled, not only when one of its skills runs.

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/scripts/session-context.sh" } ] }
    ]
  }
}
```
The script prints `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`.

## 4. Skill frontmatter and namespacing

From the [skills reference](https://code.claude.com/docs/en/skills.md): `name`, `description` (recommended), `when_to_use`, `argument-hint`, `arguments`, `disable-model-invocation` (default false; `true` means only the user can invoke), `user-invocable` (default true; `false` hides it from the menu), `allowed-tools`, `disallowed-tools`, `model`, `effort`, `context` (`fork`), `agent`, `background`, `hooks`, `paths`, `shell`, `metadata`, `license`, `compatibility`.

Plugin skills are namespaced as `/<plugin>:<skill>`. A `name` in the frontmatter replaces the last segment. The bare `/<skill>` form also works unless it collides with another command.

## 5. Agent frontmatter in plugins

From the [subagents reference](https://code.claude.com/docs/en/sub-agents.md): `name` and `description` are required. Also available: `tools`, `disallowedTools`, `model` (`sonnet`, `opus`, `haiku`, `fable`, a full ID, or `inherit`), `permissionMode`, `maxTurns`, `skills`, `mcpServers`, `hooks`, `memory`, `background`, `isolation` (`worktree`), `color`, `effort`, `initialPrompt`, `omitClaudeMd`, `autoCompactWindow`, `experimental`.

**Restriction:** `permissionMode`, `hooks`, and `mcpServers` are ignored for plugin agents. The components page also lists `initialPrompt` as ignored. Agent names cannot contain `:`, and the plugin scopes them as `<plugin>:<name>`.

Workaround: ship hooks in `hooks/hooks.json` and MCP servers in `.mcp.json`. If you need `permissionMode` on an agent, the onboard skill can copy that agent into the project's `.claude/agents/`. Make sure that trade-off is acceptable first.

## 6. Writing files into the user's project

- **Documented:** plugin skill content can reference `${CLAUDE_PROJECT_DIR}`. Nothing I found restricts a plugin skill from writing project files. Writes go through the normal permission system, so Write and Edit prompt unless allowed.
- **Plugin `settings.json` cannot grant permissions.** Only `agent` and `subagentStatusLine` take effect. So the onboard skill has to write `.claude/settings.local.json` itself. Whether Claude Code treats that file specially is not documented.
- **CLAUDE.md is context, not enforcement.** Use a PreToolUse hook for hard rules, as the memory page recommends.
- **Project-scope plugins** (declared in a repo's `.claude/settings.json`) load only after the folder trust check. Monitors don't load from project scope ([loading](https://code.claude.com/docs/en/plugins/loading.md)).
- **Eval runs** deny Write and Edit unless you pass `--allow-tools`.
- **Design advice:** make the onboard skill idempotent, show a diff, and ask before overwriting. Set `disable-model-invocation: true` so Claude never runs it on its own.

## 7. Versioning, updates, and testing

**Updates.** The docs do not describe a `/plugin update` command. The documented forms are:
- `/plugin` → Installed → Update now.
- `claude plugin update <plugin>@<marketplace>` in the shell.
- `/plugin marketplace update <name>` refreshes the listing and updates that marketplace's plugins.
- `claude plugin marketplace update` with no name refreshes listings only.

Auto-update is off by default for third-party marketplaces. Turn it on under `/plugin` → Marketplaces, or an admin can set `autoUpdate` in managed settings. The running session keeps its old version until `/reload-plugins` or a restart.

**Versioning** ([host a marketplace](https://code.claude.com/docs/en/plugins/host-marketplace.md)):
- Users get a new copy only when the computed version changes. Pushing commits without a version change does nothing for users.
- Option A: set `version` in `plugin.json` and bump it on every release. Do not set it in both `plugin.json` and the marketplace entry. If you do, `plugin.json` wins and validation warns.
- Option B: omit `version` entirely. The commit SHA then serves as the version.
- Semver is a convention. It is not enforced.

**Testing with `claude plugin eval`** ([plugin evals](https://code.claude.com/docs/en/plugin-evals.md)):
- Requires Claude Code v2.1.269 or later.
- `claude plugin eval init` runs an interview that writes cases. `claude plugin eval init --bare <name>` writes a blank template, which is the CI path.
- Layout: `evals/<case>/prompt.md` plus `evals/<case>/graders/<name>.md`.
- Graders: `regex`, `tool_used`, `tool_order`, `file_exists`, `llm`, `baseline`.
- Each case runs with and without the plugin. The report shows the delta.
- Each run is a real, billed model call.
- CI command, from the docs:
  ```bash
  claude plugin eval . --trust-plugin --json results.json --threshold 0.8 \
    --model <pinned-model> --judge-model <pinned-judge> --no-publish --max-cost-usd 20
  ```
- Exit codes: 0 pass, 1 failure or threshold miss, 2 partial (cost ceiling or rejected credential), 130 interrupted, 143 terminated.

**`/skill-doctor`.** I could not find it on any public docs page I fetched, and it does not appear in this session's skill list. Your build's `/` menu is the authority. The embedded reference describes it as a skill usage and context-cost report, so I'd treat it as unverified until you see it in your build.

For manifest checks in CI, use `claude plugin validate . --strict`.

## 8. Official examples

- [anthropics/skills](https://github.com/anthropics/skills): install with `/plugin marketplace add anthropics/skills`. It has the document skills (`docx`, `pdf`, `pptx`, `xlsx`), an Agent Skills `spec/`, and a `template/` skill. I found no academic or research skills there.
- [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official/tree/main/plugins): the closest structural examples are `plugin-dev` (plugin authoring), `skill-creator`, and `claude-md-management` (CLAUDE.md auditing). `math-proof` and `math-olympiad` are the nearest research-flavored plugins by name. I did not read their contents. I found no academic-writing plugin in the listing.
