## ploma host: Codex

- Skills are typed `$ploma:<name>`. ploma text writes `/ploma:<name>`; on Codex that means `$ploma:<name>`.
- Codex does not substitute `$ARGUMENTS`. The arguments are the text after the skill name in the user's message.
- A subagent named `ploma:<agent>` in skill text is spawned with `spawn_agent`, `agent_type: ploma-<agent>` and `fork_turns: "none"`. The roles live in `.codex/agents/`.
- The plugin root is `.ploma/plugin`, relative to the repo root. `.codex/config.toml` exports it to the shell as `CLAUDE_PLUGIN_ROOT`.
- Plugin hooks run only once the user trusts them via `/hooks`.
- `$ploma:doctor` reports `host_mismatch` when this repo is onboarded for another host; then run `$ploma:onboard`.
