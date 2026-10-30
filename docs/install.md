# Install

How to install and update ploma on Claude Code or Codex, and where API keys go. To move a repo between hosts, see [hosts.md](hosts.md).

## Claude Code

The same commands work on both machines (the development machine and the paper machine). On a machine without SSH keys for GitHub, set up HTTPS first, in the shell that starts Claude Code:

```
gh auth login && gh auth setup-git          # HTTPS credentials for git
export CLAUDE_CODE_PLUGIN_PREFER_HTTPS=1    # clone over HTTPS, skip the SSH probe
```

Then, inside Claude Code:

```
/plugin marketplace add marcgarnica13/ploma
/plugin install ploma@ploma
/ploma:onboard
```

## Codex

Install from the same repo:

```
codex plugin marketplace add marcgarnica13/ploma
codex plugin add ploma@ploma
```

Then open `/hooks` in the Codex TUI and trust ploma's hooks, and run `$ploma:onboard`. Skills are typed `$ploma:<name>`. Codex reads `.codex/config.toml` only for trusted projects, so trust the paper repo.

## Updates

Updates: `/plugin marketplace update ploma`, then `/reload-plugins`.

Updates: `codex plugin marketplace upgrade ploma`, then `codex plugin add ploma@ploma` again, then start a new session so the hook refreshes `.ploma/plugin`.

## API keys

API keys on Codex come from environment variables: `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` and `CROSSREF_MAILTO`. The scripts read them when the Claude Code plugin options are absent. ploma never writes secrets into project files. For per-machine keys, set them in `~/.codex/config.toml`:

    # ~/.codex/config.toml
    [shell_environment_policy]
    set = { OPENALEX_API_KEY = "...", SEMANTIC_SCHOLAR_API_KEY = "...", CROSSREF_MAILTO = "you@example.org" }
